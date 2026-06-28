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
| ZP indirect `($zp),y`      | 2 bytes      | 5-6c             | Repeated memory access        |
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
        sta row_start+39        ; ... repeat 40 times ...
        rts
```

## Branch Tuning

### Avoid Page-Crossing Branches

A branch that crosses a page boundary costs 4 cycles instead of 3.

```asm
        .org $01FE              ; Bad: target is on next page
        bne target              ; 4 cycles, page cross
        .org $0200

target:
```

### Compare-Free Decisions

```asm
        cpx #$10                ; Instead of:
        bcs big

        cpx #$10                ; Use: still need CMP/CPX for threshold checks
        ldx #$10                ; But for simple loops, count down to zero:
loop:

        dex                     ; ...
        bne loop
```

## Zero-Page Efficiency

Zero-page access is 1 cycle faster than absolute and 1 byte smaller.

| Access Type   | Bytes | Cycles |
|---------------|-------|--------|
| `LDA $zp`     | 2     | 3      |
| `LDA $8000`   | 3     | 4      |
| `LDA ($zp),y` | 2     | 5      |
| `LDA $8000,x` | 3     | 4-5    |

### Using ZP Pointers

ZP indirect addressing (`($zp),y`) requires two contiguous ZP bytes for the pointer. On PET BASIC 2, most ZP is consumed by the KERNAL and BASIC; there is no free block you can assume. If a routine needs ZP pointers internally, save and restore the bytes it borrows.

Only $FF is documented unused in PET BASIC 2. $FB-$FE are used by KERNAL tape routines; borrow them only when tape I/O will not run concurrently.

```asm
copy_block:

        lda $FC                 ; Routine borrowing $FB/$FC as a pointer -- saves and restores both. save borrowed ZP bytes
        pha
        lda $FB
        pha

        stx $FB                 ; X/Y = address of source in free RAM
        sty $FC

        ldy #0

copy_loop:

        lda ($FB),y             ; indirect read using borrowed ZP pointer
        sta $8000,y             ; absolute write to fixed dest
        iny
        bne copy_loop

        pla                     ; restore borrowed ZP bytes
        sta $FB
        pla
        sta $FC
        rts
```

For routines that accept an arbitrary source address via X/Y parameter, the self-modifying approach avoids ZP entirely -- see the compression routines in compression.md for worked examples.

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
        ldx #39                 ; Copy 40 bytes (one row) as fast as possible

loop:

        lda src_row,x
        sta dst_row,x
        dex
        bpl loop
```

### No Dedicated Sound

Sound requires bit-banging the VIA user port or using the internal beeper via KERNAL.

## Compare-Free Loops

### Down-Count with BNE

```asm
        ldx #$28                ; 40 iterations
loop:

        dex                     ; ... body ...
        bne loop
```

### Up-Count with BPL

```asm
        ldx #$00
loop:

        inx                     ; ... body ...
        bpl loop                ; stops at 128 iterations
```

### X-Driven Table Walk (0 to N-1)

```asm
        ldx #$00
loop:

        lda table,x
        inx                     ; ... use A ...
        cpx #size
        bne loop
```
