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
set(MOUSE_CXX_SOURCES
    port_reserver.cpp
    display_analyzer.cpp
    result_combiner.cpp
)

set(MOUSE_CXX_HEADERS
    port_reserver.h
    display_analyzer.h
    result_combiner.h
)

# ── Core library ────────────────────────────
add_library(mouse_core SHARED ${MOUSE_CXX_SOURCES} ${MOUSE_CXX_HEADERS})
target_include_directories(mouse_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Platform-specific link for sockets
if(WIN32)
    target_link_libraries(mouse_core PUBLIC ws2_32)
endif()

# Visibility settings
set_target_properties(mouse_core PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

# CUDA support (optional)
if(MOUSE_ENABLE_CUDA)
    file(GLOB MOUSE_CUDA_SOURCES "cuda/*.cu")
    file(GLOB MOUSE_CUDA_HEADERS "cuda/*.h")
    if(MOUSE_CUDA_SOURCES)
        add_library(mouse_cuda STATIC ${MOUSE_CUDA_SOURCES} ${MOUSE_CUDA_HEADERS})
        target_include_directories(mouse_cuda PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
        target_link_libraries(mouse_cuda PUBLIC CUDA::cudart)
        target_link_libraries(mouse_core PUBLIC mouse_cuda)
        target_compile_definitions(mouse_core PUBLIC MOUSE_HAS_CUDA=1)
        message(STATUS "CUDA vision kernels enabled")
    endif()
endif()

# ── ASM support ────────────────────────

# x86_64 NASM (Windows)
if(WIN32 AND CMAKE_SIZEOF_VOID_P EQUAL 8)
    enable_language(ASM_NASM)
    if(CMAKE_ASM_NASM_COMPILER)
        set(MOUSE_ASM_SOURCES
            ${CMAKE_SOURCE_DIR}/../ASM/display_reserve_x86_64.asm
        )
        if(EXISTS "${CMAKE_SOURCE_DIR}/../ASM/display_reserve_x86_64.asm")
            target_sources(mouse_core PRIVATE ${MOUSE_ASM_SOURCES})
            target_compile_definitions(mouse_core PUBLIC MOUSE_HAS_ASM=1)
            message(STATUS "x86_64 ASM port reserve enabled")
        endif()
    endif()
endif()

# ARM64 (macOS / Linux aarch64)
if((APPLE AND CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
   OR (CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64"))
    if(CMAKE_ASM_COMPILER)
        set(MOUSE_ARM64_ASM_SOURCES
            ${CMAKE_SOURCE_DIR}/../ASM/display_reserve_arm64.s
        )
        if(EXISTS "${CMAKE_SOURCE_DIR}/../ASM/display_reserve_arm64.s")
            target_sources(mouse_core PRIVATE ${MOUSE_ARM64_ASM_SOURCES})
            target_compile_definitions(mouse_core PUBLIC MOUSE_HAS_ASM=1)
            message(STATUS "ARM64 ASM port reserve enabled")
        endif()
    endif()
endif()

# ── Install ─────────────────────────────────
install(TARGETS mouse_core
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

# ── Testing ─────────────────────────────────
option(MOUSE_BUILD_TESTS "Build test suite" OFF)
if(MOUSE_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    # add_subdirectory(tests)
endif()

message(STATUS "Mouse C++ build configured — platform: ${MOUSE_PLATFORM}")
