# Memory Map & System Architecture

## Purpose

> **Scope:** 32 KB RAM ($0000-$7FFF), zero page, BASIC workspace, screen RAM, ROM regions, safe zones for ML
> **Key items:** BASIC program at $0401, screen at $8000, KERNAL at $F000, zero-page vectors at $0090-$0095

This file covers the PET 3032 memory map in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need
- **Reference tables & register maps** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                  | See instead        |
|-------------------------------|--------------------|
| VIA/PIA/CRTC register details | `hardware/chip.md` |
| KERNAL routine usage          | `system/kernal.md` |

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

## Zero Page Usage - Commodore PET BASIC 2

### Used by BASIC

| Range     | Description                                                                                                                                                           |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `$00-$02` | USR jump instruction and address                                                                                                                                      |
| `$03-$0C` | BASIC parser flags                                                                                                                                                    |
| `$0D-$10` | File I/O width and device flags                                                                                                                                       |
| `$11-$12` | Temp integer value                                                                                                                                                    |
| `$13-$53` | Temp string stack, utility pointers, BASIC text and variable and array pointers, line numbers, DATA pointer, FOR/NEXT index pointer, math temporaries                 |
| `$54-$6F` | Floating point accumulators 1 and 2, cassette buffer pointer                                                                                                          |
| `$70-$87` | CHRGET routine - self-modifying code patched by BASIC at runtime; `$77-$78` = TXTPTR (current BASIC text pointer). This entire range is executable code in zero page. |
| `$88-$8C` | RND seed                                                                                                                                                              |

### Used by KERNAL

| Range     | Description                                                                                                                                                             |
|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `$8D-$8F` | Jiffy clock (TIME)                                                                                                                                                      |
| `$90-$95` | IRQ, BRK, NMI vectors                                                                                                                                                   |
| `$96-$9A` | I/O status (ST), last key pressed, print shift flag, jiffy correction                                                                                                   |
| `$9B-$A1` | STOP key flag, tape timing, load/verify flag, keyboard buffer count, RVS flag                                                                                           |
| `$A2`     | Not used                                                                                                                                                                |
| `$A3-$B3` | Cursor position, IEEE bus buffer, cursor blink, tape handling                                                                                                           |
| `$B4-$B6` | Gaps and temp storage                                                                                                                                                   |
| `$B7-$BA` | Temp data areas                                                                                                                                                         |
| `$BB-$C3` | Tape buffer pointers, cassette temps                                                                                                                                    |
| `$C4-$DD` | Screen and cursor pointers, tape end addresses, tape timing, quote mode flag, file name and device and logical file tracking, screen line length, cursor row and column |
| `$DE-$DF` | Cassette block count, serial word buffer                                                                                                                                |
| `$E0-$F8` | Screen line link table and editor temporaries                                                                                                                           |
| `$F9-$FA` | Tape motor interlocks                                                                                                                                                   |
| `$FB-$FE` | I/O start address (`$FB-$FC`), tape load temps (`$FD-$FE`) - these are the traditional free ZP locations on C64, but on PET they are used by KERNAL                     |
| `$FF`     | Listed as not used                                                                                                                                                      |

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

## What Is Actually Safe

On PET BASIC 2, the safe zero page locations are very limited:

**`$FF`** - explicitly listed as unused.

**`$A2`** - explicitly listed as not used.

Beyond those two single bytes, there is no clean contiguous free block in zero page on a running BASIC 2 system.

This is in contrast to the C64 (which leaves `$FB-$FE` free) - on the PET those four bytes are taken by KERNAL.

### Practical Approach for ML Programs

The common technique is to disable the parts of the system you do not need, which then frees their zero page locations:

- If you do not use tape, `$9C-$C3` and `$F9-$FE` become available.
- If you do not use IEEE-488, `$A5`, `$B5-$B6`, `$B9-$BA`, `$B3` are free.
- If you take over the IRQ (as your program does with the vblank wait), you can repurpose `$90-$95`.
- If you suppress BASIC entirely (run as pure ML with no BASIC interpreter active), everything from `$03` upward through `$8C` is free.

## Stack Operations

6502 stack: 256 bytes at `$0100-$01FF`. `TSX/TXS` to read/write SP.

```asm
        tsx
        inx
        inx                     ; adjust if needed
        txs
```

**Note:** The PET KERNAL uses the stack heavily during interrupts and I/O.

Keep stack usage moderate in IRQ handlers.

## Inline-Parameter JSR Trick

A subroutine can read its own return address off the stack to find embedded data after the `JSR`, avoiding zero-page allocation:

```asm
        jsr my_routine          ; Caller:
        .byte $01, $02, $03     ; data table after JSR

my_routine:             ; Callee:

        pla                     ; pop low byte of return PC
        sta data_ptr
        pla                     ; pop high byte
        sta data_ptr+1
        rts                     ; Now data_ptr points past JSR
```
