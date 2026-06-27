# Screen I/O & PETSCII

## Purpose

> **Scope:** Screen RAM, PETSCII, screen codes, cursor, reverse video, keyboard, direct writes
> **Key items:** SCREEN=$8000, 40x25 layout, PETSCII $93 = CLR/HOME, bit 7 = reverse, row stride = 40

This file covers PET 3032 screen I/O in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need
- **Reference tables & mappings** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                  | See instead        |
|-------------------------------|--------------------|
| CRTC/PIA/VIA register details | `hardware/chip.md` |
| KERNAL routines               | `system/kernal.md` |
| Memory map                    | `system/memory.md` |

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
; result in screen_ptr ($FB-$FC)

calc_screen_addr:

        lda #<SCREEN
        sta screen_ptr
        lda #>SCREEN
        sta screen_ptr+1
        ; add row * 40
        lda row_mult_lo,x
        clc
        adc screen_ptr
        sta screen_ptr
        lda row_mult_hi,x
        adc screen_ptr+1
        sta screen_ptr+1
        ; add column
        tya
        clc
        adc screen_ptr
        sta screen_ptr
        bcc done
        inc screen_ptr+1

done:

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

## Keyboard Input

### Via KERNAL (GETIN)

```asm
wait_key:

        jsr GETIN               ; $FFE4
        beq wait_key            ; Z=1 means buffer empty
        ; A now contains PETSCII code of pressed key
```

### Direct Keyboard Matrix Scan

The keyboard is read via PIA 1.

PORT A (bits 3-0) selects the row via a 4-to-10 decoder.

PORT B returns the column states.

```asm
; Scan row 0 (keys: INST/DEL, RETURN, CURSOR RIGHT, F7, F1, F3, F5, CURSOR DOWN)
        lda #$FE                ; select row 0 (bit 0 low)
        sta $E810               ; PIA 1 PORT A
        lda $E812               ; PIA 1 PORT B
        ; each bit 0 = key pressed in that column
```

**Note:** Direct keyboard scanning is complex on the PET due to the matrix decoder.

Using KERNAL GETIN is strongly preferred unless you need to detect multiple simultaneous keys.

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
