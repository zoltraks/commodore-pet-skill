# KERNAL Vectors & I/O Routines

## Purpose

> **Scope:** KERNAL jump table ($FF00-$FFFF), indirect vectors, CHROUT/GETIN/CLALL/STOP, file I/O, tape, safe hooks
> **Key items:** CHROUT=$FFD2, GETIN=$FFE4, CLALL=$FFE7, STOP=$FFE1, CINV=$0090, CBINV=$0092, NMINV=$0094

This file covers the PET 3032 KERNAL in four progressive layers:

- **Quick-lookup table** - scan or search for the routine you need
- **Reference tables & vectors** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope             | See instead        |
|--------------------------|--------------------|
| Hardware chip registers  | `hardware/chip.md` |
| Memory map and zero page | `system/memory.md` |
| Screen RAM and PETSCII   | `system/screen.md` |

## KERNAL Jump Table ($FF00-$FFFF)

The PET KERNAL provides a jump table at the top of ROM.

Each entry is a 3-byte `JMP` instruction.

| Address | Name   | Description                        | Input                                         | Output               |
|---------|--------|------------------------------------|-----------------------------------------------|----------------------|
| $FFB7   | READST | Read I/O status word               | -                                             | A = STATUS           |
| $FFBA   | SETLFS | Set logical file params            | A = LF#, X = device, Y = SA                   | -                    |
| $FFBD   | SETNAM | Set filename                       | A = length, X/Y = name addr                   | -                    |
| $FFC0   | OPEN   | Open logical file                  | (params set by SETLFS/SETNAM)                 | C = error            |
| $FFC3   | CLOSE  | Close logical file                 | A = logical file number                       | -                    |
| $FFC6   | CHKIN  | Set input channel                  | X = logical file number                       | C = error            |
| $FFC9   | CHKOUT | Set output channel                 | X = logical file number                       | C = error            |
| $FFCC   | CLRCHN | Clear channels                     | -                                             | -                    |
| $FFCF   | BASIN  | Read byte from current input       | -                                             | A = byte             |
| $FFD2   | CHROUT | Output character to current output | A = PETSCII char                              | C = error            |
| $FFD5   | LOAD   | Load file to memory                | A = 0 (load) / 1 (verify), X/Y = addr if SA=1 | X/Y = end+1          |
| $FFD8   | SAVE   | Save memory range                  | A = ZP ptr to start, X/Y = end+1              | C = error            |
| $FFE1   | STOP   | Check STOP key                     | -                                             | Z = 1 if pressed     |
| $FFE4   | GETIN  | Read keyboard buffer               | -                                             | A = char (0 = empty) |
| $FFE7   | CLALL  | Close all files/channels           | -                                             | -                    |
| $FFEA   | UDTIM  | Update jiffy clock                 | -                                             | -                    |

### Common KERNAL Routine Usage

```asm
        lda #$93                ; PETSCII CLR/HOME
        jsr CHROUT              ; clear screen

        jsr GETIN               ; read keyboard
        beq no_key              ; A=$00 means buffer empty
        ; A now contains PETSCII code

no_key:
```

## Indirect Vectors

The KERNAL uses indirect vectors in low RAM so user programs can intercept calls.

| Address     | Name   | Description            |
|-------------|--------|------------------------|
| $0090-$0091 | CINV   | Hardware IRQ vector    |
| $0092-$0093 | CBINV  | BRK interrupt vector   |
| $0094-$0095 | NMINV  | NMI vector             |
| $0326-$0327 | IBSOUT | Indirect CHROUT vector |
| $0328-$0329 | ISTOP  | Indirect STOP vector   |
| $032A-$032B | IGETIN | Indirect GETIN vector  |
| $032C-$032D | ICLALL | Indirect CLALL vector  |
| $032E-$032F | USRCMD | User-defined vector    |
| $0330-$0331 | ILOAD  | Indirect LOAD vector   |
| $0332-$0333 | ISAVE  | Indirect SAVE vector   |

### Vector Hook Example

Redirecting the IRQ vector safely:

```asm
        sei
        lda #<my_irq
        sta CINV
        lda #>my_irq
        sta CINV+1
        cli

my_irq:

        pha
        txa
        pha
        tya
        pha
        cld
        ; ... your code ...
        jmp $E62B             ; or chain to original KERNAL handler
```

## I/O Device Numbers

| Number | Device      | Description           |
|--------|-------------|-----------------------|
| 0      | Keyboard    | Default input         |
| 1      | Cassette #1 | Tape device           |
| 2      | Cassette #2 | Tape device (via VIA) |
| 3      | Screen      | Default output        |
| 4+     | IEEE-488    | Disk, printer, etc.   |

### Setting Output Device

```asm
        lda #3
        sta DFLTO               ; $00B0: default output = screen
```

## STOP Key Detection

The STOP key is polled by the KERNAL during I/O operations.

For direct polling:

```asm
        jsr STOP                ; $FFE1
        beq stop_pressed        ; Z=1 if STOP key held
        ; continue

stop_pressed:

        ; exit or handle break
```

## File I/O Patterns

### Open a File (via KERNAL)

```asm
        lda #1                  ; logical file number
        ldx #8                  ; device number (disk)
        ldy #0                  ; secondary address
        jsr SETLFS              ; $FFBA: set logical file parameters
        ; then set filename and call OPEN ($FFC0)
```

**Note:** The PET KERNAL file OPEN/SETLFS/CLOSE patterns are similar to the C64 but at different addresses.

When writing portable code, verify addresses against the target machine.

## Tape Routines

The PET 3032 has built-in cassette tape support via PIA 1 and the VIA.

- Motor control: PIA 1 CRB bit 2 (CB2). 0 = motor on, 1 = motor off.
- Cassette sense: PIA 1 PORT A bits 4-5.
- Read data: PIA 1 CA1 (cassette #1 read line).

Direct motor control:

```asm
        lda $E813       ; PIA 1 CRB
        and #$FB        ; clear bit 2 -> motor on
        sta $E813

        ; later, turn motor off:
        lda $E813
        ora #$04        ; set bit 2 -> motor off
        sta $E813
```
