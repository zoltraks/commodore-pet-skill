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
| $40-$5F (@, A-O)          | subtract $40        | add $40           |
| $60-$7F (P-Z, etc.)       | subtract $20        | add $20           |
| $C0-$DF (graphics)        | subtract $80        | add $80           |
| $A0-$BF                   | subtract $40        | add $40           |

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

**Reverse video:** OR with `$80` to set bit 7. `AND #$7F` to clear.

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

## Reverse Video

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

## PETSCII Control Codes (for CHROUT)

These codes are sent to `CHROUT` ($FFD2) to control the cursor and screen.

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

| Shared (identical in both sets)     | Differ (letters in one set)    |
|-------------------------------------|--------------------------------|
| `$40`, `$5B`-`$5D`                  | `$41`-`$5A` (A-Z vs a-z)       |
| `$60`-`$68`, `$6A`-`$6C`            | `$5E`, `$5F`                   |
| `$6D`-`$6F`, `$70`-`$79`            | `$69` (triangle vs other)      |
| `$7B`-`$7F`                         | `$7A`                          |

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

## Semigraphics Characters

The semigraphics characters below are verified against the 901447-10 character ROM. Unless noted, these codes produce the same glyph in **both** character sets — they can be used for UI drawing without switching sets.

### Block and Fill Characters

| Screen Code | Pixel Pattern              | Description              | Both sets? |
|-------------|----------------------------|--------------------------|------------|
| `$20`       | (empty)                    | Space                    | Yes        |
| `$A0`       | (full 8x8)                 | Solid block (rev space)  | Yes        |
| `$60`       | (empty)                    | Blank (same as space)    | Yes        |
| `$61`       | `####....` (all rows)      | Left half block          | Yes        |
| `$62`       | rows 4-7 solid             | Lower half block         | Yes        |
| `$66`       | checkerboard all rows      | Full checkerboard        | Yes        |
| `$68`       | checkerboard rows 4-7      | Lower checkerboard       | Yes        |
| `$69`       | filled triangle (diagonal) | Diagonal fill            | **No**     |
| `$7F`       | `####....` / `....####`    | 2x2 quadrant checker     | Yes        |

### Quarter Blocks

| Screen Code | Pixel Pattern              | Description              |
|-------------|----------------------------|--------------------------|
| `$7E`       | top-left quarter           | TL quarter block         |
| `$7C`       | top-right quarter          | TR quarter block         |
| `$6C`       | bottom-right quarter       | BR quarter block         |
| `$7B`       | bottom-left quarter        | BL quarter block         |

### Center-Line Drawing Characters (1px through cell center)

These draw 1-pixel lines through the **center** of each character cell (row 4 or column 4). Corner characters join a center-horizontal to a center-vertical at the cell center point.

| Screen Code | Pixel Pattern             | Description              |
|-------------|---------------------------|--------------------------|
| `$40`       | row 4: `########`         | Horizontal center line   |
| `$5D`       | col 4: `....#...`         | Vertical center line     |
| `$5B`       | row 4 + col 4             | Cross / plus (┼)         |
| `$70`       | h-right + v-down          | Corner TL (center style) |
| `$6E`       | h-left + v-down           | Corner TR (center style) |
| `$6D`       | h-right + v-up            | Corner BL (center style) |
| `$7D`       | h-left + v-up             | Corner BR (center style) |
| `$71`       | h-both + v-up             | T-junction up (┴)        |
| `$72`       | h-both + v-down           | T-junction down (┬)      |
| `$73`       | v-both + h-left           | T-junction left (┤)      |
| `$6B`       | v-both + h-right          | T-junction right (├)     |

### Edge-Line Drawing Characters (1px/2px/3px at cell edges)

These draw lines at the **edges** of character cells. Adjacent cells form continuous lines. No dedicated corner characters — walls meet naturally at cell boundaries.

| Screen Code | Pixel Pattern             | Description              |
|-------------|---------------------------|--------------------------|
| `$63`       | row 0 only                | Top edge 1px             |
| `$64`       | row 7 only                | Bottom edge 1px          |
| `$65`       | col 0 only                | Left edge 1px            |
| `$67`       | col 7 only                | Right edge 1px           |
| `$77`       | rows 0-1                  | Top edge 2px             |
| `$6F`       | rows 6-7                  | Bottom edge 2px          |
| `$74`       | cols 0-1                  | Left edge 2px            |
| `$6A`       | cols 6-7                  | Right edge 2px           |
| `$78`       | rows 0-2                  | Top edge 3px             |
| `$79`       | rows 5-7                  | Bottom edge 3px          |
| `$75`       | cols 0-2                  | Left edge 3px            |
| `$76`       | cols 5-7                  | Right edge 3px           |

## Box Drawing Styles

The PET character ROM provides four distinct box-drawing styles. All use screen codes that are **identical in both character sets** — no charset switching is needed. Each style produces a visually different border weight.

### Style 1: Center-Line (1px through cell center, with corners)

Lines pass through the center of each cell. Dedicated corner characters join the horizontal and vertical at the center point.

```
#################################
#                               #
#                               #
#################################
```

| Role  | Code | Description              |
|-------|------|--------------------------|
| TL    | `$70` | h-right + v-down        |
| TR    | `$6E` | h-left + v-down         |
| BL    | `$6D` | h-right + v-up          |
| BR    | `$7D` | h-left + v-up           |
| H     | `$40` | horizontal center line  |
| V     | `$5D` | vertical center line    |

### Style 2: Thick (3px walls at cell edges)

Walls are 3 pixels wide at the edges of each cell. No dedicated corners — walls meet at cell boundaries.

```
##############################
###                        ###
##############################
```

| Role  | Code | Description              |
|-------|------|--------------------------|
| Left  | `$76` | right 3px vertical      |
| Right | `$75` | left 3px vertical       |
| Top   | `$78` | top 3px horizontal      |
| Bottom| `$62` | lower half (4px)        |

### Style 3: Medium (2px walls at cell edges)

Walls are 2 pixels wide at the edges of each cell.

```
############################
##                      ##
############################
```

| Role  | Code | Description              |
|-------|------|--------------------------|
| Left  | `$6A` | right 2px vertical      |
| Right | `$74` | left 2px vertical       |
| Top   | `$77` | top 2px horizontal      |
| Bottom| `$79` | bottom 3px horizontal   |

### Style 4: Thin (1px walls at cell edges)

Walls are 1 pixel wide at the edges of each cell.

```
##########################
#                      #
##########################
```

| Role  | Code | Description              |
|-------|------|--------------------------|
| Left  | `$67` | right 1px vertical      |
| Right | `$65` | left 1px vertical       |
| Top   | `$63` | top 1px horizontal      |
| Bottom| `$64` | bottom 1px horizontal   |

### Choosing a Style

| Style       | Line width | Corners?  | Best for                    |
|-------------|------------|-----------|-----------------------------|
| Center-line | 1px center | Yes       | UI frames, dialog boxes     |
| Thick       | 3px edge   | No        | Bold borders, titles        |
| Medium      | 2px edge   | No        | Panels, grouped sections    |
| Thin        | 1px edge   | No        | Subtle separators, grids    |

The center-line style is the only one with dedicated corner characters. The edge-line styles (thick, medium, thin) form corners naturally where the wall cells meet — the left wall cell and top wall cell share a corner pixel at the cell boundary.

### Center-Line Connectors

The center-line style provides a full set of connector characters for drawing grids and divided frames. All codes are identical in both character sets.

| Screen Code | Pixel Pattern             | Connector              |
|-------------|---------------------------|------------------------|
| `$70`       | h-right + v-down          | Corner TL (┌)         |
| `$6E`       | h-left + v-down           | Corner TR (┐)         |
| `$6D`       | h-right + v-up            | Corner BL (└)         |
| `$7D`       | h-left + v-up             | Corner BR (┘)         |
| `$72`       | h-both + v-down           | T-junction down (┬)   |
| `$71`       | h-both + v-up             | T-junction up (┴)     |
| `$6B`       | v-both + h-right          | T-junction right (├)  |
| `$73`       | v-both + h-left           | T-junction left (┤)   |
| `$5B`       | h-both + v-both           | Cross (┼)             |
| `$40`       | row 4: `########`         | Horizontal line (─)   |
| `$5D`       | col 4: `....#...`         | Vertical line (│)     |

### Grid Frame Example

A 2×2 cell grid using all nine center-line connectors — 4 corners, 4 T-junctions, and 1 cross. This is the default frame pattern for divided panels.

Screen layout (5 rows × 9 columns):

```
70 40 40 40 72 40 40 40 6E      ┌───────┬───────┐
5D 20 20 20 5D 20 20 20 5D      │       │       │
6B 40 40 40 5B 40 40 40 73      ├───────┼───────┤
5D 20 20 20 5D 20 20 20 5D      │       │       │
6D 40 40 40 71 40 40 40 7D      └───────┴───────┘
```

Rendered at pixel level:

```
#################################################################
#                               #                               #
#                               #                               #
#                               #                               #
#################################################################
#                               #                               #
#                               #                               #
#                               #                               #
#################################################################
```

To draw a grid with N columns and M rows of cells, place T-junctions (`$72`/`$71`) at internal horizontal dividers, T-junctions (`$6B`/`$73`) at internal vertical dividers, crosses (`$5B`) at internal intersections, and corners (`$70`/`$6E`/`$6D`/`$7D`) at the four outer corners.

**Reverse video rule:** Any screen code OR'd with `$80` inverts the character.

`$20 | $80 = $A0` is the solid block.

`$A0 | $80 = $20` is a space again (inverting reverses back).

### Solid Block Pattern

The most common animation primitive is alternating solid blocks and spaces:

```asm
        lda #$A0                ; solid block (reversed space)
        sta SCREEN,x            ; filled cell

        lda #$20                ; space
        sta SCREEN,x            ; empty cell
```

### Checkerboard Fill

```asm
fill_checker:

        ldx #$00
        lda #$20

.loop

        sta SCREEN,x            ; even column: space
        lda #$A0
        sta SCREEN+1,x          ; odd column: solid
        lda #$20
        inx
        inx
        cpx #$28
        bne .loop
        rts
```

### Drawing a Window Frame

Use the center-line box-drawing characters to draw a bordered window at any screen position. These codes work in both character sets — no charset switching needed.

Pass the window parameters as a 4-byte block in free RAM; put the block's address in X (low byte) and Y (high byte). The routine borrows $FB-$FD internally, saves and restores all three.

```asm
SCREEN      = $8000

BOX_TL      = $70       ; corner top-left (center-line style)
BOX_TR      = $6E       ; corner top-right
BOX_BR      = $7D       ; corner bottom-right
BOX_BL      = $6D       ; corner bottom-left
BOX_H       = $40       ; horizontal center line (top and bottom)
BOX_V       = $5D       ; vertical center line (left and right)
```

Define window parameters as data anywhere in free RAM:

```asm
win1:

        byte 5                  ; row (0-24)
        byte $0A                ; col (0-39)
        byte $14                ; width including borders
        byte 8                  ; height including borders

        ldx #<win1
        ldy #>win1
        jsr draw_box_xy
```

Multiple windows use separate labelled byte blocks -- no naming conflicts, no ZP allocation.

```asm
draw_box_xy:            ; X = low byte, Y = high byte of 4-byte parameter block; layout: row, col, width, height; borrows $FB-$FD; saves and restores all three.

        lda $FD
        pha
        lda $FC
        pha
        lda $FB
        pha

        stx $FB
        sty $FC

        ldy #3
        lda ($FB),y             ; height
        pha
        dey
        lda ($FB),y             ; width
        sta $FD                 ; keep width in $FD for the whole routine
        dey
        lda ($FB),y             ; col
        pha
        dey
        lda ($FB),y             ; row
        pha

        lda #<SCREEN
        sta $FB
        lda #>SCREEN
        sta $FC

        pla                     ; row
        tax
        beq draw_xy_col

draw_xy_rowloop:

        lda $FB
        clc
        adc #$28
        sta $FB
        bcc draw_xy_rskip
        inc $FC

draw_xy_rskip:

        dex
        bne draw_xy_rowloop

draw_xy_col:

        pla                     ; col
        clc
        adc $FB
        sta $FB
        bcc draw_xy_top
        inc $FC

draw_xy_top:

        ldy #0
        lda #BOX_TL
        sta ($FB),y
        lda #BOX_H
        ldx $FD
        dex

draw_xy_toploop:

        iny
        sta ($FB),y
        dex
        bne draw_xy_toploop

        lda #BOX_TR
        sta ($FB),y

        pla                     ; height
        sec
        sbc #2                  ; middle row count
        tax
        beq draw_xy_bottom

draw_xy_sides:

        lda $FB
        clc
        adc #$28
        sta $FB
        bcc draw_xy_side
        inc $FC

draw_xy_side:

        ldy #0
        lda #BOX_V
        sta ($FB),y
        ldy $FD
        dey                     ; right border at column width-1
        lda #BOX_V
        sta ($FB),y
        dex
        bne draw_xy_sides

draw_xy_bottom:

        lda $FB
        clc
        adc #$28
        sta $FB
        bcc draw_xy_bot
        inc $FC

draw_xy_bot:

        ldy #0
        lda #BOX_BL
        sta ($FB),y
        lda #BOX_H
        ldx $FD
        dex

draw_xy_botloop:

        iny
        sta ($FB),y
        dex
        bne draw_xy_botloop

        lda #BOX_BR
        sta ($FB),y

        pla
        sta $FB
        pla
        sta $FC
        pla
        sta $FD
        rts
```

The parameter block can sit anywhere in free RAM -- after BASIC program end, in a data section, or in tape buffers when tape is not in use.

### Horizontal Divider Line

Draw a horizontal line across an entire row. Use `$40` for a center-line style divider (1px through cell center), `$63` for a thin top-edge divider, or `$64` for a thin bottom-edge divider.

```asm
SCREEN  = $8000

draw_hline:             ; draw horizontal line across row X (0-24); A = line char; borrows $FB-$FC; saves and restores both. Uses $FF (unused by BASIC).

        sta $FF                 ; stash line char ($FF unused by PET BASIC 2)
        lda $FC
        pha
        lda $FB
        pha

        jsr get_row_ptr         ; X = row, sets $FB/$FC to row start (clobbers A)
        lda $FF                 ; restore line char into A
        ldy #$27

draw_hline_loop:

        sta ($FB),y             ; write line char across all 40 columns
        dey
        bpl draw_hline_loop
        pla
        sta $FB
        pla
        sta $FC
        rts
```

Usage:

```asm
        ldx #5                  ; row 5
        lda #$40                ; center-line horizontal divider
        jsr draw_hline

        ldx #15                 ; row 15
        lda #$64                ; thin bottom-edge divider
        jsr draw_hline
```

### Vertical Divider Line

Draw a vertical line down a column. Use `$5D` for a center-line style divider (1px through cell center), `$65` for a thin left-edge divider, or `$67` for a thin right-edge divider.

```asm
SCREEN  = $8000

draw_vline:             ; draw vertical line at column X (0-39), all 25 rows; A = line char; borrows $FB-$FC; saves and restores both. Uses $FF (unused by BASIC).

        sta $FF                 ; stash line char ($FF unused by PET BASIC 2)
        lda $FC
        pha
        lda $FB
        pha

        lda #<SCREEN
        sta $FB
        lda #>SCREEN
        sta $FC
        txa                     ; add column offset to screen base
        clc
        adc $FB
        sta $FB
        bcc draw_vl_start
        inc $FC

draw_vl_start:

        ldx #$19                ; 25 rows

draw_vl_loop:

        lda $FF                 ; load line char
        ldy #$00
        sta ($FB),y             ; write line character at current row
        lda $FB                 ; advance to next row (add 40)
        clc
        adc #$28
        sta $FB
        bcc draw_vl_next
        inc $FC

draw_vl_next:

        dex
        bne draw_vl_loop
        pla
        sta $FB
        pla
        sta $FC
        rts
```

Usage:

```asm
        ldx #10                 ; column 10
        lda #$5D                ; center-line vertical divider
        jsr draw_vline

        ldx #30                 ; column 30
        lda #$67                ; thin right-edge divider
        jsr draw_vline
```

### Filled Rectangle

Fill a rectangular area with solid blocks (`$A0`). Pass parameters as a 4-byte block (row, col, width, height), the same layout used by `draw_box_xy` above.

```asm
SCREEN  = $8000

fill_rect:              ; X = low, Y = high of 4-byte block: row, col, width, height; fills with $A0; borrows $FB-$FD; saves and restores all three.

        lda $FD
        pha
        lda $FC
        pha
        lda $FB
        pha

        stx $FB                 ; $FB/$FC = param block address
        sty $FC
        ldy #3
        lda ($FB),y             ; height
        pha
        dey
        lda ($FB),y             ; width
        sta $FD
        dey
        lda ($FB),y             ; col
        pha
        dey
        lda ($FB),y             ; row
        pha

        lda #<SCREEN
        sta $FB
        lda #>SCREEN
        sta $FC

        pla                     ; row
        tax
        beq fill_rect_col

fill_rect_rowloop:

        lda $FB
        clc
        adc #$28
        sta $FB
        bcc fill_rect_rskip
        inc $FC

fill_rect_rskip:

        dex
        bne fill_rect_rowloop

fill_rect_col:

        pla                     ; col
        clc
        adc $FB
        sta $FB
        bcc fill_rect_fill
        inc $FC

fill_rect_fill:

        pla                     ; height
        tax

fill_rect_row:

        ldy $FD                 ; Y = width
        dey

fill_rect_col_loop:

        lda #$A0                ; solid block
        sta ($FB),y
        dey
        bpl fill_rect_col_loop

        lda $FB                 ; advance to next row
        clc
        adc #$28
        sta $FB
        bcc fill_rect_next
        inc $FC

fill_rect_next:

        dex
        bne fill_rect_row

        pla
        sta $FB
        pla
        sta $FC
        pla
        sta $FD
        rts
```

Usage:

```asm
rect1:

        byte 5                  ; row (0-24)
        byte $0A                ; col (0-39)
        byte $14                ; width (20 cells)
        byte 8                  ; height (8 rows)

        ldx #<rect1
        ldy #>rect1
        jsr fill_rect
```

### Progress Bar

Draw a horizontal progress bar at a given row and column. The bar uses solid blocks (`$A0`) for the filled portion and spaces (`$20`) for the empty portion.

```asm
SCREEN    = $8000
BAR_WIDTH = 20

draw_progress:          ; draw 20-cell progress bar at row X, col Y; A = fill (0-20); borrows $FB-$FC; saves and restores both. Uses $FF (unused by BASIC).

        sta $FF                 ; stash fill count ($FF unused by PET BASIC 2)
        lda $FC
        pha
        lda $FB
        pha

        jsr get_row_ptr         ; X = row, sets $FB/$FC to row start (clobbers A)
        tya                     ; A = col (Y preserved through get_row_ptr)
        clc
        adc $FB
        sta $FB
        bcc dp_start
        inc $FC

dp_start:

        ldy #$00                ; Y = column index within bar
        ldx $FF                 ; X = fill count

dp_fill:

        cpx #$00
        beq dp_empty
        lda #$A0                ; solid block (filled)
        sta ($FB),y
        dex
        iny
        cpy #BAR_WIDTH
        bne dp_fill
        jmp dp_done

dp_empty:

        lda #$20                ; space (empty)
        sta ($FB),y
        iny
        cpy #BAR_WIDTH
        bne dp_empty

dp_done:

        pla
        sta $FB
        pla
        sta $FC
        rts
```

Usage:

```asm
        ldx #10                 ; row 10
        ldy #10                 ; column 10
        lda #15                 ; 15 of 20 cells filled (75%)
        jsr draw_progress
```

### Title Bar (Reverse Video)

A full-width title bar or status bar is a row with reverse video (bit 7) set on every character. Use `highlight_row` (defined above) for this purpose -- it sets bit 7 on all 40 characters in a row.

```asm
        ldx #0                  ; row 0 (top of screen)
        jsr highlight_row       ; title bar: reverse video on entire row
```

To write text into the title bar, OR each character's screen code with `$80` before storing it to screen RAM. See the "Reverse Video" section above for per-character and global reverse mode techniques.

## Screen Scrolling

The PET hardware does not support hardware scrolling.

Scrolling must be done in software by copying screen RAM.

### Scroll Up One Line

```asm
scroll_up:

        ldx #$00

loop:

        lda SCREEN+40,x
        sta SCREEN,x
        lda SCREEN+40+$100,x
        sta SCREEN+$100,x
        lda SCREEN+40+$200,x
        sta SCREEN+$200,x
        inx
        bne loop
        ldx #$27                 ; clear bottom row
        lda #$20

clr:

        sta SCREEN+24*40,x
        dex
        bpl clr
        rts
```
