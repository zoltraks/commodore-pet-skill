# DASM Assembler

## Purpose

> **Scope:** DASM syntax, directives, macros, segments, conditional assembly, command-line options
> **Key items:** `processor 6502`, `org $0401`, `byte`, `word`, `hex`, `equ`, `mac`/`endm`, `-f1` PRG format

This file covers DASM for PET 3032 work in four progressive layers:

- **Quick-lookup table** - scan or search for the directive you need
- **Reference tables & syntax** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                  | See instead        |
|-------------------------------|--------------------|
| File structure and formatting | `code/standard.md` |
| Naming conventions            | `code/standard.md` |
| Column alignment              | `code/standard.md` |
| BASIC stub layout             | `code/standard.md` |
| Comment placement rules       | `code/standard.md` |
| Section header banners        | `code/standard.md` |

## Contents

| Section              | Line | What it covers                                                                    |
|----------------------|------|-----------------------------------------------------------------------------------|
| Command Line         | 45   | Invocation flags: `-f1`, `-o`, `-I`, `-D`, direct binary vs Docker                |
| Docker               | 89   | dasm-container image: build, compile, includes, output                            |
| Processor Directive  | 168  | `processor 6502` requirement                                                      |
| Origin Directive     | 176  | `org $0401` and relocation                                                        |
| Addressing Modes     | 192  | Immediate, ZP, absolute, indexed, indirect syntax                                 |
| Data Directives      | 209  | `byte`, `word`, `hex`, `ds`, `dc`                                                 |
| Labels and Equates   | 258  | Local labels, `equ`/`=`, forward references                                       |
| Comments             | 333  | Semicolon style, tab-stop alignment                                               |
| Macros               | 345  | `mac`/`endm`, arguments, nesting                                                  |
| Conditional Assembly | 370  | `ifconst`, `ifnconst`, `else`, `endif`                                            |
| Repeat Loops         | 392  | `repeat`/`repend`                                                                 |
| Segments             | 402  | `seg`, `seg.u` for BSS, linking multiple segments                                 |
| Include Files        | 410  | `include` and `incbin` directives                                                 |
| Common Errors        | 422  | Undefined label, wrong format flag, forward-ref issues                            |

For file structure, formatting conventions, naming rules, column alignment, comment placement, section headers, and BASIC stub layout, see `code/standard.md`.

## Command Line

```bash
dasm source.asm -f1 -osource.prg
```

Common options:

| Option      | Description                                |
|-------------|--------------------------------------------|
| `-f1`       | Default: 2-byte load address header + data |
| `-f2`       | RAS format (origin + length + data hunks)  |
| `-f3`       | Output raw binary without header           |
| `-o<file>`  | Set output file name                       |
| `-v#`       | Verbosity 0-4                              |
| `-Dsym=val` | Predefine symbol                           |
| `-Idir`     | Add include search path                    |

For PET programs, always use `-f1` to produce a PRG file with a 2-byte load address header. This is the format expected by BASIC `LOAD` and `RUN` -- the first two bytes tell the PET where to place the program in memory (matching the `org` directive).

### Direct Binary (Fallback When Docker Is Unavailable)

If DASM is installed as a local binary (in `PATH` or at a known location), use it directly. This is the fallback when Docker is not available (e.g. Windows without Hyper-V, CI environments without a Docker daemon):

```bash
dasm source.asm -f1 -osource.prg
```

On PowerShell, the `-o` flag must be quoted to prevent PowerShell from interpreting it as a parameter:

```powershell
dasm source.asm -f1 "-obuild/source.prg"
```

The `-o` flag must be directly attached to the filename with no space (`-obuild/source.prg`, not `-o build/source.prg`). DASM treats `-o` with a space-separated argument as a different switch.

Check the installed version:

```bash
dasm
```

This prints the version banner and usage. DASM 2.20.14.1 is the current release.

## Docker

The `dasm-container` project (https://github.com/zoltraks/dasm-container) wraps DASM in a Debian 12-slim Docker image. This is the preferred way to build when Docker is available, ensuring a reproducible build environment.

Use the direct binary fallback (see above) when Docker is not available, such as on Windows without Hyper-V or in CI without a Docker daemon.

### Building the Image

Clone the repository and run the build script:

```bash
git clone https://github.com/zoltraks/dasm-container
cd dasm-container
./build.sh
```

The script downloads the DASM binary release, extracts it, and builds a local image named `dasm`. The default version is `2.20.14.1`.

Customise the build with environment variables:

| Variable  | Default     | Description                             |
|-----------|-------------|-----------------------------------------|
| `VERSION` | `2.20.14.1` | DASM version to download and install    |
| `CACHE`   | `cache`     | Directory for caching the download      |
| `IMAGE`   | `dasm`      | Name for the resulting Docker image     |
| `URL`     | (auto)      | Custom download URL (overrides VERSION) |

Examples:

```bash
VERSION=2.20.13 ./build.sh
IMAGE=my-dasm ./build.sh
```

### Compiling with the Container

The container working directory is `/src`. Mount the project directory there and pass DASM arguments after the image name:

```bash
docker run --rm -v $(pwd):/src dasm dasm source.asm -f1 -osource.prg
```

All flags from the Command Line table above apply unchanged. The output file is written back to the mounted host directory.

### Include Files

`include` directives resolve relative to the container working directory (`/src`), which maps to the mounted host directory. For include files in a subdirectory, either use a relative path in the source or pass the `-I` flag:

```bash
# source uses: include "pet.inc"
# pet.inc lives in src/
docker run --rm -v $(pwd):/src dasm dasm src/main.asm -f1 -obuild/main.prg -Isrc
```

### Output Directories

DASM does not create output directories. If the `-o` path points to a subdirectory, create it on the host first:

```bash
mkdir -p build
docker run --rm -v $(pwd):/src dasm dasm src/main.asm -f1 -obuild/main.prg
```

### Verbose Output

Pass `-v3` to see symbol table and pass information:

```bash
docker run --rm -v $(pwd):/src dasm dasm source.asm -f1 -osource.prg -v3
```

### Checking the Version

Run the container with no arguments to print the DASM version:

```bash
docker run --rm dasm
```

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
        byte <screen_data       ; low byte of address
        byte >screen_data       ; high byte of address
```

The `<` operator extracts the low byte. The `>` operator extracts the high byte.

## Labels and Equates

### Labels

Labels are case-sensitive and end with a colon. They are declared at column 0 on their own line:

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

For label spacing rules (blank lines before and after), subroutine boundary spacing, and naming conventions, see `code/standard.md`.

### Temporary Labels

Local labels start with a dot and are scoped by `SUBROUTINE` blocks:

```asm
main    subroutine
        ldx #$0A

.1

        dex
        bne .1

other   subroutine
        ldx #$14

.1

        dex                     ; different .1 from above
        bne .1
```

### Equates (EQU)

```asm
SCREEN  = $8000
GETIN   = $FFE4
CHROUT  = $FFD2
PCR     = $E84C
PCR_U   = $0C
PCR_L   = $0E
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

Comments start with a semicolon. Inline comments on instructions start at column 33 and follow tab-stop alignment (33, 41, 49, ...).

```asm
        lda #$00                ; load accumulator with zero
        lda #$93                ; PETSCII CLR/HOME
        sta PCR                 ; uppercase / graphics charset
```

For the full comment placement rules -- block intent comments, label description comments, subroutine boundary spacing, and what to avoid -- see `code/standard.md`.

## Macros

```asm
        mac     copy_row
        ldx     #$27

.1

        lda     {1},x
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

Macros are supported by DASM but are not used in the standard PET coding conventions -- see `code/standard.md`.

## Conditional Assembly

```asm
        ifconst USE_IRQ
        lda #<my_irq
        sta CINV
        lda #>my_irq
        sta CINV+1
        endif

        ifnconst DEBUG          ; skip debug code if DEBUG not defined
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
        seg     code            ; initialized code/data

        seg.u   vars            ; uninitialized segment (no output) -- useful for RAM allocation labels
```

## Include Files

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
