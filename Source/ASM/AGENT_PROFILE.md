# Agent Profile — Assembly (GPU-Level)

> 📋 Inherits from: [General Profile](../../AGENT_PROFILE.md)

## Domain

- **Scope:** Assembly source under `Source/ASM/`
- **Approach:** GPU-level screen capture — "learn from GPU result and display data"
- **Method:** Inline assembly within C/C++/Rust, not standalone `.s` files

## Strict ASM Conventions (Memory Language)

### Safety First
- **All assembly must be wrapped** in safe Rust/C++ abstractions
- **Document every register** used and its purpose in a comment block
- **No self-modifying code** — code section is read-only
- **Stack discipline:** always restore `rsp`/`sp` before returning

### Cross-Architecture
- **Two implementations required** for every ASM routine:
  - `aarch64` (Apple M4 Max) — ARMv8.x-A ISA
  - `x86-64` (Intel Xeon E3) — x86-64 with AVX2

### Documentation Template
Every inline ASM block must be preceded by:
```c
// ┌─ ASM Routine ───────────────────────────────────┐
// │ Purpose: [what this does]                       │
// │ Target: [aarch64 / x86-64]                      │
// │ Registers used: [list]                          │
// │ Registers clobbered: [list]                     │
// │ Side effects: [any memory/flag changes]         │
// └────────────────────────────────────────────────┘
```

### GPU-Specific
- **Apple Silicon:** Use Metal Performance Shaders where possible; inline ASM only for what MPS can't do
- **Nvidia:** Use CUDA (via C++ interop) for GPU compute; inline PTX assembly only for critical kernels
- **No GPU-specific ASM without a CPU fallback** for debugging

## Testing
- Every ASM routine must have a pure-C/Rust reference implementation
- Tests compare ASM output against the reference for randomized inputs
- Run on both arm64 and x86-64 CI (once set up)
