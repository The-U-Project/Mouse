/// Mouse — C++ Display Data Analyzer (implementation)
///
/// Pure C++ implementation of CV primitives.  These serve as:
///   (a) CPU fallbacks when CUDA is unavailable
///   (b) Reference implementations for testing CUDA/ASM variants

#include "display_analyzer.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace mouse {

// ─────────────────────────────────────────────────────────────────
// DisplayAnalyzer
// ─────────────────────────────────────────────────────────────────

DisplayAnalyzer::DisplayAnalyzer()  = default;
DisplayAnalyzer::~DisplayAnalyzer() = default;

// ─────────────────────────────────────────────────────────────────
// RGB → Grayscale (ITU-R BT.601 coefficients)
// ─────────────────────────────────────────────────────────────────

GrayImage DisplayAnalyzer::rgb_to_gray(const RGBImage& rgb) const {
    GrayImage out;
    out.width  = rgb.width;
    out.height = rgb.height;
    out.stride = rgb.width;
    out.data.resize(static_cast<size_t>(rgb.width) * static_cast<size_t>(rgb.height));

    rgb_to_gray(rgb.data.data(), rgb.width, rgb.height, out.data.data());
    ++m_frame_count;
    return out;
}

void DisplayAnalyzer::rgb_to_gray(
    const uint8_t* rgb,
    int width,
    int height,
    uint8_t* gray_out
) const {
    const size_t pixel_count = static_cast<size_t>(width) * static_cast<size_t>(height);

    // ITU-R BT.601:  Y = 0.299*R + 0.587*G + 0.114*B
    // Integer approximation for speed:  Y = ( 77*R + 150*G + 29*B ) >> 8
    for (size_t i = 0; i < pixel_count; ++i) {
        const uint8_t r = rgb[i * 3 + 0];
        const uint8_t g = rgb[i * 3 + 1];
        const uint8_t b = rgb[i * 3 + 2];
        gray_out[i] = static_cast<uint8_t>(
            (static_cast<uint32_t>(r) * 77 +
             static_cast<uint32_t>(g) * 150 +
             static_cast<uint32_t>(b) * 29) >> 8
        );
    }
}

// ─────────────────────────────────────────────────────────────────
// Simplified Canny edge detection (Sobel + threshold)
// ─────────────────────────────────────────────────────────────────

GrayImage DisplayAnalyzer::detect_edges(
    const GrayImage& src,
    uint8_t low,
    uint8_t high
) const {
    if (!src.valid()) return {};

    GrayImage out;
    out.width  = src.width;
    out.height = src.height;
    out.stride = src.width;
    out.data.resize(static_cast<size_t>(src.width) * static_cast<size_t>(src.height), 0);

    const int w = src.width;
    const int h = src.height;

    // 3×3 Sobel kernels
    // Gx = [-1 0 +1; -2 0 +2; -1 0 +1]
    // Gy = [-1 -2 -1; 0 0 0; +1 +2 +1]
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // clang-format off
            int gx = -1 * src.data[(y-1)*w + (x-1)] + 1 * src.data[(y-1)*w + (x+1)]
                     -2 * src.data[ y   *w + (x-1)] + 2 * src.data[ y   *w + (x+1)]
                     -1 * src.data[(y+1)*w + (x-1)] + 1 * src.data[(y+1)*w + (x+1)];

            int gy = -1 * src.data[(y-1)*w + (x-1)] - 2 * src.data[(y-1)*w + x] - 1 * src.data[(y-1)*w + (x+1)]
                     +1 * src.data[(y+1)*w + (x-1)] + 2 * src.data[(y+1)*w + x] + 1 * src.data[(y+1)*w + (x+1)];
            // clang-format on

            int mag = static_cast<int>(std::sqrt(static_cast<double>(gx * gx + gy * gy)));

            if (mag > high) {
                out.data[y * w + x] = 255;  // Strong edge
            } else if (mag > low) {
                out.data[y * w + x] = 128;  // Weak edge (simplified — no hysteresis)
            }
        }
    }

    ++m_frame_count;
    return out;
}

// ─────────────────────────────────────────────────────────────────
// Contour extraction (flood-fill → bounding boxes)
// ─────────────────────────────────────────────────────────────────

std::vector<BoundingBox> DisplayAnalyzer::extract_contours(
    const GrayImage& edge_map,
    int min_area
) const {
    std::vector<BoundingBox> results;
    if (!edge_map.valid()) return results;

    const int w = edge_map.width;
    const int h = edge_map.height;

    // Simple approach: scan for edge pixels, flood-fill to find
    // connected components, compute bounding boxes.
    std::vector<uint8_t> visited(edge_map.data.size(), 0);

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            const size_t idx = static_cast<size_t>(y) * static_cast<size_t>(w) + static_cast<size_t>(x);
            if (visited[idx] || edge_map.data[idx] == 0) continue;

            // Flood fill from (x, y)
            int min_x = x, max_x = x;
            int min_y = y, max_y = y;
            int area  = 0;

            // Stack-based flood fill
            struct Point { int px, py; };
            std::vector<Point> stack;
            stack.reserve(1024);
            stack.push_back({x, y});

            while (!stack.empty()) {
                auto [cx, cy] = stack.back();
                stack.pop_back();

                if (cx < 0 || cx >= w || cy < 0 || cy >= h) continue;
                const size_t cidx = static_cast<size_t>(cy) * static_cast<size_t>(w) + static_cast<size_t>(cx);
                if (visited[cidx] || edge_map.data[cidx] == 0) continue;

                visited[cidx] = 1;
                ++area;

                min_x = std::min(min_x, cx); max_x = std::max(max_x, cx);
                min_y = std::min(min_y, cy); max_y = std::max(max_y, cy);

                // 4-connected neighbors
                stack.push_back({cx - 1, cy});
                stack.push_back({cx + 1, cy});
                stack.push_back({cx, cy - 1});
                stack.push_back({cx, cy + 1});
            }

            if (area >= min_area) {
                results.push_back(BoundingBox{
                    min_x, min_y,
                    max_x - min_x + 1,
                    max_y - min_y + 1,
                    static_cast<float>(area) / 10000.0f,  // Rough confidence
                    0
                });
            }
        }
    }

    return results;
}

// ─────────────────────────────────────────────────────────────────
// Normalized cross-correlation template matching
// ─────────────────────────────────────────────────────────────────

MatchResult DisplayAnalyzer::match_template(
    const GrayImage& source,
    const GrayImage& tmpl,
    float threshold
) const {
    MatchResult best{0, 0, -1.0f};

    if (!source.valid() || !tmpl.valid()) return best;
    if (tmpl.width > source.width || tmpl.height > source.height) return best;

    const int sw = source.width;
    const int sh = source.height;
    const int tw = tmpl.width;
    const int th = tmpl.height;
    const int search_w = sw - tw + 1;
    const int search_h = sh - th + 1;

    // Pre-compute template mean
    double tmpl_mean = 0.0;
    for (int i = 0; i < tw * th; ++i) {
        tmpl_mean += tmpl.data[i];
    }
    tmpl_mean /= (tw * th);

    // Pre-compute template standard deviation denominator
    double tmpl_std_sum = 0.0;
    for (int i = 0; i < tw * th; ++i) {
        double d = tmpl.data[i] - tmpl_mean;
        tmpl_std_sum += d * d;
    }

    for (int y = 0; y < search_h; ++y) {
        for (int x = 0; x < search_w; ++x) {
            // Source window mean
            double src_mean = 0.0;
            for (int ty = 0; ty < th; ++ty) {
                for (int tx = 0; tx < tw; ++tx) {
                    src_mean += source.data[(y + ty) * sw + (x + tx)];
                }
            }
            src_mean /= (tw * th);

            // Cross-correlation
            double num = 0.0;
            double src_std_sum = 0.0;
            for (int ty = 0; ty < th; ++ty) {
                for (int tx = 0; tx < tw; ++tx) {
                    double sv = source.data[(y + ty) * sw + (x + tx)] - src_mean;
                    double tv = tmpl.data[ty * tw + tx] - tmpl_mean;
                    num += sv * tv;
                    src_std_sum += sv * sv;
                }
            }

            double denom = std::sqrt(src_std_sum * tmpl_std_sum);
            double score = (denom > 1e-10) ? (num / denom) : 0.0;

            if (score > best.score) {
                best.score = static_cast<float>(score);
                best.x = x;
                best.y = y;
            }
        }
    }

    if (best.score < threshold) {
        best.score = -1.0f;
    }

    return best;
}

// ─────────────────────────────────────────────────────────────────
// Region-of-interest extraction
// ─────────────────────────────────────────────────────────────────

GrayImage DisplayAnalyzer::extract_roi(
    const GrayImage& src, int x, int y, int w, int h
) const {
    GrayImage out;
    // Clamp
    x = std::max(0, std::min(x, src.width - 1));
    y = std::max(0, std::min(y, src.height - 1));
    w = std::max(1, std::min(w, src.width - x));
    h = std::max(1, std::min(h, src.height - y));

    out.width  = w;
    out.height = h;
    out.stride = w;
    out.data.resize(static_cast<size_t>(w) * static_cast<size_t>(h));

    for (int row = 0; row < h; ++row) {
        const uint8_t* src_row = src.data.data() + static_cast<size_t>(y + row) * src.width + x;
        uint8_t* dst_row = out.data.data() + static_cast<size_t>(row) * w;
        std::memcpy(dst_row, src_row, static_cast<size_t>(w));
    }

    return out;
}

RGBImage DisplayAnalyzer::extract_roi_rgb(
    const RGBImage& src, int x, int y, int w, int h
) const {
    RGBImage out;
    x = std::max(0, std::min(x, src.width - 1));
    y = std::max(0, std::min(y, src.height - 1));
    w = std::max(1, std::min(w, src.width - x));
    h = std::max(1, std::min(h, src.height - y));

    out.width  = w;
    out.height = h;
    out.data.resize(static_cast<size_t>(w) * static_cast<size_t>(h) * 3);

    for (int row = 0; row < h; ++row) {
        const uint8_t* src_row = src.data.data() + (static_cast<size_t>(y + row) * src.width + x) * 3;
        uint8_t* dst_row = out.data.data() + static_cast<size_t>(row) * w * 3;
        std::memcpy(dst_row, src_row, static_cast<size_t>(w) * 3);
    }

    return out;
}

// ─────────────────────────────────────────────────────────────────
// C-linkage exports
// ─────────────────────────────────────────────────────────────────

void* mouse_display_analyzer_create() {
    return new DisplayAnalyzer();
}

void mouse_display_analyzer_destroy(void* handle) {
    delete static_cast<DisplayAnalyzer*>(handle);
}

int mouse_rgb_to_gray(
    void* handle,
    const uint8_t* rgb_data,
    int width,
    int height,
    uint8_t* gray_out
) {
    if (!handle || !rgb_data || !gray_out) return -1;
    auto* da = static_cast<DisplayAnalyzer*>(handle);
    da->rgb_to_gray(rgb_data, width, height, gray_out);
    return 0;
}

int mouse_detect_edges(
    void* handle,
    const uint8_t* gray_data,
    int width,
    int height,
    uint8_t low_threshold,
    uint8_t high_threshold,
    uint8_t* edge_out
) {
    if (!handle || !gray_data || !edge_out) return -1;

    auto* da = static_cast<DisplayAnalyzer*>(handle);

    GrayImage src;
    src.width  = width;
    src.height = height;
    src.stride = width;
    src.data.assign(gray_data, gray_data + static_cast<size_t>(width) * height);

    GrayImage edges = da->detect_edges(src, low_threshold, high_threshold);
    if (!edges.valid()) return -1;

    std::memcpy(edge_out, edges.data.data(), edges.data.size());
    return 0;
}

float mouse_match_template(
    void* handle,
    const uint8_t* source_data,
    int src_w,
    int src_h,
    const uint8_t* tmpl_data,
    int tmpl_w,
    int tmpl_h,
    float threshold,
    int* out_x,
    int* out_y
) {
    if (!handle || !source_data || !tmpl_data || !out_x || !out_y) return -1.0f;

    auto* da = static_cast<DisplayAnalyzer*>(handle);

    GrayImage src;
    src.width  = src_w;
    src.height = src_h;
    src.stride = src_w;
    src.data.assign(source_data, source_data + static_cast<size_t>(src_w) * src_h);

    GrayImage tmpl;
    tmpl.width  = tmpl_w;
    tmpl.height = tmpl_h;
    tmpl.stride = tmpl_w;
    tmpl.data.assign(tmpl_data, tmpl_data + static_cast<size_t>(tmpl_w) * tmpl_h);

    auto result = da->match_template(src, tmpl, threshold);
    *out_x = result.x;
    *out_y = result.y;
    return result.score;
}

}  // namespace mouse
