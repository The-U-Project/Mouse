# Mouse

> **A simple computer vision cursor** — dual-approach architecture tracking the cursor via direct screen capture (Python) and GPU-level interception (Assembly/C++).

| | |
|---|---|
| 📖 **Getting Started** | [`GETTING_STARTED.md`](GETTING_STARTED.md) — hands-on setup, build, and dev guide |
| 🧠 **Agent Profile** | [`AGENT_PROFILE.md`](AGENT_PROFILE.md) — conventions, coding style, maintainer info |
| 💡 **Project Vision** | [`AI/VISION.md`](AI/VISION.md) — ideas, design decisions, open questions |
| 🛠️ **Zed Skills** | `.agents/skills/` — 7 project-local agent skills |

---

## Supported Systems

| Platform | OS | CPU | GPU | Status |
|----------|----|-----|-----|--------|
| **Mac (Dev)** | macOS (Darwin) · Arch Linux (dual boot) | Apple M4 Max (arm64) | Apple Silicon GPU | ✅ Active Development |
| **PC** | Windows 10 Pro · Kali Linux (WSL) · Ubuntu 22 (Hyper-V) | Intel Xeon E3 (x86-64) | Intel Arc + Nvidia 5000 (CUDA) | ✅ Active |

---

## Build Status

| Component | Platform | Status |
|-----------|----------|--------|
| Rust (`cargo build`) | macOS (arm64) · Windows (x86-64 cross) | ✅ Compiles |
| C++ (`cmake --build`) | macOS (Clang) · Windows (MSVC) | ✅ Configures · CUDA optional |
| Python (`mamba + uv`) | Both | ✅ Environment ready |
| TypeScript (`bun`) | Both | ✅ Runtime installed |
| PHP (`php`) | Both | ✅ Runtime installed |

---

## Tech Stack

| Language | Version | Toolchain | Role |
|----------|---------|-----------|------|
| Python | 3.14+ | `mamba` (env) + `uv` (pip) | Core CV logic, agent control |
| Rust | 1.95+ (stable) | `rustup` + `cargo` | Performance helpers |
| TypeScript | — | `bun` (primary) · `node` (fallback) | Frontend / web layer |
| C++ | C++20 | Clang 22+ / MSVC + `cmake` 4.3+ | GPU interop, CUDA |
| Assembly | ARMv8 / x86-64 | Inline (via C++/Rust) | GPU-level screen capture |
| PHP | 8.5+ | `php` | PHTML templates |

---

## Project Structure

```
Mouse/
├── src/                    # Core source (Rust, TypeScript, PHP/PHTML)
│   ├── Cargo.toml          # Rust project configuration
│   └── rust-toolchain.toml # Pinned Rust version + targets
│
├── Source/
│   ├── Python/             # Main Python codebase
│   │   ├── CodingAI/       # AI agent control for Python code
│   │   └── pyproject.toml  # Python project config (ruff, mypy, black)
│   ├── ASM/                # GPU-level assembly (ARMv8 + x86-64)
│   └── C++/                # C++/CUDA GPU interop
│       └── CMakeLists.txt  # C++ build config (macOS + Windows + opt. CUDA)
│
├── AI/                     # AI agent infrastructure (workspace-wide)
│   ├── AGENT_PROFILE.md    # Workspace AI rules & toolchain context
│   ├── VISION.md           # Project ideas, decisions, open questions
│   └── README.txt          # Directory purpose
│
├── APP/                    # Application output
├── Data/                   # Runtime data (gitignored)
├── Folders/                # User / Guest / Public file spaces
├── build/                  # C++ build output (gitignored)
├── target/                 # Rust build output (gitignored)
│
├── .agents/skills/         # Zed agent skills (project-local)
│   ├── mouse-build/        # Build all components (both platforms)
│   ├── mouse-test/         # Run all tests across languages
│   ├── mouse-lint/         # Lint & format all code
│   ├── mouse-cross/        # Cross-compile & verify Windows target
│   ├── mouse-dev/          # Full dev loop with file watchers
│   ├── mouse-knowledge/    # RAG-inspired codebase Q&A
│   └── mouse-release/      # Update docs, commit, push, create PR
│
├── AGENT_PROFILE.md        # General conventions & maintainer profile
├── GETTING_STARTED.md       # Hands-on setup & development guide
├── Cargo.lock              # Rust dependency lock
├── .editorconfig           # Editor settings (UTF-8, indentation)
├── .env                    # Local environment variables (gitignored)
├── .env.example            # Environment variable template
├── .gitignore              # Comprehensive gitignore
├── .nvmrc / .node-version  # Node.js version pinning
└── README.md               # This file
```

---

## Zed Agent Skills

This project includes 7 Zed agent skills for common tasks. Just say what you want in natural language:

| Skill | Trigger phrase | What it does |
|-------|---------------|-------------|
| `mouse-build` | "build the project" | Builds Rust, C++, Python — both platforms |
| `mouse-test` | "run the tests" | Runs `cargo test` + `pytest` + `ctest` |
| `mouse-lint` | "lint the code" | Runs ruff, clippy, clang-format |
| `mouse-cross` | "check Windows" | Cross-compiles Rust for x86-64 Windows |
| `mouse-dev` | "start dev mode" | File watchers, auto-rebuild, test on change |
| `mouse-knowledge` | "what does X do?" | RAG-style search of codebase & docs |
| `mouse-release` | "update README and PR" | Docs update → commit → push → GitHub PR |

See [`GETTING_STARTED.md`](GETTING_STARTED.md) (#agent-skills-reference) for usage details.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/The-U-Project/Mouse.git
cd Mouse

# 2. Activate Python environment
mamba activate mouse

# 3. Build Rust
cargo build

# 4. Build C++ (macOS)
cmake -B build -G Ninja -S Source/C++ && cmake --build build

# 5. Run tests
cargo test
```

> 📖 **Full guide:** [`GETTING_STARTED.md`](GETTING_STARTED.md)
