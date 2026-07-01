// Mouse — C++ Display Data Analyzer
//
// High-performance display analysis engine that processes raw screen
// pixel data.  Offloads heavy CV work from Python to native C++.
// Supports:
//   - Grayscale conversion (SIMD when available)
//   - Edge detection (Canny-style, simplified)
//   - Contour extraction
//   - Template matching (normalized cross-correlation)
//   - CUDA acceleration (when compiled with MOUSE_ENABLE_CUDA)
//
// Targets:  macOS (arm64) + Windows 10 Pro (x86-64)

#pragma once

#include <cstdint>
#include <vector>
#include <memory>
#include <string>

namespace mouse {

// ─────────────────────────────────────────────────────────────────
// Image types
// ─────────────────────────────────────────────────────────────────

/// 8-bit grayscale image.
struct GrayImage {
    int             width  = 0;
    int             height = 0;
    int             stride = 0;  // bytes per row (may be > width for alignment)
    std::vector<uint8_t> data;

    bool valid() const noexcept { return width > 0 && height > 0 && !data.empty(); }
};

/// 24-bit RGB image (tightly packed: R,G,B,R,G,B,...).
struct RGBImage {
    int             width  = 0;
    int             height = 0;
    std::vector<uint8_t> data;  // 3 × width × height bytes

    bool valid() const noexcept { return width > 0 && height > 0 && !data.empty(); }
    size_t pixel_count() const noexcept { return static_cast<size_t>(width) * static_cast<size_t>(height); }
};

// ─────────────────────────────────────────────────────────────────
// Detection results
// ─────────────────────────────────────────────────────────────────

/// Axis-aligned bounding box.
struct BoundingBox {
    int  x = 0, y = 0;
    int  w = 0, h = 0;
    float confidence = 0.0f;
    int  class_id = 0;
};

/// Template match result.
struct MatchResult {
    int  x = 0, y = 0;
    float score = 0.0f;
};

// ─────────────────────────────────────────────────────────────────
// Display Analyzer
// ─────────────────────────────────────────────────────────────────

class DisplayAnalyzer {
public:
    DisplayAnalyzer();
    ~DisplayAnalyzer();

    // ── Image conversion ─────────────────────────────────────

    /// Convert tightly-packed RGB → grayscale.
    GrayImage rgb_to_gray(const RGBImage& rgb) const;

    /// Convert RGB → grayscale in-place (overwrites data region of output).
    void rgb_to_gray(const uint8_t* rgb, int width, int height, uint8_t* gray_out) const;

    // ── Edge detection ────────────────────────────────────────

    /// Simplified Canny edge detection.
    /// Applies Sobel + thresholding to produce a binary edge map.
    GrayImage detect_edges(const GrayImage& src, uint8_t low = 50, uint8_t high = 150) const;

    // ── Contour extraction ────────────────────────────────────

    /// Extract bounding boxes of connected edge regions.
    /// Simple flood-fill-based contour finder (not full Suzuki-Abe).
    std::vector<BoundingBox> extract_contours(
        const GrayImage& edge_map,
        int min_area = 100
    ) const;

    // ── Template matching ─────────────────────────────────────

    /// Normalized cross-correlation template matching.
    /// Returns the best match location and score.
    MatchResult match_template(
        const GrayImage& source,
        const GrayImage& tmpl,
        float threshold = 0.5f
    ) const;

    // ── Region-of-interest extraction ─────────────────────────

    /// Extract a rectangular sub-region from a grayscale image.
    GrayImage extract_roi(const GrayImage& src, int x, int y, int w, int h) const;

    /// Extract a rectangular sub-region from an RGB image.
    RGBImage extract_roi_rgb(const RGBImage& src, int x, int y, int w, int h) const;

    // ── Performance ───────────────────────────────────────────

    /// Get the number of processed frames.
    uint64_t frame_count() const noexcept { return m_frame_count; }

    /// Reset the frame counter.
    void reset_counters() noexcept { m_frame_count = 0; }

private:
    uint64_t m_frame_count = 0;
};

// ─────────────────────────────────────────────────────────────────
// C-linkage exports (for Python ctypes)
// ─────────────────────────────────────────────────────────────────

extern "C" {

/// Create a DisplayAnalyzer instance.  Returns opaque handle.
[[gnu::visibility("default")]]
void* mouse_display_analyzer_create();

/// Destroy a DisplayAnalyzer instance.
[[gnu::visibility("default")]]
void mouse_display_analyzer_destroy(void* handle);

/// Convert tightly-packed RGB → grayscale.
/// gray_out must be pre-allocated with width*height bytes.
/// Returns 0 on success.
[[gnu::visibility("default")]]
int mouse_rgb_to_gray(
    void* handle,
    const uint8_t* rgb_data,
    int width,
    int height,
    uint8_t* gray_out
);

/// Detect edges in a grayscale image.
/// edge_out must be pre-allocated with width*height bytes.
/// Returns 0 on success.
[[gnu::visibility("default")]]
int mouse_detect_edges(
    void* handle,
    const uint8_t* gray_data,
    int width,
    int height,
    uint8_t low_threshold,
    uint8_t high_threshold,
    uint8_t* edge_out
);

/// Template matching.
/// Returns match score; sets *out_x, *out_y to match location.
[[gnu::visibility("default")]]
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
);

}  // extern "C"

}  // namespace mouse
