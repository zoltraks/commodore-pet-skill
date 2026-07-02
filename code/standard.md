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
| Optimization patterns            | `code/optimization.md`      |
| Compression formats and routines | `code/compression.md`       |

## Contents

| Section                  | Line | What it covers                                                      |
|--------------------------|------|---------------------------------------------------------------------|
| Toolchain                | 40   | DASM invocation, target CPU, hardware, load address                 |
| File Structure           | 49   | Top-to-bottom layout for every `.asm` file                          |
| Directives               | 65   | `processor 6502` and `org $0401` placement                          |
| Equates                  | 83   | Global hardware equates, grouping and alignment rules               |
| Zero Page Usage          | 107  | Parameter blocks, borrowing `$FB`-`$FE`, save/restore, indirect addressing limitation |
| BASIC Stub               | 222  | Standard SYS1038 stub with `nextline:` and `old_pcr:`               |
| Labels                   | 199  | Spacing, naming, colon rules, subroutine boundaries                 |
| Instruction Formatting   | 256  | Indentation, tab-stop comments, operand rules                       |
| Comment Placement        | 284  | Block intent comments, label description comments                   |
| Routine Conventions      | 336  | Contracts, scratch registers, error signalling, self-modifying code |
| Section Headers          | 371  | Major and minor banner format                                       |
| Data Directives          | 397  | `byte`, `word`, string bytes, screen row layout                     |
| Screen RAM Operations    | 442  | 1000-byte screen invariant, 768+232 clear/fill/copy pattern         |
| End-of-File Format       | 472  | Trailing blank line rule                                            |
| Naming Conventions       | 476  | Convention table for all identifier kinds, abbreviations            |
| Column Alignment Summary | 491  | Column position table for every source element                      |
| 6502 Flag Semantics      | 506  | Flag-affecting instructions, branch-after-load bug, BIT A-AND-operand hazard |

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

Declared at the top of the file, before `org`. Names are `UPPER_SNAKE_CASE`. Within each contiguous equate group, the `=` sign is aligned in a single column, placed one space after the longest constant name in that group. Shorter names are padded with spaces so their `=` lines up. Inline comments within a group are aligned to the same tab-stop column (see Inline Comment Alignment below).

```asm
SCREEN      = $8000
BUFFER      = $7C00     ; 1000-byte back buffer, page-aligned
VIA_PORTB   = $E840     ; VIA port B (PB5 = VBLANK signal)
RETRACE_BIT = $20       ; PB5 mask: LOW during VBLANK
PCR         = $E84C     ; VIA Peripheral Control Register
PCR_U       = $0C       ; PCR bits 3:1 = 110 -> uppercase/graphics set
PCR_L       = $0E       ; PCR bits 3:1 = 111 -> lowercase/text set
```

Rules:

- Group logically related equates together (screen, KERNAL, hardware registers).
- Separate groups with a single blank line.
- Within each group, align all `=` signs to one space after the longest name. The alignment column is determined per group, not globally.
- Equates without comments still pad to the group's `=` column.
- Inline comments within a group align to the same tab-stop column, determined by the longest content among lines that have comments.
- Do not describe what a hardware address physically is if the name already encodes it.
- Always use "KERNAL" (uppercase) when referring to Commodore KERNAL routines.

## Zero Page Usage

PET BASIC 2 leaves almost no zero page free. Only `$FF` and `$A2` are documented unused; everything else belongs to the KERNAL or BASIC. The rule is not to avoid naming a zero-page address but to never use one without saving and restoring it.

### Parameter Block Convention

Prefer passing multi-byte inputs to a routine as a data block in free RAM. The caller loads X with the block's low byte and Y with the high byte, then JSRs. This avoids committing to a zero-page address at all.

```asm
win_params:

        byte 5                  ; row
        byte $0A                ; col

        ldx #<win_params
        ldy #>win_params
        jsr draw_window
```

### Borrowing Zero Page

When a routine needs zero page for `($zp),y` indirect addressing, borrow `$FB`-`$FE` (the KERNAL tape pointers, idle when tape I/O is not running), save the previous contents on entry, and restore them on exit. Aliasing the borrowed bytes with `snake_case` equates is allowed and reads better than repeating raw addresses.

```asm
src_lo  = $FB           ; borrowed KERNAL tape pointer
src_hi  = $FC           ; saved and restored below

        lda src_hi
        pha
        lda src_lo
        pha
        stx src_lo
        sty src_hi

        lda (src_lo),y          ; Check compression flag

        pla
        sta src_lo
        pla
        sta src_hi
```

Rules:

- Comment the borrowed byte where it is declared to state what it holds and that it is saved/restored.
- Save and restore in mirrored pairs (push order reversed on the pull side).
- Reference borrowed bytes by alias or by raw hex; either is fine as long as the save/restore is present.

### What to Avoid

The mistake is not naming a ZP address -- it is using one without the save/restore obligation:

```asm
; Wrong: borrows $F7/$F8 but never saves or restores them
src_lo  = $F7
src_hi  = $F8
        stx src_lo              ; clobbers whatever KERNAL/BASIC kept there
        sty src_hi
```

Only `$FF` and `$A2` are documented unused by PET BASIC 2 and may be used without saving.

### Indirect Indexed Addressing Limitation

The 6502 supports only **one** indirect indexed addressing mode: `(zp),y`. There is no `(zp),x` mode. DASM will reject `(zp),x` with `error: Illegal Addressing mode`.

This constraint matters when a loop needs to index both a source buffer and a destination (e.g., copying data from a file buffer to screen RAM). Since Y is the only register that works with `(zp),y`, you cannot use two indirect pointers simultaneously with independent indices.

**Wrong** (will not assemble):

```asm
        lda (src_ptr),x          ; ERROR: no (zp),x mode on 6502
        sta (dst_ptr),y
```

**Solution 1: Save/restore Y** -- Use Y for one pointer and a temp variable for the other index:

```asm
        ldy #0
loop:
        lda (src_ptr),y          ; read source via (zp),y
        sty ytmp                 ; save source index
        ldy dst_col              ; load destination column
        sta (dst_ptr),y          ; write destination via (zp),y
        inc dst_col
        ldy ytmp                 ; restore source index
        iny
        cpy #count
        bne loop
```

**Solution 2: Advance the pointer** -- Instead of indexing, advance the zero-page pointer itself after each byte:

```asm
        ldy #0
loop:
        lda (src_ptr),y
        sta (dst_ptr),y
        inc src_lo               ; advance source pointer
        bne skip_src_hi
        inc src_hi
skip_src_hi:
        inc dst_lo               ; advance destination pointer
        bne skip_dst_hi
        inc dst_hi
skip_dst_hi:
        dex
        bne loop
```

Solution 1 is preferred when the source and destination indices differ (e.g., source starts at 0, destination starts at column 1). Solution 2 is simpler when both pointers advance in lockstep.

## BASIC Stub

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

Do not insert any code or data ahead of the stub. Anything placed before it shifts the `$0401` load address and the `SYS1038` entry target, so the BASIC line no longer jumps to the start of the machine code.

## Labels

Labels are declared at column 0. A code label (a label on its own line, with no instruction or data after the colon) is always preceded by exactly one blank line and followed by exactly one blank line before the first instruction or directive. One blank line, not zero and not two.

This rule applies to all code labels without exception:

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

A compact data label has its data directive on the same line as the label (e.g. `byte`, `word`, `ds`). Consecutive compact data labels in a declaration block do not require blank lines between them, since the label and its data form a single logical line:

```asm
frame_idx_lo:    byte $00
frame_idx_hi:    byte $00
```

A code label (label on its own line, no data after the colon) always gets exactly one blank line before and after, even when consecutive:

```asm
        rts

copy_loop_2:

        lda screen_data+$300,x
        sta SCREEN+$300,x
```

Rules:

- Names are `snake_case`.
- No colon on equate names. Colons appear only on labels that represent addresses.
- Never place an instruction on the same line as a code label.
- Code labels: exactly one blank line before and one after. Not zero, not two.
- Compact data labels: no blank line required between consecutive declarations in the same block.
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

Inline comments on instructions use tab-stop alignment. Within a contiguous code block (a run of instructions between blank lines, labels, or comment blocks), all inline comments align to the same tab-stop column. The minimum tab stop for instruction comments is column 33. If any instruction in the block that has a comment extends past column 31, the comment column shifts to the next tab stop (41, 49, 57, 65, and so on). There must be at least one space between the end of the instruction and the semicolon. See Inline Comment Alignment below for the full rule.

```asm
        ldy #2                  ; type at record offset 2 (already screen code)
        lda (sp_lo),y
        ora #$80                ; reverse video
        ldy #38
        sta (dp_lo),y
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

### Full-Line Comments

A full-line comment is a line whose first non-whitespace character is `;` and that carries no instruction or data. Section banners, descriptive blocks, and standalone annotations are all full-line comments.

When a full-line comment (or a block of consecutive full-line comment lines) appears in the file, it must be surrounded by exactly one blank line before and after. One blank line, not zero and not two.

```asm
PET_FNLEN       = $D1        ; filename length
PET_FNADR_LO    = $DA        ; filename address low
PET_FNADR_HI    = $DB        ; filename address high

; ---- KERNAL zero-page mirrors -------------------------

STATUS = $0096
BLNSW  = $00A7
```

Rules:

- Exactly one blank line before the first comment line of the block.
- Exactly one blank line after the last comment line of the block.
- No blank lines between consecutive comment lines within the same block.
- Never use two or more consecutive blank lines anywhere in the file.
- The first line of the file and the line after `org` are exempt: a comment block at the very top of the file needs no blank line before it.

### Block Intent Comments

A comment that describes what a single block of code does should be placed as an inline comment on the first instruction of that block. Prefer inline comments over standalone `;` lines for brief block-intent notes.

When a standalone full-line comment is used for a longer explanation that does not fit inline, it follows the full-line comment spacing rule above.

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

Label description comments start at column 25, with the same tab-stop fallback rule as inline comments (33, 41, 49, ...) if the label name is unusually long.

### Inline Comment Guidelines

Comment only what is not evident from the instruction and its operands. Acceptable uses:

- Clarifying a magic constant: `; PETSCII CLR/HOME`
- Describing the register state after a step: `; X = literal count (may be 15)`
- Explaining a flag check: `; Check compression flag (byte 3): 0 = uncompressed, 1 = compressed`
- Noting hardware register semantics: `; CA2 high: uppercase / graphics charset`

Do not comment what the mnemonic already says. Do not leave commented-out code.

### File-Level Comments

Major section banners serve as the file-level structural comments. No file header block or author line is used.

## Inline Comment Alignment

Within a group of related lines (a contiguous equate group, a compact data declaration block, or a code block between blank lines, labels, or comment blocks), all inline comments start at the same column. The column is a tab stop: a multiple of 8 plus 1 (1, 9, 17, 25, 33, 41, 49, 57, 65, ...). There must be at least one space between the end of the content and the semicolon.

The comment column is determined per group:

- Find the longest content (everything before the `;`) among lines in the group that have inline comments. Lines without comments do not push the column.
- The comment column is the smallest tab stop that is greater than the longest content end, with a minimum tab stop depending on the group type:
  - **Equate groups and compact data label groups** (lines at column 0): minimum tab stop is 25.
  - **Code blocks** (lines indented 8 spaces): minimum tab stop is 33.

A continuation comment is a standalone comment line indented to more than 8 spaces (aligned to the group's inline comment column). It is part of the group, not a block-level comment. Continuation comments do not have content before the `;` and do not count toward the longest content. They align to the group's comment column and have no blank line between them and adjacent group lines.

```asm
PANEL_ROWS  = 18        ; visible directory rows in each panel (rows 4..21)
PANEL_WIDTH = 20        ; columns per panel including frame borders
PANEL_INNER = 18        ; inner content columns (excluding frame borders)
MAX_ENTRY   = 64        ; entries per panel
ENT_SIZE    = 20        ; bytes per entry record
                        ; layout: blo, bhi, type, name[16], pad
```

A block comment is a standalone comment indented to exactly 8 spaces (the code indent level). It is a structural comment, not part of the inline comment group. Block comments keep blank lines around them and are not aligned to the inline comment column.

```asm
        ; ---- Type char at col 38 (reversed) ----

        ldy #2                  ; type at record offset 2 (already screen code)
        lda (sp_lo),y
        ora #$80                ; reverse video
```

Rules:

- Tab stops are at columns 1, 9, 17, 25, 33, 41, 49, 57, 65, ... (8k+1 for k = 0, 1, 2, ...).
- At least one space between the end of the content and the `;`.
- All inline comments in a group share the same column.
- Lines without comments do not affect the column calculation.
- Continuation comments (> 8-space indent) are part of the group: no blank lines around them, aligned to the group's comment column.
- Block comments (8-space indent) are structural: blank lines around them, not aligned to the inline comment column.

## Routine Conventions

The 6502 has no call frames, no exceptions, and no enforced calling convention. The discipline below keeps routines callable without surprises.

### Document the Contract

Every non-trivial routine begins with a comment stating its inputs, its outputs, and which registers it clobbers. State register preservation explicitly -- a caller cannot otherwise know what survives a `jsr`.

```asm
; draw_entry: render one directory entry.
;   In:  X = entry index, A = screen row
;   Out: carry set on error (row off screen)
;   Clobbers: A, Y. Preserves X.
draw_entry:

        ; ...
```

### Registers Are Scratch

Treat A, X, and Y as scratch across a `jsr` unless the called routine's contract documents that it preserves one. A routine that promises to preserve a register must save and restore it (stack push/pull or a saved byte).

### Signal Errors Through a Flag

Because there are no exceptions, signal success or failure through the carry flag or a documented register, and have the caller branch on it. Keep error paths reachable: a routine that can fail must set a flag the caller checks or a visible status, never fail silently.

```asm
        jsr open_file
        bcs open_failed         ; carry set = error
```

### Self-Modifying Code

Self-modifying code (writing to an operand of an instruction at runtime) is allowed but must carry a comment explaining what is patched and why. Do not use it on a hot path without a measured reason.

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

| Kind                         | Convention                      | Example                                 |
|------------------------------|---------------------------------|-----------------------------------------|
| Hardware / KERNAL equates    | `UPPER_SNAKE_CASE`              | `PCR`, `CHROUT`, `PCR_U`                |
| Zero-page aliases            | `snake_case`                    | `src_lo`, `dest_hi`, `scratch`          |
| Code labels                  | `snake_case`                    | `decompress_lz4`                        |
| Loop labels                  | `snake_case`                    | `copy_loop_1`, `lz4_token`              |
| Data labels                  | `snake_case`                    | `screen_data`, `old_pcr`                |
| Internal continuation labels | `snake_case` with shared prefix | `lz4_inc_source`, `lz4_inc_source_done` |

Prefixes group related labels. A subroutine and all its internal branch targets share the same prefix (`lz4_`). This makes the structure readable when scanning label names alone.

Abbreviations are allowed when they are conventional for the platform: `lo`, `hi`, `ptr`, `sp`, `dp`, `zp`, `dos`, `sa` (secondary address). Do not invent new cryptic abbreviations; spell out anything a reader would not recognise at a glance.

## Column Alignment Summary

Column numbers are 1-indexed: the first character of a line is column 1.

| Element                          | Column                                      |
|----------------------------------|---------------------------------------------|
| Labels                           | 0                                           |
| `processor`, `org` directives    | 8                                           |
| Instructions and data directives | 8                                           |
| `=` in equate groups             | one space after longest name in group       |
| Inline comments (equates/data)   | min 25, then 33, 41, ... (per group)        |
| Inline comments (instructions)   | min 33, then 41, 49, ... (per group)        |
| Inline comments on labels        | 25, then 33, 41, ... (tab stops every 8)    |

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

If the loaded byte happens to be zero, `bne` exits the loop even though X has not reached zero. If the loaded byte is never zero (common with uninitialized RAM filled with `$AA`), the loop never exits when X wraps past zero -- it continues writing past the intended range, corrupting memory.

This bug was found in the double-buffer `copy_tail` routine. See `system/screen.md` for the full real-world example and its consequences.

Two fixes exist. Both are correct:

```asm
; FIX 1: txa after sta -- bne tests X (counter)
        dex
        lda BUFFER+$300,x
        sta SCREEN+$300,x
        txa
        bne copy_loop

; FIX 2: dex after sta -- bne tests X (counter)
        lda BUFFER+$300,x
        sta SCREEN+$300,x
        dex
        bne copy_loop
```

Fix 1 (`txa`) costs one extra byte and one extra cycle. Fix 2 reorders the loop body and costs nothing extra.

### Decision Rule

When any instruction between the counter update and the branch does not affect flags, **the counter update must be the last instruction before the branch**. Apply this rule whenever a loop body contains `sta`, `jsr`, `jmp`, or any other non-flag instruction.

If reordering is not possible (e.g., the counter must decrement before the load), insert `txa` or `tya` between the last flag-affecting instruction and the branch to restore the counter's flags.

### BIT Tests A AND Operand, Not Operand Alone

The `BIT` instruction performs a logical AND of the accumulator (`A`) with the memory operand, then sets the Z flag based on the **result of that AND**, not on the operand's value alone. N and V are copied from bits 7 and 6 of the operand.

A common mistake is to use `bit flag_var` to test whether `flag_var` is zero, while A holds an unrelated data byte. In that case `bne`/`beq` tests `A AND flag_var`, not `flag_var`:

```asm
; BAD -- bne tests (A AND view_charset), not view_charset alone
        lda (dp_lo),y           ; A = data byte from buffer
        bit view_charset        ; Z = (A AND view_charset) == 0
        bne is_lower            ; branches on bit 0 of the DATA, not the flag
```

If `view_charset` is `$01` (LOWER) and the data byte has bit 0 set (e.g. any odd PETSCII value), the branch is taken regardless of the actual flag value.

**Fix 1: Test the flag before loading data** (preferred when register pressure is low):

```asm
        lda view_charset        ; A = flag
        bne is_lower            ; tests the flag directly
        lda (dp_lo),y           ; now load data
```

**Fix 2: Save/restore A around the flag test** (when the data byte must survive):

```asm
        pha                     ; save data byte
        lda view_charset        ; A = flag
        bne is_lower
        pla                     ; restore data byte
        ; ... process UPPER case
```

This hazard is specific to `BIT` -- `CMP`, `LDA`, and `INC`/`DEC` all set flags from their own result, not from a second operand.
