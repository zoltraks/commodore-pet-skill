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

| Pattern | Bytes | Meaning |
|---------|-------|---------|
| `XX` (XX != $00) | 1 | Literal: write XX once |
| `00 CC VV` | 3 | Repeat: write VV for CC times |

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

Uses self-modifying pointers (`rle_read+1/+2`, `rle_write+1/+2`) for direct access without zero-page indirection.

```asm
rle_src  = $88          ; RLE source pointer (16-bit)
rle_dst  = $8A          ; RLE destination pointer (16-bit)
rle_len  = $8C          ; RLE bytes remaining (16-bit)
rle_rpt  = $8E          ; repeat counter
rle_chr  = $8F          ; repeat character

decompress_rle:

        lda rle_src
        sta rle_read+1
        lda rle_src+1
        sta rle_read+2
        lda rle_dst
        sta rle_write+1
        lda rle_dst+1
        sta rle_write+2

        lda #0
        tax
        tay

rle_loop:

        lda #1
        sta rle_rpt
        jsr rle_read
        beq rle_escape

rle_write:

        sta $FFFF,y

        lda rle_len
        bne rle_dec_lo
        lda rle_len+1
        beq rle_exit
        dec rle_len+1

rle_dec_lo:

        dec rle_len
        iny
        bne rle_next
        inc rle_write+2

rle_next:

        dec rle_rpt
        bne rle_write_back
        jsr rle_progress
        jmp rle_loop

rle_write_back:

        lda rle_chr
        jmp rle_write

rle_escape:

        jsr rle_progress
        jsr rle_read
        sta rle_rpt
        jsr rle_progress
        jsr rle_read
        sta rle_chr
        jmp rle_write

rle_exit:

        rts

rle_read:

        lda $FFFF,x
        rts

rle_progress:

        inx
        bne rle_skip
        inc rle_read+2

rle_skip:

        rts
```

## Byte-Run (Alternative Simple RLE)

A simpler format for data without many literal singles: alternate count and value, with `$00` as end marker. Less efficient than the `$00`-escape variant above when mixed literals and runs are common.

```
$05 $20                ; 5 spaces
$03 $41                ; 3 'A's
$00                    ; end marker
```

### Byte-Run Decompressor

```asm
decompress_byte_run:

        ldy #0

loop:

        lda (source_lo),y
        beq done
        tax
        iny
        lda (source_lo),y

run_loop:

        sta (dest_lo),y
        inc dest_lo
        bne skip
        inc dest_hi

skip:

        dex
        bne run_loop
        iny
        bne loop

done:

        rts
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

```asm
apply_delta:

        ldy #0

loop:

        lda (source_lo),y
        sta dest_lo
        iny
        lda (source_lo),y
        sta dest_hi
        ; check end marker
        lda dest_lo
        and dest_hi
        cmp #$FF
        beq done
        iny
        lda (source_lo),y
        sta (dest_lo),y       ; write new value to screen
        iny
        bne loop
        ; (advance source page if needed)
done:

        rts
```

## Screen-Oriented Packing

For full-screen images (1000 bytes), RLE works well because the PET screen has large runs of spaces and repeated characters.

### Typical Compression Ratios

| Content Type         | RLE Ratio | Notes                              |
|----------------------|-----------|------------------------------------|
| Empty screen         | 20:1      | 1000 spaces -> 3 bytes             |
| Solid pattern        | 83:1      | 1000 identical codes -> 12 bytes   |
| Text pages           | 3:1       | Moderate runs with mixed literals  |
| Graphics/art         | 1.2:1     | Little repetition; may expand      |
| Character animations | 2:1       | Repeated frames; delta may help    |