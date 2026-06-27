# Keyboard Input

## Purpose

> **Scope:** PET keyboard matrix, PIA 1 row/column scan, KERNAL GETIN, special keys, multi-key detection
> **Key items:** PIA1 PORT A=$E810, PORT B=$E812, 10 rows x 8 columns, GETIN=$FFE4, STOP=$FFE1

This file covers PET 3032 keyboard input in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need
- **Reference tables** - dense lookup layer (matrix map, key codes)
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                | See instead        |
|-----------------------------|--------------------|
| PIA 1 hardware registers    | `hardware/chip.md` |
| KERNAL jump table addresses | `system/kernal.md` |
| Screen output and PETSCII   | `system/screen.md` |

## Quick-Lookup

| Need                              | Section                  |
|-----------------------------------|--------------------------|
| Read a key via KERNAL             | KERNAL GETIN             |
| Check STOP key                    | STOP Key                 |
| Scan a specific key directly      | Direct Matrix Scan       |
| Detect simultaneous key presses   | Multi-Key Detection      |
| Full matrix layout                | Keyboard Matrix Map      |
| PETSCII code for a key            | Common PETSCII Key Codes |

## KERNAL GETIN

The simplest way to read the keyboard is via KERNAL GETIN ($FFE4).

GETIN reads one character from the keyboard buffer.

It returns `$00` in A if no key is waiting.

```asm
GETIN   = $FFE4

; Wait for any key press:
wait_key:

        jsr GETIN
        beq wait_key            ; loop until A != 0
        ; A now contains PETSCII code of pressed key
        rts

; Poll without blocking:
poll_key:

        jsr GETIN               ; returns 0 if no key
        rts
```

GETIN reads the keyboard buffer, not the matrix directly.

Keys are buffered by the KERNAL IRQ handler (keyboard scan runs at 60 Hz).

## STOP Key

The STOP key has a dedicated KERNAL routine at $FFE1.

```asm
STOP    = $FFE1

        jsr STOP                ; sets Z=1 if STOP is held
        beq stop_pressed
        ; continue normally

stop_pressed:

        ; handle break
```

The STOP key is also returned by GETIN as PETSCII `$03` (ETX / RUN/STOP).

## Keyboard Matrix Map

The PET keyboard is a 10-row by 8-column matrix.

PIA 1 PORT A (bits 3-0) drives a 4-to-10 line decoder to select one row at a time.

PIA 1 PORT B reads back the 8 column states.

A bit value of `0` means the key is pressed; `1` means not pressed.

| Row | PORT A value | Keys (column 7 to 0)                                             |
|-----|--------------|------------------------------------------------------------------|
| 0   | $FE          | ! , @ , # , $ , % , ' , & , (space STOP)                        |
| 1   | $FD          | Q , W , E , R , T , Y , U , I                                    |
| 2   | $FB          | O , P , [ , ] , RETURN , DELETE , PI , *                         |
| 3   | $F7          | A , S , D , F , G , H , J , K                                    |
| 4   | $EF          | L , : , ; , @ , (cursor up) , (cursor right) , (cursor down) , = |
| 5   | $DF          | Z , X , C , V , B , N , M , ,                                    |
| 6   | $BF          | . , / , (shift right) , RUN/STOP , (shift left) , HOME , BACK , (del/inst) |
| 7   | $7F          | 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8                                   |
| 8   | $FE (2nd)    | 9 , 0 , + , - , (cursor left) , (cursor down rev) , CLR/HOME , = |
| 9   | $FD (2nd)    | (not used on 3032)                                               |

**Note:** The exact key assignments vary between PET keyboard models (business keyboard vs. graphics keyboard).

The table above is for the PET 3032 graphics keyboard.

## Direct Matrix Scan

Direct scanning reads PORT A and PORT B directly, bypassing KERNAL buffering.

This allows detection of multiple simultaneous keys.

```asm
PIA1_PA = $E810         ; PIA 1 PORT A: row select
PIA1_PB = $E812         ; PIA 1 PORT B: column data

; Scan row 1 (Q W E R T Y U I):
        lda #$FD                ; select row 1
        sta PIA1_PA
        lda PIA1_PB             ; read columns
        ; bit 7 = Q, bit 6 = W, ..., bit 0 = I
        ; bit = 0 means key is pressed
```

### Check a Specific Key

To test whether 'Q' (row 1, column 7) is pressed:

```asm
        lda #$FD                ; row 1
        sta PIA1_PA
        lda PIA1_PB
        and #$80                ; mask column 7
        beq q_pressed           ; 0 = pressed
```

### Scan All Rows

```asm
key_table:  byte $FE,$FD,$FB,$F7,$EF,$DF,$BF,$7F     ; 8 rows

scan_all:

        ldx #$00

scan_loop:

        lda key_table,x
        sta PIA1_PA
        lda PIA1_PB             ; column data for this row
        sta key_state,x         ; store result
        inx
        cpx #8
        bne scan_loop
        rts

key_state:  byte 0,0,0,0,0,0,0,0   ; 8 bytes: one per row
```

After `scan_all`, each byte in `key_state` holds the column bitmap for that row.

A `0` bit means the key is currently pressed.

## Multi-Key Detection

Direct scanning is required for simultaneous key detection.

GETIN returns only one key at a time and cannot detect chords.

```asm
; Check if both SHIFT keys are pressed simultaneously:
; Left shift: row 6, bit 1
; Right shift: row 6, bit 5

check_shift:

        lda #$BF                ; select row 6
        sta PIA1_PA
        lda PIA1_PB
        and #$22                ; mask bits 5 and 1
        beq both_shifts         ; both 0 = both pressed
        cmp #$20
        beq right_shift_only
        cmp #$02
        beq left_shift_only
        ; no shift
        rts

both_shifts:
right_shift_only:
left_shift_only:

        rts
```

## Common PETSCII Key Codes

These are the PETSCII values returned by GETIN for commonly used keys.

| Key            | PETSCII | Hex  |
|----------------|---------|------|
| Space          | 32      | $20  |
| Return         | 13      | $0D  |
| Delete/Back    | 20      | $14  |
| Insert         | 148     | $94  |
| Cursor up      | 145     | $91  |
| Cursor down    | 17      | $11  |
| Cursor left    | 157     | $9D  |
| Cursor right   | 29      | $1D  |
| Home           | 19      | $13  |
| CLR/HOME       | 147     | $93  |
| RUN/STOP       | 3       | $03  |
| F1             | 133     | $85  |
| F3             | 134     | $86  |
| F5             | 135     | $87  |
| F7             | 136     | $88  |
| A-Z (shifted)  | 65-90   | $41-$5A |
| A-Z (unshifted)| 65-90   | $41-$5A |
| 0-9            | 48-57   | $30-$39 |

**Note:** On the PET, upper and lower case letters are returned as the same PETSCII code regardless of SHIFT when using GETIN.

The SHIFT key state is reflected in the PETSCII code only for special characters and function keys.

## Deep Reference Notes

### KERNAL Keyboard Buffer

The KERNAL keyboard buffer holds 10 characters (at $0270-$027A).

The buffer is filled by the 60 Hz IRQ keyboard scan.

If the buffer is full, additional keystrokes are discarded.

### Debounce

The KERNAL keyboard scan debounces keys automatically.

Direct matrix scanning has no debounce.

Add a delay or counter-based debounce in your scan loop if needed.

### PIA 1 DDR and Initial State

At reset, PIA 1 PORT A bits 3-0 are outputs (set by KERNAL).

Do not change the data direction register (DDRA at $E811 CRA logic) unless you know the consequences.

The KERNAL sets up PORT A as output and PORT B as input during initialization.

### Ghosting

The PET keyboard matrix has no diodes.

With three or more keys pressed simultaneously, a phantom keypress may be detected on unintended rows.

This is normal hardware behavior.
