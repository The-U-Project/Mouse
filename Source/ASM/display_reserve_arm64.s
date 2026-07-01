// Mouse — ARM64 (AArch64) Assembly: Display Data Reserve
//
// ARMv8 equivalent of display_reserve_x86_64.asm for Apple Silicon
// (M4 Max) and other aarch64 platforms.
//
// Provides ultra-low-latency port selection logic called from the
// C++ port_reserver module.
//
// Target:  macOS arm64 (M4 Max) / Linux aarch64
//
// Build:   clang -arch arm64 -c display_reserve_arm64.s   (macOS)
//       or as   -o display_reserve_arm64.o display_reserve_arm64.s  (Linux)
//
// ┌─ ASM Routine ───────────────────────────────────┐
// │ Purpose: Reserve a display data port number     │
// │ Target: ARM64 (AArch64)                         │
// │ Registers used: x0-x4, x9                       │
// │ Registers clobbered: x0, x9, nzcv (flags)       │
// │ Side effects: None (pure function)              │
// └────────────────────────────────────────────────┘

.text
.global _mouse_asm_reserve_port
.global _mouse_asm_validate_port_range
.global _mouse_asm_get_default_port

// macOS prepends underscores; Linux does not.
// Apple assembler uses .p2align; gas uses .balign
.p2align 4

// ─────────────────────────────────────────────────────────────────
// mouse_asm_reserve_port
//
// Signature (C):
//   int mouse_asm_reserve_port(int preferred, int fallback_low,
//                              int fallback_high);
//
// ARM64 calling convention:
//   x0 = preferred port
//   x1 = fallback_low
//   x2 = fallback_high
//   x0 = return value
//
// Returns:
//   x0 = reserved port number, or 0 if no port available
// ─────────────────────────────────────────────────────────────────

_mouse_asm_reserve_port:
    // If preferred >= 1024 && preferred <= 65535, return it
    cmp     w0, #1024
    b.lt    Ltry_fallback
    cmp     w0, #65535
    b.gt    Ltry_fallback
    ret                                 // Valid preferred port → return it

Ltry_fallback:
    // Clamp fallback_low to 1024 minimum
    mov     w0, w1                      // fallback_low
    cmp     w0, #1024
    b.ge    Llow_ok
    mov     w0, #8765                   // Default Mouse port
Llow_ok:
    // Clamp fallback_high to 65535 maximum
    mov     w9, w2                      // fallback_high
    cmp     w9, #65535
    b.le    Lrange_ok
    mov     w9, #65535

Lrange_ok:
    // Walk port range looking for a valid port
Lport_loop:
    cmp     w0, w9
    b.gt    Lno_port
    cmp     w0, #1024
    b.ge    Lfound                      // Found valid port
    add     w0, w0, #1
    b       Lport_loop

Lfound:
    ret

Lno_port:
    mov     w0, #0
    ret

// ─────────────────────────────────────────────────────────────────
// mouse_asm_validate_port_range
//
// Signature (C):
//   int mouse_asm_validate_port_range(int low, int high);
//
// x0 = low, x1 = high
// Returns x0 = 1 if valid, 0 if invalid
// ─────────────────────────────────────────────────────────────────

_mouse_asm_validate_port_range:
    // low >= 1024
    cmp     w0, #1024
    b.lt    Linvalid
    // high <= 65535
    cmp     w1, #65535
    b.gt    Linvalid
    // low <= high
    cmp     w0, w1
    b.gt    Linvalid

    mov     w0, #1
    ret

Linvalid:
    mov     w0, #0
    ret

// ─────────────────────────────────────────────────────────────────
// mouse_asm_get_default_port
//
// Signature (C):
//   int mouse_asm_get_default_port(void);
//
// Returns x0 = 8765
// ─────────────────────────────────────────────────────────────────

_mouse_asm_get_default_port:
    mov     w0, #8765
    ret
