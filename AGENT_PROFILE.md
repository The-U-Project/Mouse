# Agent Profile — Mouse (General)

> ⚠️ This is the **master profile**. All specialized profiles inherit from this one.
> Specialized profiles: [Python](Source/Python/AGENT_PROFILE.md) · [Python AI](Source/Python/CodingAI/AGENT_PROFILE.md) · [Rust/TS](src/AGENT_PROFILE.md) · [ASM](Source/ASM/AGENT_PROFILE.md) · [C++](Source/C++/AGENT_PROFILE.md) · [Workspace AI](AI/AGENT_PROFILE.md)
> Vision & ideas: [VISION.md](AI/VISION.md)

## Maintainer

- **Name / Handle:** MCHIGM
- **Contact:** [Add your email/GitHub if desired]
- **Role:** Project owner, architect, primary developer

## Project Identity

- **Name:** Mouse
- **Tagline:** A simple computer vision cursor
- **Description:** A multi-language, dual-approach computer vision system that tracks and controls a cursor by directly analyzing screen output (Python) and by learning from GPU render data (Assembly). Targets both Apple Silicon (M4 Max, macOS) and Intel + Nvidia (Xeon E3, Nvidia 5000, Windows 10 Pro).

## Project Lifecycle

- **Current phase:** 🚧 Early scaffolding — directory structure built, no implementation yet
- **Target audience:** Developers, power users, accessibility applications
- **Deployment:** Cross-platform binary / application

## Supported Systems

| Platform | OS | CPU | GPU | Status |
|----------|----|-----|-----|--------|
| Mac (Dev) | macOS (Darwin) | Apple M4 Max (arm64) | Apple Silicon GPU | ✅ Active Development |
| PC (Target) | Windows 10 Pro | Intel Xeon E3 (x86-64) | Nvidia 5000 (CUDA) | 🎯 Planned Support |

## Coding Philosophy

- **Pragmatic** — choose the right tool for each sub-problem
- **Performance-conscious** — computer vision is latency-sensitive; profile before optimizing
- **Multi-paradigm** — OOP for high-level organization, functional for data pipelines, procedural for hot paths

## General Agent Rules (All Languages)

1. **Ask before system changes** — never install packages, modify configs, or alter PATH without confirmation
2. **Cross-platform thinking** — every decision must consider both arm64/macOS and x86-64/Windows targets
3. **Strict conventions for memory languages** — Rust, C++, and ASM must follow the strict rules in their specialized profiles
4. **Strict conventions for Python** — follow the Python specialized profile for all Python code
5. **Read before write** — check existing README.txt files in any directory before making changes
6. **Commit style:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`)
7. **Always run tests** (once they exist) before suggesting a PR or finalizing changes
8. **Prefer simple solutions** over clever ones — readability first

## Communication Preferences

- Be direct and concise
- Show before/after diffs for code changes
- Explain non-obvious trade-offs
- Reference relevant README.txt files when touching a directory
