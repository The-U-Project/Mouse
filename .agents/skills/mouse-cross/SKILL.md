---
name: mouse-cross
description: Cross-compile and verify the Mouse project for Windows 10 Pro (Intel Xeon E3, Nvidia 5000). Use this when verifying cross-platform compatibility or preparing for Windows deployment.
---

# Mouse Cross-Compile

Verify that all Mouse components compile for the Windows 10 Pro target.

## Target Platform

- **OS:** Windows 10 Pro
- **CPU:** Intel Xeon E3 (x86-64)
- **GPU:** Nvidia 5000 (CUDA, sm_90)

## Cross-Compile Commands

```bash
# Rust — cross-compile for Windows
cargo build --target x86_64-pc-windows-msvc
cargo check --target x86_64-pc-windows-msvc  # Faster: check only

# C++ — verify CMake config for MSVC (syntax check only on macOS)
cmake -B build-win -G "Visual Studio 17" -S Source/C++ 2>&1 | tail -5
# Note: actual MSVC compilation requires Windows machine

# Python — check for Windows-incompatible code
mamba run -n mouse python3 -c "
import ast, sys, os
# Check all .py files for platform assumptions
for root, dirs, files in os.walk('Source/Python'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fp:
                content = fp.read()
            if 'darwin' in content.lower() or 'macos' in content.lower():
                print(f'  ⚠️  {path}: contains macOS-specific code')
"
echo "Done"
```

## What to Check

1. **Platform-specific code:** Search for `#[cfg(target_os = "macos")]` — ensure a Windows counterpart exists
2. **File paths:** No hardcoded `/` paths (use `std::path::Path` or `os.path.join`)
3. **GPU code:** Apple Metal code should have `#[cfg(target_os = "macos")]`; CUDA code should have `#[cfg(target_os = "windows")]`
4. **Assembly:** Every ASM routine must have both `aarch64` and `x86-64` variants

## After Cross-Check

Report:

| Component | macOS | Windows (cross) | Issues |
|-----------|-------|-----------------|--------|
| Rust | ✅ | ✅/⚠️/❌ | ... |
| C++ | ✅ | — (needs Windows) | ... |
| Python | ✅ | ✅/⚠️ | ... |
