// Mouse — C++ Port Reservation Engine
//
// Reserves and manages TCP ports for the "Method 1" screen streaming
// analysis pipeline.  Provides a thread-safe API that Python can call
// via ctypes / pybind11.
//
// Targets:  macOS (arm64 / Clang 22+)  +  Windows 10 Pro (x86-64 / MSVC)

#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <mutex>
#include <unordered_set>

namespace mouse {

// ─────────────────────────────────────────────────────────────────
// Port reservation result
// ─────────────────────────────────────────────────────────────────

struct PortReservation {
    int         port        = 0;       // 0 = invalid / failed
    bool        success     = false;
    std::string error_msg;
};

// ─────────────────────────────────────────────────────────────────
// Port Manager — singleton that tracks reserved ports
// ─────────────────────────────────────────────────────────────────

class PortManager {
public:
    /// Get the global singleton.
    static PortManager& instance() noexcept;

    /// Reserve a specific port.  Returns success=false if already in use.
    PortReservation reserve(int port);

    /// Reserve any available port in [low, high].
    PortReservation reserve_any(int low = 10000, int high = 65535);

    /// Release a port back to the pool.
    void release(int port);

    /// Check whether a port is currently reserved by us.
    bool is_reserved(int port) const noexcept;

    /// List all currently reserved ports.
    std::vector<int> reserved_ports() const;

    /// Release all ports (shutdown).
    void release_all();

private:
    PortManager() = default;
    ~PortManager();

    // Non-copyable, non-movable
    PortManager(const PortManager&) = delete;
    PortManager& operator=(const PortManager&) = delete;

    bool port_is_free(int port) const;

    mutable std::mutex               m_mutex;
    std::unordered_set<int>          m_reserved;
};

// ─────────────────────────────────────────────────────────────────
// C-linkage exports (for Python ctypes / pybind11)
// ─────────────────────────────────────────────────────────────────

extern "C" {

/// Reserve a stream port for screen analysis.
/// Returns 0 on failure, > 0 on success (the port number).
[[gnu::visibility("default")]]
int mouse_reserve_port(int preferred_port);

/// Release a reserved port.
/// Returns 0 on success, -1 if the port was not reserved.
[[gnu::visibility("default")]]
int mouse_release_port(int port);

/// Get the currently recommended stream port.
/// Returns the port number or 0 if none reserved.
[[gnu::visibility("default")]]
int mouse_get_stream_port();

/// Reserve a block of ports for the analysis pipeline.
/// Sets *out_count to the number successfully reserved.
/// Returns a heap-allocated array of port numbers (caller must free with mouse_free_ports).
[[gnu::visibility("default")]]
int* mouse_reserve_port_block(int count, int* out_count);

/// Free an array returned by mouse_reserve_port_block.
[[gnu::visibility("default")]]
void mouse_free_ports(int* ports);

}  // extern "C"

}  // namespace mouse
