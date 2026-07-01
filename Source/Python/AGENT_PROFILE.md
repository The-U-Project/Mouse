# Agent Profile — Python Source

> 📋 Inherits from: [General Profile](../../AGENT_PROFILE.md)

## Domain

- **Scope:** All Python code under `Source/Python/`
- **Approach:** Direct screen capture — "seeing" the screen via Python computer vision

## Python Conventions (Strict)

### Style
- **PEP 8** — enforced; no exceptions
- **Type hints** — mandatory on all function signatures (`def foo(x: int) -> str:`)
- **Docstrings** — Google-style docstrings on all public functions and classes
- **Line length:** 100 characters max
- **Imports:** `isort` order (stdlib → third-party → local); no wildcard imports

### Naming
- **Classes:** `PascalCase`
- **Functions / methods:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private members:** prefix with single underscore `_private_method`
- **Modules:** short, lowercase, no underscores unless necessary

### Testing
- **Framework:** `pytest`
- **Coverage:** minimum 80% on all modules
- **Test files:** mirror source structure under a `tests/` directory
- **No test:** no merge — untested features are incomplete

### Performance
- Use `numpy` for array operations — no raw Python loops over pixel data
- Prefer `asyncio` for I/O-bound tasks (screen capture, file I/O)
- Use `multiprocessing` or subprocess for CPU-bound tasks, not threads
- Profile with `cProfile` before optimizing

### Error Handling
- Explicit exception types — never bare `except:`
- Custom exception hierarchy under `exceptions.py` in each module
- Log errors with `logging`, not `print()`

## Directory-Specific Rules

### `files/`
- KEEPER.py: Manages file persistence and state. Must be idempotent.
- WIKI.py: Documentation generation. Must output valid markdown.

### `library/`
- LIBRARIAN.py: Library index/catalog. Must handle missing entries gracefully.
- WIKI.py: Library documentation. Sync with actual code.

### `modules/`
- KEEPER.py: Module registry. Must support hot-reload.
- `externalLangMods/`: External language module loader. Must validate before loading.

### `CodingAI/`
- See [Python AI Profile](../CodingAI/AGENT_PROFILE.md) for agent control rules.
