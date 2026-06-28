# Compression Patterns

## Purpose

> **Scope:** RLE, byte-run, frame-delta, LZ4, decompression routines for PET screen data and animation
> **Key items:** RLE flag bytes, run length encoding, delta frames, LZ4 token decode, screen-oriented depackers

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
decompress_rle:

        lda $FE                 ; ZP borrowed: $FB = repeat counter  $FC = repeat character $FD = len lo          $FE = len hi
        pha
        lda $FD
        pha
        lda $FC
        pha
        lda $FB
        pha

        stx rle_param+1         ; patch param block address into reader
        sty rle_param+2
        ldy #0

rle_param:

        lda $FFFF,y             ; src lo (self-modified to param block)
        sta rle_read+1
        iny
        lda $FFFF,y             ; src hi
        sta rle_read+2
        iny
        lda $FFFF,y             ; dst lo
        sta rle_write+1
        iny
        lda $FFFF,y             ; dst hi
        sta rle_write+2
        iny
        lda $FFFF,y             ; len lo
        sta $FD
        iny
        lda $FFFF,y             ; len hi
        sta $FE

        ldx #0                  ; X = source index
        ldy #0                  ; Y = dest index

rle_loop:

        lda #1
        sta $FB                 ; repeat count = 1 (literal default)
        jsr rle_read
        beq rle_escape          ; $00 begins an escape run

rle_write:

        sta $FFFF,y             ; write to dest (self-modified)

        lda $FD                 ; decrement byte count
        bne rle_dec_lo
        lda $FE
        beq rle_exit            ; count exhausted
        dec $FE

rle_dec_lo:

        dec $FD
        iny                     ; advance dest index
        bne rle_next
        inc rle_write+2         ; dest page crossed

rle_next:

        dec $FB                 ; repeat counter--
        bne rle_write_back      ; still copies remaining
        jsr rle_progress        ; advance source past current byte
        jmp rle_loop

rle_write_back:

        lda $FC                 ; reload repeat character
        jmp rle_write

rle_escape:

        jsr rle_progress        ; past $00
        jsr rle_read
        sta $FB                 ; repeat count from stream
        jsr rle_progress
        jsr rle_read
        sta $FC                 ; character to repeat
        jmp rle_write           ; write $FB copies of $FC

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

        lda $FFFF,x             ; self-modified: base = source start
        rts

rle_progress:

        inx
        bne rle_prog_skip
        inc rle_read+2          ; source page crossed

rle_prog_skip:

        rts
```

### Usage Example

```asm
rle_block:

        word packed_screen      ; src address
        word $8000              ; dst = screen RAM
        word $03E8              ; len = 1000 bytes (40x25)

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

        stx br_param+1          ; patch param block address
        sty br_param+2
        ldy #0

br_param:

        lda $FFFF,y             ; src lo (self-modified to param block)
        sta br_src+1
        iny
        lda $FFFF,y             ; src hi
        sta br_src+2
        iny
        lda $FFFF,y             ; dst lo
        sta br_write+1
        iny
        lda $FFFF,y             ; dst hi
        sta br_write+2

        ldx #0                  ; X = source index

br_loop:

        jsr br_src              ; read count byte
        beq br_done             ; count $00 = end of stream
        tay                     ; Y = number of copies
        jsr br_advance
        jsr br_src              ; A = value byte
        jsr br_advance          ; advance past value; A preserved

br_write:

        sta $FFFF               ; write to dest (self-modified, no index)

        inc br_write+1          ; advance dest address
        bne br_cnt
        inc br_write+2

br_cnt:

        dey
        bne br_write            ; write same value again
        jmp br_loop

br_done:

        rts

br_src:

        lda $FFFF,x             ; self-modified: base = source start
        rts

br_advance:

        inx
        bne br_adv_skip
        inc br_src+2            ; source page crossed

br_adv_skip:

        rts
```

### Usage Example

```asm
br_block:

        word packed_data        ; src address
        word target_buffer      ; dst address

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

        stx dl_param+1          ; patch param block address
        sty dl_param+2
        ldy #0

dl_param:

        lda $FFFF,y             ; src lo (self-modified to param block)
        sta dl_read+1
        iny
        lda $FFFF,y             ; src hi
        sta dl_read+2

        ldx #0                  ; X = source index

dl_loop:

        jsr dl_read             ; dst lo
        tay                     ; save dst lo in Y
        jsr dl_advance
        jsr dl_read             ; dst hi (in A)
        cpy #$FF
        bne dl_not_end          ; dst lo != $FF: not end marker
        cmp #$FF
        beq dl_done             ; both $FF: end of stream

dl_not_end:

        sty dl_write+1          ; patch dest address lo
        sta dl_write+2          ; patch dest address hi
        jsr dl_advance
        jsr dl_read             ; value to write (in A)
        jsr dl_advance

dl_write:

        sta $FFFF               ; write to patched screen address
        jmp dl_loop

dl_done:

        rts

dl_read:

        lda $FFFF,x             ; self-modified: base = source start
        rts

dl_advance:

        inx
        bne dl_adv_skip
        inc dl_read+2           ; source page crossed

dl_adv_skip:

        rts
```

### Usage Example

```asm
dl_block:

        word frame_delta        ; src address (delta stream)

        ldx #<dl_block
        ldy #>dl_block
        jsr apply_delta
```

## LZ4 Block Format

LZ4 is a byte-oriented compression format that stores literal runs and back-references (matches). It achieves better ratios than RLE on data with repeated patterns at non-adjacent offsets.

### Format

Each block starts with a token byte:

| Token Nibble | Meaning                              |
|--------------|--------------------------------------|
| High nibble  | Literal count (0-14, or 15 = extend) |
| Low nibble   | Match count (0-14, or 15 = extend)   |

After the token:

1. If literal count = 15: read extension bytes. Each byte adds to the count. Continue while byte = `$FF`. Stop at the first byte < `$FF`.
2. Copy literal bytes from source to destination.
3. If source is exhausted after literals, the block is done.
4. Read 2-byte match offset (little-endian). Offset `$0000` signals end of stream. Otherwise, go back N bytes from current destination position.
5. If match count = 15: read extension bytes the same way as literals.
6. Match length = match count + 4 (minimum match is 4 bytes).
7. Copy match bytes from `destination - offset` to `destination`, one byte at a time. Overlapping copies are allowed and are the core of LZ4's compression.

### Example Encoding

```
$40 $41 $42 $43 $04      ; token: 4 literals, 0 match
                          ; literals: $41 $42 $43 $04

$10 $05 $00              ; token: 1 literal, 0 match (4 bytes)
                          ; literal: $05
                          ; offset: $0005 (go back 5 bytes)
                          ; match: copy 4 bytes from dst-5

$00                      ; token: 0 literals, 0 match
                          ; offset: $0000 = end of stream
```

### Decompressor

Uses self-modifying pointers for source reads and destination writes. A shared write subroutine handles both literal and match copies. Borrows ZP `$FB`-`$FE` for working registers; saves and restores all four. Uses `$FF` (documented unused by PET BASIC 2) for the literal count high byte without saving.

**Calling convention:** X = low byte, Y = high byte of a 4-byte parameter block in free RAM.

```
; parameter block layout:
; +0 src lo  +1 src hi  +2 dst lo  +3 dst hi
```

```asm
decompress_lz4:

        lda $FE                 ; ZP borrowed: $FB = temp token      $FC = match offset lo $FD = match offset hi  $FE = working counter $FF = literal count hi (unused by BASIC, no save needed)
        pha
        lda $FD
        pha
        lda $FC
        pha
        lda $FB
        pha

        stx lz4_param+1         ; patch param block address into reader
        sty lz4_param+2
        ldy #0

lz4_param:

        lda $FFFF,y             ; src lo (self-modified to param block)
        sta lz4_src+1
        iny
        lda $FFFF,y             ; src hi
        sta lz4_src+2
        iny
        lda $FFFF,y             ; dst lo
        sta lz4_put+1
        iny
        lda $FFFF,y             ; dst hi
        sta lz4_put+2

        ldx #0                  ; X = source index

lz4_token:

        jsr lz4_src             ; read token byte
        jsr lz4_inc_src
        sta $FB                 ; save token for match-length decode
        lsr                     ; high nibble -> low nibble (literal count)
        lsr
        lsr
        lsr
        sta $FE                 ; literal count lo
        lda #0
        sta $FF                 ; literal count hi
        lda $FE
        cmp #$0F
        bne lz4_copy_literals

lz4_lit_ext:

        jsr lz4_src             ; read extension byte
        jsr lz4_inc_src
        pha                     ; save extension byte for $FF comparison
        clc
        adc $FE
        sta $FE
        bcc lz4_lit_ext_nc
        inc $FF

lz4_lit_ext_nc:

        pla                     ; restore extension byte
        cmp #$FF
        beq lz4_lit_ext

lz4_copy_literals:

        lda $FE                 ; check if any literals to copy
        ora $FF
        beq lz4_read_match

lz4_lit_loop:

        jsr lz4_src             ; read literal byte
        jsr lz4_inc_src
        jsr lz4_put             ; write to dest (shared write subroutine)
        lda $FE                 ; decrement 16-bit literal count
        bne lz4_lit_dec
        lda $FF
        beq lz4_read_match      ; count exhausted
        dec $FF

lz4_lit_dec:

        dec $FE
        jmp lz4_lit_loop

lz4_read_match:

        jsr lz4_src             ; read match offset lo
        jsr lz4_inc_src
        sta $FC
        jsr lz4_src             ; read match offset hi
        jsr lz4_inc_src
        sta $FD

        lda $FC                 ; offset $0000 = end of stream
        ora $FD
        beq lz4_done

        lda $FB                 ; retrieve original token
        and #$0F                ; low nibble = match count
        clc
        adc #4                  ; minimum match = 4 bytes
        sta $FE                 ; match length
        lda $FB
        and #$0F
        cmp #$0F
        bne lz4_copy_match

lz4_match_ext:

        jsr lz4_src             ; read extension byte
        jsr lz4_inc_src
        clc
        adc $FE
        sta $FE
        cmp #$FF
        beq lz4_match_ext

lz4_copy_match:

        sec                     ; match read ptr = dest - offset
        lda lz4_put+1
        sbc $FC
        sta lz4_mread+1
        lda lz4_put+2
        sbc $FD
        sta lz4_mread+2

lz4_match_loop:

lz4_mread:

        lda $FFFF               ; read from dest-offset (self-modified)
        jsr lz4_put             ; write to dest (shared write subroutine)
        inc lz4_mread+1         ; advance match read pointer
        bne lz4_mread_skip
        inc lz4_mread+2

lz4_mread_skip:

        dec $FE                 ; decrement match length
        bne lz4_match_loop

        jmp lz4_token           ; next token

lz4_done:

        pla
        sta $FB
        pla
        sta $FC
        pla
        sta $FD
        pla
        sta $FE
        rts

lz4_src:

        lda $FFFF,x             ; self-modified: base = source start
        rts

lz4_inc_src:

        inx
        bne lz4_src_skip
        inc lz4_src+2           ; source page crossed

lz4_src_skip:

        rts

lz4_put:

        sta $FFFF               ; self-modified: dest address
        inc lz4_put+1           ; advance dest pointer
        bne lz4_put_skip
        inc lz4_put+2           ; dest page crossed

lz4_put_skip:

        rts
```

### Token Invariant

The `lz4_lit_ext` extension loop must not overwrite the token byte stored in `$FB`. The original token must survive intact from `lz4_token` through the match-length decode, which reads the token's lower nibble with `and #$0F` to get the match count.

The decompressor above uses `pha`/`pla` to save the extension byte on the CPU stack for the `$FF` continuation test. This preserves the token in `$FB` throughout the extension loop.

Do not use `sta $FB` / `lda $FB` in the extension loop -- this destroys the token before the match-length decode reads it:

```asm
        jsr lz4_src
        jsr lz4_inc_src
        sta $FB                 ; BAD: destroys token needed for match-length decode
        clc
        adc $FE
        ...
        lda $FB                 ; BAD: reads last extension byte, not original token
        cmp #$FF
```

This bug only fires on tokens with literal count 15 or higher (high nibble `$F`). Tokens below that threshold never enter the extension loop, so the token reaches the match-length decode intact.

The `lz4_match_ext` loop may use `$FB` as scratch because it runs after the match-length nibble has already been decoded.

### Usage Example

```asm
lz4_block:

        word packed_screen      ; src address
        word $8000              ; dst = screen RAM

        ldx #<lz4_block
        ldy #>lz4_block
        jsr decompress_lz4
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
