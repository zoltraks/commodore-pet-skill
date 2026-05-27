# Optimization Patterns

## Purpose

> **Scope:** 6502 size/speed trade-offs, unrolled loops, branch tuning, zero-page usage, PET-specific constraints
> **Key items:** 7-cycle penalty branches, unrolled screen copies, ZP indirect vs absolute, RTS chains

This file covers optimization patterns for the PET 3032 in four progressive layers:

- **Quick-lookup table** - scan or search for the pattern you need
- **Reference tables** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

## Size vs Speed Quick Reference

| Technique                  | Size         | Speed            | Use When                      |
|----------------------------|--------------|------------------|-------------------------------|
| ZP indirect `($F7),y`      | 2 bytes      | 5-6c             | Repeated memory access        |
| Absolute `$8000`           | 3 bytes      | 4c               | One-off access                |
| Indexed absolute `$8000,x` | 3 bytes      | 4-5c             | Fixed-base table walk         |
| Unrolled loop              | large        | fastest          | Tight inner loop, small count |
| BNE countdown              | 2 bytes/iter | 3c/iter + branch | Generic loop                  |
| JMP table                  | medium       | 3c dispatch      | Multi-way branch              |
| Inline code                | large        | no JSR/RTS       | One-shot sequence             |

## Unrolled Loops

The PET has no DMA and no hardware copy assist. For maximum speed, unroll loops that touch screen RAM or copy data.

### Unrolled Screen Row Clear (40 bytes)

```asm
clear_row:

        lda #$20
        ldx #39

loop:

        sta row_start,x
        dex
        bpl loop
        rts
```

### Fully Unrolled (fastest, largest)

```asm
clear_row_fast:

        lda #$20
        sta row_start+0
        sta row_start+1
        sta row_start+2
        ; ... repeat 40 times ...
        sta row_start+39
        rts
```

## Branch Tuning

### Avoid Page-Crossing Branches

A branch that crosses a page boundary costs 4 cycles instead of 3.

```asm
        ; Bad: target is on next page
        .org $01FE
        bne target      ; 4 cycles, page cross
        .org $0200


target:

```

### Compare-Free Decisions

```asm
        ; Instead of:
        cpx #$10
        bcs big

        ; Use:
        cpx #$10        ; still need CMP/CPX for threshold checks
        ; But for simple loops, count down to zero:
        ldx #$10
loop    ; ...
        dex
        bne loop
```

## Zero-Page Efficiency

Zero-page access is 1 cycle faster than absolute and 1 byte smaller.

| Access Type   | Bytes | Cycles |
|---------------|-------|--------|
| `LDA $F7`     | 2     | 3      |
| `LDA $8000`   | 3     | 4      |
| `LDA ($F7),y` | 2     | 5      |
| `LDA $8000,x` | 3     | 4-5    |

### Keep Pointers in Zero Page

```asm
source_lo = $F7
source_hi = $F8
dest_lo   = $F9
dest_hi   = $FA

        lda (source_lo),y
        sta (dest_lo),y
```

## Stack Shortcuts

### RTS as Jump Table

```asm
        ldx index
        lda jump_table_hi,x
        pha
        lda jump_table_lo,x
        pha
        rts                     ; jumps to address from stack

jump_table_lo:

        .byte <handler0, <handler1, <handler2

jump_table_hi:

        .byte >handler0, >handler1, >handler2
```

### Fast Parameter Passing via Stack

```asm
        lda param
        pha
        jsr routine
        pla                     ; retrieve if needed
```

## PET-Specific Constraints

### No Hardware Sprites

All graphics are character-based. Animation requires writing to screen RAM directly or switching character sets via PCR.

### No Hardware Scroll

Scrolling requires copying screen RAM in software. Optimize by copying in blocks:

```asm
; Copy 40 bytes (one row) as fast as possible
        ldx #39

loop:

        lda src_row,x
        sta dst_row,x
        dex
        bpl loop
```

### No Dedicated Sound

Sound requires bit-banging the VIA user port or using the internal beeper via KERNAL.
