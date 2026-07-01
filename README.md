# Mouse
A simple computer vision cursor!

> 📖 **New here?** Start with [GETTING_STARTED.md](GETTING_STARTED.md) — the hands-on guide with setup, build, and development workflows.
> 🧠 Agent conventions: [AGENT_PROFILE.md](AGENT_PROFILE.md) | 💡 Project ideas: [AI/VISION.md](AI/VISION.md)

## Supported Systems

| Platform | OS | CPU | GPU | Status |
|----------|----|-----|-----|--------|
| **Mac (Dev)** | macOS (Darwin) & Arch Linux (Duel boot) | Apple M4 Max (arm64) | Apple Silicon GPU | ✅ Active Development |
| **PC** | Windows 10 Pro & Kali Linux (WSL) & Ubuntu 22 (Hyper-V) | Intel Xeon E3 (x86-64) | Intel Arc + Nvidia 5000 (CUDA) | ✅ Active |

## Tech Stack

| Language | Role | Status |
|----------|------|--------|
| Python | Core logic, computer vision, agent control | 🚧 Scaffolding |
| Rust | Performance-critical helpers | 🚧 Scaffolding |
| TypeScript | Frontend / web layer | 🚧 Scaffolding |
| Assembly | Low-level GPU screen capture | 🚧 Scaffolding |
| C++ | GPU interop / CUDA | 🚧 Scaffolding |
| PHTML | Templates | 🚧 Scaffolding |

## Project Structure

```
Mouse/
├── src/            # Core source (Rust, TypeScript, PHTML)
├── Source/         # Language-specific implementations
│   ├── Python/     # Main Python codebase + CodingAI agents
│   ├── ASM/        # GPU-level assembly implementations
│   └── C++/        # C++ / CUDA implementations
├── AI/             # AI agent skills, tools & plugins (workspace-wide)
├── APP/            # Application output
├── Data/           # Data files
└── Folders/        # User / guest / public file spaces
```
