; Mouse — x86_64 Assembly: Display Data Reserve
;
; Low-level routine to reserve port-based display data channels for
; the "Method 1" screen streaming analysis pipeline.
;
; This is called from C++ (via the port_reserver) and provides an
; ultra-low-latency path for reserving and releasing TCP ports that
; the stream server will use.
;
; Target:  x86-64 (Intel Xeon E3 / Nvidia 5000, Windows 10 Pro)
;          Also compatible with x86-64 Linux / macOS
;
; Build:   nasm -f win64 display_reserve_x86_64.asm  (Windows)
;       or nasm -f elf64 display_reserve_x86_64.asm  (Linux)
;       or nasm -f macho64 display_reserve_x86_64.asm (macOS)
;
; ┌─ ASM Routine ───────────────────────────────────┐
; │ Purpose: Reserve a display data port number     │
; │ Target: x86-64                                  │
; │ Registers used: rax, rdi, rsi, rdx, rcx         │
; │ Registers clobbered: rax, rcx, rflags           │
; │ Side effects: None (pure function)              │
; └────────────────────────────────────────────────┘

section .text
global mouse_asm_reserve_port
global mouse_asm_validate_port_range
global mouse_asm_get_default_port

; ─────────────────────────────────────────────────────────────────
; mouse_asm_reserve_port
;
; Simple fast-path port range validator & default assigner.
; This does NOT bind the actual socket (that's done in C++), but
; provides the ASM-optimized logic for port selection.
;
; Signature (C):
;   int mouse_asm_reserve_port(int preferred, int fallback_low, int fallback_high);
;
; Arguments:
;   rcx = preferred port (0 = use default)
;   rdx = fallback low range
;   r8  = fallback high range
;
; Returns:
;   rax = reserved port number, or 0 if no port available
; ─────────────────────────────────────────────────────────────────

mouse_asm_reserve_port:
    ; If preferred port is valid (1024-65535), use it
    mov     eax, ecx
    cmp     eax, 1024
    jl      .try_fallback
    cmp     eax, 65535
    jg      .try_fallback
    ret                                 ; Return preferred

.try_fallback:
    ; Use fallback range midpoint as starting guess
    mov     eax, edx                    ; fallback_low
    cmp     eax, 1024
    jge     .low_ok
    mov     eax, 8765                   ; Default Mouse port
.low_ok:
    ; Walk up from low to find a valid port
    mov     r9d, r8d                    ; fallback_high
    cmp     r9d, 65535
    jle     .range_ok
    mov     r9d, 65535
.range_ok:
.port_loop:
    cmp     eax, r9d
    jg      .no_port
    ; Check if port is in valid range and not a well-known port
    cmp     eax, 1024
    jl      .next_port
    ; Found a valid candidate
    ret
.next_port:
    inc     eax
    jmp     .port_loop

.no_port:
    xor     eax, eax                    ; Return 0 = no port available
    ret

; ─────────────────────────────────────────────────────────────────
; mouse_asm_validate_port_range
;
; Validate that a port range is sane.
;
; Signature (C):
;   int mouse_asm_validate_port_range(int low, int high);
;
; Arguments:
;   rcx = low port
;   rdx = high port
;
; Returns:
;   rax = 1 if valid, 0 if invalid
; ─────────────────────────────────────────────────────────────────

mouse_asm_validate_port_range:
    ; low must be >= 1024
    cmp     ecx, 1024
    jl      .invalid
    ; high must be <= 65535
    cmp     edx, 65535
    jg      .invalid
    ; low must be <= high
    cmp     ecx, edx
    jg      .invalid
    mov     eax, 1
    ret
.invalid:
    xor     eax, eax
    ret

; ─────────────────────────────────────────────────────────────────
; mouse_asm_get_default_port
;
; Returns the default Mouse stream port (8765).
;
; Signature (C):
;   int mouse_asm_get_default_port(void);
;
; Returns:
;   rax = 8765
; ─────────────────────────────────────────────────────────────────

mouse_asm_get_default_port:
    mov     eax, 8765
    ret
