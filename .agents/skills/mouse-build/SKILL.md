---
name: mouse-build
description: Build all Mouse project components (Python, Rust, C++) across both macOS and Windows targets. Use this when the user asks to build, compile, or verify the project builds.
---

# Mouse Build

Build all components of the Mouse computer vision cursor project.

## Quick Build

```bash
# All platforms
cd Source/Python && mamba run -n mouse python3 -c "print('Python OK')"

# Rust (macOS native)
cd project-root && cargo build

# Rust (Windows cross-compile)
cd project-root && cargo build --target x86_64-pc-windows-msvc

# C++ (macOS)
cd project-root && cmake -B build -G Ninja -S Source/C++ && cmake --build build

# C++ (Windows — run on Windows machine)
cmake -B build -G "Visual Studio 17" -S Source/C++ && cmake --build build --config Release
```

## What to Build

Check which language components were modified and build only those:

- **Python:** Verify `mamba run -n mouse python3 -c "import sys; print(sys.version)"`
- **Rust / src/:** `cargo build` (and optionally `cargo build --target x86_64-pc-windows-msvc`)
- **C++ / Source/C++/:** `cmake -B build -G Ninja -S Source/C++ && cmake --build build`
- **TypeScript / PHP:** No build step needed (interpreted)

## After Building

Report:
- Which components compiled successfully
- Any warnings or errors
- Whether the Windows cross-compile target also passes (if applicable)
