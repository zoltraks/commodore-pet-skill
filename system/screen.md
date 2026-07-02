# Screen I/O & PETSCII

## Purpose

> **Scope:** Screen RAM, PETSCII, screen codes, cursor, reverse video, direct writes
> **Key items:** SCREEN=$8000, 40x25 layout, PETSCII $93 = CLR/HOME, bit 7 = reverse, row stride = 40

This file covers PET 3032 screen I/O in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need
- **Reference tables & mappings** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                  | See instead          |
|-------------------------------|----------------------|
| CRTC/PIA/VIA register details | `hardware/chip.md`   |
| KERNAL routines               | `system/kernal.md`   |
| Memory map                    | `system/memory.md`   |
| Keyboard matrix and GETIN     | `system/keyboard.md` |
| Semigraphics and box drawing  | `system/graphics.md` |

## Contents

| Section                 | Line | What it covers                                                |
|-------------------------|------|---------------------------------------------------------------|
| Screen RAM Layout       | 35   | Base address, 40x25 layout, row address table, 1000-byte rule |
| PETSCII vs Screen Codes | 118  | Conversion table, working converter, inverse video from PETSCII |
| Cursor Control          | 180  | KERNAL cursor routines, PLOT, TAB                             |
| Clear and Home          | 206  | CLR/HOME PETSCII, clear screen routine                        |
| Reverse Video           | 243  | Bit 7, RVS on/off, highlight_row routine                      |
| PETSCII Control Codes   | 376  | CHROUT control code table                                     |
| Character Sets          | 400  | Uppercase/graphics vs lowercase/text, PCR switching, charset-aware label rendering |
| Double Buffering        | 482  | Back buffer, VBLANK sync, copy routine, tail flag hazard, bounded poll, deferred charset flush, common mistakes |
| Raw Screen Codes        | 740  | Storing byte values directly as screen codes for hex viewer ASCII columns |
| Frame Composition       | 822  | Drawing order for bordered frames with header, content, and footer       |

## Screen RAM Layout

- Base address: `$8000`
- 40 columns, 25 rows = 1000 bytes
- Address range: `$8000-$83E7`
- Each byte = screen code (not PETSCII)
- Bit 7 set = reverse video (hardware inverted)
- Row stride: 40 bytes

### Screen Size Invariant

Screen RAM is exactly 1000 bytes (`$8000-$83E7`), not 1024. A naive 4-page loop (256 x 4 = 1024) writes 24 bytes past the screen into `$83E8-$83FF`, which is not display memory and may overwrite working storage or KERNAL variables.

When clearing, filling, or copying screen RAM, always write exactly 1000 bytes. The standard technique uses page striding for the first 3 full pages (768 bytes), then a 232-byte tail loop for the final partial page (`$8300-$83E7`).

See `code/standard.md` for the full screen clear rule.

### Row Address Table

| Row | Start | End   |
|-----|-------|-------|
| 0   | $8000 | $8027 |
| 1   | $8028 | $804F |
| 2   | $8050 | $8077 |
| ... | ...   | ...   |
| 24  | $83C0 | $83E7 |

### Direct Screen Write

```asm
SCREEN  = $8000

        lda #$20                ; space character screen code
        sta SCREEN              ; row 0, column 0
        lda #$41                ; 'A' screen code
        sta SCREEN+1            ; row 0, column 1
```

### Calculating Screen Address from (row, col)

```asm
calc_screen_addr:

        lda #<SCREEN            ; X = row (0-24), Y = column (0-39); result in $FB (lo) and $FC (hi); caller saves/restores if needed.
        sta $FB
        lda #>SCREEN
        sta $FC
        lda row_mult_lo,x       ; add row * 40
        clc
        adc $FB
        sta $FB
        lda row_mult_hi,x
        adc $FC
        sta $FC
        tya                     ; add column
        clc
        adc $FB
        sta $FB
        bcc csa_done
        inc $FC

csa_done:

        rts

row_mult_lo:

        byte <$0000,<$0028,<$0050,<$0078,<$00A0,<$00C8,<$00F0,<$0118
        byte <$0140,<$0168,<$0190,<$01B8,<$01E0,<$0208,<$0230,<$0258
        byte <$0280,<$02A8,<$02D0,<$02F8,<$0320,<$0348,<$0370,<$0398
        byte <$03C0

row_mult_hi:

        byte >$0000,>$0028,>$0050,>$0078,>$00A0,>$00C8,>$00F0,>$0118
        byte >$0140,>$0168,>$0190,>$01B8,>$01E0,>$0208,>$0230,>$0258
        byte >$0280,>$02A8,>$02D0,>$02F8,>$0320,>$0348,>$0370,>$0398
        byte >$03C0
```

## PETSCII vs Screen Codes

PETSCII (the character codes used in BASIC strings and CHROUT) differ from screen codes (the values stored in screen RAM).

### Conversion Rules

| Range                     | PETSCII to Screen   | Screen to PETSCII |
|---------------------------|---------------------|-------------------|
| $00-$1F (control)         | undefined           | undefined         |
| $20-$3F (symbols/numbers) | subtract $00 (same) | add $00 (same)    |
| $40-$5F (@, A-Z, brackets) | subtract $40       | add $40           |
| $60-$7F (graphics)        | subtract $20        | add $20           |
| $A0-$BF (shifted graphics)| subtract $40        | add $40           |
| $C0-$FF (reversed @, A-Z) | subtract $80        | add $80           |

On the PET, `$60-$7F` are graphics characters (not lowercase letters as on the C64). Programs that only display ASCII-range text (letters, digits, punctuation) can simplify the converter by passing `$60-$7F` through unchanged, since those values are never produced by normal text input.

### Working Converter

A compact `petscii_to_screen` routine that handles all ranges needed for UI text:

```asm
petscii_to_screen:

        cmp #$20
        bcc p2s_done            ; control codes pass through
        cmp #$40
        bcc p2s_done            ; $20-$3F unchanged
        cmp #$60
        bcc p2s_sub40           ; $40-$5F: subtract $40
        cmp #$80
        bcc p2s_done            ; $60-$7F unchanged (rare in text)
        cmp #$C0
        bcc p2s_sub40           ; $80-$BF: subtract $40
        ; $C0-$FF: subtract $80
        sec
        sbc #$80
        rts

p2s_sub40:

        sec
        sbc #$40
        rts

p2s_done:

        rts
```

### Common Characters

| Char  | PETSCII | Screen Code |
|-------|---------|-------------|
| Space | $20     | $20         |
| 0-9   | $30-$39 | $30-$39     |
| A-Z   | $41-$5A | $01-$1A     |
| @     | $40     | $00         |
| [     | $5B     | $1B         |
| ]     | $5D     | $1D         |
| _     | $A4     | $64         |

### Inverse Video from PETSCII

Inverse video does not require a separate PETSCII-to-ASCII conversion. Convert PETSCII to screen code first, then set bit 7 with `ORA #$80`. The conversion and the reverse-bit setting are independent operations:

```asm
        lda #$41                ; PETSCII 'A'
        jsr petscii_to_screen   ; A = $01 (screen code for 'A')
        ora #$80                ; A = $81 (reversed 'A')
        sta (screen_ptr),y      ; store to screen RAM
```

This works for all printable characters. Do not OR `$80` before calling `petscii_to_screen` -- the conversion routine treats `$80-$BF` as a different PETSCII range (shifted graphics), which would produce the wrong screen code. Always convert first, then set the reverse bit.

To clear reverse video: `and #$7F`.

## Cursor Control

### KERNAL Cursor Pointers

| Address     | Name  | Description                            |
|-------------|-------|----------------------------------------|
| $00C4-$00C5 | PNT   | Current screen line address            |
| $00C6       | PNTR  | Cursor column on current line (0-39)   |
| $00D8       | TBLX  | Cursor physical line number (0-24)     |
| $00A9       | GDBLN | Character under cursor                 |
| $00A7       | BLNSW | Cursor blink enable (0 = flash cursor) |

### Disable Cursor Blink

```asm
        lda #$01
        sta BLNSW               ; $00A7: stop cursor flashing
```

### Restore Cursor Blink

```asm
        lda #$00
        sta BLNSW               ; $00A7: resume cursor flashing
```

## Clear and Home

### Using KERNAL (CHROUT)

```asm
        lda #$93                ; PETSCII CLR/HOME
        jsr CHROUT              ; $FFD2
```

### Direct Screen Clear

Screen RAM is 1000 bytes (`$8000-$83E7`), not 1024. A naive 4-page loop writes 24 bytes past the screen into `$83E8-$83FF`, which is not display memory. The correct approach writes 3 full pages (768 bytes) with page striding, then a 232-byte tail for the final partial page.

```asm
clear_screen:

        ldx #$00
        lda #$20                ; space character

clear_loop:

        sta SCREEN,x            ; $8000-$80FF
        sta SCREEN+$100,x       ; $8100-$81FF
        sta SCREEN+$200,x       ; $8200-$82FF
        inx
        bne clear_loop          ; 768 bytes done (3 pages)

        ldx #$E8                ; remaining 232 bytes: $8300-$83E7

clear_tail:

        dex
        sta SCREEN+$300,x       ; x = 231..0, writes $83E7..$8300
        bne clear_tail          ; 232 bytes done, total = 1000
        rts
```

The `clear_tail` loop is safe because `sta` does not affect flags -- `bne` tests the Z flag set by `dex`. This differs from the `copy_buffer` tail, which inserts an `lda` between `dex` and `sta`. See the Tail Loop Flag Hazard section under Double Buffering below.

### Per-Character Reverse

Set bit 7 of the screen RAM byte:

```asm
        lda SCREEN,x
        ora #$80                ; set reverse bit
        sta SCREEN,x
```

### Global Reverse Mode

Set the RVS flag before calling CHROUT:

```asm
        lda #$FF
        sta RVS                 ; $009F: reverse flag
        lda #$41                ; 'A'
        jsr CHROUT              ; prints reversed 'A'
        lda #$00
        sta RVS                 ; clear reverse mode
```

### Menu Item Highlighting

Set bit 7 on a row's screen codes to highlight the current menu selection. Clear bit 7 to deselect.

`highlight_row` and `unhighlight_row` borrow $FB-$FC as a screen pointer; they save and restore both bytes. `get_row_ptr` is an internal helper and does not save/restore.

```asm
SCREEN      = $8000

highlight_row:          ; set reverse video on all 40 chars in screen row X (0-24); borrows $FB-$FC; saves and restores both.

        lda $FC
        pha
        lda $FB
        pha
        jsr get_row_ptr
        ldy #$27

highlight_loop:

        lda ($FB),y
        ora #$80                ; set reverse video
        sta ($FB),y
        dey
        bpl highlight_loop

        pla
        sta $FB
        pla
        sta $FC
        rts

unhighlight_row:        ; clear reverse video on all 40 chars in screen row X; borrows $FB-$FC; saves and restores both.

        lda $FC
        pha
        lda $FB
        pha
        jsr get_row_ptr
        ldy #$27

unhighlight_loop:

        lda ($FB),y
        and #$7F                ; clear reverse video
        sta ($FB),y
        dey
        bpl unhighlight_loop

        pla
        sta $FB
        pla
        sta $FC
        rts

get_row_ptr:            ; set $FB/$FC to address of screen row X (internal helper)

        lda #<SCREEN
        sta $FB
        lda #>SCREEN
        sta $FC
        txa
        beq get_row_done        ; row 0: base is already correct

get_row_loop:

        lda $FB
        clc
        adc #$28
        sta $FB
        bcc get_row_skip
        inc $FC

get_row_skip:

        dex
        bne get_row_loop

get_row_done:

        rts
```

Move the selection down and update the highlight. `$FF` is one of the two ZP bytes explicitly unused by PET BASIC 2 (the other is `$A2`), so it is safe to allocate as a single-byte variable:

```asm
menu_sel    = $FF               ; safe: $FF unused by PET BASIC 2 KERNAL

menu_move_down:

        ldx menu_sel
        jsr unhighlight_row
        inc menu_sel
        lda menu_sel
        cmp #menu_count
        bcc menu_show
        lda #0
        sta menu_sel

menu_show:

        ldx menu_sel
        jsr highlight_row
        rts
```

Set `menu_count` to the number of items. Use `menu_move_down` and a mirror `menu_move_up` for arrow key navigation.

## PETSCII Control Codes

These codes are sent to `CHROUT` (`$FFD2`) to control the cursor and screen.

They are not stored in screen RAM.

| Code         | Hex | Description                                |
|--------------|-----|--------------------------------------------|
| HOME         | $13 | Move cursor to top-left (no clear)         |
| CLR/HOME     | $93 | Clear screen and move to top-left          |
| CURSOR DOWN  | $11 | Move cursor one row down                   |
| CURSOR UP    | $91 | Move cursor one row up                     |
| CURSOR RIGHT | $1D | Move cursor one column right               |
| CURSOR LEFT  | $9D | Move cursor one column left                |
| RETURN       | $0D | Carriage return + line feed                |
| DELETE       | $14 | Delete character to the left               |
| INSERT       | $94 | Insert space at cursor                     |
| RVS ON       | $12 | Enable reverse video for subsequent CHROUT |
| RVS OFF      | $92 | Disable reverse video                      |
| LINE FEED    | $0A | Move cursor down one line                  |
| TAB          | $09 | Move to next tab stop                      |

**Note:** On the PET 3032, color control codes (used on C64) have no effect - the PET has a monochrome display.

## Character Sets

The PET 3032 has two built-in character sets, selected via the VIA PCR register (`$E84C`) bits 3:1. See `hardware/chip.md` for the PCR switching mechanism and read-modify-write rules.

| Set       | PCR   | CA2  | Also Called | Letters              | Default |
|-----------|-------|------|-------------|----------------------|---------|
| Uppercase | `$0C` | low  | "graphics"  | A-Z only (uppercase) | Yes     |
| Lowercase | `$0E` | high | "text"      | A-Z and a-z          | No      |

### Uppercase / Graphics Set (default)

The uppercase set is the power-on default. It contains uppercase letters A-Z, digits 0-9, punctuation, and a rich selection of semigraphics characters: box-drawing lines, corners, solid blocks, checkerboard patterns, and diagonal lines.

This set is called "graphics" because the absence of lowercase letters frees character ROM space for semigraphics glyphs. Use this set for UI drawing, borders, frames, and any screen layout that relies on box-drawing or block characters.

### Lowercase / Text Set (alternative)

The lowercase set replaces many semigraphics glyphs with lowercase letters a-z. It is called "text" because it is better suited for prose and text editing where both upper and lower case are needed.

### Codes Shared Between Both Sets

The box-drawing and block characters in the `$40`-`$7F` range that are **not letters** are identical in both character sets. The ROM stores the same pixel patterns for these codes in both halves. Specifically, these codes produce the same glyph regardless of which set is active:

| Shared (identical in both sets) | Differ (letters in one set) |
|---------------------------------|-----------------------------|
| `$40`, `$5B`-`$5D`              | `$41`-`$5A` (A-Z vs a-z)    |
| `$60`-`$68`, `$6A`-`$6C`        | `$5E`, `$5F`                |
| `$6D`-`$6F`, `$70`-`$79`        | `$69` (triangle vs other)   |
| `$7B`-`$7F`                     | `$7A`                       |

This means UI elements drawn with the box-drawing codes below work in **both** character sets without switching. You only need to switch to `PCR_U` if you need uppercase-only symbols that the lowercase set replaces with letters.

### Switching Character Sets

Always use read-modify-write on PCR to preserve CB2 bits (CB2 drives the IEEE-488 NDAC line; overwriting it breaks disk I/O):

```asm
PCR     = $E84C
PCR_U   = $0C           ; uppercase / graphics charset
PCR_L   = $0E           ; lowercase / text charset

        lda PCR                 ; switch to uppercase/graphics for UI drawing
        and #$F1                ; clear bits 3:1 (CA2 mode)
        ora #PCR_U              ; bits 3:1 = 110 -> uppercase/graphics
        sta PCR

        lda PCR                 ; switch back to lowercase/text
        and #$F1                ; clear bits 3:1
        ora #PCR_L              ; bits 3:1 = 111 -> lowercase/text
        sta PCR
```

See `hardware/chip.md` for the full PCR register reference and the CB2 hazard warning.

**Flicker hazard with double buffering**: writing PCR directly while the screen still shows the old frame content causes a one-frame flash -- the old content appears under the new character set until the next VBLANK blit. In a double-buffered program, defer the PCR write and flush it during VBLANK alongside the back-buffer copy. See "Synchronizing Character-Set Switches With VBLANK" under Double Buffering below.

### Charset-Aware Label Rendering

The screen codes for uppercase letters differ between the two character sets: `A`-`Z` are `$01`-`$1A` in the uppercase set and `$41`-`$5A` in the lowercase set. The frame border and block codes are identical in both sets, but fixed text labels are not.

When a program draws UI labels (e.g. `VIEW`, `EXIT`, `HELP`) as hardcoded screen codes and allows the user to switch character sets at runtime, the labels must be redrawn with the correct codes for the active set, or they will display as the wrong glyphs (typically lowercase letters or graphics symbols) in the other set.

**Pattern**: keep a `char_offset` byte (`$00` for uppercase, `$40` for lowercase) and OR it into each label letter's screen code before storing it to the back buffer. Do not apply the offset to non-letter codes (spaces, borders, reversed-space fills):

```asm
view_char_offset = $00          ; $00 UPPER, $40 LOWER

        ldy #3
        lda #$96               ; 'V' reversed (uppercase-set code)
        ora view_char_offset   ; shift to lowercase-set code if LOWER
        sta (sp_lo),y
```

When the user presses a key to switch character sets, update `view_char_offset` and re-render the frame. The labels redraw automatically with the correct codes.

**Filename exception**: text that comes from user data (e.g. a file name) should be converted once via `petscii_to_screen` and not re-translated on a charset switch. The name will then follow the active set -- `FILE.TXT` displays as `file.txt` in the lowercase set. This side effect is useful as a visible indicator of the active character set without adding a separate status field.

For semigraphics characters, box drawing styles, window/line/rect drawing routines, and screen scrolling, see `system/graphics.md`.

## Double Buffering

Writing directly to screen RAM while the display is being drawn causes visible flicker -- partial updates appear as torn frames. Double buffering eliminates this by rendering each frame into a back buffer in RAM, then copying the complete frame to screen RAM during VBLANK.

### How It Works

1. Render the next frame into a back buffer in RAM (not screen RAM).
2. Wait for VBLANK (see `system/irq.md` for the two-phase VBLANK poll).
3. Copy the back buffer to screen RAM during VBLANK -- the display is not drawing, so no flicker.
4. Repeat.

The copy must complete within the VBLANK period. At 1 MHz, the 1000-byte copy takes roughly 6000 cycles (6 bytes per iteration: LDA/STA pair × 3 pages + tail). The PET VBLANK period is long enough for this.

### Back Buffer Placement

The back buffer is 1000 bytes, matching screen RAM. Place it in free RAM just below screen RAM, aligned to a 256-byte page boundary. The standard choice is `$7C00`, occupying the space just before the end of RAM and leaving a 1024-byte gap below screen RAM:

```asm
SCREEN  = $8000
BUFFER  = $7C00          ; 1000-byte back buffer, page-aligned
```

Page alignment is the convention, not merely a convenience: it lets the copy loop use the page-strided pattern below (3 full pages plus a 232-byte tail) without addressing corner cases. Keep the label `BUFFER` (not `SCREEN_BUFFER`) and keep `SCREEN` for screen RAM at `$8000`.

### Ready Flag

Use a flag byte to track whether the back buffer holds a new frame. Set it after rendering, clear it after copying:

```asm
READY   = $0351          ; 0 = no frame ready, 1 = frame ready to copy
```

The main loop checks the flag each VBLANK. If set, it copies the buffer and clears the flag. If not set, it skips the copy -- the screen keeps showing the previous frame.

For event-driven programs (file managers, editors) that redraw only on keypress, a `READY` flag is unnecessary. Call the present routine directly after each redraw -- the program spends most of its time in a `GETIN` poll loop, not rendering frames.

### Buffer Copy Routine

Copy 1000 bytes from `BUFFER` to `SCREEN` using the same page-strided pattern as the screen clear (3 full pages + 232-byte tail):

```asm
SCREEN  = $8000
BUFFER  = $7C00

copy_buffer:

        ldx #$00

copy_loop:

        lda BUFFER,x            ; $7C00-$7CFF -> $8000-$80FF
        sta SCREEN,x
        lda BUFFER+$100,x       ; $7D00-$7DFF -> $8100-$81FF
        sta SCREEN+$100,x
        lda BUFFER+$200,x       ; $7E00-$7EFF -> $8200-$82FF
        sta SCREEN+$200,x
        inx
        bne copy_loop           ; 768 bytes done (3 pages)

        ldx #$E8                ; remaining 232 bytes: $7F00-$7FE7 -> $8300-$83E7

copy_tail:

        dex
        lda BUFFER+$300,x       ; x = 231..0, reads $7FE7..$7F00
        sta SCREEN+$300,x       ; writes $83E7..$8300
        txa                     ; test X (loop counter), not the loaded byte
        bne copy_tail           ; 232 bytes done, total = 1000
        rts
```

### Tail Loop Flag Hazard

The `copy_tail` section above contains a subtle flag hazard that does not affect the `clear_screen` tail. In `clear_screen`, the tail body is `dex` / `sta` / `bne` -- `sta` does not affect flags, so `bne` correctly tests the Z flag set by `dex`. In `copy_buffer`, the tail body is `dex` / `lda` / `sta` / `bne` -- `lda` **does** affect the Z flag, so `bne` tests the loaded byte, not the loop counter.

If the back buffer tail region contains no `$00` bytes (common with uninitialized RAM filled with `$AA` or other garbage), the loop never exits when X reaches zero. Instead, X wraps from `$00` to `$FF`, and the loop continues writing past `$83E7` into `$83E8-$83FF` and beyond -- overwriting KERNAL variables, I/O registers, or VIA/PIA hardware. This corrupts the keyboard interrupt and freezes input.

Two fixes exist. Both are correct; pick either based on register availability:

```asm
; FIX 1: txa after sta -- bne tests X (counter)
        dex
        lda BUFFER+$300,x
        sta SCREEN+$300,x
        txa
        bne copy_tail

; FIX 2: dex after sta -- bne tests X (counter)
        lda BUFFER+$300,x
        sta SCREEN+$300,x
        dex
        bne copy_tail
```

Fix 1 (`txa`) costs one extra byte and one extra cycle versus the broken version. Fix 2 (`dex`-after-`sta`) reorders the loop body and costs nothing extra. See `code/standard.md` for the general flag-semantics rule.

### Tail Loop Address Off-by-One

A separate bug in `copy_buffer` involved the base address used in the tail loop. The original code used `BUFFER+$300-1,x` (i.e. `BUFFER+$2FF+x`), which when x ranges from 231 down to 0 covers offsets `$2FF` through `$3E6` -- only 232 bytes, but shifted down by one from the intended `$300` through `$3E7`. This meant the last byte of screen memory (row 24, column 39) was never copied from the back buffer to the screen, while the byte at offset `$2FF` (already covered by the page-strided main loop) was copied twice.

The fix is to use `BUFFER+$300,x` and `SCREEN+$300,x` without the `-1` offset. With x ranging from 231 to 0, this covers offsets `$300` through `$3E7` exactly. The `clear_screen` tail already used `BUFFER+$300,x` correctly -- only `copy_buffer` had the off-by-one.

### Bounded VBLANK Poll

The unbounded two-phase VBLANK poll in `system/irq.md` hangs forever if the retrace bit never toggles. VICE 3.7 xpet does not mirror the VBLANK signal onto VIA PB5 (`$E840` bit 5), so the poll loops indefinitely and the program appears frozen with the initial screen visible.

Use a bounded poll that gives up after a fixed number of iterations. On real hardware the bound is never reached (the bit toggles within one frame). On emulators without the retrace bit, the bound expires and the copy proceeds without sync -- still flicker-free because the full 1000-byte copy is atomic relative to a single `GETIN` poll:

```asm
VIA_PORTB   = $E840
RETRACE_BIT = $20

wait_vblank:

        ldx #$00

wv_p1:

        lda VIA_PORTB
        and #RETRACE_BIT
        bne wv_p2               ; bit HIGH: VBLANK ended -> phase 2
        dex
        bne wv_p1
        rts                     ; phase 1 bound exhausted: give up (no sync)

wv_p2:

        ldx #$00

wv_p2_loop:

        lda VIA_PORTB
        and #RETRACE_BIT
        beq wv_done             ; bit LOW: VBLANK started
        dex
        bne wv_p2_loop
        rts                     ; phase 2 bound exhausted: give up (no sync)

wv_done:

        rts                     ; at start of VBLANK
```

A 256-iteration bound per phase is approximately 2 ms at 1 MHz -- short enough to keep interactive response snappy if the bit is stuck, long enough to catch a real VBLANK (approximately 1.6 ms at 60 Hz).

### Present Routine

The present routine combines VBLANK sync and buffer copy. Call it after each redraw entry point:

```asm
present_screen:

        jsr wait_vblank
        jsr copy_buffer
        rts
```

For event-driven programs, call `present_screen` at the end of every redraw routine (`full_redraw`, `redraw_panels`, `redraw_active`, `view_render`) and after each interactive row-24 update (prompt label, prompt buffer, status message). The program's main loop is a `GETIN` poll; between keypresses, no redraw or present occurs.

### Synchronizing Character-Set Switches With VBLANK

The double-buffering principle applies not only to screen RAM content but also to display control registers that affect how the screen is interpreted. The most common case is the VIA PCR character-set switch (see "Switching Character Sets" above).

**The hazard**: if a program writes PCR immediately when the user requests a charset change, but the new screen content is only blitted later during VBLANK, the user sees the OLD frame rendered under the NEW character set for one frame. This is a visible flash on every charset switch. The same mismatch occurs on viewer entry (PCR switches before the first viewer frame is blitted) and on viewer exit (PCR restores before the panel redraw is blitted).

**The fix**: defer the PCR write so it happens during the same VBLANK window as the back-buffer blit. Stage the charset bits in a variable, set the `char_offset` byte immediately (so label rendering into the back buffer composes with the correct screen codes), and flush the staged PCR write inside `present_screen` between `wait_vblank` and `copy_buffer`:

```asm
; Stage the switch (called on key press, viewer entry, viewer exit)
view_set_pcr_charset:

        ldx view_charset
        beq vspc_upper
        lda #PCR_L             ; LOWER bits to stage
        ldx #$40
        bne vspc_store
vspc_upper:

        lda #PCR_U             ; UPPER bits to stage
        ldx #$00
vspc_store:

        sta view_pending_pcr_cs ; stage the PCR write (do not touch PCR yet)
        stx view_char_offset    ; set offset now for label rendering
        lda #$ff
        sta view_pcr_pending    ; mark a write as pending
        rts

; Flush the staged write during VBLANK (called by present_screen)
view_flush_pcr:

        lda view_pcr_pending
        beq vfp_done            ; no-op when nothing is staged
        lda PCR
        and #$F1               ; clear bits 3:1
        ora view_pending_pcr_cs ; apply staged bits
        sta PCR
        lda #0
        sta view_pcr_pending
vfp_done:

        rts

; Extended present routine with deferred register flush
present_screen:

        jsr wait_vblank
        jsr view_flush_pcr      ; apply staged PCR charset during VBLANK
        jsr copy_buffer
        rts
```

The PCR read-modify-write still preserves CB2 (IEEE-488 NDAC). The flush adds roughly 10 cycles, negligible against the 6000-cycle copy budget. When nothing is staged (all main-program present calls), the cost is one load plus one branch.

**When to use this pattern**: any time a display control register change affects how the current screen content is interpreted, and the new content is being composed into a back buffer. This includes interactive charset switches, and entry/exit transitions where the register changes before the first or last frame is blitted.

**When not needed**: if the register change and the content change are both atomic relative to a single `GETIN` poll (no double buffering), or if the register does not affect how existing screen content is displayed.

### Main Loop with VBLANK Sync

The main loop synchronizes screen updates to VBLANK and only copies when a new frame is ready:

```asm
VIA_PORTB   = $E840
RETRACE_BIT = $20

main_loop:

        jsr wait_vblank         ; sync to start of VBLANK

        lda READY               ; if a frame is prepared, copy it now
        beq no_copy
        jsr copy_buffer
        lda #$00
        sta READY

no_copy:

        ; ... check keys, advance animation, render next frame to BUFFER ...
        ; ... set READY = 1 after rendering ...

        jmp main_loop
```

The buffer copy runs inside VBLANK, so the user never sees a partially updated screen. Frame rendering (decompression, drawing) happens outside VBLANK and can take as long as needed.

### Common Mistakes

| Mistake                                                            | Consequence                                          | Fix                                                                  |
|--------------------------------------------------------------------|------------------------------------------------------|----------------------------------------------------------------------|
| `bne copy_tail` after `lda` in copy tail                           | Loop tests loaded byte, not counter; X wraps past 0 | Insert `txa` before `bne`, or move `dex` after `sta`                 |
| `BUFFER+$300-1,x` in copy tail (off-by-one)                        | Last screen byte (row 24 col 39) never copied        | Use `BUFFER+$300,x` without the `-1` offset                          |
| Unbounded VBLANK poll under VICE                                   | Program hangs -- PB5 never toggles                   | Bound each phase to 256 iterations                                   |
| Writing past `$83E7` in copy tail                                  | Overwrites KERNAL vars or I/O registers              | Use the 768 + 232 split, never a 4-page loop                         |
| Forgetting to clear BUFFER in init                                 | First blit shows garbage from uninitialized RAM     | Call `clear_screen` (writing to `BUFFER`) before first redraw        |
| Calling `present_screen` inside a tight poll loop                  | Wastes cycles on redundant blits                     | Call only after a redraw or interactive update                        |
| Writing PCR charset immediately in a double-buffered program       | Old frame flashes under new charset for one frame    | Stage the PCR write and flush it during VBLANK alongside the blit    |

## Raw Screen Codes

When displaying binary data (e.g., a hex viewer's ASCII column), each byte can be written directly to screen RAM as a screen code without PETSCII conversion. The character ROM maps every byte value `$00`-`$FF` to a glyph (or reversed glyph for `$80`-`$FF`).

### Direct Byte-to-Screen Mapping

Store the raw byte value at the screen position. No `petscii_to_screen` conversion, no dot substitution:

```asm
        lda (data_ptr),y        ; load raw byte from file buffer
        sta (screen_ptr),y      ; store directly as screen code
```

| Byte Value | Screen Code | Glyph (uppercase set)     |
|------------|-------------|---------------------------|
| `$00`      | `$00`       | `@`                       |
| `$01`      | `$01`       | `A`                       |
| `$0B`      | `$0B`       | `K` (graphics glyph)      |
| `$20`      | `$20`       | space                     |
| `$41`      | `$41`       | graphics glyph (not 'A')  |
| `$F8`      | `$F8`       | reversed graphics glyph   |
| `$FF`      | `$FF`       | reversed `@` (solid block)|

### When to Use Raw Screen Codes vs PETSCII Conversion

| Scenario                          | Approach                | Reason                                     |
|-----------------------------------|-------------------------|--------------------------------------------|
| Displaying text from a file       | `petscii_to_screen`     | File data is PETSCII; needs conversion     |
| Hex viewer ASCII column           | Raw screen code         | Shows exact byte value; no conversion      |
| Non-printable byte placeholder    | `$2E` (dot)             | User needs a visible "not printable" marker|
| Reversed text in a title bar      | `petscii_to_screen` + `ora #$80` | Text is PETSCII; reverse for emphasis |

### Why No Dot Substitution for Raw Display

In a hex viewer, the ASCII column is a visual representation of the raw byte value. Substituting dots for "non-printable" bytes hides information that the user might need (e.g., distinguishing `$00` from `$20`). By showing the raw screen code, every byte produces a visible glyph -- the user sees exactly what the byte maps to in the character ROM, including graphics characters and reversed characters for bytes `$80`-`$FF`.

### Indirect Addressing for Dual-Pointer Rendering

When rendering content from a data buffer to screen RAM, two zero-page pointers are needed: one for the source data and one for the destination screen row. The 6502 only supports `(zp),y` indirect indexed addressing -- there is no `(zp),x` mode.

This means Y must be used for the pointer offset. When both source and destination need indexed access in the same loop, save/restore Y via a temp variable:

```asm
; src_ptr -> data buffer, dst_ptr -> screen row
        ldy #0                   ; Y indexes source data
        ldx #1                   ; X tracks screen column (col 1 inside frame)
data_loop:
        cpy valid_count
        bcs pad_loop
        lda (src_ptr),y          ; load source byte via (zp),y
        pha                      ; save byte
        txa                      ; X -> A for screen column
        tay                      ; screen column -> Y
        pla                      ; restore byte
        sta (dst_ptr),y          ; store to screen via (zp),y
        inx                      ; next screen column
        txa
        pha                      ; save screen column
        ; ... restore Y for next source index
```

A cleaner approach uses a temp variable for the screen column and keeps Y for the source:

```asm
        ldy #0                   ; Y indexes source data
        lda #1
        sta screen_col           ; screen column starts at 1
data_loop:
        cpy valid_count
        bcs pad_loop
        lda (src_ptr),y          ; load source byte
        ; ... convert if needed ...
        sty ytmp                 ; save source index
        ldy screen_col
        sta (dst_ptr),y          ; store to screen
        inc screen_col
        ldy ytmp                 ; restore source index
        iny
        cpy #COLS_PER_ROW
        bcc data_loop
```

## Frame Composition

A full-screen UI with a bordered frame (header, content area, footer) requires a specific drawing order to avoid overwriting borders with content.

### Drawing Order

1. **Clear the back buffer** (`clear_screen` -- fills BUFFER with spaces)
2. **Draw the header bar** (row 0 -- reverse-video bar with half-block borders)
3. **Draw the frame borders** (top border, bottom border, side borders, internal dividers)
4. **Draw the content** (rows 2-22 -- content renderer fills the area inside the frame)
5. **Draw the footer bar** (row 24 -- reverse-video bar with shortcut labels)
6. **Present the screen** (`present_screen` -- VBLANK-synced copy from BUFFER to SCREEN)

### Why This Order Matters

- The header and footer are drawn before the frame borders so that the frame's top and bottom borders (rows 1 and 23) do not overlap.
- The frame borders are drawn before the content so that the content renderer can skip border columns (cols 0 and 39) and internal divider columns, writing only to the inner content area.
- The content renderer does not need to clear the content area because `clear_screen` already filled it with spaces.
- All drawing targets the back buffer (BUFFER at `$7C00`), not screen RAM. The final `present_screen` call copies the completed frame to screen RAM during VBLANK.

### Content Area Boundaries

When a frame occupies rows 1-23 with borders at columns 0 and 39, the content area is rows 2-22, columns 1-38 (21 rows x 38 columns = 798 cells). The content renderer must start at column 1 (not 0) and stop at column 38 (not 39):

```asm
        ldx #2                   ; first content row
content_row:
        stx row_tmp
        jsr row_addr_sp          ; set sp_lo/sp_hi to BUFFER row address
        ldy #1                   ; start at col 1 (inside left border)
        ; ... render up to 38 bytes ...
        ; ... pad with spaces up to col 38 ...
        ldx row_tmp
        inx
        cpx #23                  ; rows 2..22 (21 rows)
        bne content_row
```

### Row Address Helper

A `row_addr_sp` routine converts a row number in X to a BUFFER address in `sp_lo`/`sp_hi`:

```asm
BUFFER  = $7C00

row_addr_sp:
        lda #<BUFFER
        sta sp_lo
        lda #>BUFFER
        sta sp_hi
        txa
        asl                     ; A = row * 2
        asl                     ; A = row * 4
        asl                     ; A = row * 8
        sta tmp
        asl                     ; A = row * 16
        asl                     ; A = row * 32
        clc
        adc tmp                 ; A = row * 40
        clc
        adc sp_lo
        sta sp_lo
        lda sp_hi
        adc #0
        sta sp_hi
        rts
```

This computes `BUFFER + row * 40` using shifts instead of multiplication. The result is a zero-page pointer pair that supports `(sp_lo),y` indirect indexed writes to any column in the row.

