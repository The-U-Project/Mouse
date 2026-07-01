/// Mouse — CUDA Vision Kernels
///
/// GPU-accelerated computer vision primitives for screen analysis.
/// These kernels offload heavy pixel processing from the CPU.
///
/// Target:  Nvidia 5000 series (sm_90 / Blackwell architecture)
/// Fallback: Pure C++ CPU implementation in display_analyzer.cpp
///
/// Compile with:  nvcc -arch=sm_90 -std=c++20 vision_kernels.cu -o vision_kernels.ptx

#pragma once

#include <cstdint>

namespace mouse {
namespace cuda {

/// Initialize CUDA context.  Must call once before any kernel.
/// Returns 0 on success, CUDA error code on failure.
int init();

/// Release CUDA resources.
void shutdown();

/// Check if CUDA is available.
bool is_available();

// ─────────────────────────────────────────────────────────────────
// RGB → Grayscale conversion (GPU)
// ─────────────────────────────────────────────────────────────────

/// Convert RGB image to grayscale on the GPU.
/// @param d_rgb    Device pointer to tightly-packed RGB data (3 × W × H bytes).
/// @param d_gray   Device pointer to output grayscale (W × H bytes).
/// @param width    Image width in pixels.
/// @param height   Image height in pixels.
/// @return 0 on success, CUDA error code on failure.
int rgb_to_gray_gpu(
    const uint8_t* d_rgb,
    uint8_t* d_gray,
    int width,
    int height
);

// ─────────────────────────────────────────────────────────────────
// Sobel edge detection (GPU)
// ─────────────────────────────────────────────────────────────────

/// Run Sobel edge detection on the GPU.
/// @param d_gray    Device pointer to grayscale input.
/// @param d_edges   Device pointer to output edge map.
/// @param width     Image width.
/// @param height    Image height.
/// @param low       Low threshold (0–255).
/// @param high      High threshold (0–255).
/// @return 0 on success.
int sobel_edges_gpu(
    const uint8_t* d_gray,
    uint8_t* d_edges,
    int width,
    int height,
    uint8_t low,
    uint8_t high
);

// ─────────────────────────────────────────────────────────────────
// Template matching (GPU)
// ─────────────────────────────────────────────────────────────────

/// GPU-accelerated normalized cross-correlation template matching.
/// @param d_source   Device pointer to source grayscale image.
/// @param src_w      Source width.
/// @param src_h      Source height.
/// @param d_tmpl     Device pointer to template grayscale image.
/// @param tmpl_w     Template width.
/// @param tmpl_h     Template height.
/// @param d_result   Device pointer to output match scores (src_w × src_h float array).
/// @return 0 on success.
int match_template_gpu(
    const uint8_t* d_source,
    int src_w,
    int src_h,
    const uint8_t* d_tmpl,
    int tmpl_w,
    int tmpl_h,
    float* d_result
);

}  // namespace cuda
}  // namespace mouse
