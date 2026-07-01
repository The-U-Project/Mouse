/// Mouse — C++ Result Combiner (implementation)

#include "result_combiner.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace mouse {

// ─────────────────────────────────────────────────────────────────
// Backend name
// ─────────────────────────────────────────────────────────────────

const char* backend_name(Backend b) noexcept {
    switch (b) {
        case Backend::CPU_CXX:   return "C++";
        case Backend::CPU_ASM:   return "ASM";
        case Backend::GPU_CUDA:  return "CUDA";
        case Backend::GPU_METAL: return "Metal";
        default:                 return "Unknown";
    }
}

// ─────────────────────────────────────────────────────────────────
// Combine all results
// ─────────────────────────────────────────────────────────────────

CombinedResult ResultCombiner::combine(
    const std::vector<BackendResult>& results
) const {
    if (results.empty()) return {};

    // Filter to valid results only
    std::vector<BackendResult> valid_results;
    for (const auto& r : results) {
        if (r.valid) valid_results.push_back(r);
    }

    if (valid_results.empty()) return {};

    if (valid_results.size() == 1) {
        const auto& r = valid_results[0];
        CombinedResult cr;
        cr.cursor_x        = r.cursor_x;
        cr.cursor_y        = r.cursor_y;
        cr.confidence      = r.confidence;
        cr.backends_used   = 1;
        cr.total_latency_ms = r.latency_ms;
        cr.valid           = r.valid;
        cr.regions         = r.regions;
        return cr;
    }

    switch (m_strategy) {
        case FusionStrategy::BEST_CONFIDENCE: return combine_best_confidence(valid_results);
        case FusionStrategy::WEIGHTED_AVERAGE: return combine_weighted_avg(valid_results);
        case FusionStrategy::MAJORITY_VOTE:   return combine_majority_vote(valid_results);
        case FusionStrategy::FASTEST:         return combine_fastest(valid_results);
    }
    return {};
}

CombinedResult ResultCombiner::combine_two(
    const BackendResult& a,
    const BackendResult& b
) const {
    return combine({a, b});
}

// ─────────────────────────────────────────────────────────────────
// Strategy implementations
// ─────────────────────────────────────────────────────────────────

CombinedResult ResultCombiner::combine_best_confidence(
    const std::vector<BackendResult>& results
) const {
    const auto* best = &results[0];
    for (const auto& r : results) {
        if (r.confidence > best->confidence) best = &r;
    }

    CombinedResult cr;
    cr.cursor_x         = best->cursor_x;
    cr.cursor_y         = best->cursor_y;
    cr.confidence       = best->confidence;
    cr.backends_used    = static_cast<int>(results.size());
    cr.valid            = true;
    cr.regions          = best->regions;

    for (const auto& r : results) {
        cr.total_latency_ms += r.latency_ms;
    }
    return cr;
}

CombinedResult ResultCombiner::combine_weighted_avg(
    const std::vector<BackendResult>& results
) const {
    double total_weight = 0.0;
    double sum_x = 0.0, sum_y = 0.0, sum_conf = 0.0;

    for (const auto& r : results) {
        double w = static_cast<double>(r.confidence);
        sum_x   += static_cast<double>(r.cursor_x) * w;
        sum_y   += static_cast<double>(r.cursor_y) * w;
        sum_conf += static_cast<double>(r.confidence) * w;
        total_weight += w;
    }

    CombinedResult cr;
    if (total_weight > 1e-10) {
        cr.cursor_x   = static_cast<int>(sum_x / total_weight);
        cr.cursor_y   = static_cast<int>(sum_y / total_weight);
        cr.confidence = static_cast<float>(sum_conf / total_weight);
    } else {
        // Equal-weighted fallback
        cr.cursor_x   = results[0].cursor_x;
        cr.cursor_y   = results[0].cursor_y;
        cr.confidence = results[0].confidence;
    }

    cr.backends_used = static_cast<int>(results.size());
    cr.valid         = true;

    // Merge regions from all backends (simple concatenation)
    for (const auto& r : results) {
        for (const auto& reg : r.regions) {
            cr.regions.push_back(reg);
        }
    }

    for (const auto& r : results) {
        cr.total_latency_ms += r.latency_ms;
    }
    return cr;
}

CombinedResult ResultCombiner::combine_majority_vote(
    const std::vector<BackendResult>& results
) const {
    // Group results that agree within tolerance
    // Simplified: cluster into groups by proximity, take largest group's centroid
    if (results.size() <= 2) {
        return combine_weighted_avg(results);
    }

    // Build clusters
    struct Cluster { double sum_x = 0, sum_y = 0; int count = 0; };
    std::vector<Cluster> clusters;
    std::vector<int> assigned(results.size(), -1);

    for (size_t i = 0; i < results.size(); ++i) {
        if (assigned[i] >= 0) continue;

        Cluster cl;
        for (size_t j = i; j < results.size(); ++j) {
            if (assigned[j] >= 0) continue;
            double dx = std::abs(static_cast<double>(results[i].cursor_x - results[j].cursor_x));
            double dy = std::abs(static_cast<double>(results[i].cursor_y - results[j].cursor_y));
            if (dx <= m_vote_tolerance && dy <= m_vote_tolerance) {
                cl.sum_x += results[j].cursor_x;
                cl.sum_y += results[j].cursor_y;
                cl.count++;
                assigned[j] = static_cast<int>(clusters.size());
            }
        }
        clusters.push_back(cl);
    }

    // Find largest cluster
    int best_idx = 0;
    for (size_t i = 1; i < clusters.size(); ++i) {
        if (clusters[i].count > clusters[best_idx].count) {
            best_idx = static_cast<int>(i);
        }
    }

    const auto& best_cl = clusters[best_idx];

    CombinedResult cr;
    cr.cursor_x      = static_cast<int>(best_cl.sum_x / best_cl.count);
    cr.cursor_y      = static_cast<int>(best_cl.sum_y / best_cl.count);
    cr.confidence    = static_cast<float>(best_cl.count) / static_cast<float>(results.size());
    cr.backends_used = static_cast<int>(results.size());
    cr.valid         = true;

    // Merge regions from the majority cluster's backends
    for (size_t i = 0; i < results.size(); ++i) {
        if (assigned[i] == best_idx) {
            for (const auto& reg : results[i].regions) {
                cr.regions.push_back(reg);
            }
        }
    }

    for (const auto& r : results) {
        cr.total_latency_ms += r.latency_ms;
    }
    return cr;
}

CombinedResult ResultCombiner::combine_fastest(
    const std::vector<BackendResult>& results
) const {
    const auto* fastest = &results[0];
    for (const auto& r : results) {
        if (r.latency_ms < fastest->latency_ms) fastest = &r;
    }

    CombinedResult cr;
    cr.cursor_x         = fastest->cursor_x;
    cr.cursor_y         = fastest->cursor_y;
    cr.confidence       = fastest->confidence;
    cr.backends_used    = 1;  // Only fastest is used
    cr.total_latency_ms = fastest->latency_ms;
    cr.valid            = fastest->valid;
    cr.regions          = fastest->regions;
    return cr;
}

// ─────────────────────────────────────────────────────────────────
// C-linkage exports
// ─────────────────────────────────────────────────────────────────

int mouse_combine_results(
    int x1, int y1, float conf1, int backend1, float lat1, int valid1,
    int x2, int y2, float conf2, int backend2, float lat2, int valid2,
    int strategy,
    int* out_x, int* out_y, float* out_conf, int* out_backends
) {
    if (!out_x || !out_y || !out_conf || !out_backends) return -1;

    BackendResult a;
    a.cursor_x   = x1;
    a.cursor_y   = y1;
    a.confidence = conf1;
    a.source     = static_cast<Backend>(static_cast<uint8_t>(backend1));
    a.latency_ms = lat1;
    a.valid      = (valid1 != 0);

    BackendResult b;
    b.cursor_x   = x2;
    b.cursor_y   = y2;
    b.confidence = conf2;
    b.source     = static_cast<Backend>(static_cast<uint8_t>(backend2));
    b.latency_ms = lat2;
    b.valid      = (valid2 != 0);

    ResultCombiner rc;
    rc.set_strategy(static_cast<FusionStrategy>(static_cast<uint8_t>(strategy)));

    CombinedResult cr = rc.combine({a, b});

    *out_x        = cr.cursor_x;
    *out_y        = cr.cursor_y;
    *out_conf     = cr.confidence;
    *out_backends = cr.backends_used;

    return cr.valid ? 0 : -1;
}

const char* mouse_backend_name(int backend) {
    return backend_name(static_cast<Backend>(static_cast<uint8_t>(backend)));
}

}  // namespace mouse
