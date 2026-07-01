---
name: mouse-test
description: Run tests across all Mouse project languages (Python pytest, Rust cargo test, C++ ctest). Use this when the user asks to test, verify, or run the test suite.
---

# Mouse Test

Run the test suite across all language components of the Mouse project.

## Test Commands

```bash
# Python (mamba env)
mamba run -n mouse pytest Source/Python/tests/ -v

# Rust
cargo test

# Rust (all targets including Windows)
cargo test --target x86_64-pc-windows-msvc 2>&1 || echo "Cross-compile tests may require Windows runtime"

# C++ (if tests exist)
cd build && ctest --output-on-failure
```

## What to Test

- **If Python files changed:** run `pytest` for that module only first, then full suite
- **If Rust files changed:** run `cargo test` — specific test with `cargo test <test_name>`
- **If C++ files changed:** configure with `-DMOUSE_BUILD_TESTS=ON` and run `ctest`
- **If cross-platform code changed:** test on both macOS AND verify Windows cross-compile

## Test Expectations

- All tests must pass before suggesting a PR or merge
- If tests don't exist yet for new code, suggest creating them
- Failed tests: report the failing test name + output, don't guess the fix

## After Testing

Report a table:

| Language | Tests Run | Passed | Failed | Skipped |
|----------|-----------|--------|--------|---------|
| Python | 0 | — | — | — |
| Rust | 0 | — | — | — |
| C++ | 0 | — | — | — |
