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
│   ├── main.rs             # Rust entry point
│   ├── helper.rs           # Rust helpers
│   ├── main.ts             # TypeScript main
│   └── index.phtml         # PHP template
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
├── GETTING_STARTED.md      # Hands-on setup & development guide
├── Cargo.toml              # Rust project config
├── rust-toolchain.toml     # Rust toolchain channel + targets
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

---

Credits & Badges: 

Supported AI APIs

![ChatGPT](https://img.shields.io/badge/chatGPT-74aa9c?style=for-the-badge&logo=openai&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-D97757?style=for-the-badge&logo=claude&logoColor=white)
![DeepSeek](https://img.shields.io/badge/DeepSeek-5786FE?style=for-the-badge&logo=deepseek&logoColor=white)
![GitHub Copilot](https://img.shields.io/badge/github_copilot-8957E5?style=for-the-badge&logo=github-copilot&logoColor=white)
![Google Gemini](https://img.shields.io/badge/google%20gemini-8E75B2?style=for-the-badge&logo=google%20gemini&logoColor=white)
![Minimax](https://img.shields.io/badge/minimax-B4393C?style=for-the-badge&logo=minimax&logoColor=white)
![MistralAI](https://img.shields.io/badge/mistralai-FA520F?style=for-the-badge&logo=mistralai&logoColor=white)
![Perplexity](https://img.shields.io/badge/perplexity-000000?style=for-the-badge&logo=perplexity&logoColor=088F8F)

Used browsers during testing

![Google Chrome](https://img.shields.io/badge/Google%20Chrome-4285F4?style=for-the-badge&logo=GoogleChrome&logoColor=white)
![IE](https://img.shields.io/badge/Internet%20Explorer-0076D6?style=for-the-badge&logo=Internet%20Explorer&logoColor=white)
![Safari](https://img.shields.io/badge/Safari-000000?style=for-the-badge&logo=Safari&logoColor=white)
![Tor](https://img.shields.io/badge/Tor-7D4698?style=for-the-badge&logo=Tor-Browser&logoColor=white)

Automation workflow for development

![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)

Cloud storage for output data (used in testing)

![Dropbox](https://img.shields.io/badge/Dropbox-%233B4D98.svg?style=for-the-badge&logo=Dropbox&logoColor=white)
![Google Drive](https://img.shields.io/badge/Google%20Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)
![iCloud](https://img.shields.io/badge/icloud-%233693F3.svg?style=for-the-badge&logo=icloud&logoColor=white)
![OneDrive](https://img.shields.io/badge/OneDrive-white?style=for-the-badge&logo=Microsoft%20OneDrive&logoColor=0078D4)
![OneDrive](https://img.shields.io/badge/OneDrive-0078D4.svg?style=for-the-badge&logo=microsoftonedrive&logoColor=white)

Trained from sites

![Hackerearth](https://img.shields.io/badge/HackerEarth-%232C3454.svg?&style=for-the-badge&logo=HackerEarth&logoColor=Blue)
![Kaggle](https://img.shields.io/badge/Kaggle-035a7d?style=for-the-badge&logo=kaggle&logoColor=white)
![Reddit](https://img.shields.io/badge/Reddit-%23FF4500.svg?style=for-the-badge&logo=Reddit&logoColor=white)
![Stack Exchange](https://img.shields.io/badge/StackExchange-%23ffffff.svg?style=for-the-badge&logo=StackExchange)
![Stack Overflow](https://img.shields.io/badge/-Stackoverflow-FE7A16?style=for-the-badge&logo=stack-overflow&logoColor=white)
![Wikipedia](https://img.shields.io/badge/Wikipedia-%23000000.svg?style=for-the-badge&logo=wikipedia&logoColor=white)
![Codecademy](https://img.shields.io/badge/Codecademy-FFF0E5?style=for-the-badge&logo=codecademy&logoColor=1F243A)
![GeeksForGeeks](https://img.shields.io/badge/GeeksforGeeks-gray?style=for-the-badge&logo=geeksforgeeks&logoColor=35914c)
![Google Scholar](https://img.shields.io/badge/Google%20Scholar-4285F4?style=for-the-badge&logo=google-scholar&logoColor=white)
![Skill Share](https://img.shields.io/badge/Skill%20share-002333?style=for-the-badge&logo=skillshare&logoColor=00FF84)
![W3 Schools](https://img.shields.io/badge/W3%20Schools-04AA6D?style=for-the-badge&logo=w3schools&logoColor=white) 

Frameworks

![.Net](https://img.shields.io/badge/.NET-5C2D91?style=for-the-badge&logo=.net&logoColor=white) (Supports .NET framework via NuGet)
![Anaconda](https://img.shields.io/badge/Anaconda-%2344A833.svg?style=for-the-badge&logo=anaconda&logoColor=white) (PyPI)
![Arm](https://img.shields.io/badge/arm-%230091BD.svg?style=for-the-badge&logo=arm&logoColor=white)
![Homebrew](https://img.shields.io/badge/homebrew-%23FBB040.svg?style=for-the-badge&logo=homebrew&logoColor=black) (APP)
![NPM](https://img.shields.io/badge/NPM-%23CB3837.svg?style=for-the-badge&logo=npm&logoColor=white) (npm)
![NuGet](https://img.shields.io/badge/nuget-%23004880.svg?style=for-the-badge&logo=nuget&logoColor=white) (Microsoft NuGet)
![PlatformIO](https://img.shields.io/badge/platformio-%23000.svg?style=for-the-badge&logo=platformio&logoColor=F5822A) ([WIP] micro & distilled version)
![PNPM](https://img.shields.io/badge/pnpm-%234a4a4a.svg?style=for-the-badge&logo=pnpm&logoColor=f69220)
![uv](https://img.shields.io/badge/uv-%23DE5FE9.svg?style=for-the-badge&logo=uv&logoColor=white)
![Yarn](https://img.shields.io/badge/yarn-%232C8EBB.svg?style=for-the-badge&logo=yarn&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![Bun](https://img.shields.io/badge/Bun-%23000000.svg?style=for-the-badge&logo=bun&logoColor=white)

Made with

![Neovim](https://img.shields.io/badge/NeoVim-%2357A143.svg?&style=for-the-badge&logo=neovim&logoColor=white) (Main for Linux testing purposes)
![Spyder](https://img.shields.io/badge/Spyder-838485?style=for-the-badge&logo=spyder%20ide&logoColor=maroon) (Main for Mouse-Python development)
![Zed](https://img.shields.io/badge/zedindustries-084CCF.svg?style=for-the-badge&logo=zedindustries&logoColor=white) (Main for REPO development)
![VS Code Insiders](https://img.shields.io/badge/VS%20Code%20Insiders-35b393.svg?style=for-the-badge&logo=visual-studio-code&logoColor=white)
![Xcode](https://img.shields.io/badge/Xcode-007ACC?style=for-the-badge&logo=Xcode&logoColor=white) (Main for MacOS testing purposes)
![Visual Studio](https://img.shields.io/badge/Visual%20Studio-5C2D91.svg?style=for-the-badge&logo=visual-studio&logoColor=white) (Main for Windows testing purposes)

Written in

![AssemblyScript](https://img.shields.io/badge/assembly%20script-%23000000.svg?style=for-the-badge&logo=assemblyscript&logoColor=white)
![C#](https://img.shields.io/badge/c%23-%23239120.svg?style=for-the-badge&logo=csharp&logoColor=white) (CUDA)
![C++](https://img.shields.io/badge/c++-%2300599C.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)

Tested on

![Alpine Linux](https://img.shields.io/badge/Alpine_Linux-%230D597F.svg?style=for-the-badge&logo=alpine-linux&logoColor=white) (Shell only)
![Arch](https://img.shields.io/badge/Arch%20Linux-1793D1?logo=arch-linux&logoColor=fff&style=for-the-badge) (Full UI navigation)
![FreeBSD](https://img.shields.io/badge/-FreeBSD-%23870000?style=for-the-badge&logo=freebsd&logoColor=white) (Shell only)
![Kali](https://img.shields.io/badge/Kali-268BEE?style=for-the-badge&logo=kalilinux&logoColor=white) (Full UI navigation)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0) (Daily use)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white) (Full UI navigation)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white) (Daily use)
![Intel](https://img.shields.io/badge/intel-%230068B5%20.svg?style=for-the-badge&logo=intel&logoColor=white) (Intel Xeon CPU)
![Arm](https://img.shields.io/badge/arm-%230091BD.svg?style=for-the-badge&logo=arm&logoColor=white) (Apple M-seriec CPU)

and
![CMake](https://img.shields.io/badge/CMake-%23008FBA.svg?style=for-the-badge&logo=cmake&logoColor=white) (CMake compiler, also supports using MSVC)

Use it on

![GNOME Terminal](https://img.shields.io/badge/gnometerminal-%23ffffff.svg?style=for-the-badge&logo=gnometerminal&logoColor=%23241F31) (Linux)
![iTerm2](https://img.shields.io/badge/iTerm2-%23000000?style=for-the-badge&logo=iterm2&logoColor=white) (Linux / MacOS)
![Termius](https://img.shields.io/badge/termius-%23000000?style=for-the-badge&logo=termius&logoColor=white) (Cloud)
![tmux](https://img.shields.io/badge/tmux-%23000000?style=for-the-badge&logo=tmux&logoColor=%231BB91F) (Linux / MacOS)
![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white) (Cloud)
