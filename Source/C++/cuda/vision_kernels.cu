/// Mouse — CUDA Vision Kernels (implementation)
///
/// GPU kernels for screen analysis acceleration.
/// Compile with: nvcc -arch=sm_90 --std=c++20 -c vision_kernels.cu

#include "vision_kernels.h"

#include <cstdio>
#include <cuda_runtime.h>

namespace mouse {
namespace cuda {

// ─────────────────────────────────────────────────────────────────
// Error checking macro
// ─────────────────────────────────────────────────────────────────

#define CUDA_CHECK(call)                                                \
    do {                                                                \
        cudaError_t err = (call);                                       \
        if (err != cudaSuccess) {                                       \
            std::fprintf(stderr, "CUDA error at %s:%d: %s\n",          \
                        __FILE__, __LINE__, cudaGetErrorString(err));   \
            return static_cast<int>(err);                               \
        }                                                               \
    } while (0)

// ─────────────────────────────────────────────────────────────────
// Init / shutdown
// ─────────────────────────────────────────────────────────────────

int init() {
    int device_count = 0;
    cudaError_t err = cudaGetDeviceCount(&device_count);
    if (err != cudaSuccess || device_count == 0) {
        return static_cast<int>(cudaErrorNoDevice);
    }
    return 0;
}

void shutdown() {
    cudaDeviceReset();
}

bool is_available() {
    int count = 0;
    return cudaGetDeviceCount(&count) == cudaSuccess && count > 0;
}

// ─────────────────────────────────────────────────────────────────
// RGB → Grayscale kernel
// ─────────────────────────────────────────────────────────────────

__global__ void rgb_to_gray_kernel(
    const uint8_t* __restrict__ rgb,
    uint8_t* __restrict__ gray,
    int width,
    int height
) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x >= width || y >= height) return;

    int idx      = y * width + x;
    int rgb_idx  = idx * 3;

    // ITU-R BT.601: Y = 0.299R + 0.587G + 0.114B
    uint8_t r = rgb[rgb_idx + 0];
    uint8_t g = rgb[rgb_idx + 1];
    uint8_t b = rgb[rgb_idx + 2];

    // Integer approximation: (77R + 150G + 29B) >> 8
    gray[idx] = static_cast<uint8_t>(
        (static_cast<uint32_t>(r) * 77 +
         static_cast<uint32_t>(g) * 150 +
         static_cast<uint32_t>(b) * 29) >> 8
    );
}

int rgb_to_gray_gpu(
    const uint8_t* d_rgb,
    uint8_t* d_gray,
    int width,
    int height
) {
    dim3 block(16, 16);
    dim3 grid(
        (static_cast<unsigned int>(width)  + block.x - 1) / block.x,
        (static_cast<unsigned int>(height) + block.y - 1) / block.y
    );

    rgb_to_gray_kernel<<<grid, block>>>(d_rgb, d_gray, width, height);

    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) return static_cast<int>(err);

    return static_cast<int>(cudaDeviceSynchronize());
}

// ─────────────────────────────────────────────────────────────────
// Sobel edge detection kernel
// ─────────────────────────────────────────────────────────────────

__global__ void sobel_edges_kernel(
    const uint8_t* __restrict__ gray,
    uint8_t* __restrict__ edges,
    int width,
    int height,
    uint8_t low,
    uint8_t high
) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    // Skip border pixels
    if (x < 1 || x >= width - 1 || y < 1 || y >= height - 1) {
        if (x < width && y < height) {
            edges[y * width + x] = 0;
        }
        return;
    }

    int idx = y * width + x;

    // clang-format off
    // Sobel Gx
    int gx = -1 * gray[(y-1)*width + (x-1)] + 1 * gray[(y-1)*width + (x+1)]
             -2 * gray[ y   *width + (x-1)] + 2 * gray[ y   *width + (x+1)]
             -1 * gray[(y+1)*width + (x-1)] + 1 * gray[(y+1)*width + (x+1)];

    // Sobel Gy
    int gy = -1 * gray[(y-1)*width + (x-1)] - 2 * gray[(y-1)*width + x] - 1 * gray[(y-1)*width + (x+1)]
             +1 * gray[(y+1)*width + (x-1)] + 2 * gray[(y+1)*width + x] + 1 * gray[(y+1)*width + (x+1)];
    // clang-format on

    int mag = static_cast<int>(sqrtf(static_cast<float>(gx * gx + gy * gy)));

    if (mag > high) {
        edges[idx] = 255;
    } else if (mag > low) {
        edges[idx] = 128;
    } else {
        edges[idx] = 0;
    }
}

int sobel_edges_gpu(
    const uint8_t* d_gray,
    uint8_t* d_edges,
    int width,
    int height,
    uint8_t low,
    uint8_t high
) {
    dim3 block(16, 16);
    dim3 grid(
        (static_cast<unsigned int>(width)  + block.x - 1) / block.x,
        (static_cast<unsigned int>(height) + block.y - 1) / block.y
    );

    sobel_edges_kernel<<<grid, block>>>(d_gray, d_edges, width, height, low, high);

    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) return static_cast<int>(err);

    return static_cast<int>(cudaDeviceSynchronize());
}

// ─────────────────────────────────────────────────────────────────
// Template matching kernel (NCC)
// ─────────────────────────────────────────────────────────────────

__global__ void ncc_template_match_kernel(
    const uint8_t* __restrict__ source,
    int src_w,
    int src_h,
    const uint8_t* __restrict__ tmpl,
    int tmpl_w,
    int tmpl_h,
    float* __restrict__ result
) {
    int out_x = blockIdx.x * blockDim.x + threadIdx.x;
    int out_y = blockIdx.y * blockDim.y + threadIdx.y;

    int search_w = src_w - tmpl_w + 1;
    int search_h = src_h - tmpl_h + 1;

    if (out_x >= search_w || out_y >= search_h) return;

    // Compute mean of template (pre-computed in shared memory potentially)
    float tmpl_mean = 0.0f;
    for (int ty = 0; ty < tmpl_h; ++ty) {
        for (int tx = 0; tx < tmpl_w; ++tx) {
            tmpl_mean += tmpl[ty * tmpl_w + tx];
        }
    }
    tmpl_mean /= static_cast<float>(tmpl_w * tmpl_h);

    // Compute source window mean
    float src_mean = 0.0f;
    for (int ty = 0; ty < tmpl_h; ++ty) {
        for (int tx = 0; tx < tmpl_w; ++tx) {
            src_mean += source[(out_y + ty) * src_w + (out_x + tx)];
        }
    }
    src_mean /= static_cast<float>(tmpl_w * tmpl_h);

    // Cross-correlation
    float num = 0.0f;
    float src_std_sum = 0.0f;
    float tmpl_std_sum = 0.0f;

    for (int ty = 0; ty < tmpl_h; ++ty) {
        for (int tx = 0; tx < tmpl_w; ++tx) {
            float sv = static_cast<float>(source[(out_y + ty) * src_w + (out_x + tx)]) - src_mean;
            float tv = static_cast<float>(tmpl[ty * tmpl_w + tx]) - tmpl_mean;
            num += sv * tv;
            src_std_sum += sv * sv;
            tmpl_std_sum += tv * tv;
        }
    }

    float denom = sqrtf(src_std_sum * tmpl_std_sum);
    int out_idx = out_y * search_w + out_x;
    result[out_idx] = (denom > 1e-10f) ? (num / denom) : 0.0f;
}

int match_template_gpu(
    const uint8_t* d_source,
    int src_w,
    int src_h,
    const uint8_t* d_tmpl,
    int tmpl_w,
    int tmpl_h,
    float* d_result
) {
    int search_w = src_w - tmpl_w + 1;
    int search_h = src_h - tmpl_h + 1;

    if (search_w <= 0 || search_h <= 0) return -1;

    dim3 block(16, 16);
    dim3 grid(
        (static_cast<unsigned int>(search_w) + block.x - 1) / block.x,
        (static_cast<unsigned int>(search_h) + block.y - 1) / block.y
    );

    ncc_template_match_kernel<<<grid, block>>>(
        d_source, src_w, src_h,
        d_tmpl, tmpl_w, tmpl_h,
        d_result
    );

    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) return static_cast<int>(err);

    return static_cast<int>(cudaDeviceSynchronize());
}

}  // namespace cuda
}  // namespace mouse
