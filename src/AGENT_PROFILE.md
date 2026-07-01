# Agent Profile — Rust + TypeScript Core

> 📋 Inherits from: [General Profile](../../AGENT_PROFILE.md)

## Domain

- **Scope:** All source files under `src/` (Rust, TypeScript, PHTML)
- **Files:** `helper.rs` (Rust), `main.ts` (TypeScript), `index.phtml` (PHP/HTML)

## Rust Conventions (Strict — Memory Language)

### Safety
- **`unsafe` code:** 🚫 Banned unless:
  1. A benchmark proves it's necessary for performance
  2. The `unsafe` block is isolated in a dedicated module with `# Safety` doc comments
  3. MCHIGM approves it explicitly
- **`unwrap()` / `expect()`:** 🚫 Banned in production code — use proper error handling (`Result`, `?`, `anyhow`, `thiserror`)
- **Panics:** Must not panic in library code. Use `Result`-based error propagation.

### Style
- **`rustfmt`** with default settings — enforced
- **`clippy`** with `--deny warnings` — all warnings treated as errors
- **Documentation:** `///` doc comments on all public items, `//!` module docs
- **Module structure:** one module per file, `mod.rs` pattern discouraged (use `module_name.rs`)

### Performance
- Profile with `cargo-flamegraph` before optimizing
- Prefer stack allocation over heap when sizes are known
- Use `rayon` for data parallelism
- Target `x86_64-pc-windows-msvc` and `aarch64-apple-darwin`

### Testing
- Unit tests in the same file (`#[cfg(test)]` module)
- Integration tests in `tests/` directory
- Property-based testing with `proptest` for data structures

## TypeScript Conventions

### Style
- **Strict mode:** `"strict": true` in `tsconfig.json`
- **No `any`** — use `unknown` or proper types
- **Prettier** formatting with 2-space indent
- **ESLint** with recommended rules

### Runtime
- Primary: **Bun** (1.3.14+)
- Fallback: **Node.js** (26.4.0+)

## PHP / PHTML Conventions

- **PHP 8.5+** syntax
- Strict types: `declare(strict_types=1);`
- PHTML files: presentation only, no business logic
- Follow PSR-12 coding style
