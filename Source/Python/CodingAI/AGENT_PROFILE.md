# Agent Profile — Python CodingAI

> 📋 Inherits from: [Python Profile](../AGENT_PROFILE.md) · [General Profile](../../../AGENT_PROFILE.md)

## Domain

- **Scope:** AI agent control within `Source/Python/`
- **Purpose:** Agents that write, review, and manage Python source code

## Agent Rules (Python AI)

1. **All Python conventions from the [Python Profile](../AGENT_PROFILE.md) apply strictly.**
2. **Before writing code:** read the relevant README.txt and AGENT_PROFILE.md
3. **After writing code:** run `pytest` (once tests exist) and `ruff` or `black` for formatting
4. **No silent assumptions** — if unsure about a design decision, ask MCHIGM
5. **Explain changes** in the format:
   ```
   ## What I changed
   - [file]: [brief reason]
   ## Why
   - [rationale]
   ## Trade-offs
   - [any concerns]
   ```

## Module Ownership

| File | Role | Agent Notes |
|------|------|-------------|
| `files/KEEPER.py` | File state manager | Must preserve data integrity; never lose user files |
| `files/WIKI.py` | Doc generator | Must stay in sync with source |
| `library/LIBRARIAN.py` | Library index | Handle duplicates and missing entries |
| `library/WIKI.py` | Library docs | Auto-generated from LIBRARIAN |
| `modules/KEEPER.py` | Module registry | Thread-safe; support hot reload |
| `modules/externalLangMods/LOADER.py` | External loader | Must validate signatures before loading |

## Change Authorization

| Change type | Authorization |
|-------------|---------------|
| Bug fixes | ✅ Auto-approved (explain in commit) |
| New features | ⚠️ Ask MCHIGM first |
| Refactoring | ⚠️ Ask MCHIGM first |
| Dependency changes | ⚠️ Ask MCHIGM first |
| API / interface changes | 🚫 Requires explicit approval |
