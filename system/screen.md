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
- Each byte = screen code (not PETSCII)
- Bit 7 set = reverse video (hardware inverted)
- Row stride: 40 bytes

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
; X = row (0-24), Y = column (0-39)
; Result written to $FB (lo) and $FC (hi); caller saves/restores if needed.

calc_screen_addr:

        lda #<SCREEN
        sta $FB
        lda #>SCREEN
        sta $FC
        ; add row * 40
        lda row_mult_lo,x
        clc
        adc $FB
        sta $FB
        lda row_mult_hi,x
        adc $FC
        sta $FC
        ; add column
        tya
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
| @     | $00     | $00         |
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

```asm
clear_screen:

        ldx #$00
        lda #$20                ; space character

loop:

        sta SCREEN,x
        sta SCREEN+$100,x
        sta SCREEN+$200,x
        sta SCREEN+$300,x
        inx
        bne loop
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

; highlight_row: set reverse video on all 40 chars in screen row X (0-24)
; Borrows $FB-$FC; saves and restores both.
highlight_row:

        lda $FC
        pha
        lda $FB
        pha
        jsr get_row_ptr
        ldy #39

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

; unhighlight_row: clear reverse video on all 40 chars in screen row X
; Borrows $FB-$FC; saves and restores both.
unhighlight_row:

        lda $FC
        pha
        lda $FB
        pha
        jsr get_row_ptr
        ldy #39

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

; get_row_ptr: set $FB/$FC to address of screen row X (internal helper)
get_row_ptr:

        lda #<SCREEN
        sta $FB
        lda #>SCREEN
        sta $FC
        txa
        beq get_row_done        ; row 0: base is already correct

get_row_loop:

        lda $FB
        clc
        adc #40
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

## Graphics Characters (Uppercase + Graphics Charset)

In the uppercase and graphics character set (PCR CA2 high, `PCR_U = $0C`), the PET provides block graphics and line-drawing characters.

Screen codes in the $60-$7F range are the "graphics" portion of the charset.

Key screen codes for demoscene and animation:

| Screen Code | Description                   | Common Use      |
|-------------|-------------------------------|-----------------|
| $20         | Space - empty cell            | Background      |
| $A0         | Solid block (`$20` reversed)  | Foreground fill |
| $60         | Diagonal lines / checkerboard | Texture         |
| $62         | Horizontal line (top)         | Box top         |
| $63         | Vertical line (right)         | Box right       |
| $64         | Horizontal line (bottom)      | Box bottom      |
| $65         | Vertical line (left)          | Box left        |
| $66         | Corner top-left               | Box drawing     |
| $67         | Corner top-right              | Box drawing     |
| $68         | Corner bottom-right           | Box drawing     |
| $69         | Corner bottom-left            | Box drawing     |
| $7F         | Full square solid             | Pixel art       |

**Reverse video rule:** Any screen code OR'd with `$80` inverts the character.

`$20 | $80 = $A0` is the solid block.

`$A0 | $80 = $20` is a space again (inverting reverses back).

### Solid Block Pattern

The most common animation primitive is alternating solid blocks and spaces:

```asm
        lda #$A0        ; solid block (reversed space)
        sta SCREEN,x    ; filled cell

        lda #$20        ; space
        sta SCREEN,x    ; empty cell
```

### Checkerboard Fill

```asm
fill_checker:

        ldx #$00
        lda #$20
.loop   sta SCREEN,x            ; even column: space
        lda #$A0
        sta SCREEN+1,x          ; odd column: solid
        lda #$20
        inx
        inx
        cpx #40
        bne .loop
        rts
```

### Drawing a Window Frame

Use the box-drawing characters to draw a bordered window at any screen position. The uppercase + graphics character set must be active (`PCR = PCR_U`).

Pass the window parameters as a 4-byte block in free RAM; put the block's address in X (low byte) and Y (high byte). The routine borrows $FB-$FD internally, saves and restores all three.

```asm
SCREEN      = $8000

BOX_TL      = $66        ; corner top-left
BOX_TR      = $67        ; corner top-right
BOX_BR      = $68        ; corner bottom-right
BOX_BL      = $69        ; corner bottom-left
BOX_HTOP    = $62        ; horizontal top edge
BOX_HBOT    = $64        ; horizontal bottom edge
BOX_VLEFT   = $65        ; vertical left edge
BOX_VRIGHT  = $63        ; vertical right edge
```

Define window parameters as data anywhere in free RAM:

```asm
win1:
        byte 5          ; row (0-24)
        byte 10         ; col (0-39)
        byte 20         ; width including borders
        byte 8          ; height including borders

        ldx #<win1
        ldy #>win1
        jsr draw_box_xy
```

Multiple windows use separate labelled byte blocks -- no naming conflicts, no ZP allocation.

```asm
; draw_box_xy: X = low byte, Y = high byte of 4-byte parameter block
; Block layout: byte row, col, width, height
; Borrows $FB-$FD; saves and restores all three.
draw_box_xy:

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
        adc #40
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
        lda #BOX_HTOP
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
        adc #40
        sta $FB
        bcc draw_xy_side
        inc $FC

draw_xy_side:

        ldy #0
        lda #BOX_VLEFT
        sta ($FB),y
        ldy $FD
        dey                     ; right border at column width-1
        lda #BOX_VRIGHT
        sta ($FB),y
        dex
        bne draw_xy_sides

draw_xy_bottom:

        lda $FB
        clc
        adc #40
        sta $FB
        bcc draw_xy_bot
        inc $FC

draw_xy_bot:

        ldy #0
        lda #BOX_BL
        sta ($FB),y
        lda #BOX_HBOT
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
        ; clear bottom row
        ldx #39
        lda #$20

clr:

        sta SCREEN+24*40,x
        dex
        bpl clr
        rts
```
