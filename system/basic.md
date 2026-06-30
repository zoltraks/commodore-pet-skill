# BASIC Program Storage

## Purpose

> **Scope:** How a BASIC program is laid out in PET 3032 RAM -- start address, line link/number/token format, tokenization, the BASIC zero-page pointers, and the full BASIC 2 token table
> **Key items:** start `$0401`, leading `$00` at `$0400`, line = link + line# + tokens + `$00`, end = null link, start-of-BASIC pointer `$28/$29`, tokens `$80`-`$CB`

A PET stores a BASIC program as tokenised text in RAM from `$0401` up. Machine code that reads, generates, or relocates BASIC -- or that simply needs to understand the `SYS` stub the skill ships -- needs this layout.

Everything here was verified against a BASIC 2 (`basic-2.901465-01-02`) machine in VICE: the token table was decoded from the keyword table at `$C092`, and the line format from a live memory dump.

| Out of scope                  | See instead        |
|-------------------------------|--------------------|
| Zero-page map (all locations) | `system/memory.md` |
| CHRGET text scanner / wedge   | `system/rom.md`    |
| The `SYS1038` boot stub       | `code/standard.md` |

## Where BASIC Lives

BASIC program text starts at `$0401` (decimal 1025). Location `$0400` holds a single `$00` byte that sits just below the program.

Variables and arrays grow upward from the end of the program; strings grow downward from the top of memory. Five zero-page pointers track these regions.

| Pointer   | Points to                                  |
|-----------|--------------------------------------------|
| `$28-$29` | Start of BASIC text (`$0401`)              |
| `$2A-$2B` | End of BASIC text / start of variables     |
| `$2C-$2D` | End of variables / start of arrays         |
| `$2E-$2F` | End of arrays                              |
| `$30-$31` | Bottom of string space (moving down)       |
| `$34-$35` | Top of BASIC memory (highest usable RAM)   |

Lower `$34-$35` before BASIC starts to reserve high memory for machine code or data. The currently executing line number is in `$36-$37`; it reads `$00` when BASIC is in direct mode.

## Line Storage Format

Each program line is a variable-length block:

```
[link lo][link hi]  [line# lo][line# hi]  [token bytes ...]  [$00]
```

- The **link** is the address of the next line's first byte. The interpreter follows links to move between lines.
- The **line number** is a 16-bit binary value (0-65535), low byte first.
- The line body is tokenised text (see below), terminated by a `$00` byte.
- The **end of the whole program** is a link field of `$0000` (two zero bytes) where the next line would begin.

Lines are always stored in ascending line-number order. Inserting a line shifts higher-numbered lines up in memory and recomputes every link.

A live example -- the program `10 PRINT"HI"` stored from `$0401`:

```
$0400:  00              ; leading zero byte below the program
$0401:  0B 04           ; link -> $040B (start of next line)
$0403:  0A 00           ; line number 10
$0405:  99              ; PRINT token
$0406:  22 48 49 22     ; "HI"  (quote, H, I, quote)
$040A:  00              ; end of line
$040B:  00 00           ; null link = end of program
```

On an empty program the start pointer `$28/$29` holds `$0401` and the two bytes at `$0401` are `$00 $00` -- the end-of-program marker with no lines in between.

## Tokenisation

When a line is entered, BASIC keywords are compressed to single bytes called tokens, all with bit 7 set (`$80` and up). `PRINT` becomes one byte `$99` instead of five ASCII characters. Everything that is not a keyword -- variable names, numbers, string literals, punctuation -- is stored as plain PETSCII.

The tokeniser matches only the first letters of a keyword, which is why abbreviations work: type the first letter, then the next letter shifted (for example `?` for `PRINT`, `pO` for `POKE`).

A token value is an index into the keyword table at `$C092`: token minus `$80` is the keyword's position in that table.

## BASIC 2 Token Table

These are the tokens for BASIC 2 (3008/3016/3032), decoded from the ROM keyword table. Operators (`+ - * / ^ > = <`) and `AND`/`OR`/`NOT` are tokenised too.

| Token | Keyword   | Token | Keyword  |
|-------|-----------|-------|----------|
| `$80` | `END`     | `$A6` | `SPC(`   |
| `$81` | `FOR`     | `$A7` | `THEN`   |
| `$82` | `NEXT`    | `$A8` | `NOT`    |
| `$83` | `DATA`    | `$A9` | `STEP`   |
| `$84` | `INPUT#`  | `$AA` | `+`      |
| `$85` | `INPUT`   | `$AB` | `-`      |
| `$86` | `DIM`     | `$AC` | `*`      |
| `$87` | `READ`    | `$AD` | `/`      |
| `$88` | `LET`     | `$AE` | `^`      |
| `$89` | `GOTO`    | `$AF` | `AND`    |
| `$8A` | `RUN`     | `$B0` | `OR`     |
| `$8B` | `IF`      | `$B1` | `>`      |
| `$8C` | `RESTORE` | `$B2` | `=`      |
| `$8D` | `GOSUB`   | `$B3` | `<`      |
| `$8E` | `RETURN`  | `$B4` | `SGN`    |
| `$8F` | `REM`     | `$B5` | `INT`    |
| `$90` | `STOP`    | `$B6` | `ABS`    |
| `$91` | `ON`      | `$B7` | `USR`    |
| `$92` | `WAIT`    | `$B8` | `FRE`    |
| `$93` | `LOAD`    | `$B9` | `POS`    |
| `$94` | `SAVE`    | `$BA` | `SQR`    |
| `$95` | `VERIFY`  | `$BB` | `RND`    |
| `$96` | `DEF`     | `$BC` | `LOG`    |
| `$97` | `POKE`    | `$BD` | `EXP`    |
| `$98` | `PRINT#`  | `$BE` | `COS`    |
| `$99` | `PRINT`   | `$BF` | `SIN`    |
| `$9A` | `CONT`    | `$C0` | `TAN`    |
| `$9B` | `LIST`    | `$C1` | `ATN`    |
| `$9C` | `CLR`     | `$C2` | `PEEK`   |
| `$9D` | `CMD`     | `$C3` | `LEN`    |
| `$9E` | `SYS`     | `$C4` | `STR$`   |
| `$9F` | `OPEN`    | `$C5` | `VAL`    |
| `$A0` | `CLOSE`   | `$C6` | `ASC`    |
| `$A1` | `GET`     | `$C7` | `CHR$`   |
| `$A2` | `NEW`     | `$C8` | `LEFT$`  |
| `$A3` | `TAB(`    | `$C9` | `RIGHT$` |
| `$A4` | `TO`      | `$CA` | `MID$`   |
| `$A5` | `FN`      | `$CB` | `GO`     |

## Walking a Program from Machine Code

To traverse a program, start at `$0401`, read the two-byte link, and follow it; stop when the link is `$0000`. The line number sits at offset 2-3 of each block, the tokens at offset 4.

```asm
        lda $28
        sta $FB                 ; borrow $FB/$FC as a line pointer
        lda $29
        sta $FC                 ; $FB/$FC -> first line

walk_line:
        ldy #0
        lda ($FB),y             ; link low
        tax
        iny
        lda ($FB),y             ; link high
        beq walk_done           ; high byte 0 with low byte 0 -> end of program
        ; ... line number at offset 2-3, tokens from offset 4 ...
        ; advance $FB/$FC to the link, then loop
        stx $FB
        sta $FC
        jmp walk_line

walk_done:
```

A null link (`$0000`) is the only end-of-program marker; there is no separate count of lines.
