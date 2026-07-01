/// Mouse — C++ Port Reservation Engine (implementation)
///
/// Provides the actual port management logic.  On Windows this wraps
/// Winsock2; on macOS/Linux it wraps POSIX sockets to probe port
/// availability before reserving.

#include "port_reserver.h"

#include <algorithm>
#include <cstring>
#include <stdexcept>

#ifdef _WIN32
  #ifndef WIN32_LEAN_AND_MEAN
    #define WIN32_LEAN_AND_MEAN
  #endif
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
#else
  #include <unistd.h>
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
#endif

namespace mouse {

// ─────────────────────────────────────────────────────────────────
// RAII winsock initializer (Windows only)
// ─────────────────────────────────────────────────────────────────

#ifdef _WIN32
namespace {
    struct WinsockInit {
        WinsockInit() {
            WSADATA wsa;
            if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
                m_ok = false;
            } else {
                m_ok = true;
            }
        }
        ~WinsockInit() {
            if (m_ok) WSACleanup();
        }
        bool ok() const noexcept { return m_ok; }
    private:
        bool m_ok = false;
    };

    static WinsockInit s_winsock;
}  // anon
#endif

// ─────────────────────────────────────────────────────────────────
// PortManager — singleton
// ─────────────────────────────────────────────────────────────────

PortManager& PortManager::instance() noexcept {
    static PortManager mgr;
    return mgr;
}

PortManager::~PortManager() {
    release_all();
}

PortReservation PortManager::reserve(int port) {
    std::lock_guard<std::mutex> lock(m_mutex);

    if (m_reserved.contains(port)) {
        return PortReservation{0, false, "Port " + std::to_string(port) + " is already reserved by Mouse"};
    }

    if (!port_is_free(port)) {
        return PortReservation{0, false, "Port " + std::to_string(port) + " is in use by another process"};
    }

    m_reserved.insert(port);
    return PortReservation{port, true, ""};
}

PortReservation PortManager::reserve_any(int low, int high) {
    std::lock_guard<std::mutex> lock(m_mutex);

    // Clamp range
    if (low < 1) low = 10000;
    if (high > 65535) high = 65535;

    for (int port = low; port <= high; ++port) {
        if (m_reserved.contains(port)) continue;
        if (!port_is_free(port)) continue;

        m_reserved.insert(port);
        return PortReservation{port, true, ""};
    }

    return PortReservation{0, false, "No free ports in range [" +
                           std::to_string(low) + ", " + std::to_string(high) + "]"};
}

void PortManager::release(int port) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_reserved.erase(port);
}

bool PortManager::is_reserved(int port) const noexcept {
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_reserved.contains(port);
}

std::vector<int> PortManager::reserved_ports() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    return {m_reserved.begin(), m_reserved.end()};
}

void PortManager::release_all() {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_reserved.clear();
}

bool PortManager::port_is_free(int port) const {
    // Try to bind a test socket to localhost:port
    // If bind succeeds, the port is free.

#ifdef _WIN32
    if (!s_winsock.ok()) return false;
#endif

    int sock = static_cast<int>(socket(AF_INET, SOCK_STREAM, 0));
    if (sock < 0) return false;

    struct sockaddr_in addr{};
    addr.sin_family      = AF_INET;
    addr.sin_port        = htons(static_cast<uint16_t>(port));
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    int result = ::bind(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));

#ifdef _WIN32
    closesocket(sock);
#else
    close(sock);
#endif

    return result == 0;
}

// ─────────────────────────────────────────────────────────────────
// C-linkage exports
// ─────────────────────────────────────────────────────────────────

int mouse_reserve_port(int preferred_port) {
    if (preferred_port <= 0) {
        preferred_port = 8765;  // Default Mouse stream port
    }
    auto res = PortManager::instance().reserve(preferred_port);
    if (!res.success) {
        // Fallback: try any available port
        res = PortManager::instance().reserve_any(10000, 65535);
    }
    return res.success ? res.port : 0;
}

int mouse_release_port(int port) {
    if (!PortManager::instance().is_reserved(port)) return -1;
    PortManager::instance().release(port);
    return 0;
}

int mouse_get_stream_port() {
    auto ports = PortManager::instance().reserved_ports();
    return ports.empty() ? 0 : ports.front();
}

int* mouse_reserve_port_block(int count, int* out_count) {
    if (out_count == nullptr) return nullptr;
    *out_count = 0;

    if (count <= 0 || count > 256) return nullptr;

    auto* ports = new int[static_cast<size_t>(count)]{};
    for (int i = 0; i < count; ++i) {
        auto res = PortManager::instance().reserve_any(10000, 65535);
        if (res.success) {
            ports[*out_count] = res.port;
            (*out_count)++;
        } else {
            break;
        }
    }

    if (*out_count == 0) {
        delete[] ports;
        return nullptr;
    }
    return ports;
}

void mouse_free_ports(int* ports) {
    delete[] ports;
}

}  // namespace mouse
