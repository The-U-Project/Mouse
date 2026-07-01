# Mouse — Getting Started

> 🖱️ **Mouse** — A simple computer vision cursor.
> This is the hands-on guide. For agent conventions, see [AGENT_PROFILE.md](AGENT_PROFILE.md).
> For project ideas & decisions, see [AI/VISION.md](AI/VISION.md).

---

## Project Overview

**Mouse** uses a dual-approach architecture to track and control a cursor:

1. **Python (Direct Vision):** "See" the screen — capture display output and use computer vision to locate the cursor. High-level, flexible.
2. **Assembly (GPU Vision):** "Learn" from the GPU — intercept render data at the hardware level. Low-level, ultra-fast.

The goal is to compare, combine, and learn from both approaches across two hardware platforms.

---

## Supported Platforms

| Platform | OS | CPU | GPU | Status |
|----------|----|-----|-----|--------|
| **Mac (Dev)** | macOS | Apple M4 Max (arm64) | Apple Silicon GPU | ✅ Active |
| **PC** | Windows 10 Pro | Intel Xeon E3 (x86-64) | Nvidia 5000 (CUDA) | ✅ Active |

---

## Tech Stack

| Language | Version | Toolchain | Role |
|----------|---------|-----------|------|
| Python | 3.14+ | `mamba` (env) + `uv` (pip) | Core CV logic, agent control |
| Rust | 1.95+ (stable) | `rustup` + `cargo` | Performance helpers |
| TypeScript | — | `bun` (primary) / `node` (fallback) | Creating the mouse |
| C++ | C++20 | Clang 22+ / MSVC + `cmake` 4.3+ | GPU interop, CUDA |
| Assembly | ARMv8 / x86-64 | Inline (via C++/Rust) | GPU-level capture |
| PHP | 8.5+ | `php` | PHTML templates |

---

## Prerequisites

### macOS (M4 Max)

These are pre-installed on the dev machine. If setting up from scratch:

```bash
# System tools (Homebrew)
brew install python@3.14 rustup cmake php node bun

# Rust toolchain
rustup default stable
rustup target add x86_64-pc-windows-msvc    # Windows cross-compile

# Python environment manager
conda install -c conda-forge mamba -y
mamba create -n mouse python=3.14 -y         # or: mamba activate mouse (already exists)

# Fast pip inside mamba env
mamba run -n mouse uv pip install pytest ruff black mypy

# JavaScript runtime
# Bun is installed at ~/.bun/bin/bun — added to PATH via ~/.zshrc
# Node.js is installed at /opt/homebrew/bin/node (v26+)
```

### Windows 10 Pro (Xeon E3 + Nvidia 5000)

```bash
# Python
# Install miniconda → then: conda install -c conda-forge mamba
mamba create -n mouse python=3.14 -y

# Rust
# Install rustup-init.exe from https://rustup.rs
rustup default stable
rustup target add x86_64-pc-windows-msvc

# C++
# Install Visual Studio 2022+ with "Desktop C++" + MSVC toolchain
# Install CMake from https://cmake.org (4.3+)
cmake -B build -G "Visual Studio 17"
cmake --build build --config Release

# CUDA (Nvidia 5000)
# Install CUDA Toolkit 12+ from https://developer.nvidia.com/cuda-downloads
cmake -B build -G "Visual Studio 17" -DMOUSE_ENABLE_CUDA=ON
```

---

## Quick Start — 5 Minutes to Running

### 1. Clone & Enter

```bash
git clone https://github.com/The-U-Project/Mouse.git
cd Mouse
```

### 2. Activate Python Environment

```bash
mamba activate mouse
# Verify: python3 --version  →  Python 3.14.6
```

### 3. Build Everything

```bash
# Rust
cargo build

# C++ (macOS)
cmake -B build -G Ninja -S Source/C++ && cmake --build build

# C++ (Windows)
cmake -B build -G "Visual Studio 17" -S Source/C++ && cmake --build build --config Release
```

### 4. Run Tests

```bash
cargo test                                    # Rust
mamba run -n mouse pytest Source/Python/tests/  # Python
ctest --test-dir build                        # C++
```

### 5. Start Developing

```bash
# Full dev loop (see mouse-dev skill)
cargo watch -x check -x test                  # Terminal 1: Rust
fswatch -o Source/C++ | xargs -n1 -I{} cmake --build build  # Terminal 2: C++
```

---

## Project Structure

```
Mouse/
├── src/                    # Core source (Rust, TypeScript, PHP/PHTML)
│   ├── main.rs             # Rust entry point
│   ├── helper.rs           # Rust helpers
│   ├── main.ts             # TypeScript main
│   └── index.phtml          # PHP template
│
├── Source/
│   ├── Python/             # Main Python codebase
│   │   ├── files/          # File operations (KEEPER, WIKI)
│   │   ├── library/        # Index & catalog (LIBRARIAN, WIKI)
│   │   ├── modules/        # Module system (KEEPER, externalLangMods)
│   │   ├── CodingAI/       # AI agent control for Python code
│   │   ├── pyproject.toml  # Python project config (uv + mamba)
│   │   └── AGENT_PROFILE.md
│   ├── ASM/                # GPU-level assembly (ARMv8 + x86-64)
│   │   └── AGENT_PROFILE.md
│   └── C++/                # C++/CUDA GPU interop
│       ├── CMakeLists.txt   # C++ build config (macOS + Windows + CUDA)
│       └── AGENT_PROFILE.md
│
├── AI/                     # AI infrastructure (workspace-wide)
│   ├── README.txt          # AI directory purpose
│   ├── AGENT_PROFILE.md    # Workspace AI rules + toolchain context
│   └── VISION.md           # Project ideas, decisions, open questions
│
├── APP/                    # Application output
├── Data/                   # Runtime data (gitignored except .gitkeep)
├── Folders/                # User / Guest / Public / Mouse file spaces
│
├── .agents/skills/         # Zed agent skills (project-local)
│   ├── mouse-build/        # Build all components
│   ├── mouse-test/         # Run all tests
│   ├── mouse-lint/         # Lint & format all code
│   ├── mouse-cross/        # Cross-compile for Windows
│   ├── mouse-dev/          # Full dev loop with watchers
│   ├── mouse-knowledge/    # RAG-inspired knowledge index
│   └── mouse-release/      # Update docs, commit, push, create PR
│
├── AGENT_PROFILE.md        # General conventions & maintainer info
├── Cargo.toml              # Rust project config
├── Cargo.lock              # Rust dependency lock
├── rust-toolchain.toml     # Pinned Rust version + targets
├── .cargo/
│   └── config.toml         # Cross-compilation targets + release profile
├── .env                    # Local environment variables (gitignored)
├── .env.example            # Environment template
├── .editorconfig           # Editor settings (UTF-8, indentation)
├── .gitignore              # Comprehensive gitignore
├── .nvmrc / .node-version  # Node.js version pinning
└── README.md               # Project overview
```

---

## Development Workflow

### Daily Commands

| Action | Command |
|--------|---------|
| Activate env | `mamba activate mouse` |
| Build Rust | `cargo build` |
| Build C++ | `cmake --build build` |
| Test Rust | `cargo test` |
| Test Python | `mamba run -n mouse pytest` |
| Lint Python | `mamba run -n mouse ruff check Source/Python/` |
| Lint Rust | `cargo clippy -- -D warnings` |
| Format Python | `mamba run -n mouse ruff format Source/Python/` |
| Format Rust | `cargo fmt` |
| Cross-check | `cargo check --target x86_64-pc-windows-msvc` |

### Feature Workflow

```
1. Read AI/VISION.md          — understand project intent
2. Read relevant AGENT_PROFILE.md — know the conventions
3. git checkout -b feat/my-feature
4. Implement + write tests
5. mouse-lint → mouse-test → mouse-cross
6. Present to MCHIGM for review
```

### Python Package Management (mamba + uv)

```
# Heavy/binary deps (numpy, opencv, onnxruntime)
mamba install -n mouse numpy opencv -y

# Pure Python deps — lightning fast
mamba run -n mouse uv pip install pydantic pillow rich

# Dev tools (already installed)
mamba run -n mouse uv pip install pytest ruff black mypy
```

### Cross-Platform Development

```
# Rust: cross-compile for Windows from macOS
cargo build --target x86_64-pc-windows-msvc

# C++: verify CMake config (syntax only on macOS)
cmake -B build-win -G "Visual Studio 17" -S Source/C++

# Python: check for macOS-only assumptions
grep -r "darwin\|macos" Source/Python/ --include="*.py"
```

---

## Agent Skills Reference

These Zed agent skills are available in this project:

| Skill | What it does | Trigger |
|-------|-------------|---------|
| `mouse-build` | Build Python, Rust, C++ (both platforms) | "build the project" |
| `mouse-test` | Run all tests across languages | "run tests" |
| `mouse-lint` | Lint & format all code | "lint the code" / "format" |
| `mouse-cross` | Verify Windows cross-compilation | "check Windows compatibility" |
| `mouse-dev` | Full dev loop with file watchers | "start developing" / "dev mode" |
| `mouse-knowledge` | RAG-style codebase Q&A | "what does X do?" / "where is Z?" |
| `mouse-release` | Update docs & create GitHub PR | "release changes" / "update README and PR" |

### How to Use Agents & Skills

Zed's AI agent automatically detects which skill to load based on what you say. **You don't need to type skill names** — just say what you want in natural language.

#### Triggering Skills

| You say... | Agent loads... | What happens |
|-----------|----------------|-------------|
| "build the project" | `mouse-build` | Builds Rust, C++, Python — reports pass/fail per component |
| "run the tests" | `mouse-test` | Runs `cargo test` + `pytest` + `ctest` — reports results |
| "lint my code" or "format everything" | `mouse-lint` | Runs ruff, clippy, clang-format across all source |
| "does this compile on Windows?" | `mouse-cross` | Cross-compiles Rust for `x86_64-pc-windows-msvc`, checks CMake |
| "start dev mode" or "watch my files" | `mouse-dev` | Sets up file watchers, rebuilds on change, runs tests |
| "what does the Python module do?" or "where is the CUDA code?" | `mouse-knowledge` | Searches READMEs, profiles, source code — returns a knowledge card |
| "update the README and make a PR" | `mouse-release` | Scans for changes, updates docs, commits, pushes, creates PR |

#### Manual Invocation

If you want to be explicit (e.g., for scripting or clarity), use the skill name with `@`:

```
@mouse-build Build everything and tell me if the Windows target compiles too
@mouse-knowledge Explain the dual-approach architecture
@mouse-release Update README with the new CUDA support and open a PR
```

You can also chain them together:

```
"Lint the code, run all tests, and if everything passes, create a release PR"
# → mouse-lint → mouse-test → mouse-release (if all green)
```

#### What Skills Know

Each skill draws from specific project knowledge files:

| Skill | Reads these files |
|-------|------------------|
| All | `GETTING_STARTED.md`, `AGENT_PROFILE.md` |
| `mouse-dev` / `mouse-build` / `mouse-cross` | `Cargo.toml`, `CMakeLists.txt`, `rust-toolchain.toml`, `.cargo/config.toml` |
| `mouse-test` / `mouse-lint` | `pyproject.toml`, `rust-toolchain.toml`, per-directory `AGENT_PROFILE.md` |
| `mouse-knowledge` | All `README.txt`, all `AGENT_PROFILE.md`, `AI/VISION.md`, all source code |
| `mouse-release` | `README.md`, `GETTING_STARTED.md`, git history, GitHub remote config |

#### Adding New Skills

Skills are plain Markdown files in `.agents/skills/<name>/SKILL.md`. To create one:

```
@create-skill Help me build a skill that auto-generates release notes from git log
```

The agent will scaffold the directory, write the `SKILL.md` with frontmatter, and guide you through customizing the instructions. Skills can include templates, examples, and reference files in their directory.

---

## Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `LANG` / `LC_ALL` | UTF-8 locale | `en_US.UTF-8` |
| `CONDA_ENV` | Python env name | `mouse` |
| `RUST_LOG` | Rust log level | `info` |
| `SCREEN_CAPTURE_FPS` | Capture framerate | `60` |
| `LOG_LEVEL` | App log level | `INFO` |

---

## Conventions at a Glance

| Aspect | Rule |
|--------|------|
| **Commits** | Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`) |
| **Python** | PEP 8, type hints mandatory, 80%+ coverage, numpy for arrays |
| **Rust** | No `unsafe` without benchmarks + approval, clippy `--deny warnings` |
| **C++** | C++20, RAII, ASan+UBSan in debug, must compile on MSVC AND Clang |
| **ASM** | Inline only, dual-arch (arm64 + x86-64), register docs required |
| **Branching** | Feature branches from `main`, merge via PR |
| **AI agents** | Ask before system changes, read README.txt before touching directory |

Full conventions: [AGENT_PROFILE.md](AGENT_PROFILE.md) and per-directory `AGENT_PROFILE.md` files.

---

## Troubleshooting

### "mamba: command not found"
```bash
# mamba is inside conda — ensure conda is initialized
conda init zsh
source ~/.zshrc
```

### "Missing manifest in toolchain" (rustup)
```bash
# The initial download was interrupted. Force reinstall:
rustup toolchain install stable --force
rustup default stable
```

### Node.js broken (missing llhttp dylib)
```bash
brew reinstall node
```

### Bun not found
```bash
# Bun is at ~/.bun/bin — ensure it's in PATH
echo 'export PATH="$HOME/.bun/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### CMake can't find CUDA (expected on macOS)
```bash
# CUDA is optional. Build without it:
cmake -B build -G Ninja -S Source/C++    # CUDA is OFF by default
# On Windows with Nvidia GPU:
cmake -B build -G "Visual Studio 17" -S Source/C++ -DMOUSE_ENABLE_CUDA=ON
```

### Locale issues (garbled output, encoding errors)
```bash
# Ensure UTF-8 is exported in shell:
echo 'export LANG=en_US.UTF-8' >> ~/.zshrc
echo 'export LC_ALL=en_US.UTF-8' >> ~/.zshrc
source ~/.zshrc
```

---

## Maintainer

**MCHIGM** — project owner, architect, primary developer.

Questions? Check [AI/VISION.md](AI/VISION.md) for project ideas and design rationale.
