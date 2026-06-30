# KERNAL Vectors & I/O Routines

## Purpose

> **Scope:** KERNAL jump table ($FFC0-$FFEA), indirect vectors, CHROUT/GETIN/CLALL/STOP, file I/O, tape, safe hooks, PET vs C64 differences
> **Key items:** CHROUT=$FFD2, GETIN=$FFE4, CLALL=$FFE7, STOP=$FFE1, CINV=$0090, CBINV=$0092, NMINV=$0094

This file covers the PET 3032 KERNAL in four progressive layers:

- **Quick-lookup table** - scan or search for the routine you need
- **Reference tables & vectors** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                                | See instead        |
|---------------------------------------------|--------------------|
| Hardware chip registers                     | `hardware/chip.md` |
| Memory map and zero page                    | `system/memory.md` |
| Screen RAM and PETSCII                      | `system/screen.md` |
| Callable ROM routines beyond the jump table | `system/rom.md`    |

## KERNAL Jump Table ($FFC0-$FFEA)

The PET 3032 KERNAL provides a jump table at the top of ROM.

Each entry is a 3-byte `JMP` instruction.

**Critical:** The PET jump table starts at `$FFC0`, NOT `$FFB7`. The addresses `$FFB7-$FFBF` contain ROM code text (`"C. 0978 CBM "`) and filler bytes (`$AA` = `TAX`), NOT jump table entries. The C64 has `SETNAM` at `$FFBD`, `SETLFS` at `$FFBA`, and `READST` at `$FFB7` — **these do NOT exist on the PET**. Calling them executes `TAX TAX TAX` and falls through to `OPEN` with wrong parameters, causing `?SYNTAX ERROR`.

| Address | Name   | Description                          | Input                                         | Output                 |
|---------|--------|--------------------------------------|-----------------------------------------------|------------------------|
| $FFC0   | OPEN   | Open logical file (BASIC parsing!)   | (params set via ZP, see below)                | jumps to error on fail |
| $FFC3   | CLOSE  | Close logical file (BASIC parsing!)  | A = logical file number                       | jumps to error on fail |
| $FFC6   | CHKIN  | Set input channel                    | X = logical file number                       | C=0 ok, C=1 error      |
| $FFC9   | CHKOUT | Set output channel                   | X = logical file number                       | C=0 ok, C=1 error      |
| $FFCC   | CLRCHN | Clear channels                       | -                                             | -                      |
| $FFCF   | BASIN  | Read byte from current input         | -                                             | A = byte               |
| $FFD2   | CHROUT | Output character to current output   | A = PETSCII char                              | -                      |
| $FFD5   | LOAD   | Load file to memory (BASIC parsing!) | A = 0 (load) / 1 (verify), X/Y = addr if SA=1 | X/Y = end+1            |
| $FFD8   | SAVE   | Save memory range (BASIC parsing!)   | A = ZP ptr to start, X/Y = end+1              | -                      |
| $FFE1   | STOP   | Check STOP key                       | -                                             | Z = 1 if pressed       |
| $FFE4   | GETIN  | Read keyboard buffer                 | -                                             | A = char (0 = empty)   |
| $FFE7   | CLALL  | Close all files/channels             | -                                             | -                      |
| $FFEA   | UDTIM  | Update jiffy clock                   | -                                             | -                      |

### Routines that do NOT exist on PET KERNAL

| C64 address | C64 name | PET reality                                                      |
|-------------|----------|------------------------------------------------------------------|
| $FFB7       | READST   | ROM text bytes, not a JMP. Read `$96` (STATUS) directly instead. |
| $FFBA       | SETLFS   | ROM text bytes, not a JMP. Set `$D2`, `$D3`, `$D4` directly.     |
| $FFBD       | SETNAM   | Filler `$AA` bytes, not a JMP. Set `$D1`, `$DA`, `$DB` directly. |

### OPEN and CLOSE include BASIC parameter parsing

The PET's `OPEN` (`$FFC0`) and `CLOSE` (`$FFC3`) jump table entries include BASIC text parameter parsing — they expect to read parameters from the BASIC text pointer (`$77-$78`), not from registers. When called from machine code, they will fail or crash.

To call OPEN or CLOSE from machine code, use the **low-level ROM entry points** that skip the BASIC parsing:

| Routine | Jump table | Low-level (ML-safe) | What the low-level entry skips |
|---------|------------|---------------------|--------------------------------|
| OPEN    | $FFC0      | $F560               | BASIC param parse at $F4CE     |
| CLOSE   | $FFC3      | $F2DD               | BASIC param parse at $F4CE     |

CHKIN, CHKOUT, CLRCHN, CHRIN, CHROUT, GETIN, CLALL, and STOP work correctly from the jump table — they do NOT include BASIC parsing.

### PET file I/O zero-page locations

Since the PET lacks SETNAM/SETLFS, file I/O parameters are set by writing directly to KERNAL zero-page locations:

| Address | Name    | Purpose                      | Set by (C64) | Set by (PET)               |
|---------|---------|------------------------------|--------------|----------------------------|
| $D1     | FNLEN   | Filename length              | SETNAM       | Direct write               |
| $D2     | LA      | Logical file number          | SETLFS       | Direct write               |
| $D3     | SA      | Secondary address            | SETLFS       | Direct write               |
| $D4     | DEV     | Device number                | SETLFS       | Direct write               |
| $DA     | FNADR   | Filename address (low byte)  | SETNAM       | Direct write               |
| $DB     | FNADR+1 | Filename address (high byte) | SETNAM       | Direct write               |
| $AE     | -       | Open file count              | (internal)   | Read to check OPEN success |
| $96     | STATUS  | I/O status byte              | READST       | Read directly              |

### PET-specific file I/O wrappers

Since the PET lacks SETNAM/SETLFS and its OPEN/CLOSE include BASIC parsing, use these wrapper routines for machine-code file I/O:

```asm
; ---- PET file I/O zero-page locations ----
PET_FNLEN       = $D1
PET_LA          = $D2
PET_SA          = $D3
PET_DEV         = $D4
PET_FNADR_LO    = $DA
PET_FNADR_HI    = $DB
PET_OPEN_LOGIC  = $F560       ; OPEN past BASIC parsing
PET_CLOSE_LOGIC = $F2DD       ; CLOSE past BASIC parsing

; pet_setnam: A=length, X=addr_lo, Y=addr_hi
pet_setnam:
        sta PET_FNLEN
        stx PET_FNADR_LO
        sty PET_FNADR_HI
        rts

; pet_setlfs: A=LFN, X=DEV, Y=SA
pet_setlfs:
        sta PET_LA
        stx PET_DEV
        sty PET_SA
        rts

; pet_open: call PET OPEN logic (params already set up)
; Returns carry clear on success, set on error.
; The PET OPEN routine jumps to BASIC error handler on failure
; instead of using carry. We detect success by checking if
; $AE (file count) increased.
pet_open:
        lda $AE
        pha
        jsr PET_OPEN_LOGIC
        pla
        cmp $AE         ; old vs new: C=0 if old < new (increased)
        bcc po_ok       ; file count increased -> success
        sec
        rts
po_ok:
        clc
        rts

; pet_close: A = logical file number to close
pet_close:
        sta PET_LA
        jsr PET_CLOSE_LOGIC
        rts
```

**Error handling note:** The PET's OPEN and CLOSE do NOT use the carry flag for error reporting. On failure, they jump directly to the BASIC error handler (`$CE03`), which prints `?SYNTAX ERROR` or similar and returns to BASIC. If the routine returns at all, it succeeded. The `pet_open` wrapper above detects OPEN success by checking if `$AE` (file count) increased. CHKIN and CHKOUT use the carry flag normally: C=0 on success, C=1 on error.

### Common KERNAL Routine Usage

```asm
        lda #$93                ; PETSCII CLR/HOME
        jsr CHROUT              ; clear screen

        jsr GETIN               ; read keyboard
        beq no_key              ; A=$00 means buffer empty

no_key:                 ; A now contains PETSCII code
```

## Indirect Vectors

The KERNAL uses indirect vectors in low RAM so user programs can intercept calls.

| Address     | Name    | Description            |
|-------------|---------|------------------------|
| $0090-$0091 | CINV    | Hardware IRQ vector    |
| $0092-$0093 | CBINV   | BRK interrupt vector   |
| $0094-$0095 | NMINV   | NMI vector             |
| $031A-$031B | IOPEN   | Indirect OPEN vector   |
| $031C-$031D | ICLOSE  | Indirect CLOSE vector  |
| $031E-$031F | ICHKIN  | Indirect CHKIN vector  |
| $0320-$0321 | ICHKOUT | Indirect CHKOUT vector |
| $0322-$0323 | ICLRCHN | Indirect CLRCHN vector |
| $0324-$0325 | ICHRIN  | Indirect CHRIN vector  |
| $0326-$0327 | IBSOUT  | Indirect CHROUT vector |
| $0328-$0329 | ISTOP   | Indirect STOP vector   |
| $032A-$032B | IGETIN  | Indirect GETIN vector  |
| $032C-$032D | ICLALL  | Indirect CLALL vector  |
| $032E-$032F | USRCMD  | User-defined vector    |
| $0330-$0331 | ILOAD   | Indirect LOAD vector   |
| $0332-$0333 | ISAVE   | Indirect SAVE vector   |

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
        jmp (old_cinv)          ; chain to original KERNAL handler (save before install)
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
        beq stop_pressed        ; Z=1 if STOP key held, else continue

stop_pressed:           ; exit or handle break
```

## File I/O Patterns

### Open a File (via PET KERNAL)

On the PET, there is no SETLFS or SETNAM KERNAL call. Set the zero-page locations directly, then call the low-level OPEN logic:

```asm
        ; Set filename
        lda #1                  ; filename length
        ldx #<fname             ; filename address low
        ldy #>fname             ; filename address high
        jsr pet_setnam          ; sets $D1, $DA, $DB

        ; Set logical file params
        lda #2                  ; logical file number
        ldx #8                  ; device number (disk)
        ldy #0                  ; secondary address
        jsr pet_setlfs          ; sets $D2, $D3, $D4

        jsr pet_open            ; calls $F560, checks $AE for success
        bcc open_ok
        jmp open_error

open_ok:
```

See the "PET-specific file I/O wrappers" section above for the wrapper routine definitions.

**Note:** The PET KERNAL file I/O differs significantly from the C64. The C64 has SETNAM ($FFBD) and SETLFS ($FFBA) in its jump table; the PET does not. Always use the PET-specific wrappers when writing machine code for the PET.

