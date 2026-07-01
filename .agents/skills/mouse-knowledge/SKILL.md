---
name: mouse-knowledge
description: >-
  NotebookLM-style knowledge management for the Mouse project. RAG-inspired:
  indexes project documentation, README files, agent profiles, and source code
  to answer questions about the codebase. Use this when the user asks
  "what does X do?", "how is Y structured?", "where is Z?", or wants to
  learn about any part of the project.
---

# Mouse Knowledge (RAG-Inspired)

A NotebookLM-like knowledge system for the Mouse project. Indexes, retrieves, and synthesizes information from across the codebase to answer questions and build understanding.

## Knowledge Sources (Index)

When activated, scan and index these information sources in order of priority:

### Primary Sources (always read first)

| Source | Path | Content |
|--------|------|---------|
| Vision | `AI/VISION.md` | Project ideas, design decisions, open questions |
| General Profile | `AGENT_PROFILE.md` | Maintainer, conventions, lifecycle |
| Agent Instructions | `GETTING_STARTED.md` | Build commands, tech stack, structure |
| Workspace AI | `AI/AGENT_PROFILE.md` | Toolchain, jurisdiction, agent rules |
| Skills Index | `.agents/skills/` | Project-local Zed agent skills |

### Directory Context (read relevant one)

| Directory | README | Profile | What it tells you |
|-----------|--------|---------|-------------------|
| `AI/` | `AI/README.txt` | `AI/AGENT_PROFILE.md` | Agent control, public scope |
| `Source/Python/` | `Source/Python/README.txt` | `Source/Python/AGENT_PROFILE.md` | Direct screen capture approach |
| `Source/Python/CodingAI/` | `Source/Python/CodingAI/README.txt` | `Source/Python/CodingAI/AGENT_PROFILE.md` | Agent rules for Python code |
| `Source/ASM/` | `Source/ASM/README.txt` | `Source/ASM/AGENT_PROFILE.md` | GPU-level screen capture |
| `Source/C++/` | — | `Source/C++/AGENT_PROFILE.md` | CUDA interop, MSVC support |
| `src/` | — | `src/AGENT_PROFILE.md` | Rust/TS/PHP conventions |

### Source Code (search when needed)

| Language | Directory | Key files |
|----------|-----------|-----------|
| Python | `Source/Python/` | `files/`, `library/`, `modules/` |
| Rust | `src/` | `main.rs`, `helper.rs` |
| TypeScript | `src/` | `main.ts` |
| PHP | `src/` | `index.phtml` |
| Assembly | `Source/ASM/` | *(empty)* |
| C++ | `Source/C++/` | `CMakeLists.txt` |

### Skills (Agent Automation)

| Skill | Path | What it does |
|-------|------|-------------|
| mouse-build | `.agents/skills/mouse-build/` | Build all components (Python, Rust, C++) for macOS & Windows |
| mouse-test | `.agents/skills/mouse-test/` | Run tests across all languages |
| mouse-lint | `.agents/skills/mouse-lint/` | Lint and format all code |
| mouse-cross | `.agents/skills/mouse-cross/` | Cross-compile and verify for Windows |
| mouse-dev | `.agents/skills/mouse-dev/` | Full dev loop — watch, rebuild, test |
| mouse-knowledge | `.agents/skills/mouse-knowledge/` | RAG-inspired knowledge management |
| mouse-release | `.agents/skills/mouse-release/` | Update docs, commit, push, create PR |

## How to Answer Questions

### When the user asks "What is X?" or "Explain Y?"

1. **Search primary sources** — check VISION.md, GETTING_STARTED.md, README files
2. **Search code** — grep for relevant symbols, classes, functions
3. **Synthesize** — combine findings into a clear answer
4. **Cite sources** — reference which file you found the info in

### When the user asks "Where is Z?"

1. **grep** across the project for the symbol/name
2. **Find README.txt** in the containing directory for context
3. **Report:** file path + relevant README context

### When the user asks "How does the project work?"

Present a structured overview:

```
## Mouse — How It Works

### Architecture
[Dual-approach diagram / explanation]

### Key Directories
[What each directory does, from README files]

### Data Flow
[How data moves through the system]

### Key Decisions
[From VISION.md decision log]
```

## Indexing (Automatic)

On first activation in a session:

1. **Read all README.txt files** — build a map of what each directory does
2. **Read all AGENT_PROFILE.md files** — build a map of conventions per directory
3. **Read VISION.md** — understand project intent and open questions
4. **Scan source tree** — build a symbol map (classes, functions, modules)

## Knowledge Synthesis

When asked to "learn about" or "deep dive into" a topic:

1. Search all README.txt + AGENT_PROFILE.md + VISION.md for mentions
2. Grep source code for related symbols
3. Present findings as a structured knowledge card:

```markdown
## 📚 Knowledge Card: [Topic]

### What it is
[Concise explanation]

### Where it lives
- Primary: `path/to/file`
- Related: `path/to/related`

### How it works
[Step-by-step or diagram]

### Conventions
[Relevant rules from AGENT_PROFILE.md]

### Open Questions
[From VISION.md if applicable]
```

## Memory

Track what was discussed across sessions by reading and updating:
- `AI/VISION.md` — add new ideas or decisions
- Relevant `README.txt` — update if directory purpose changes
- Never modify `AGENT_PROFILE.md` without asking MCHIGM
