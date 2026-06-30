# Semigraphics & UI Drawing

## Purpose

> **Scope:** Semigraphics characters, box drawing styles, window/line/rect routines, double-density plotting, screen scrolling
> **Key items:** Screen codes for UI drawing, center-line vs edge-line styles, draw_box_xy, fill_rect, scroll_up, 80x50 plot_point

This file covers PET 3032 semigraphics and UI drawing techniques in four progressive layers:

- **Quick-lookup table** - scan or search for the character code you need
- **Reference tables & mappings** - dense lookup layer for semigraphics codes
- **Working code examples** - verified ASM snippets for drawing routines
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                  | See instead        |
|-------------------------------|--------------------|
| Screen RAM layout and PETSCII | `system/screen.md` |
| CRTC/PIA/VIA register details | `hardware/chip.md` |
| KERNAL routines               | `system/kernal.md` |
| Reverse video fundamentals    | `system/screen.md` |

## Contents

| Section                 | Line | What it covers                                                      |
|-------------------------|------|---------------------------------------------------------------------|
| Semigraphics Characters | 33   | Block, fill, quarter-block, center-line, edge-line character tables |
| Box Drawing Styles      | 97   | Four styles: center-line, thick, medium, thin; choosing a style     |
| Center-Line Connectors  | 183  | Full connector set: corners, T-junctions, cross, grid frame example |
| Drawing Routines        | 237  | draw_box_xy, horizontal/vertical dividers, fill_rect, progress bar  |
| Double-Density Plotting | 740  | 80x50 pixel grid via 2x2 quadrant chars; quadrant map; plot_point   |
| Title Bar               | 856  | Reverse-video full-width title/status bar                           |
| Screen Scrolling        | 867  | Software scroll-up by copying screen RAM                            |

## Semigraphics Characters

The semigraphics characters below are verified against the 901447-10 character ROM. Unless noted, these codes produce the same glyph in **both** character sets — they can be used for UI drawing without switching sets.

### Block and Fill Characters

| Screen Code | Pixel Pattern              | Description             | Both sets? |
|-------------|----------------------------|-------------------------|------------|
| `$20`       | (empty)                    | Space                   | Yes        |
| `$A0`       | (full 8x8)                 | Solid block (rev space) | Yes        |
| `$60`       | (empty)                    | Blank (same as space)   | Yes        |
| `$61`       | `####....` (all rows)      | Left half block         | Yes        |
| `$62`       | rows 4-7 solid             | Lower half block        | Yes        |
| `$66`       | checkerboard all rows      | Full checkerboard       | Yes        |
| `$68`       | checkerboard rows 4-7      | Lower checkerboard      | Yes        |
| `$69`       | filled triangle (diagonal) | Diagonal fill           | **No**     |
| `$7F`       | `####....` / `....####`    | 2x2 quadrant checker    | Yes        |

### Quarter Blocks

| Screen Code | Pixel Pattern        | Description      |
|-------------|----------------------|------------------|
| `$7E`       | top-left quarter     | TL quarter block |
| `$7C`       | top-right quarter    | TR quarter block |
| `$6C`       | bottom-right quarter | BR quarter block |
| `$7B`       | bottom-left quarter  | BL quarter block |

### Center-Line Drawing Characters (1px through cell center)

These draw 1-pixel lines through the **center** of each character cell (row 4 or column 4). Corner characters join a center-horizontal to a center-vertical at the cell center point.

| Screen Code | Pixel Pattern     | Description              |
|-------------|-------------------|--------------------------|
| `$40`       | row 4: `########` | Horizontal center line   |
| `$5D`       | col 4: `....#...` | Vertical center line     |
| `$5B`       | row 4 + col 4     | Cross / plus (┼)         |
| `$70`       | h-right + v-down  | Corner TL (center style) |
| `$6E`       | h-left + v-down   | Corner TR (center style) |
| `$6D`       | h-right + v-up    | Corner BL (center style) |
| `$7D`       | h-left + v-up     | Corner BR (center style) |
| `$71`       | h-both + v-up     | T-junction up (┴)        |
| `$72`       | h-both + v-down   | T-junction down (┬)      |
| `$73`       | v-both + h-left   | T-junction left (┤)      |
| `$6B`       | v-both + h-right  | T-junction right (├)     |

### Edge-Line Drawing Characters (1px/2px/3px at cell edges)

These draw lines at the **edges** of character cells. Adjacent cells form continuous lines. No dedicated corner characters — walls meet naturally at cell boundaries.

| Screen Code | Pixel Pattern | Description     |
|-------------|---------------|-----------------|
| `$63`       | row 0 only    | Top edge 1px    |
| `$64`       | row 7 only    | Bottom edge 1px |
| `$65`       | col 0 only    | Left edge 1px   |
| `$67`       | col 7 only    | Right edge 1px  |
| `$77`       | rows 0-1      | Top edge 2px    |
| `$6F`       | rows 6-7      | Bottom edge 2px |
| `$74`       | cols 0-1      | Left edge 2px   |
| `$6A`       | cols 6-7      | Right edge 2px  |
| `$78`       | rows 0-2      | Top edge 3px    |
| `$79`       | rows 5-7      | Bottom edge 3px |
| `$75`       | cols 0-2      | Left edge 3px   |
| `$76`       | cols 5-7      | Right edge 3px  |

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

| Role | Code  | Description            |
|------|-------|------------------------|
| TL   | `$70` | h-right + v-down       |
| TR   | `$6E` | h-left + v-down        |
| BL   | `$6D` | h-right + v-up         |
| BR   | `$7D` | h-left + v-up          |
| H    | `$40` | horizontal center line |
| V    | `$5D` | vertical center line   |

### Style 2: Thick (3px walls at cell edges)

Walls are 3 pixels wide at the edges of each cell. No dedicated corners — walls meet at cell boundaries.

```
##############################
###                        ###
##############################
```

| Role   | Code  | Description        |
|--------|-------|--------------------|
| Left   | `$76` | right 3px vertical |
| Right  | `$75` | left 3px vertical  |
| Top    | `$78` | top 3px horizontal |
| Bottom | `$62` | lower half (4px)   |

### Style 3: Medium (2px walls at cell edges)

Walls are 2 pixels wide at the edges of each cell.

```
############################
##                        ##
############################
```

| Role   | Code  | Description           |
|--------|-------|-----------------------|
| Left   | `$6A` | right 2px vertical    |
| Right  | `$74` | left 2px vertical     |
| Top    | `$77` | top 2px horizontal    |
| Bottom | `$79` | bottom 3px horizontal |

### Style 4: Thin (1px walls at cell edges)

Walls are 1 pixel wide at the edges of each cell.

```
##########################
#                        #
##########################
```

| Role   | Code  | Description           |
|--------|-------|-----------------------|
| Left   | `$67` | right 1px vertical    |
| Right  | `$65` | left 1px vertical     |
| Top    | `$63` | top 1px horizontal    |
| Bottom | `$64` | bottom 1px horizontal |

### Choosing a Style

| Style       | Line width | Corners? | Best for                 |
|-------------|------------|----------|--------------------------|
| Center-line | 1px center | Yes      | UI frames, dialog boxes  |
| Thick       | 3px edge   | No       | Bold borders, titles     |
| Medium      | 2px edge   | No       | Panels, grouped sections |
| Thin        | 1px edge   | No       | Subtle separators, grids |

The center-line style is the only one with dedicated corner characters. The edge-line styles (thick, medium, thin) form corners naturally where the wall cells meet — the left wall cell and top wall cell share a corner pixel at the cell boundary.

## Center-Line Connectors

The center-line style provides a full set of connector characters for drawing grids and divided frames. All codes are identical in both character sets.

| Screen Code | Pixel Pattern     | Connector            |
|-------------|-------------------|----------------------|
| `$70`       | h-right + v-down  | Corner TL (┌)        |
| `$6E`       | h-left + v-down   | Corner TR (┐)        |
| `$6D`       | h-right + v-up    | Corner BL (└)        |
| `$7D`       | h-left + v-up     | Corner BR (┘)        |
| `$72`       | h-both + v-down   | T-junction down (┬)  |
| `$71`       | h-both + v-up     | T-junction up (┴)    |
| `$6B`       | v-both + h-right  | T-junction right (├) |
| `$73`       | v-both + h-left   | T-junction left (┤)  |
| `$5B`       | h-both + v-both   | Cross (┼)            |
| `$40`       | row 4: `########` | Horizontal line (─)  |
| `$5D`       | col 4: `....#...` | Vertical line (│)    |

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

## Drawing Routines

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

## Double-Density Plotting

The 40x25 text screen can act as an 80x50 pixel grid by using the 2x2 quarter-block graphics. Each character cell holds four quadrants -- top-left, top-right, bottom-left, bottom-right -- and the character set has a glyph for all 16 on/off combinations. Plotting a pixel sets one quadrant of one cell to the glyph that matches the resulting combination, leaving the cell's other quadrants intact.

Pixel `(x, y)` with `(0, 0)` at the top-left maps to cell column `x / 2`, cell row `y / 2`, and the quadrant picked by the low bit of `x` (left or right) and the low bit of `y` (top or bottom).

### Quadrant Character Map

Screen code for each combination of lit quadrants, verified against the 901447-10 character ROM. Combinations beyond the four base quarter-blocks use the reverse-video glyph (bit 7 set).

| TL | TR | BL | BR | Screen code | Looks like  |
|----|----|----|----|-------------|-------------|
| .  | .  | .  | .  | `$20`       | empty       |
| #  | .  | .  | .  | `$7E`       | TL quarter  |
| .  | #  | .  | .  | `$7C`       | TR quarter  |
| #  | #  | .  | .  | `$E2`       | top half    |
| .  | .  | #  | .  | `$7B`       | BL quarter  |
| #  | .  | #  | .  | `$61`       | left half   |
| .  | #  | #  | .  | `$FF`       | diagonal /  |
| #  | #  | #  | .  | `$EC`       | all but BR  |
| .  | .  | .  | #  | `$6C`       | BR quarter  |
| #  | .  | .  | #  | `$7F`       | diagonal \  |
| .  | #  | .  | #  | `$E1`       | right half  |
| #  | #  | .  | #  | `$FB`       | all but BL  |
| .  | .  | #  | #  | `$62`       | bottom half |
| #  | .  | #  | #  | `$FC`       | all but TR  |
| .  | #  | #  | #  | `$FE`       | all but TL  |
| #  | #  | #  | #  | `$A0`       | full block  |

### plot_point Routine

`plot_point` reads the cell's current glyph, adds one quadrant, and writes the glyph for the new combination. Because it reads before it writes, repeated calls build up a shape pixel by pixel. It calls `calc_screen_addr` (see `system/screen.md`) to turn the cell row and column into a screen address.

```asm
SCREEN  = $8000

; plot_point: set one pixel in the 80x50 double-density grid.
;   In:  X = pixel column (0..79), Y = pixel row (0..49); (0,0) = top-left
;   Borrows $FB-$FE (saved and restored). Clobbers A.
plot_point:

        lda $FB                 ; save borrowed bytes
        pha
        lda $FC
        pha
        lda $FD
        pha
        lda $FE
        pha
        stx $FE                 ; $FE = pixel column
        sty $FD                 ; $FD = pixel row

        lda $FE                 ; quadrant index = x_odd + 2*y_odd
        and #1
        tax                     ; X = x_odd (0 or 1)
        lda $FD
        and #1
        beq pp_xy
        inx
        inx                     ; +2 selects the bottom row
pp_xy:
        lda quad_bit,x          ; quadrant mask: 1, 2, 4, or 8
        pha                     ; keep it across calc_screen_addr

        lda $FD                 ; cell row = pixel row / 2
        lsr
        tax
        lda $FE                 ; cell column = pixel column / 2
        lsr
        tay
        jsr calc_screen_addr    ; -> $FB/$FC = cell address

        pla
        sta $FD                 ; $FD = quadrant mask (row no longer needed)

        ldy #0
        lda ($FB),y             ; current glyph in this cell
        ldx #15                 ; find its quadrant pattern (0..15)
pp_rev:
        cmp quad_chars,x
        beq pp_found
        dex
        bpl pp_rev
        ldx #0                  ; not a quadrant glyph: treat cell as empty
pp_found:
        txa
        ora $FD                 ; add the new quadrant
        tax
        lda quad_chars,x        ; glyph for the new combination
        ldy #0
        sta ($FB),y

        pla                     ; restore borrowed bytes
        sta $FE
        pla
        sta $FD
        pla
        sta $FC
        pla
        sta $FB
        rts

quad_bit:

        byte 1,2,4,8

quad_chars:

        byte $20,$7E,$7C,$E2,$7B,$61,$FF,$EC
        byte $6C,$7F,$E1,$FB,$62,$FC,$FE,$A0
```

To clear a pixel instead of setting it, force the target quadrant off while leaving the other three alone. Replace the `txa` / `ora $FD` pair with `txa` / `eor #$0F` / `ora $FD` / `eor #$0F`: inverting, OR-ing the quadrant bit, and inverting again is `pattern AND NOT bit`, which clears just that quadrant.

Plotting onto a cell that holds a normal character (text) finds no matching quadrant pattern, so the cell is treated as empty and the character is replaced. Keep plotted graphics and text in separate screen regions.

## Title Bar (Reverse Video)

A full-width title bar or status bar is a row with reverse video (bit 7) set on every character. Use `highlight_row` (defined in `system/screen.md`) for this purpose -- it sets bit 7 on all 40 characters in a row.

```asm
        ldx #0                  ; row 0 (top of screen)
        jsr highlight_row       ; title bar: reverse video on entire row
```

To write text into the title bar, OR each character's screen code with `$80` before storing it to screen RAM. See `system/screen.md` "Reverse Video" section for per-character and global reverse mode techniques.

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
