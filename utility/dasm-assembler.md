# DASM Assembler

## Purpose

> **Scope:** DASM syntax, directives, macros, segments, conditional assembly, PET conventions
> **Key items:** `processor 6502`, `org $0401`, `byte`, `word`, `hex`, `equ`, `mac`/`endm`, `-f3` raw binary

This file covers DASM for PET 3032 work in four progressive layers:

- **Quick-lookup table** - scan or search for the directive you need
- **Reference tables & syntax** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

## Command Line

```bash
dasm source.asm -f3 -obinary.bin
```

Common options:

| Option      | Description                               |
|-------------|-------------------------------------------|
| `-f3`       | Output raw binary without header          |
| `-f2`       | RAS format (origin + length + data hunks) |
| `-f1`       | Default: 2-byte origin header + data      |
| `-o<file>`  | Set output file name                      |
| `-v#`       | Verbosity 0-4                             |
| `-Dsym=val` | Predefine symbol                          |
| `-Idir`     | Add include search path                   |

For PET programs, always use `-f3` to produce raw binary loadable via BASIC `SYS` or monitor `L` command.

## Processor Directive

```asm
        processor 6502
```

Must appear at the start of the file for 6502 code. Only one `PROCESSOR` directive per assembly.

## Origin Directive

```asm
        org $0401
```

Sets the program counter (assembly address). The PET 3032 uses `org $0401` for the BASIC stub start.

**With default fill:**

```asm
        org $0401, $00
```

Sets fill byte for skipped regions. Default is $00.

## Addressing Modes

| Mode             | Syntax    | Example       |
|------------------|-----------|---------------|
| Immediate        | `#$value` | `lda #$00`    |
| Zero page        | `$zp`     | `lda $F7`     |
| Zero page,X      | `$zp,x`   | `lda $F7,x`   |
| Zero page,Y      | `$zp,y`   | `lda $F7,y`   |
| Absolute         | `$addr`   | `lda $8000`   |
| Absolute,X       | `$addr,x` | `lda $8000,x` |
| Absolute,Y       | `$addr,y` | `lda $8000,y` |
| Indirect         | `($addr)` | `jmp ($0300)` |
| Indexed indirect | `($zp,x)` | `lda ($F7,x)` |
| Indirect indexed | `($zp),y` | `lda ($F7),y` |
| Implied          | none      | `inx`, `rts`  |
| Relative         | label     | `bne loop`    |

## Data Directives

### byte (DC.B)

Define one or more bytes:

```asm
        byte $9E
        byte "1","0","3","8",0
        byte $0C, $08
```

### word (DC.W)

Define 16-bit words in little-endian order (6502 mode):

```asm
        word nextline
        word 0
```

Stores low byte first, then high byte. Used for BASIC line pointers and terminators.

### String Bytes

PETSCII tokens and digit strings use quoted single-character `byte` values:

```asm
        byte $9E
        byte "1","0","3","8",0
```

### hex

Define raw hex data compactly (no `$` prefix):

```asm
        hex 1A45 45 13254F 3E12
```

### Low/High Byte Extraction

```asm
        byte <screen_data      ; low byte of address
        byte >screen_data      ; high byte of address
```

The `<` operator extracts the low byte. The `>` operator extracts the high byte.

## Labels and Equates

### Labels

Labels are case-sensitive and end with a colon:

```asm
nextline:

        word 0

start:

        lda PCR
        sta old_pcr
```

Labels can be used as addresses in instructions:

```asm
        jsr decompress_rle
        jmp wait_key
        lda screen_data,x
```

### Temporary Labels

Local labels start with a dot and are scoped by `SUBROUTINE` blocks:

```asm
main    subroutine
        ldx #10
.1      dex
        bne .1

other   subroutine
        ldx #20
.1      dex                 ; different .1 from above
        bne .1
```

### Equates (EQU)

```asm
SCREEN  = $8000
GETIN   = $FFE4
CHROUT  = $FFD2
PCR     = $E84C
PCR_U   = $0C
PCR_L   = $08
```

Alternate syntax:

```asm
symbol  equ     $8000
symbol  =       $8000
```

### Set (Reassignable)

```asm
COUNT   set     0
        ; ...
COUNT   set     COUNT + 1
```

## Comments

Comments start with a semicolon. Inline comments on instructions start at column 33. If the instruction is too long, ensure at least one space before the semicolon.

```asm
        lda #$00        ; load accumulator with zero
        lda #$93        ; PETSCII CLR/HOME
        sta PCR         ; CA2 high: uppercase / graphics charset
```

Comment only what is not evident from the instruction and its operands. Do not comment what the mnemonic already says. Do not leave commented-out code.

## Macros

```asm
        mac     copy_row
        ldx     #39
.1      lda     {1},x
        sta     {2},x
        dex
        bpl     .1
        endm
```

Arguments referenced with `{1}`, `{2}`, etc. `{0}` is the entire argument line.

**Invocation:**

```asm
        copy_row src_row, dst_row
```

Macros are supported by DASM but are not used in the PET LAB code generation pipeline.

## Conditional Assembly

```asm
        ifconst USE_IRQ
        lda #<my_irq
        sta CINV
        lda #>my_irq
        sta CINV+1
        endif

        ifnconst DEBUG
        ; skip debug code if DEBUG not defined
        endif
```

| Directive       | True When                       |
|-----------------|---------------------------------|
| `IFCONST expr`  | expression is defined           |
| `IFNCONST expr` | expression is undefined         |
| `IF expr`       | expression defined AND non-zero |
| `ELSE`          | alternative branch              |
| `ENDIF` / `EIF` | end conditional                 |

## Repeat Loops

```asm
        repeat  10
        byte    $20
        repend
```

Generates 10 space bytes. Labels inside REPEAT should be temporary labels inside a SUBROUTINE.

## Segments

```asm
        seg     code
        ; initialized code/data

        seg.u   vars
        ; uninitialized segment (no output)
        ; useful for RAM allocation labels
```

## Naming Conventions

| Kind                      | Convention         | Example                    |
|---------------------------|--------------------|----------------------------|
| Hardware / KERNAL equates | `UPPER_SNAKE_CASE` | `PCR`, `CHROUT`, `PCR_U`   |
| Zero page equates         | `snake_case`       | `source_lo`, `dest_hi`     |
| Code labels               | `snake_case`       | `decompress_rle`           |
| Loop labels               | `snake_case`       | `copy_loop_1`, `lz4_token` |
| Data labels               | `snake_case`       | `screen_data`, `old_pcr`   |

Prefixes group related labels.

A subroutine and all its internal branch targets share the same prefix.

## Column Alignment

Column numbers are 1-indexed.

| Element                          | Column |
|----------------------------------|--------|
| `processor`, `org` directives    | 8      |
| Instructions and data directives | 8      |
| `=` in global equates            | 8      |
| `=` in zero page equate group    | 16     |
| Inline comments on equates       | 25     |
| Inline comments on instructions  | 33     |
| Labels                           | 0      |

## PET-Specific DASM Conventions

### File Structure

Every generated `.asm` file follows this top-to-bottom layout:

1. `processor 6502` directive
2. Blank line
3. Global equates (hardware addresses and KERNAL routines)
4. Blank line
5. `org $0401`
6. Blank line
7. BASIC stub section
8. Data labels embedded in stub (`nextline:`, `old_pcr:`)
9. One or more major code and data sections

Sections are separated by major section header banners. There is no footer or end-of-file marker.

### Standard File Header

```asm
        processor 6502

SCREEN  = $8000
GETIN   = $FFE4
CHROUT  = $FFD2

PCR     = $E84C
PCR_U   = $0C
PCR_L   = $08

        org $0401

; BASIC stub: SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0
```

### Include Files

```asm
        include "pet_constants.asm"
```

### INCBIN (Raw Binary Include)

```asm
        incbin  "charset.bin"
```

## Common Errors

| Error            | Cause                        | Fix                                  |
|------------------|------------------------------|--------------------------------------|
| Phase error      | Forward reference unresolved | Add more passes with `-p#`           |
| Origin redefined | ORG set after code generated | Use SEG for multiple regions         |
| Label not found  | Typo or wrong scope          | Check spelling and SUBROUTINE blocks |