# ROM Routine Map

## Purpose

> **Scope:** Callable BASIC-2 (new-ROM) ROM entry points beyond the KERNAL jump table: editor/screen routines, interrupt entry, floating-point math, number and string conversion
> **Key items:** clear `$E229`, home `$E257`, scroll `$E53F`, IRQ entry `$E61B`, FAC1 `$5E-$63`, FAC2 `$66-$6B`, CHRGET `$70`, FP add `$D76E`, FAC->ASCII `$DCE9`

This file lists ROM routines that have **no KERNAL jump-table equivalent** but are useful from machine code on the PET 3032.

Every address here is **version-specific** and applies only to **BASIC 2 ("new ROM")** machines: the 3008, 3016, and 3032. They are not stable like the `$FFC0-$FFEA` jump table. On a BASIC 1 or BASIC 4 machine they are wrong. Use the jump table (`system/kernal.md`) whenever a routine exists there; reach into raw ROM only for things the jump table does not expose (floating point, scrolling, number formatting).

Every address in this file was verified by disassembling the `basic-2.901465-01-02`, `edit-2-n.901447-24`, and `kernal-2.901465-03` ROMs in VICE (`xpet -model 3032`). To confirm on your own ROM set, see `utility/vice-emulator.md`.

| Out of scope                      | See instead        |
|-----------------------------------|--------------------|
| KERNAL jump table (`$FFC0-$FFEA`) | `system/kernal.md` |
| Zero-page map                     | `system/memory.md` |
| BASIC line format and tokens      | `system/basic.md`  |
| Screen RAM and PETSCII            | `system/screen.md` |

## Contents

| Section                 | Line | What it covers                                       |
|-------------------------|------|------------------------------------------------------|
| Detecting the ROM       | 33   | Confirm BASIC 2 before calling any address here      |
| ROM Memory Regions      | 44   | What lives where in `$C000-$FFFF`                    |
| Screen and Editor       | 58   | Clear, home, scroll, insert, print to screen         |
| Interrupt Entry Points  | 79   | `$E61B` IRQ entry and `$E62E` clock/keyboard service |
| Floating-Point Routines | 92   | FAC layout, load/store, arithmetic, functions        |
| Number and String       | 130  | FAC<->ASCII, print line number, string functions     |
| CHRGET and the Wedge    | 148  | `$70-$87` text scanner; adding commands to BASIC     |

## Detecting the ROM

Before any program calls these addresses, confirm it is running on a new-ROM machine. Location `$C353` (50003 decimal) reads `0` on old-ROM (BASIC 1) machines and `1` on new-ROM (BASIC 2) machines.

```asm
        lda $C353               ; 50003: ROM revision flag
        beq wrong_rom           ; 0 = old ROM (BASIC 1) -> addresses here are invalid
```

There is no in-ROM flag that distinguishes BASIC 2 from BASIC 4; a program that must run on both should call the jump table only, or carry its own per-ROM address table.

## ROM Memory Regions

The upper 16 KB splits into these regions on a new-ROM machine.

| Range         | Contents                                                |
|---------------|---------------------------------------------------------|
| `$0400-$7FFF` | User RAM (program, variables, arrays, strings)          |
| `$8000-$8FFF` | Video RAM (1000 bytes used at `$8000-$83E7`)            |
| `$9000-$BFFF` | Unused / ROM expansion sockets                          |
| `$C000-$E0F8` | Microsoft BASIC interpreter                             |
| `$E0F9-$E7FF` | Editor ROM: keyboard scan, screen, interrupt service    |
| `$E810-$E84F` | I/O chips (PIA 1, PIA 2, VIA) -- see `hardware/chip.md` |
| `$F000-$FFFF` | KERNAL: reset, tape, IEEE, LOAD/SAVE, monitor, vectors  |

## Screen and Editor

These editor-ROM routines drive the screen directly. Most take no parameters; the screen cursor state lives in zero page (`$C6` = cursor column, `$D8` = cursor line, `$C4-$C5` = pointer to current screen line).

| Address | Routine                | Notes                                                       |
|---------|------------------------|-------------------------------------------------------------|
| `$E229` | Clear screen           | Faster than `CHROUT #$93`; resets the line-link table       |
| `$E257` | Home cursor            | Sets `$C6` and `$D8` to 0                                   |
| `$E3D8` | Output ASCII to screen | Screen-editor character handler (what `CHROUT` reaches)     |
| `$E519` | Advance to next line   | Moves cursor down one screen line                           |
| `$E53F` | Scroll screen up       | One physical scroll; no PETSCII equivalent                  |
| `$E5BA` | Open a line (insert)   | Same action as the INSERT key                               |
| `$E6EA` | Print char to screen   | Char in `A`; waits for retrace (`$E840` bit 5) before write |

Prefer `CHROUT` (`$FFD2`) for normal output -- it routes through `$E3D8` and respects the current output device. Call these directly only when you specifically need the editor action (an explicit scroll, a fast full-screen clear) without going through PETSCII control codes.

```asm
        jsr $E229               ; clear screen directly
        jsr $E257               ; home cursor
```

## Interrupt Entry Points

The hardware IRQ vector (`$FFFE`) points to `$E61B`. This is the routine that runs 60 times a second.

| Address | Routine                | Notes                                                                          |
|---------|------------------------|--------------------------------------------------------------------------------|
| `$E61B` | Main IRQ entry         | Saves A/X/Y, tests the stacked B flag, dispatches via `$0090`/`$0092`          |
| `$E62E` | Clock/keyboard service | Default target of CINV (`$0090`); calls `UDTIM`, scans keyboard, blinks cursor |

`$E61B` saves the registers, then does `JMP ($0092)` for a BRK or `JMP ($0090)` (CINV) for a normal IRQ. Because the entry dispatches through the RAM vector CINV, the correct and stable way to hook the interrupt is to chain through CINV, not to JSR `$E62E` directly. See `system/irq.md` for the full hook-and-chain pattern.

The default contents of CINV (`$0090`) are `$E62E`; the default BRK vector (`$0092`) points into the machine-language monitor.

## Floating-Point Routines

The BASIC interpreter contains the standard Microsoft 6502 floating-point package. ML code can borrow it for real-number math. Numbers are held in two floating accumulators in zero page:

| Zero page | Register                                        |
|-----------|-------------------------------------------------|
| `$5E-$63` | FAC1 -- exponent, 4 mantissa bytes, sign        |
| `$66-$6B` | FAC2 -- second operand for two-operand routines |

Arithmetic operates on FAC1 and FAC2 and leaves the result in FAC1.

| Address | Routine                |
|---------|------------------------|
| `$DAAE` | Load FAC1 from memory  |
| `$DAD3` | Store FAC1 to memory   |
| `$D998` | Load FAC2 from memory  |
| `$DB08` | Copy FAC2 to FAC1      |
| `$DB18` | Copy FAC1 to FAC2      |
| `$D76E` | Add (FAC1 + FAC2)      |
| `$D733` | Subtract               |
| `$D937` | Multiply               |
| `$DA1E` | Divide                 |
| `$DBD8` | INT (truncate)         |
| `$DB45` | SGN                    |
| `$DB64` | ABS                    |
| `$DB67` | Compare FAC1 to memory |
| `$D8F6` | LOG                    |
| `$DE5E` | SQR                    |
| `$DE68` | Power (`^`)            |
| `$DEDA` | EXP                    |
| `$DF7F` | RND                    |
| `$DFDF` | SIN                    |
| `$DFD8` | COS                    |
| `$E028` | TAN                    |
| `$E08C` | ATN                    |

Exact register and pointer conventions differ per entry point (some assume an operand pointer in `A`/`Y`, some assume FAC2 is already loaded). Disassemble the specific routine before depending on a calling sequence; this table is a verified map of where each function lives, not a full ABI.

## Number and String

| Address | Routine                       | Notes                                        |
|---------|-------------------------------|----------------------------------------------|
| `$D26D` | Convert fixed point to float  | Integer to FAC1                              |
| `$D6D2` | Convert float to fixed point  | FAC1 to a signed integer                     |
| `$DBFF` | Convert ASCII string to float | Parses a number string into FAC1 (VAL core)  |
| `$DCE9` | Convert number to ASCII       | FAC1 to a digit string built from `$0100` up |
| `$DCD9` | Print BASIC line number       | Prints an unsigned integer                   |
| `$D5DA` | LEFT$                         | String function                              |
| `$D606` | RIGHT$                        | String function                              |
| `$D611` | MID$                          | String function                              |
| `$D656` | LEN                           | String to numeric length                     |
| `$D665` | ASC                           | First character code of a string             |
| `$D687` | VAL                           | String to number                             |

`$DCE9` is the practical one for ML: load a value into FAC1, JSR `$DCE9`, and a printable ASCII string of the number is built starting at `$0100`, ready to feed to `CHROUT`.

## CHRGET and the Wedge

At cold start the editor ROM copies a short text-scanner routine from `$E0F9` into zero page at `$70-$87`. This is CHRGET -- the routine BASIC calls to fetch the next character of program text.

| Zero page | Role                                                     |
|-----------|----------------------------------------------------------|
| `$70`     | CHRGET entry: advance the text pointer, return next char |
| `$73`     | CHRGOT entry: re-read the current character              |
| `$77-$78` | Text pointer CHRGET reads through (lo, hi)               |

Because CHRGET lives in RAM, a program can patch it to intercept every character BASIC reads -- the classic "wedge" used to add commands to BASIC. Replace the entry with a `JMP` to your own scanner, inspect the character, then either handle your new command or jump back into the original CHRGET code. See `system/basic.md` for how BASIC text is laid out once CHRGET reaches it.
