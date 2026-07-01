---
name: mouse-dev
description: Full development loop for Mouse — watch files, rebuild on change, run tests. Use this when the user wants to start developing or needs a live-reload workflow.
---

# Mouse Dev

Full development workflow with file watching and auto-rebuild.

## Start Developing

```bash
# Activate the Python environment
mamba activate mouse

# Watch all components (in separate terminals):

# Terminal 1: Rust watcher
cargo watch -x check -x test

# Terminal 2: Python watcher (requires watchdog)
mamba run -n mouse python3 -c "
# Simple file watcher — re-run tests on Python changes
# pip install watchdog if not installed
"

# Terminal 3: C++ watcher (requires entr or fswatch)
# macOS: brew install fswatch
fswatch -o Source/C++ | xargs -n1 -I{} cmake --build build
```

## Dev Loop

When the user says "start dev" or "dev mode":

1. **Activate environment:** `mamba activate mouse`
2. **Check build:** `cargo check` (fast) + `cmake --build build`
3. **Start watchers** for the language being worked on
4. **Run tests** after each change

## Quick Iteration

For a single change across languages:

```bash
# 1. Make changes
# 2. Lint
mamba run -n mouse ruff check Source/Python/ && cargo clippy

# 3. Build
cargo build && cmake --build build

# 4. Test
cargo test && mamba run -n mouse pytest Source/Python/tests/

# 5. Cross-check
cargo check --target x86_64-pc-windows-msvc
```

## New Feature Workflow

When starting a new feature:

1. Read `AI/VISION.md` — understand project intent
2. Read relevant `AGENT_PROFILE.md` — know the conventions
3. Create a feature branch: `git checkout -b feat/my-feature`
4. Implement with tests
5. Run `mouse-lint` → `mouse-test` → `mouse-cross`
6. Present changes to MCHIGM for review
