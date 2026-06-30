# Assembly Engineering Standards

## Purpose

> **Scope:** 6502/DASM assembly coding standards for the Commodore PET 3032 -- file structure, formatting, labels, equates, comments, section headers, naming, column alignment, flag semantics
> **Key items:** `processor 6502`, `org $0401`, BASIC stub, label spacing, tab-stop comments, section banners, `UPPER_SNAKE_CASE` equates, `snake_case` labels, flag-affecting instructions, branch-after-load bug

This file is the authoritative coding standard for writing PET 3032 assembly with DASM.

Follow these rules when writing new `.asm` files or editing existing ones to keep code uniform across projects.

| Out of scope                     | See instead                 |
|----------------------------------|-----------------------------|
| DASM syntax and directives       | `utility/dasm-assembler.md` |
| 6502 instruction set reference   | `hardware/cpu.md`           |
| Zero-page usage policy           | `STYLE.md`                  |
| Optimization patterns            | `code/optimization.md`      |
| Compression formats and routines | `code/compression.md`       |

## Contents

| Section                  | Line | What it covers                                                     |
|--------------------------|------|--------------------------------------------------------------------|
| Toolchain                | 40   | DASM invocation, target CPU, hardware, load address                |
| File Structure           | 49   | Top-to-bottom layout for every `.asm` file                         |
| Directives               | 65   | `processor 6502` and `org $0401` placement                         |
| Equates                  | 83   | Global hardware equates, zero page borrowing rules, grouping rules |
| BASIC Stub               | 137  | Standard SYS1038 stub with `nextline:` and `old_pcr:`              |
| Labels                   | 165  | Spacing, naming, colon rules, subroutine boundaries                |
| Instruction Formatting   | 222  | Indentation, tab-stop comments, operand rules                      |
| Comment Placement        | 250  | Block intent comments, label description comments                  |
| Section Headers          | 302  | Major and minor banner format                                      |
| Data Directives          | 328  | `byte`, `word`, string bytes, screen row layout                    |
| Screen RAM Operations    | 373  | 1000-byte screen invariant, 768+232 clear/fill/copy pattern        |
| End-of-File Format       | 403  | Trailing blank line rule                                           |
| Naming Conventions       | 407  | Convention table for all identifier kinds                          |
| Column Alignment Summary | 420  | Column position table for every source element                     |
| 6502 Flag Semantics      | 435  | Flag-affecting instructions, branch-after-load bug pattern         |

## Toolchain

- **DASM**: macro assembler producing 6502 PRG files. Invoked as `dasm source.asm -f1 -osource.prg`.
- **Target CPU**: MOS 6502 (`processor 6502` directive required at the top of every file).
- **Target hardware**: Commodore PET 3032 -- 32 KB RAM, screen RAM at `$8000`, 60 Hz VBLANK, KERNAL at `$FFD2`/`$FFE4`.
- **Load address**: `$0401` via `org $0401`.

For DASM command-line options and Docker invocation, see `utility/dasm-assembler.md`.

## File Structure

Every `.asm` file follows this top-to-bottom layout, in order:

1. `processor 6502` directive
2. Blank line
3. Global equates (hardware addresses and KERNAL routines)
4. Blank line
5. `org $0401`
6. Blank line
7. BASIC stub section
8. Data label(s) embedded in stub (`nextline:`, `old_pcr:`)
9. One or more major code and data sections

Sections are separated by major section header banners. There is no footer or end-of-file marker.

## Directives

### Processor

Always the first line of the file, at column 8 (one indent level):

```asm
        processor 6502
```

### Origin

Always `$0401` for PET BASIC stub programs, at column 8:

```asm
        org $0401
```

## Equates

### Global Hardware Equates

Declared at the top of the file, before `org`. Names are `UPPER_SNAKE_CASE`. The `=` sign is placed at column 8 (one extra space per name as needed to reach that column). Values are followed by inline comments at column 25 when a description is needed.

```asm
SCREEN  = $8000
GETIN   = $FFE4
CHROUT  = $FFD2         ; KERNAL: Output character

PCR     = $E84C         ; PET Character Set Register
PCR_U   = $0C           ; uppercase / graphics charset (PCR bits 3:1 = 110)
PCR_L   = $0E           ; lowercase / text charset (PCR bits 3:1 = 111)
```

Rules:

- Group logically related equates together (screen, KERNAL, hardware registers).
- Separate groups with a single blank line.
- Equates without comments need no alignment padding beyond the column 8 `=`.
- Do not describe what a hardware address physically is if the name already encodes it.
- Always use "KERNAL" (uppercase) when referring to Commodore KERNAL routines.

### Zero Page Usage

PET BASIC 2 leaves almost no zero page free. Do not declare equates that name a specific zero-page address as if your routine owns it -- the only addresses safe for a named equate are `$FF` and `$A2`.

If a routine needs zero page for `($zp),y` indirect addressing, borrow `$FB`-`$FE` (the KERNAL tape pointers, idle when tape I/O is not running), save the previous contents on entry, and restore them on exit. Reference borrowed bytes with raw hex in instructions, not an equate -- the raw hex makes the borrow visible at the call site instead of implying ownership.

```asm
        lda $FC
        pha
        lda $FB
        pha
        stx $FB
        sty $FC

        lda ($FB),y             ; Check compression flag

        pla
        sta $FB
        pla
        sta $FC
```

Rules:

- Comment the first use of a borrowed byte to state what it holds and that it is saved/restored.
- Save and restore in mirrored pairs (push order reversed on the pull side).
- Prefer the parameter-block convention (pass a pointer in X/Y to a block in free RAM) over zero-page borrowing when the routine does not need `($zp),y` addressing.

For the full zero-page borrowing and save/restore policy, see `STYLE.md`.

## BASIC Stub

The BASIC stub is always the first section in the file. It produces a one-line BASIC program (`10 SYS1038`) that jumps to machine code at address `$040E` (decimal 1038).

```asm
; =========================================================
; BASIC stub: SYS1038
; =========================================================

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0
```

- `nextline:` holds the BASIC line list terminator (`word 0`).
- `old_pcr:` holds one byte for saving and restoring the PCR register on exit.
- Both labels follow label formatting rules (see below).
- The major section header `; BASIC stub: SYS1038` is emitted once. Do not duplicate it.

## Labels

Labels are declared at column 0, always on their own line. Every label is preceded by exactly one blank line and followed by exactly one blank line before the first instruction or directive. The first label immediately after a section header does not require an additional blank line before it.

This rule applies to all labels without exception:

- **Global labels** (`start:`, `decompress_lz4:`)
- **Local labels** (`@fn_scan:`, `@fd_done:`) -- DASM local labels follow the same spacing rules
- **Loop and branch target labels** (`lz4_token:`, `ts_dir_left:`, `rto_loop:`) -- targets inside subroutines are not exempt

```asm
        inx
        bne copy_loop_1

        ldx #$E7

copy_loop_2:

        lda screen_data+$300,x
        sta SCREEN+$300,x
```

Consecutive data labels in a compact variable declaration block do not require a blank line between them, but each still must be followed by a blank line before the data directive:

```asm
frame_idx_lo:

        byte $00

frame_idx_hi:

        byte $00
```

Rules:

- Names are `snake_case`.
- No colon on equate names. Colons appear only on labels that represent addresses.
- Never place an instruction on the same line as a label.
- Never omit the blank line after a label.
- Never use two or more consecutive blank lines anywhere in the file.
- After a subroutine's final `rts`, there must be exactly one blank line before the next subroutine or section header begins.

### Subroutine Boundary Spacing

When one subroutine ends and another begins, the final `rts` of the first subroutine must be followed by exactly one blank line, then the next label:

```asm
        rts

wait_vblank:

        lda VIA_PORT_B
```

This also applies between a subroutine and a following major section header.

## Instruction Formatting

Instructions are indented 8 spaces (one indent level). There is no use of tabs.

```asm
        lda PCR
        sta old_pcr
```

Inline comments on instructions use tab-stop alignment. The first tab stop is column 33. If the instruction extends to column 32 or beyond, shift the comment to the next tab stop at column 41. Continue shifting by 8-column increments (49, 57, 65, and so on) as needed. There must always be at least two spaces between the end of the instruction and the semicolon.

```asm
        lda #$93                ; PETSCII CLR/HOME
        lda ($FB),y             ; Check compression flag
        sta $FD                 ; Stash token
        lda #<animation_sequence        ; Restart from beginning
```

Rules:

- Numeric literals larger than 9 are written in hexadecimal with the `$` prefix (`#$0A`, `#$27`, `#$E8`). Decimal literals 0-9 are written as-is (`#0`, `#3`, `#8`).
- Operands are written in lowercase hex (`$FF`, `#$0C`).
- Mnemonics are lowercase (`lda`, `jsr`, `bne`).
- Use named equates rather than bare addresses wherever a name exists (`sta PCR` not `sta $E84C`).
- Use the `<` and `>` operators for low/high byte extraction (`lda #<screen_data`, `lda #>screen_data`).
- Do not comment obvious instructions. Comment non-obvious values, intent, or side effects.
- Exception: BASIC line numbers in `word` directives are always decimal (`word 10`) because they represent BASIC source line numbers, not memory values.

## Comment Placement

### Block Intent Comments

A comment that describes what a block of code does must be placed as an inline comment on the first instruction of that block. It must never appear as a standalone `;` comment line above the block.

```asm
; BAD -- standalone comment line
        ; Look up frame offset from frame_offsets table (2 bytes per frame)
        lda frame_idx_lo
        asl
        tax

; GOOD -- inline on the first instruction
        lda frame_idx_lo        ; Look up frame offset from frame_offsets table (2 bytes per frame)
        asl
        tax
```

### Label Description Comments

A comment that describes a label, especially a data label such as frame data, must be placed on the same line as the label declaration. It must never appear on a separate line below the label.

```asm
; BAD -- comment on separate line
frame_0:
; frame 0 compressed data
        byte $00,$00,$66,$00

; GOOD -- inline on the label line
frame_0:                ; frame 0 compressed data

        byte $00,$00,$66,$00
```

Label description comments start at column 25, with the same tab-stop fallback rule as instruction comments if the label name is unusually long.

### Inline Comment Guidelines

Comment only what is not evident from the instruction and its operands. Acceptable uses:

- Clarifying a magic constant: `; PETSCII CLR/HOME`
- Describing the register state after a step: `; X = literal count (may be 15)`
- Explaining a flag check: `; Check compression flag (byte 3): 0 = uncompressed, 1 = compressed`
- Noting hardware register semantics: `; CA2 high: uppercase / graphics charset`

Do not comment what the mnemonic already says. Do not leave commented-out code.

### File-Level Comments

Major section banners serve as the file-level structural comments. No file header block or author line is used.

## Section Headers

### Major Sections

Used to separate the primary structural divisions of a file: BASIC stub, code, decompressor, screen data. Each section must have exactly one header banner. Duplicate headers are not allowed.

```asm
; =========================================================
; CODE
; =========================================================
```

The banner line is `; ` followed by 55 `=` characters. The title line is `; ` followed by the section name. The header is followed by exactly one blank line before the first content line. The header is preceded by exactly one blank line, except when it follows the `org` directive.

### Minor Sections

Used inside data sections to label sub-groups such as screen rows.

```asm
; ---------------------------------------------------------
; ROW 6
; ---------------------------------------------------------
```

The banner line is `; ` followed by 55 `-` characters. Same blank-line rules as major headers.

## Data Directives

### byte

Screen data is emitted as rows of `byte` directives. Each `byte` line holds exactly 10 values, separated by commas with no spaces. Four `byte` lines per row cover the full 40-column width.

```asm
; ---------------------------------------------------------
; ROW 6
; ---------------------------------------------------------

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$A0,$A0
        byte $A0,$A0,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
```

For compressed data, the grouping is 10 bytes per line with no row sub-headers:

```asm
screen_data:

        byte $E8,$03,$00,$01,$1F,$20,$01,$00,$C6,$4F
        byte $A0,$A0,$A0,$A0,$DD,$00,$10,$00,$27,$00
```

### word

Used for BASIC line pointers and terminators. One `word` directive per value:

```asm
        word nextline
        word 10
        word 0
```

### String Bytes

PETSCII SYS token and digit strings use quoted single-character `byte` values:

```asm
        byte $9E
        byte "1","0","3","8",0
```

## Screen RAM Operations

PET 3032 screen RAM is exactly 1000 bytes at `$8000-$83E7` (40 columns x 25 rows). This is not a power of two.

Never use a naive 4-page loop (`sta SCREEN,x` / `sta SCREEN+$100,x` / `sta SCREEN+$200,x` / `sta SCREEN+$300,x` with `inx` / `bne`) to clear, fill, or copy screen RAM. That loop writes 1024 bytes -- 24 bytes past the screen into `$83E8-$83FF`, which is not display memory.

The correct technique writes 3 full pages (768 bytes) with page striding, then a 232-byte tail loop for the final partial page:

```asm
        ldx #$00

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
```

The same 768 + 232 split applies to any screen-sized operation: clears, fills, copies, and frame transfers. See `system/screen.md` for the full screen layout and row address table.

## End-of-File Format

Every `.asm` file must end with exactly one trailing blank line. No more, no less.

## Naming Conventions

| Kind                                  | Convention                      | Example                                 |
|---------------------------------------|---------------------------------|-----------------------------------------|
| Hardware / KERNAL equates             | `UPPER_SNAKE_CASE`              | `PCR`, `CHROUT`, `PCR_U`                |
| Reserved ZP equate (`$FF`/`$A2` only) | `snake_case`                    | `scratch`                               |
| Code labels                           | `snake_case`                    | `decompress_lz4`                        |
| Loop labels                           | `snake_case`                    | `copy_loop_1`, `lz4_token`              |
| Data labels                           | `snake_case`                    | `screen_data`, `old_pcr`                |
| Internal continuation labels          | `snake_case` with shared prefix | `lz4_inc_source`, `lz4_inc_source_done` |

Prefixes group related labels. A subroutine and all its internal branch targets share the same prefix (`lz4_`). This makes the structure readable when scanning label names alone.

## Column Alignment Summary

Column numbers are 1-indexed: the first character of a line is column 1.

| Element                          | Column                                      |
|----------------------------------|---------------------------------------------|
| Labels                           | 0                                           |
| `processor`, `org` directives    | 8                                           |
| Instructions and data directives | 8                                           |
| `=` in global equates            | 8                                           |
| `=` in zero page equate group    | 16                                          |
| Inline comments on equates       | 25                                          |
| Inline comments on labels        | 25                                          |
| Inline comments on instructions  | 33, 41, 49, 57, 65, ... (tab stops every 8) |

## 6502 Flag Semantics

Branch instructions (`beq`, `bne`, `bmi`, `bpl`, `bcs`, `bcc`, `bvs`, `bvc`) test the flag register state produced by the **most recent instruction that actually updates flags**, not the instruction you might expect.

### Critical Flag Rules

| Instruction(s)             | Flags Affected    |
|----------------------------|-------------------|
| `lda`, `ldx`, `ldy`        | N, Z              |
| `sta`, `stx`, `sty`        | none              |
| `inx`, `dex`, `iny`, `dey` | N, Z              |
| `inc`, `dec` (memory)      | N, Z              |
| `asl`, `lsr`, `rol`, `ror` | N, Z, C           |
| `adc`, `sbc`               | N, V, Z, C        |
| `cmp`, `cpx`, `cpy`        | N, Z, C           |
| `and`, `ora`, `eor`        | N, Z              |
| `tax`, `txa`, `tay`, `tya` | N, Z              |
| `jsr`, `rts`, `jmp`, `rti` | none              |
| `pha`, `pla`, `php`, `plp` | N, Z (`pla` only) |
| `txs`, `tsx`               | N, Z (`tsx` only) |
| `clc`, `sec`, `cld`, `sed` | C or D (single)   |
| `clv`                      | V                 |
| `bit`                      | N, V, Z           |

For the full instruction set reference, see `hardware/cpu.md`.

### Branch-After-Load Bug Pattern

This common loop bug places `dex` too early, then relies on `sta` which does not affect flags, causing `bne` to test the `lda` value instead of the counter:

```asm
; BAD -- bne tests lda flags (loaded data), not dex
        dex
        lda BUFFER+$300,x
        sta SCREEN+$300,x
        bne copy_loop
```

If the loaded byte happens to be zero, `bne` exits the loop even though X has not reached zero. The correct order puts `dex` immediately before the branch so the branch tests the loop counter:

```asm
; GOOD -- bne tests dex flags (loop counter)
        lda BUFFER+$300-1,x
        sta SCREEN+$300-1,x
        dex
        bne copy_loop
```

### Decision Rule

When any instruction between the counter update and the branch does not affect flags, **the counter update must be the last instruction before the branch**. Apply this rule whenever a loop body contains `sta`, `jsr`, `jmp`, or any other non-flag instruction.
