# PRG Loading

## Purpose

> **Scope:** Loading PRG and binary data files from cassette tape and IEEE-488 disk via the LOAD KERNAL call
> **Key items:** LOAD=$FFD5, pet_setlfs, pet_setnam, SA=0 (header addr), SA=1 (fixed addr), device 1=tape, device 8=disk

| Out of scope             | See instead        |
|--------------------------|--------------------|
| KERNAL routine reference | `system/kernal.md` |
| Sequential file I/O      | `system/file.md`   |
| Safe memory zones        | `system/memory.md` |

> **Verify before relying on this (ML caveat):** On the PET, the `LOAD` (`$FFD5`) and `SAVE` (`$FFD8`) jump-table entries are BASIC-command implementations. Both begin with `JSR $F43E`, which **unconditionally resets `$D1` (filename length), `$D3` (SA), and `$D4` (device) and then reads the real parameters from the BASIC text pointer** (`$77/$78`) — exactly like `OPEN`/`CLOSE` (see `system/kernal.md`). This was confirmed by disassembling `kernal-2.901465-03`. Consequently the "call `pet_setnam`/`pet_setlfs`, then `jsr $FFD5`" pattern shown below does **not** carry the filename through from pure machine code: `$F43E` wipes it before the load runs. To LOAD/SAVE a named file from ML you must either (a) run with the BASIC text pointer aimed at a valid `LOAD`-statement argument string, or (b) enter the routine past the parse (LOAD continues at `$F3C9`, SAVE at `$F6A1`, with `$D1/$DA/$DB` and the load/verify flag `$9D` pre-set). Test the exact sequence under VICE before depending on it.

## Loading a Binary File (LOAD)

`LOAD` reads a PRG file and places it into RAM.

With secondary address SA=0, `LOAD` uses the 2-byte start address stored in the file header.

With SA=1, `LOAD` ignores the file header and loads to the address in X/Y on entry.

After `LOAD` returns, X = low byte and Y = high byte of the byte after the last loaded byte.

```asm
; PET does not have SETLFS - use pet_setlfs wrapper
; PET does not have SETNAM - use pet_setnam wrapper
LOAD    = $FFD5
STATUS  = $0096

fname:

        byte "FRAMES"

fname_end:

load_frames:

        lda #fname_end-fname    ; filename length
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #1                  ; logical file number
        ldx #1                  ; device: cassette #1
        ldy #0                  ; SA=0: use address from file header
        jsr pet_setlfs

        lda #0                  ; 0 = LOAD (not VERIFY)
        jsr LOAD                ; X/Y = end+1 on return

        lda STATUS              ; non-zero = error
        bne load_error
        rts

load_error:

        rts
```

Check STATUS after every LOAD call. Bit 4 = file not found. Bit 5 = device not present.

## Loading to a Fixed Address (SA=1)

To force loading to a specific address regardless of the file header, use SA=1 and pass the destination in X/Y before calling LOAD:

```asm
        lda #1
        ldx #1                  ; device: cassette
        ldy #1                  ; SA=1: load to address in X/Y
        jsr pet_setlfs

        lda #0
        ldx #<$4000             ; destination low byte
        ldy #>$4000             ; destination high byte
        jsr LOAD
```

## Loading from IEEE-488 Disk (Device 8)

Disk loading uses the same call sequence as tape but with device number 8:

```asm
load_from_disk:

        lda #fname_end-fname
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #1
        ldx #8                  ; device: IEEE-488 disk drive
        ldy #0                  ; SA=0: relocating load (header address)
        jsr pet_setlfs

        lda #0
        jsr LOAD

        lda STATUS
        bne load_error
        rts
```

## Reading Raw Bytes via CHKIN/CHRIN

For streaming data byte by byte without using LOAD (useful when data is not a PRG file or needs custom parsing):

```asm
OPEN    = $FFC0
CLOSE   = $FFC3
CHKIN   = $FFC6
CLRCHN  = $FFCC
CHRIN   = $FFCF
STATUS  = $0096

read_stream:

        jsr pet_open                ; SETNAM + SETLFS already called

        lda #1                  ; logical file number
        jsr CHKIN               ; set file as current input

        ldy #0

read_loop:

        jsr CHRIN               ; read one byte into A
        sta dest_buf,y
        lda STATUS
        bne read_done           ; any non-zero STATUS = EOF or error
        iny
        bne read_loop

read_done:

        jsr CLRCHN
        lda #1
        jsr pet_close
        rts
```

See `system/file.md` for the full STATUS bit reference and complete sequential file I/O patterns.

## Tape File Format

The PET cassette file format consists of:

- A short leader tone
- Sync byte (`$89`)
- Header block: filename (16 bytes padded with `$20`), start address (2 bytes LE), end address (2 bytes LE), file type (1 byte)
- File type: `$00` = relocatable, `$01` = sequential, `$02` = non-relocatable (PRG)
- A second copy of the header (redundancy)
- Data block containing the raw binary
- A second copy of the data block

For animation data saved from an emulator or cross-tool, use type `$00` (relocatable) or `$02` (PRG).

## BASIC Stub with Loader

A complete program that immediately loads animation frame data on RUN:

```asm
        processor 6502

; PET does not have SETLFS - use pet_setlfs wrapper
; PET does not have SETNAM - use pet_setnam wrapper
LOAD    = $FFD5
CHROUT  = $FFD2
STATUS  = $0096

        org $0401

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0

start:

        lda #aname_end-aname
        ldx #<aname
        ldy #>aname
        jsr pet_setnam

        lda #1
        ldx #1                  ; cassette
        ldy #1                  ; SA=1: fixed address load
        jsr pet_setlfs

        lda #0
        ldx #<$4000             ; animation data destination
        ldy #>$4000
        jsr LOAD

        lda STATUS
        bne load_error

        jmp $4000               ; jump to loaded animation player

load_error:

        lda #$93
        jsr CHROUT              ; clear screen
        rts

aname:

        byte "DATA"

aname_end:
```
