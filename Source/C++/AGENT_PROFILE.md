# Agent Profile — C++ / CUDA

> 📋 Inherits from: [General Profile](../../AGENT_PROFILE.md)

## Domain

- **Scope:** C++ source under `Source/C++/`
- **Purpose:** GPU interop (CUDA, Metal), performance-critical kernels, MSVC-compatible libraries
- **Status:** 🚧 Scaffolding — build configs in place for both macOS and Windows

## Strict C++ Conventions (Memory Language)

### Language Standard
- **C++20** minimum — use concepts, ranges, coroutines where appropriate
- No raw `new`/`delete` — use `std::unique_ptr`, `std::shared_ptr`, `std::vector`
- RAII for all resource management

### Safety
- **AddressSanitizer (ASan)** and **UndefinedBehaviorSanitizer (UBSan)** mandatory in debug builds
- **No raw pointers** in public interfaces — use references or smart pointers
- **Bounds checking:** use `.at()` or span with checks; no unchecked `[]` without justification
- **Thread safety:** document which methods are thread-safe; use `std::atomic` and `std::mutex` explicitly

### Style
- **clang-format** with LLVM style (4-space indent)
- **clang-tidy** with all modern checks enabled
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Header-only** for templates; `.h` + `.cpp` for everything else
- **`#pragma once`** for header guards

### Build System
- **CMake 4.3+** — modern CMake with targets, not variables
- **MSVC support** — all code must compile with MSVC (Windows target) AND Clang (macOS)
- **CUDA support** — use CMake's `enable_language(CUDA)` for Nvidia GPU kernels

### Cross-Platform
- Every `.cpp` file must compile and pass tests on:
  - macOS arm64 (Clang 22+)
  - Windows x86-64 (MSVC)
- Use `std::filesystem` instead of platform-specific paths

## CUDA Conventions (Planned)

- CUDA kernels in `.cu` files, compiled with `nvcc`
- Host code in standard `.cpp`, linked via CMake CUDA support
- Always provide a CPU fallback for every CUDA kernel
- Target: Nvidia 5000 series (compute capability sm_120 or appropriate)

## Testing
- **Framework:** Google Test (`gtest`)
- **Coverage:** minimum 80% line coverage
- **CI:** test on both macOS (Clang) and Windows (MSVC) once CI is set up
