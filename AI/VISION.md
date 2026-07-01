# VISION.md — Project Ideas & Communication Hub

> 🧠 **Purpose:** This is where MCHIGM records project ideas, vision, and design intent.
> AI agents: read this file to understand *why* things are built the way they are.
> MCHIGM: add, update, or remove ideas freely — this is your thinking space.

---

## Project Vision

*What is Mouse really about? Why does it exist?*

The Mouse project is a **computer vision cursor** — but more than that, it's an exploration of **two fundamentally different approaches to screen understanding**:

1. **Python (Direct Vision):** "See" the screen as a human would — capture the display output and use computer vision to locate and track the cursor. High-level, flexible, but potentially slower.

2. **Assembly (GPU Vision):** "See" the screen as the GPU sees it — intercept render data at the GPU level and learn from the raw output. Low-level, extremely fast, but tightly coupled to hardware.

The goal is to **compare, combine, and learn** from both approaches. Which one works better? Can they complement each other? What insights does the GPU path provide that the Python path misses?

---

## Current Ideas

*Add your ideas, questions, and design thoughts below.*


### Idea 1: [Title]

[Description]

### Idea 2: [Title]

[Description]

---

## Design Decisions Log

*Record important decisions and their rationale here.*

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-01 | Multi-language architecture (Python + Rust + TS + ASM + C++) | Each sub-problem needs the right tool; Python for CV prototyping, Rust for safe performant helpers, ASM for GPU-level access, C++ for CUDA interop |
| 2026-07-01 | Agent-first design (AI/ + CodingAI/) | The project is complex enough that AI agents will be essential for development velocity |
| 2026-07-01 | Dual-platform (Apple M4 Max + Intel Xeon/Nvidia 5000) | Must work on both architectures from day one to validate the dual-approach hypothesis |

---

## Questions & Open Issues

*Things we haven't figured out yet.*

- [ ] Which screen capture API to use on macOS? (ScreenCaptureKit? CGDisplay?)
- [ ] Which screen capture API to use on Windows? (DXGI Desktop Duplication?)
- [ ] How to benchmark ASM vs Python approaches fairly?
- [ ] Should the cursor be a physical device or an on-screen overlay?

---

## How Agents Should Use This File

1. **Read this before proposing major changes** — understand the intent behind the architecture
2. **Reference ideas in commit messages** — e.g., `feat: implement Idea 3 (GPU cursor tracking)`
3. **Suggest new ideas** — add them to the "Current Ideas" section with your name/agent tag
4. **Update the decision log** when a significant architectural choice is made
5. **Don't contradict the vision** — if you think an idea is wrong, discuss with MCHIGM first
