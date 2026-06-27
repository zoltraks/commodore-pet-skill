# Compression Patterns

## Purpose

> **Scope:** RLE, byte-run, frame-delta, decompression routines for PET screen data and animation
> **Key items:** RLE flag bytes, run length encoding, delta frames, screen-oriented depackers

This file covers compression patterns for the PET 3032 in four progressive layers:

- **Quick-lookup table** - scan or search for the pattern you need
- **Format descriptions** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

## RLE for Screen Codes ($00 Escape)

### Why This Variant

PET screen codes include values > 127 (inverse video via bit 7). A sign-bit flag (`bmi`) cannot distinguish literal `$81` from a repeat marker. This variant uses `$00` as an escape because `$00` (the `@` screen code) is rare in typical screen content.

### Format

| Pattern          | Bytes | Meaning                       |
|------------------|-------|-------------------------------|
| `XX` (XX != $00) | 1     | Literal: write XX once        |
| `00 CC VV`       | 3     | Repeat: write VV for CC times |

**Repeat count wraparound:**
 A count of `$00` means 256 repetitions because `dec` wraps from `$00` to `$FF` (non-zero).

**Literal zero:** `$00 $01 $00` encodes a single `$00` screen code.

### Example Encoding

```
$66                    ; literal: one $66
$00 $00 $66            ; repeat: $66 for 256 times
$00 $E8 $66            ; repeat: $66 for 232 times
```

A full screen of `$66` (1000 bytes) compresses to 12 bytes:
```
$00,$00,$66,$00,$00,$66,$00,$00,$66,$00,$E8,$66
```

### Decompressor

Uses self-modifying pointers (`rle_read+1/+2`, `rle_write+1/+2`) for source and destination access -- no zero-page indirection needed. Borrows ZP $FB-$FE for working registers; saves and restores all four.

**Calling convention:** X = low byte, Y = high byte of a 6-byte parameter block in free RAM.

```
; parameter block layout:
; +0 src lo  +1 src hi  +2 dst lo  +3 dst hi  +4 len lo  +5 len hi
```

```asm
; ZP borrowed: $FB = repeat counter  $FC = repeat character
;              $FD = len lo          $FE = len hi

decompress_rle:

        lda $FE
        pha
        lda $FD
        pha
        lda $FC
        pha
        lda $FB
        pha

        stx rle_param+1     ; patch param block address into reader
        sty rle_param+2
        ldy #0

rle_param:

        lda $FFFF,y         ; src lo (self-modified to param block)
        sta rle_read+1
        iny
        lda $FFFF,y         ; src hi
        sta rle_read+2
        iny
        lda $FFFF,y         ; dst lo
        sta rle_write+1
        iny
        lda $FFFF,y         ; dst hi
        sta rle_write+2
        iny
        lda $FFFF,y         ; len lo
        sta $FD
        iny
        lda $FFFF,y         ; len hi
        sta $FE

        ldx #0              ; X = source index
        ldy #0              ; Y = dest index

rle_loop:

        lda #1
        sta $FB             ; repeat count = 1 (literal default)
        jsr rle_read
        beq rle_escape      ; $00 begins an escape run

rle_write:

        sta $FFFF,y         ; write to dest (self-modified)

        lda $FD             ; decrement byte count
        bne rle_dec_lo
        lda $FE
        beq rle_exit        ; count exhausted
        dec $FE

rle_dec_lo:

        dec $FD
        iny                 ; advance dest index
        bne rle_next
        inc rle_write+2     ; dest page crossed

rle_next:

        dec $FB             ; repeat counter--
        bne rle_write_back  ; still copies remaining
        jsr rle_progress    ; advance source past current byte
        jmp rle_loop

rle_write_back:

        lda $FC             ; reload repeat character
        jmp rle_write

rle_escape:

        jsr rle_progress    ; past $00
        jsr rle_read
        sta $FB             ; repeat count from stream
        jsr rle_progress
        jsr rle_read
        sta $FC             ; character to repeat
        jmp rle_write       ; write $FB copies of $FC

rle_exit:

        pla
        sta $FB
        pla
        sta $FC
        pla
        sta $FD
        pla
        sta $FE
        rts

rle_read:

        lda $FFFF,x         ; self-modified: base = source start
        rts

rle_progress:

        inx
        bne rle_prog_skip
        inc rle_read+2      ; source page crossed

rle_prog_skip:

        rts
```

### Usage Example

```asm
rle_block:

        word packed_screen  ; src address
        word $8000          ; dst = screen RAM
        word $03E8          ; len = 1000 bytes (40x25)

        ldx #<rle_block
        ldy #>rle_block
        jsr decompress_rle
```

## Byte-Run (Alternative Simple RLE)

A simpler format for data without many literal singles: alternate count and value, with `$00` as end marker. Less efficient than the `$00`-escape variant above when mixed literals and runs are common.

```
$05 $20                ; 5 spaces
$03 $41                ; 3 'A's
$00                    ; end marker
```

### Byte-Run Decompressor

Uses self-modifying pointers for source reads and a self-modifying absolute write for destination -- no zero-page required.

**Calling convention:** X = low byte, Y = high byte of a 4-byte parameter block in free RAM.

```
; parameter block layout:
; +0 src lo  +1 src hi  +2 dst lo  +3 dst hi
```

```asm
decompress_byte_run:

        stx br_param+1      ; patch param block address
        sty br_param+2
        ldy #0

br_param:

        lda $FFFF,y         ; src lo (self-modified to param block)
        sta br_src+1
        iny
        lda $FFFF,y         ; src hi
        sta br_src+2
        iny
        lda $FFFF,y         ; dst lo
        sta br_write+1
        iny
        lda $FFFF,y         ; dst hi
        sta br_write+2

        ldx #0              ; X = source index

br_loop:

        jsr br_src          ; read count byte
        beq br_done         ; count $00 = end of stream
        tay                 ; Y = number of copies
        jsr br_advance
        jsr br_src          ; A = value byte
        jsr br_advance      ; advance past value; A preserved

br_write:

        sta $FFFF           ; write to dest (self-modified, no index)

        inc br_write+1      ; advance dest address
        bne br_cnt
        inc br_write+2

br_cnt:

        dey
        bne br_write        ; write same value again
        jmp br_loop

br_done:

        rts

br_src:

        lda $FFFF,x         ; self-modified: base = source start
        rts

br_advance:

        inx
        bne br_adv_skip
        inc br_src+2        ; source page crossed

br_adv_skip:

        rts
```

### Usage Example

```asm
br_block:

        word packed_data    ; src address
        word target_buffer  ; dst address

        ldx #<br_block
        ldy #>br_block
        jsr decompress_byte_run
```

## Frame-Delta Compression

For animation, store only changed bytes between frames.

### Format

Each delta record: 3 bytes (offset low, offset high, new value)
Terminated by offset $FFFF.

```
$10 $80 $41           ; screen[$8010] = $41
$25 $80 $42           ; screen[$8025] = $42
$FF $FF               ; end of delta
```

### Delta Applier

Uses self-modifying code for source reads; patches each write address directly from the delta record. No zero-page required.

**Calling convention:** X = low byte, Y = high byte of a 2-byte parameter block in free RAM.

```
; parameter block layout:
; +0 src lo  +1 src hi
```

```asm
apply_delta:

        stx dl_param+1      ; patch param block address
        sty dl_param+2
        ldy #0

dl_param:

        lda $FFFF,y         ; src lo (self-modified to param block)
        sta dl_read+1
        iny
        lda $FFFF,y         ; src hi
        sta dl_read+2

        ldx #0              ; X = source index

dl_loop:

        jsr dl_read         ; dst lo
        tay                 ; save dst lo in Y
        jsr dl_advance
        jsr dl_read         ; dst hi (in A)
        cpy #$FF
        bne dl_not_end      ; dst lo != $FF: not end marker
        cmp #$FF
        beq dl_done         ; both $FF: end of stream

dl_not_end:

        sty dl_write+1      ; patch dest address lo
        sta dl_write+2      ; patch dest address hi
        jsr dl_advance
        jsr dl_read         ; value to write (in A)
        jsr dl_advance

dl_write:

        sta $FFFF           ; write to patched screen address
        jmp dl_loop

dl_done:

        rts

dl_read:

        lda $FFFF,x         ; self-modified: base = source start
        rts

dl_advance:

        inx
        bne dl_adv_skip
        inc dl_read+2       ; source page crossed

dl_adv_skip:

        rts
```

### Usage Example

```asm
dl_block:

        word frame_delta    ; src address (delta stream)

        ldx #<dl_block
        ldy #>dl_block
        jsr apply_delta
```

## Screen-Oriented Packing

For full-screen images (1000 bytes), RLE works well because the PET screen has large runs of spaces and repeated characters.

### Typical Compression Ratios

| Content Type         | RLE Ratio | Notes                             |
|----------------------|-----------|-----------------------------------|
| Empty screen         | 20:1      | 1000 spaces -> 3 bytes            |
| Solid pattern        | 83:1      | 1000 identical codes -> 12 bytes  |
| Text pages           | 3:1       | Moderate runs with mixed literals |
| Graphics/art         | 1.2:1     | Little repetition; may expand     |
| Character animations | 2:1       | Repeated frames; delta may help   |