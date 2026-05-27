# Data Loading

## Purpose

> **Scope:** Loading binary data from tape and IEEE-488 disk via KERNAL routines
> **Key items:** SETNAM=$FFBD, SETLFS=$FFBA, LOAD=$FFD5, device 1=tape, device 8=disk, STATUS=$0096

This file covers how to load raw binary data into PET RAM from cassette or disk, which is the standard way to supply animation frame data to a player program.

| Out of scope               | See instead                |
|----------------------------|----------------------------|
| KERNAL jump table overview | `system/kernal-vectors.md` |
| Safe memory zones          | `system/memory-map.md`     |

## KERNAL I/O Addresses

| Address | Name   | Description                                 |
|---------|--------|---------------------------------------------|
| $FFBA   | SETLFS | Set logical file, device, secondary address |
| $FFBD   | SETNAM | Set filename                                |
| $FFC0   | OPEN   | Open logical file                           |
| $FFC3   | CLOSE  | Close logical file                          |
| $FFC6   | CHKIN  | Set input channel                           |
| $FFC9   | CHKOUT | Set output channel                          |
| $FFCC   | CLRCHN | Clear channels (restore default I/O)        |
| $FFCF   | BASIN  | Read byte from current input                |
| $FFD2   | CHROUT | Write byte to current output                |
| $FFD5   | LOAD   | Load file to memory                         |
| $FFD8   | SAVE   | Save memory range to file                   |
| $FFB7   | READST | Read I/O status word                        |

## Device Numbers

| Device           | Number | Notes                     |
|------------------|--------|---------------------------|
| Keyboard         | 0      | Default input             |
| Cassette #1      | 1      | Primary tape drive        |
| Cassette #2      | 2      | Second tape drive via VIA |
| Screen           | 3      | Default output            |
| IEEE-488 #1      | 8      | Disk drive, primary       |
| IEEE-488 #2      | 9      | Second disk drive         |
| IEEE-488 printer | 4-5    | Printer                   |

## Loading a Binary File (LOAD)

`LOAD` reads a file and places it into memory. On the PET, for cassette (device 1), the file header contains a 2-byte start address. `LOAD` with A=0 uses the address from the file header. With secondary address=0 (SA=0), the file is placed at the address in the header.

```asm
SETLFS  = $FFBA
SETNAM  = $FFBD
LOAD    = $FFD5
STATUS  = $0096

fname:

        byte "FRAMES",0

fname_end:

load_frames:

        lda #fname_end-fname-1  ; filename length
        ldx #<fname
        ldy #>fname
        jsr SETNAM

        lda #1                  ; logical file number
        ldx #1                  ; device: cassette #1
        ldy #0                  ; secondary address: 0 = use header address
        jsr SETLFS

        lda #0                  ; 0 = LOAD (not VERIFY)
        jsr LOAD                ; loads file, sets X/Y to end address

        lda STATUS              ; check I/O status
        bne load_error          ; non-zero = error

        rts

load_error:

        ; STATUS bits: bit 5 = device not present, bit 4 = file not found
        rts
```

After LOAD returns, X = low byte and Y = high byte of the byte after the last loaded byte.

## Loading to a Fixed Address

To force load to a specific address regardless of the file header, use SA=1:

```asm
        lda #1
        ldx #1                  ; device: cassette
        ldy #1                  ; secondary address 1 = force address from X/Y on LOAD call
        jsr SETLFS

        lda #0
        ldx #<$4000             ; force destination low byte
        ldy #>$4000             ; force destination high byte
        jsr LOAD
```

With SA=1, X and Y on entry to LOAD specify the destination address, ignoring the file header.

## Loading from IEEE-488 Disk (Device 8)

Disk loading works the same as tape but uses device 8 and requires a Commodore disk drive on the IEEE-488 bus.

```asm
load_from_disk:

        lda #fname_end-fname-1
        ldx #<fname
        ldy #>fname
        jsr SETNAM

        lda #1
        ldx #8                  ; device: IEEE-488 disk
        ldy #0                  ; SA=0: relocating load (header address)
        jsr SETLFS

        lda #0
        jsr LOAD

        lda STATUS
        bne load_error
        rts
```

## Reading Raw Bytes via CHKIN/BASIN

For streaming frame data byte by byte (useful if data is not a PRG file or you need custom parsing):

```asm
OPEN    = $FFC0
CLOSE   = $FFC3
CHKIN   = $FFC6
CLRCHN  = $FFCC
BASIN   = $FFCF
STATUS  = $0096

read_stream:

        ; open the file first (SETNAM + SETLFS already called)
        jsr OPEN

        lda #1                  ; logical file number
        jsr CHKIN               ; set file as current input

        ldy #0

read_loop:

        jsr BASIN               ; read one byte into A
        sta dest_buf,y          ; store
        iny
        lda STATUS
        bne read_done           ; EOF or error
        cpy #$00                ; 256 bytes check
        bne read_loop
        ; advance page here if needed

read_done:

        jsr CLRCHN              ; restore default I/O
        lda #1
        jsr CLOSE               ; close logical file
        rts
```

## STATUS Word Bits

| Bit | Meaning                                   |
|-----|-------------------------------------------|
| 0   | Time-out reading IEEE-488                 |
| 1   | Time-out writing IEEE-488                 |
| 2   | Short block (tape)                        |
| 3   | Long block (tape)                         |
| 4   | Unrecoverable read error / file not found |
| 5   | Checksum error / device not present       |
| 6   | End of file (tape: EOT)                   |
| 7   | End of file (IEEE-488: EOI received)      |
Check bit 7 or 6 for normal EOF; bits 4-5 for errors.

## Typical Animation Player Load Sequence

```asm
SETLFS  = $FFBA
SETNAM  = $FFBD
LOAD    = $FFD5
STATUS  = $0096

anim_fname:

        byte "ANIM"

anim_fname_end:

load_animation:

        lda #anim_fname_end-anim_fname
        ldx #<anim_fname
        ldy #>anim_fname
        jsr SETNAM

        lda #1
        ldx #1                  ; tape
        ldy #1                  ; SA=1: load to fixed address
        jsr SETLFS

        lda #0                  ; LOAD
        ldx #<$4000             ; animation data destination
        ldy #>$4000
        jsr LOAD

        lda STATUS
        bne load_error
        rts

load_error:

        ; clear screen and print error message via CHROUT
        rts
```

## Tape File Format

The PET cassette file format consists of:

- A short leader tone
- Sync byte ($89)
- Header block: filename (16 bytes, padded with $20), start address (2 bytes LE), end address (2 bytes LE), file type (1 byte)
- File type: $00 = relocatable, $01 = sequential, $02 = non-relocatable (PRG)
- A second copy of the header (redundancy)
- Data block containing the raw binary
- A second copy of the data block

For animation data saved from an emulator or cross-tool, use type $00 (relocatable) or $02 (non-relocatable/PRG). The PET KERNAL accepts both.

## BASIC Stub with Loader

A complete BASIC stub that immediately loads animation data on RUN:

```asm
        processor 6502

SETLFS  = $FFBA
SETNAM  = $FFBD
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
        jsr SETNAM

        lda #1
        ldx #1                  ; cassette
        ldy #1                  ; fixed address load
        jsr SETLFS

        lda #0
        ldx #<$4000
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
