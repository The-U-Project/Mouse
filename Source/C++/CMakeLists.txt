# Mouse — C++ Build Configuration
# CMake 4.3+ required
# Supports: macOS (Clang) + Windows (MSVC) + CUDA (Nvidia 5000)

cmake_minimum_required(VERSION 4.3)

# CUDA is optional — enable with -DMOUSE_ENABLE_CUDA=ON (requires Nvidia GPU)
option(MOUSE_ENABLE_CUDA "Enable CUDA support (Nvidia GPU)" OFF)

set(MOUSE_LANGUAGES CXX C)
if(MOUSE_ENABLE_CUDA)
    include(CheckLanguage)
    check_language(CUDA)
    if(CMAKE_CUDA_COMPILER)
        enable_language(CUDA)
        list(APPEND MOUSE_LANGUAGES CUDA)
        message(STATUS "CUDA enabled")
    else()
        message(WARNING "CUDA requested but not found — continuing without CUDA")
        set(MOUSE_ENABLE_CUDA OFF)
    endif()
endif()

project(Mouse VERSION 0.1.0 LANGUAGES ${MOUSE_LANGUAGES})

# C++20 standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Platform Detection ──────────────────────
if(APPLE)
    message(STATUS "Building for macOS (Apple Silicon / M4 Max)")
    set(MOUSE_PLATFORM "macos-arm64")
    set(CMAKE_OSX_ARCHITECTURES "arm64")
elseif(WIN32)
    message(STATUS "Building for Windows 10 Pro (Intel Xeon E3 / Nvidia 5000)")
    set(MOUSE_PLATFORM "windows-x86_64")
else()
    message(WARNING "Unknown platform — proceeding with defaults")
endif()

# ── CUDA Support (if enabled) ───────────────
if(MOUSE_ENABLE_CUDA)
    find_package(CUDAToolkit REQUIRED)
    set(CMAKE_CUDA_STANDARD 20)
    set(CMAKE_CUDA_STANDARD_REQUIRED ON)
    set(CMAKE_CUDA_ARCHITECTURES "90")  # Nvidia 5000 (Blackwell)
    message(STATUS "CUDA enabled — arch: sm_90")
endif()

# ── Compiler Flags ──────────────────────────
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|AppleClang")
    add_compile_options(-Wall -Wextra -Wpedantic -finput-charset=UTF-8)
    # AddressSanitizer + UBSan in debug
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
        add_link_options(-fsanitize=address,undefined)
    endif()
elseif(MSVC)
    add_compile_options(/W4 /utf-8)
    # MSVC sanitizer equivalent
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        add_compile_options(/fsanitize=address)
    endif()
endif()

# ── Source Files ────────────────────────────
# Add source files here as they're created
# file(GLOB_RECURSE MOUSE_SOURCES "*.cpp" "*.cxx" "*.cc")
# file(GLOB_RECURSE MOUSE_HEADERS "*.h" "*.hpp" "*.hxx")

# add_library(mouse_core ${MOUSE_SOURCES} ${MOUSE_HEADERS})
# target_include_directories(mouse_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# if(MOUSE_ENABLE_CUDA)
#     file(GLOB_RECURSE MOUSE_CUDA_SOURCES "*.cu")
#     target_sources(mouse_core PRIVATE ${MOUSE_CUDA_SOURCES})
#     target_link_libraries(mouse_core PUBLIC CUDA::cudart)
# endif()

# ── Testing ─────────────────────────────────
option(MOUSE_BUILD_TESTS "Build test suite" OFF)
if(MOUSE_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    # add_subdirectory(tests)
endif()

message(STATUS "Mouse C++ build configured — platform: ${MOUSE_PLATFORM}")
