# Memory Map & System Architecture

## Purpose

> **Scope:** 32 KB RAM ($0000-$7FFF), zero page, BASIC workspace, screen RAM, ROM regions, safe zones for ML
> **Key items:** BASIC program at $0401, screen at $8000, KERNAL at $F000, zero-page vectors at $0090-$0095

This file covers the PET 3032 memory map in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need
- **Reference tables & register maps** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                  | See instead                |
|-------------------------------|----------------------------|
| VIA/PIA/CRTC register details | `hardware/pet-chips.md`    |
| KERNAL routine usage          | `system/kernal-vectors.md` |

## Full Memory Map

### By Region

| Region             | Range       | Size   | Description                              |
|--------------------|-------------|--------|------------------------------------------|
| Zero page          | $0000-$00FF | 256 B  | System variables, pointers, vectors      |
| Stack              | $0100-$01FF | 256 B  | 6502 hardware stack                      |
| BASIC input buffer | $0200-$0250 | 81 B   | System INPUT buffer                      |
| File tables        | $0251-$0270 | 32 B   | KERNAL logical file tables               |
| Keyboard buffer    | $0270-$027A | 11 B   | Keyboard buffer queue                    |
| Tape buffers       | $027A-$03F9 | 576 B  | Tape I/O buffers                         |
| BASIC program      | $0400-$7FFF | ~31 KB | Tokenized BASIC + free RAM               |
| Screen RAM         | $8000-$83E7 | 1000 B | 40x25 character screen                   |
| Unused video       | $83E8-$83FF | 24 B   | Unused video RAM                         |
| Expansion ROM      | $A000-$AFFF | 4 KB   | Free space for 4K EPROM                  |
| BASIC ROM          | $B000-$DFFF | 12 KB  | BASIC keywords and operators             |
| Editor ROM         | $E000-$E7FF | 2 KB   | Screen editor functions                  |
| I/O area           | $E800-$E8FF | 256 B  | VIA, PIA, CRTC registers                 |
| National ROM       | $E900-$EFFF | 1792 B | Nationalized keyboard mapping (board #4) |
| KERNAL ROM         | $F000-$FFFF | 4 KB   | Tape, IEEE-488, jump table               |

### PET 3032 RAM Layout

The PET 3032 has 32 KB of contiguous RAM from `$0000` to `$7FFF`.

- `$0000-$00FF`: Zero page - heavily used by BASIC and KERNAL
- `$0100-$01FF`: Stack - 256 bytes, grows down from `$01FF`
- `$0200-$03FF`: System buffers - safe to use if not using tape or keyboard queue
- `$0400-$7FFF`: BASIC program area and free RAM

### Machine Code Loading Conventions

- Machine code typically loads at `$0401` (via BASIC stub `SYS1038`)
- The region `$0400-$7FFF` is available for ML after BASIC program end
- Top of BASIC memory is controlled by pointer at `$0034/$0035` (MEMSIZ)
- For pure ML programs, set MEMSIZ low to protect your code from BASIC, or stay below BASIC start

## Zero Page ($0000-$00FF)

### Critical System Pointers

| Label  | Address     | Description                   |
|--------|-------------|-------------------------------|
| TXTTAB | $0028-$0029 | Start of BASIC text           |
| VARTAB | $002A-$002B | Start of BASIC variables      |
| ARYTAB | $002C-$002D | Start of BASIC arrays         |
| STREND | $002E-$002F | End of BASIC arrays (+1)      |
| FRETOP | $0030-$0031 | Bottom of string storage      |
| MEMSIZ | $0034-$0035 | Highest address used by BASIC |
| CURLIN | $0036-$0037 | Current BASIC line number     |

### KERNAL Vectors

| Label | Address     | Description                              |
|-------|-------------|------------------------------------------|
| CINV  | $0090-$0091 | Hardware IRQ vector (redirects to $E62B) |
| CBINV | $0092-$0093 | BRK interrupt vector                     |
| NMINV | $0094-$0095 | NMI vector                               |

### I/O State

| Label  | Address | Description                         |
|--------|---------|-------------------------------------|
| STATUS | $0096   | KERNAL I/O status word              |
| LSTX   | $0097   | Current key pressed ($FF = none)    |
| NDX    | $009E   | Number of chars in keyboard buffer  |
| DFLTN  | $00AF   | Default input device (0 = keyboard) |
| DFLTO  | $00B0   | Default output device (3 = screen)  |
| LA     | $00D2   | Current logical file number         |
| SA     | $00D3   | Current secondary address           |
| FA     | $00D4   | Current device number               |

### Cursor and Screen

| Label | Address     | Description                            |
|-------|-------------|----------------------------------------|
| PNT   | $00C4-$00C5 | Pointer to current screen line address |
| PNTR  | $00C6       | Cursor column on current line          |
| TBLX  | $00D8       | Current cursor physical line number    |
| GDBLN | $00A9       | Character under cursor                 |
| BLNSW | $00A7       | Cursor blink enable (0 = flash cursor) |

## Safe Memory Zones for Machine Code

### Fully Safe (BASIC/KERNAL do not touch)

| Zone                  | Range       | Notes                          |
|-----------------------|-------------|--------------------------------|
| High RAM below screen | varies      | Between end of BASIC and $7FFF |
| Screen unused         | $83E8-$83FF | Only 24 bytes                  |

### Safe if Feature Not Used

| Zone            | Range       | Condition                               |
|-----------------|-------------|-----------------------------------------|
| Tape buffer #1  | $027A-$0329 | Safe if no cassette I/O                 |
| Tape buffer #2  | $033A-$03F9 | Safe if no cassette I/O                 |
| Keyboard buffer | $0270-$027A | Safe if not reading keyboard via KERNAL |

### Zero-Page Scratch

| Zone          | Range   | Condition                                        |
|---------------|---------|--------------------------------------------------|
| User ZP       | $00-$0F | First 16 bytes generally safe if not using USR() |
| Temp pointers | $FB-$FE | Often used by KERNAL but safe in tight loops     |

## Stack Operations

6502 stack: 256 bytes at `$0100-$01FF`. `TSX/TXS` to read/write SP.

```asm
        tsx
        inx
        inx             ; adjust if needed
        txs
```

**Note:** The PET KERNAL uses the stack heavily during interrupts and I/O. Keep stack usage moderate in IRQ handlers.

## Inline-Parameter JSR Trick

A subroutine can read its own return address off the stack to find embedded data after the `JSR`, avoiding zero-page allocation:

```asm
        ; Caller:
        jsr my_routine
        .byte $01, $02, $03   ; data table after JSR

        ; Callee:

my_routine:

        pla                  ; pop low byte of return PC
        sta data_ptr
        pla                  ; pop high byte
        sta data_ptr+1
        ; Now data_ptr points past JSR
        rts
```
