// Mouse — C++ Result Combiner
//
// Combines analysis results from multiple backends (C++ CPU, CUDA GPU,
// x86_64 ASM) into a unified output.  Provides weighted fusion, voting,
// and confidence merging strategies.
//
// The Python pipeline calls this via the C-linkage exports to get the
// combined "best" result from all acceleration backends.

#pragma once

#include <cstdint>
#include <vector>
#include <string>

namespace mouse {

// ─────────────────────────────────────────────────────────────────
// Backend identifiers
// ─────────────────────────────────────────────────────────────────

enum class Backend : uint8_t {
    CPU_CXX    = 0,   // Pure C++ (reference)
    CPU_ASM    = 1,   // x86_64 / ARMv8 assembly
    GPU_CUDA   = 2,   // Nvidia CUDA kernels
    GPU_METAL  = 3,   // Apple Metal (future)
    UNKNOWN    = 255,
};

const char* backend_name(Backend b) noexcept;

// ─────────────────────────────────────────────────────────────────
// Analysis result from a single backend
// ─────────────────────────────────────────────────────────────────

struct BackendResult {
    Backend     source     = Backend::UNKNOWN;
    int         cursor_x   = -1;
    int         cursor_y   = -1;
    float       confidence = 0.0f;
    float       latency_ms = 0.0f;   // Processing time for this backend
    bool        valid      = false;   // false = backend failed this frame

    // Detected regions (bounding boxes)
    struct Region {
        int    x = 0, y = 0, w = 0, h = 0;
        float  confidence = 0.0f;
        int    class_id   = 0;
    };
    std::vector<Region> regions;
};

// ─────────────────────────────────────────────────────────────────
// Fusion strategy
// ─────────────────────────────────────────────────────────────────

enum class FusionStrategy : uint8_t {
    /// Take the result with highest confidence.
    BEST_CONFIDENCE = 0,

    /// Weighted average of all valid results (weights by confidence).
    WEIGHTED_AVERAGE = 1,

    /// Majority vote: use the result agreed on by most backends
    /// (within a tolerance radius).
    MAJORITY_VOTE = 2,

    /// Always prefer the fastest backend (lowest latency).
    FASTEST = 3,
};

// ─────────────────────────────────────────────────────────────────
// Combined (fused) result
// ─────────────────────────────────────────────────────────────────

struct CombinedResult {
    int         cursor_x      = -1;
    int         cursor_y      = -1;
    float       confidence     = 0.0f;
    int         backends_used  = 0;       // How many backends contributed
    float       total_latency_ms = 0.0f;  // Summed latency
    bool        valid          = false;

    // Fused regions from all backends (deduplicated)
    std::vector<BackendResult::Region> regions;
};

// ─────────────────────────────────────────────────────────────────
// Result Combiner
// ─────────────────────────────────────────────────────────────────

class ResultCombiner {
public:
    ResultCombiner() = default;

    /// Set the fusion strategy.
    void set_strategy(FusionStrategy s) noexcept { m_strategy = s; }
    FusionStrategy strategy() const noexcept { return m_strategy; }

    /// Set the tolerance radius for MAJORITY_VOTE (pixels).
    void set_vote_tolerance(int pixels) noexcept { m_vote_tolerance = pixels; }

    /// Combine multiple backend results into one.
    CombinedResult combine(const std::vector<BackendResult>& results) const;

    /// Convenience: combine two results.
    CombinedResult combine_two(
        const BackendResult& a,
        const BackendResult& b
    ) const;

private:
    CombinedResult combine_best_confidence(const std::vector<BackendResult>& results) const;
    CombinedResult combine_weighted_avg(const std::vector<BackendResult>& results) const;
    CombinedResult combine_majority_vote(const std::vector<BackendResult>& results) const;
    CombinedResult combine_fastest(const std::vector<BackendResult>& results) const;

    FusionStrategy m_strategy = FusionStrategy::WEIGHTED_AVERAGE;
    int            m_vote_tolerance = 20;  // pixels
};

// ─────────────────────────────────────────────────────────────────
// C-linkage exports
// ─────────────────────────────────────────────────────────────────

extern "C" {

/// Combine two backend results (CPU + GPU, or CPU + ASM).
/// Returns 0 on success; writes combined x,y,confidence to out params.
[[gnu::visibility("default")]]
int mouse_combine_results(
    int x1, int y1, float conf1, int backend1, float lat1, int valid1,
    int x2, int y2, float conf2, int backend2, float lat2, int valid2,
    int strategy,
    int* out_x, int* out_y, float* out_conf, int* out_backends
);

/// Get the name of a backend (for logging).
[[gnu::visibility("default")]]
const char* mouse_backend_name(int backend);

}  // extern "C"

}  // namespace mouse
