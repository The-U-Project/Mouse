# Agent Profile — Workspace AI

> 📋 Inherits from: [General Profile](../AGENT_PROFILE.md)

## Domain

- **Scope:** All AI agent activity in this workspace
- **Role:** Controls how AI agents operate across the entire `Pjt-Mouse` project
- **Public scope:** Rules here apply to every directory and file in this workspace

## Communication Rules

1. **Wizard-style interaction** — agents must announce what they're about to do and confirm before proceeding
2. **No silent changes** — every action must be explained
3. **Read before write** — check relevant README.txt and AGENT_PROFILE.md before touching any directory
4. **Respect boundaries** — specialized profiles take precedence over general rules

## Directory Jurisdiction

| When touching... | Apply rules from... |
|------------------|---------------------|
| Any file | [General Profile](../AGENT_PROFILE.md) |
| `Source/Python/**` | [Python Profile](../Source/Python/AGENT_PROFILE.md) |
| `Source/Python/CodingAI/**` | [Python AI Profile](../Source/Python/CodingAI/AGENT_PROFILE.md) |
| `src/**` | [Rust/TS Profile](../src/AGENT_PROFILE.md) |
| `Source/ASM/**` | [ASM Profile](../Source/ASM/AGENT_PROFILE.md) |
| `Source/C++/**` | [C++ Profile](../Source/C++/AGENT_PROFILE.md) |

## Toolchain Context (Auto-Discovered)

| Language | Tool | Version |
|----------|------|---------|
| Python | python3 + pip3 + uv + mamba | 3.14.4 |
| Rust | rustup (stable) + cargo | 1.95.0 |
| TypeScript | Bun (primary) / Node.js (fallback) | Bun 1.3.14 / Node 26.4.0 |
| C++ | Clang + cmake / MSVC (Win) | Clang 22.1.4 / cmake 4.3.4 |
| PHP | php | 8.5.7 |
| GPU | Apple Silicon GPU / Nvidia 5000 (CUDA planned) | — |

## Agent Self-Management

- Profiles can be updated by agents when conventions evolve — but must note the change in commit
- If a rule is consistently causing problems, the agent should flag it to MCHIGM
- New specialized profiles can be created for new directories as they're added
