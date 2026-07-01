---
name: mouse-lint
description: Lint and format all Mouse project code (Python ruff, Rust clippy, C++ clang-format). Use this when the user asks to lint, format, or check code quality.
---

# Mouse Lint

Lint and format all language components in the Mouse project.

## Lint Commands

```bash
# Python — ruff (fast linter + formatter)
mamba run -n mouse ruff check Source/Python/
mamba run -n mouse ruff format --check Source/Python/

# Rust — clippy + rustfmt
cargo clippy -- -D warnings
cargo fmt --check

# C++ — clang-tidy + clang-format
find Source/C++ -name "*.cpp" -o -name "*.h" | xargs clang-tidy
find Source/C++ -name "*.cpp" -o -name "*.h" | xargs clang-format --dry-run -Werror

# TypeScript (if ESLint/Prettier configured)
# bun run lint
```

## Auto-Fix

When user says "fix lint" or "format", apply auto-fixes:

```bash
mamba run -n mouse ruff format Source/Python/
cargo fmt
find Source/C++ -name "*.cpp" -o -name "*.h" | xargs clang-format -i
```

## Severity Rules

| Level | Action |
|-------|--------|
| **Error** | Must fix before committing |
| **Warning** | Should fix; explain if leaving |
| **Note/Style** | Fix if touching the file anyway |

## After Linting

Report:
- Number of issues found/fixed per language
- Any remaining issues that need manual attention
- Whether code passes the "ready to commit" threshold
