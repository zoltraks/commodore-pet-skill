# KERNAL File I/O

## Purpose

> **Scope:** PET file architecture, logical files, device numbers, secondary addresses, all KERNAL file routines, call sequences, STATUS byte, error handling
> **Key items:** pet_setnam/pet_setlfs wrappers, OPEN=$FFC0 (use $F524), CLOSE=$FFC3 (use $F2AC), CHKIN=$FFC6, CHKOUT=$FFC9, CLRCHN=$FFCC, CHRIN=$FFCF, CHROUT=$FFD2, LOAD=$FFD5, SAVE=$FFD8, STATUS=$0096

This file covers the complete PET 3032 KERNAL file I/O system.

The PET 3032 runs BASIC 2.0 and uses a KERNAL that was the ancestor of the C64 KERNAL.

**Critical PET difference:** The PET KERNAL does NOT have `SETNAM` ($FFBD), `SETLFS` ($FFBA), or `READST` ($FFB7) in its jump table — those are C64-only addresses. On the PET, file I/O parameters are set by writing directly to zero-page locations ($D1, $D2, $D3, $D4, $DA, $DB). The PET's `OPEN` and `CLOSE` jump table entries also include BASIC parameter parsing, so machine code must call the low-level ROM entry points ($F524, $F2AC) instead. See the wrapper routines below.

Do not use C64 addresses - they differ.

| Out of scope               | See instead        |
|----------------------------|--------------------|
| DOS commands and directory | `system/disk.md`   |
| Complete DASM examples     | `example/file.md`  |
| KERNAL jump table overview | `system/kernal.md` |
| Safe memory zones          | `system/memory.md` |

## Contents

| Section                     | Line | What it covers                                                                                     |
|-----------------------------|------|----------------------------------------------------------------------------------------------------|
| File Architecture Overview  | 40   | Logical files, device numbers, secondary addresses, file types                                     |
| KERNAL Routine Reference    | 139  | pet_setnam, pet_setlfs, OPEN, CLOSE, CHKIN, CHKOUT, CLRCHN, CHRIN, CHROUT, LOAD, SAVE, CLALL, STOP |
| Call Sequences              | 821  | Open-read, open-write, load PRG, save PRG patterns                                                 |
| EOF Detection               | 1009 | STATUS bit 6 (disk), STATUS bit 4 (cassette)                                                       |
| Error Handling              | 1061 | OPEN error codes, device not present, file not found                                               |
| PETSCII Filename Rules      | 1123 | Uppercase, wildcards, drive prefix                                                                 |
| Tape File Notes             | 1149 | Cassette SA values, sequential vs PRG                                                              |
| Multiple Open Files         | 1161 | Table limits, safe LFN allocation                                                                  |
| Chunk-Based Partial Reading | 1190 | Re-open and skip to offset, read fixed-size chunks, STATUS-based EOF                               |
| No Backward Seek            | 1308 | CBM-DOS cannot seek backward; re-open and skip forward for scroll-up                               |
| Zero-Page Save and Restore  | 1336 | restore_zp pattern: save $FB-$FE on entry, restore before each KERNAL call                         |
| Troubleshooting             | 1382 | Common bugs and their causes                                                                       |

## File Architecture Overview

The PET KERNAL implements a uniform byte-stream I/O model.

Every I/O device - keyboard, screen, cassette, IEEE-488 disk, printer - is addressed through the same set of KERNAL calls.

The model has three layers:

- **Logical file numbers** - a number chosen by your program (1-127) to identify an open connection
- **Device numbers** - a hardware address identifying the physical device
- **Secondary addresses** - a sub-channel within the device (meaning varies per device)

### Logical File Numbers

A logical file number (LFN) is a handle your program uses to refer to an open connection.

Choose any number from 1 to 127.

Numbers 128-255 are reserved.

Up to 10 logical files may be open simultaneously (limited by KERNAL internal tables at $0251-$026E).

You use the same LFN in CHKIN, CHKOUT, and CLOSE calls.

### Device Numbers

| Number | Device             | Bus              |
|--------|--------------------|------------------|
| 0      | Keyboard           | Internal         |
| 1      | Cassette #1        | Internal (PIA 1) |
| 2      | Cassette #2        | VIA user port    |
| 3      | Screen             | Internal         |
| 4      | Printer #1         | IEEE-488         |
| 5      | Printer #2         | IEEE-488         |
| 6      | Plotter            | IEEE-488         |
| 7      | (reserved)         | IEEE-488         |
| 8      | Disk drive #1      | IEEE-488         |
| 9      | Disk drive #2      | IEEE-488         |
| 10-15  | Additional devices | IEEE-488         |

Device numbers 4-15 are addressed over the IEEE-488 bus.

Device numbers 8 and 9 are the standard primary and secondary disk drives.

### Secondary Addresses

Secondary addresses (SA) carry different meanings depending on the device.

**Cassette (devices 1-2):**

| SA  | Meaning                  |
|-----|--------------------------|
| 0   | Read (load)              |
| 1   | Write (save, append off) |
| 2   | Write with EOT marker    |

**Disk drives (devices 8-15):**

| SA   | Meaning                                   |
|------|-------------------------------------------|
| 0    | Load (PRG read, relocating)               |
| 1    | Save (PRG write)                          |
| 2-14 | Sequential or relative file data channel  |
| 15   | Command channel (DOS commands and status) |

SA 15 is the command channel - always open it to check and send DOS commands.

SA 0 and 1 are reserved for program (PRG) file load and save.

Use SA 2-14 for sequential data files.

### Sequential vs Program Files

**Program files (PRG):** Begin with a 2-byte little-endian load address.

LOAD reads the address and places data starting there.

SAVE writes the address automatically from the start parameter.

Use SA 0 (read) and SA 1 (write) for PRG files.

**Sequential files (SEQ):** Raw byte streams with no embedded address.

Access via CHKIN/CHRIN for reading and CHKOUT/CHROUT for writing.

Use SA 2-14 for sequential files.

### BASIC Commands and KERNAL Calls

| BASIC Statement        | KERNAL calls used (from ML)      |
|------------------------|----------------------------------|
| `OPEN n,dev,sa,"name"` | pet_setnam, pet_setlfs, pet_open |
| `CLOSE n`              | pet_close                        |
| `INPUT# n, var`        | CHKIN, CHRIN (loop), CLRCHN      |
| `PRINT# n, data`       | CHKOUT, CHROUT (loop), CLRCHN    |
| `GET# n, var`          | CHKIN, CHRIN, CLRCHN             |
| `LOAD "name", dev`     | pet_setnam, pet_setlfs, LOAD     |
| `SAVE "name", dev`     | pet_setnam, pet_setlfs, SAVE     |

## KERNAL Routine Reference

### PET File I/O Wrapper Routines

The PET 3032 KERNAL lacks `SETNAM`, `SETLFS`, and `READST` (those are C64-only). Additionally, the PET's `OPEN` ($FFC0) and `CLOSE` ($FFC3) jump table entries include BASIC parameter parsing, making them unsafe to call directly from machine code.

Use these wrapper routines instead. They set the PET's zero-page file I/O locations directly and call the low-level ROM logic:

```asm
; ---- PET file I/O zero-page locations ----
PET_FNLEN       = $D1        ; filename length
PET_LA          = $D2        ; logical file number
PET_SA          = $D3        ; secondary address
PET_DEV         = $D4        ; device number
PET_FNADR_LO    = $DA        ; filename address low
PET_FNADR_HI    = $DB        ; filename address high
PET_OPEN_LOGIC  = $F524      ; OPEN past BASIC parsing (after JSR $F4CE)
PET_CLOSE_LOGIC = $F2AC      ; CLOSE past BASIC parsing (after JSR $F4CE)
STATUS          = $0096      ; I/O status byte (read directly, no READST)

; pet_setnam: A=length, X=addr_lo, Y=addr_hi
pet_setnam:
        sta PET_FNLEN
        stx PET_FNADR_LO
        sty PET_FNADR_HI
        rts

; pet_setlfs: A=LFN, X=DEV, Y=SA
pet_setlfs:
        sta PET_LA
        stx PET_DEV
        sty PET_SA
        rts

; pet_open: call PET OPEN logic (params already set up)
; Returns carry clear on success, set on error.
; The PET OPEN routine jumps to BASIC error handler on failure
; instead of using carry. We detect success by checking if
; $AE (file count) increased.
pet_open:
        lda $AE
        pha
        jsr PET_OPEN_LOGIC
        pla
        cmp $AE         ; old vs new: C=0 if old < new (increased)
        bcc po_ok       ; file count increased -> success
        sec
        rts
po_ok:
        clc
        rts

; pet_close: A = logical file number to close
pet_close:
        sta PET_LA
        jsr PET_CLOSE_LOGIC
        rts
```

### pet_setnam - Set Filename

**Purpose:** Store a pointer to the filename and its length in KERNAL workspace.

Must be called before pet_open, LOAD, or SAVE.

**Inputs:**

| Register | Value                         |
|----------|-------------------------------|
| A        | Filename length (0 = no name) |
| X        | Low byte of filename address  |
| Y        | High byte of filename address |

**Outputs:** None.

**Side effects:** Stores length at `$D1` and address at `$DA-$DB` in KERNAL workspace.

**Notes:**

- The filename must be in PETSCII uppercase.
- For cassette files with no name, call with A=0; X and Y are ignored.
- For disk files the filename must always be provided.
- The filename string does not need a null terminator.
- This is a wrapper routine, not a KERNAL jump table entry. The PET does not have SETNAM.

```asm
        processor 6502

fname:

        byte "MYDATA"

fend:

        lda #fend-fname         ; length = 6
        ldx #<fname             ; low byte of filename address
        ldy #>fname             ; high byte of filename address
        jsr pet_setnam
```

---

### pet_setlfs - Set Logical File Parameters

**Purpose:** Store the logical file number, device number, and secondary address.

Must be called after pet_setnam and before pet_open, LOAD, or SAVE.

**Inputs:**

| Register | Value               |
|----------|---------------------|
| A        | Logical file number |
| X        | Device number       |
| Y        | Secondary address   |

**Outputs:** None.

**Side effects:** Stores parameters at `$D2` (LFN), `$D3` (SA), `$D4` (device) in KERNAL workspace.

**Notes:**

- The logical file number must be unique among all currently open files.
- For LOAD and SAVE the LFN is ignored by some KERNAL versions; still provide a valid value.
- SA 255 ($FF) is sometimes used as "no secondary address" for certain devices.
- This is a wrapper routine, not a KERNAL jump table entry. The PET does not have SETLFS.

```asm
        lda #2                  ; logical file number 2
        ldx #8                  ; device 8 (disk drive)
        ldy #2                  ; secondary address 2 (sequential data channel)
        jsr pet_setlfs
```

---

### pet_open - Open Logical File

**Purpose:** Open a logical file using parameters set by pet_setlfs and pet_setnam.

**Inputs:** None (uses KERNAL workspace set by pet_setnam and pet_setlfs).

**Outputs:**

| Register | Value                  |
|----------|------------------------|
| C        | 0 = success, 1 = error |

**Registers used:** A, X, Y.

**Side effects:**

- Adds the file to the KERNAL logical file table.
- For disk: sends OPEN message over IEEE-488 to the drive.
- For cassette: prepares tape I/O buffers.

**Error handling:**

The PET's OPEN routine does NOT use carry for error reporting. On failure, it jumps directly to the BASIC error handler (`$CE03`), which prints `?SYNTAX ERROR` or similar and returns to BASIC. The `pet_open` wrapper detects success by checking if `$AE` (open file count) increased. If OPEN fails by jumping to the error handler, the wrapper never returns — the program crashes to BASIC.

**Notes:**

- Always call pet_setnam and pet_setlfs before pet_open.
- pet_open does not set the input or output channel - call CHKIN or CHKOUT next.
- For SA=15 (command channel), OPEN sends the filename string as a DOS command.
- After OPEN with SA=15 and no filename, the channel is open for reading drive status.
- This wrapper calls $F524 (low-level OPEN logic), NOT $FFC0 (which includes BASIC parsing).

```asm
        jsr pet_open            ; open the file
        bcc open_ok             ; carry clear = success
        jmp open_error          ; carry set = error (file count did not increase)

open_ok:
```

---

### pet_close - Close Logical File

**Purpose:** Close a logical file and release its resources.

**Inputs:**

| Register | Value               |
|----------|---------------------|
| A        | Logical file number |

**Outputs:** None.

**Registers used:** A, X, Y.

**Side effects:**

- Removes the file from the KERNAL logical file table.
- For disk: sends CLOSE command over IEEE-488 to the drive.
- For cassette: writes end-of-tape marker if opened for write.

**Notes:**

- Always close every logical file you open.
- Failing to close files leaves them in the KERNAL table and may cause "too many files" errors.
- If a file is the current input or output channel, call CLRCHN before CLOSE.
- CLALL closes all files; use CLOSE for targeted cleanup.

```asm
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see above)

        lda #2                  ; close logical file 2
        jsr pet_close
```

---

### CHKIN - Set Input Channel

**Address:** `$FFC6` (calls through vector at `$031E`)

**Purpose:** Redirect all subsequent CHRIN calls to read from the specified logical file.

Must be called after OPEN.

**Inputs:**

| Register | Value               |
|----------|---------------------|
| X        | Logical file number |

**Outputs:**

| Register | Value                  |
|----------|------------------------|
| C        | 0 = success, 1 = error |

**Registers used:** A, X.

**Side effects:** Changes the KERNAL current input device pointer.

**Notes:**

- Only one input channel is active at a time.
- Calling CHKIN again redirects input to the new file.
- Always call CLRCHN to restore keyboard input when done reading.
- CHKIN does not clear STATUS ($0096); check it after each CHRIN.

```asm
CHKIN   = $FFC6

        ldx #2                  ; logical file number 2
        jsr CHKIN
        bcc chkin_ok            ; C=1 means error: file not open or not readable

chkin_ok:
```

---

### CHKOUT - Set Output Channel

**Address:** `$FFC9` (calls through vector at `$0320`)

**Purpose:** Redirect all subsequent CHROUT calls to write to the specified logical file.

Must be called after OPEN.

**Inputs:**

| Register | Value               |
|----------|---------------------|
| X        | Logical file number |

**Outputs:**

| Register | Value                  |
|----------|------------------------|
| C        | 0 = success, 1 = error |

**Registers used:** A, X.

**Side effects:** Changes the KERNAL current output device pointer.

**Notes:**

- Only one output channel is active at a time.
- Calling CHKOUT again redirects output to the new file.
- Always call CLRCHN to restore screen output when done writing.
- CHROUT calls after CHKOUT write to the file, not to the screen.

```asm
CHKOUT  = $FFC9

        ldx #2                  ; logical file number 2
        jsr CHKOUT
        bcc chkout_ok           ; C=1 means error

chkout_ok:
```

---

### CLRCHN - Clear I/O Channels

**Address:** `$FFCC` (calls through vector at `$0322`)

**Purpose:** Restore the default input (keyboard) and default output (screen).

**Inputs:** None.

**Outputs:** None.

**Registers used:** A, X.

**Side effects:** Resets KERNAL current input to device 0 (keyboard) and current output to device 3 (screen).

**Notes:**

- CLRCHN does not close any files.
- Always call CLRCHN after a sequence of CHKIN/CHRIN or CHKOUT/CHROUT.
- Failure to call CLRCHN will cause subsequent CHROUT calls to still go to the file.
- If you call CHROUT to print an error message after a write sequence, call CLRCHN first.

```asm
CLRCHN  = $FFCC

        jsr CLRCHN              ; restore keyboard input, screen output
```

---

### CHRIN - Read Byte from Input Channel

**Address:** `$FFCF` (calls through vector at `$0324`)

**Also called:** BASIN (the PET KERNAL name in some documentation)

**Purpose:** Read one byte from the current input channel.

**Inputs:** None.

**Outputs:**

| Register | Value                            |
|----------|----------------------------------|
| A        | Byte read                        |
| C        | 1 if STATUS error (check STATUS) |

**Registers used:** A, Y.

**Side effects:** Updates STATUS byte at `$0096`.

**Notes:**

- Call CHKIN first to select a file; otherwise reads from keyboard.
- For keyboard input, CHRIN waits for a full line and returns one character per call.
- For disk/cassette, CHRIN returns the next byte in the stream.
- After each CHRIN call, read STATUS to check for EOF or errors.
- STATUS bit 6 = EOF on tape; STATUS bit 7 = EOI (EOF) on IEEE-488.
- When STATUS bit 4 is set, an unrecoverable read error occurred.

```asm
CHRIN   = $FFCF
STATUS  = $0096

        jsr CHRIN               ; read one byte
        sta byte_buf            ; store byte before checking STATUS
        lda STATUS              ; check status AFTER storing
        bne got_eof_or_error    ; non-zero STATUS = stop reading
        jmp read_loop           ; process byte_buf...

got_eof_or_error:       ; byte_buf valid on disk EOF (bit 7=EOI); may be invalid on error (bits 0-5)
```

---

### CHROUT - Write Byte to Output Channel

**Address:** `$FFD2` (calls through vector at `$0326`)

**Also called:** BSOUT in some documentation

**Purpose:** Write one byte to the current output channel.

**Inputs:**

| Register | Value                   |
|----------|-------------------------|
| A        | Byte to write (PETSCII) |

**Outputs:** None.

**Registers used:** None (A is consumed).

**Side effects:** Updates STATUS byte at `$0096`.

**Notes:**

- Without calling CHKOUT first, CHROUT writes to the screen.
- After calling CHKOUT, CHROUT writes to the selected file.
- For disk sequential files, any byte value may be written.
- For cassette, any byte value may be written.
- Check STATUS after every CHROUT when writing to disk to detect write errors.
- STATUS bit 1 = write timeout on IEEE-488.

```asm
CHROUT  = $FFD2
STATUS  = $0096

        lda #'H'                ; PETSCII 'H'
        jsr CHROUT
        lda STATUS
        bne write_error
```

---

### STATUS - Read I/O Status

**Address:** `$0096` (zero page, read directly)

**Purpose:** Return the current value of the STATUS byte.

The PET does NOT have a `READST` KERNAL call (that is C64-only at `$FFB7`). Read the STATUS byte directly from zero page.

**Inputs:** None.

**Outputs:**

| Register | Value               |
|----------|---------------------|
| A        | STATUS byte ($0096) |

**Registers used:** A.

**Side effects:** None.

**Notes:**

- STATUS is directly readable at zero page address `$0096`.
- STATUS is set by CHRIN, CHROUT, LOAD, and SAVE.
- STATUS is cleared at the start of CHKIN and CHKOUT.
- Reading STATUS does not clear it.

```asm
STATUS  = $0096

        lda STATUS              ; A = STATUS byte
        and #$BF                ; mask out bit 6 (tape EOF, not meaningful on disk)
        bne error_or_eof
```

**STATUS Byte Bit Meanings:**

| Bit | Mask | Meaning                                   | Device         |
|-----|------|-------------------------------------------|----------------|
| 0   | $01  | Read timeout (device did not respond)     | IEEE-488       |
| 1   | $02  | Write timeout (device did not respond)    | IEEE-488       |
| 2   | $04  | Short block                               | Cassette       |
| 3   | $08  | Long block                                | Cassette       |
| 4   | $10  | Unrecoverable read error / file not found | Cassette, disk |
| 5   | $20  | Checksum error / device not present       | Cassette       |
| 6   | $40  | End of file (tape EOT)                    | Cassette       |
| 7   | $80  | End of file (IEEE-488 EOI received)       | IEEE-488       |

For disk EOF detection: check bit 7 ($80).

For cassette EOF detection: check bit 6 ($40).

For any error: check bits 0-5.

---

### LOAD - Load File to Memory

**Address:** `$FFD5` (calls through vector at `$0330`)

**Purpose:** Load or verify a file into memory.

Must call pet_setnam and pet_setlfs first.

**Inputs:**

| Register | Value                                          |
|----------|------------------------------------------------|
| A        | 0 = load, 1 = verify (compare to memory)       |
| X        | Load address low byte (if SA=1 on pet_setlfs)  |
| Y        | Load address high byte (if SA=1 on pet_setlfs) |

**Outputs:**

| Register | Value                                       |
|----------|---------------------------------------------|
| C        | 0 = success, 1 = error                      |
| A        | Error code if C=1                           |
| X        | Low byte of address after last loaded byte  |
| Y        | High byte of address after last loaded byte |

**Registers used:** A, X, Y.

**Side effects:** Overwrites memory at the load destination. Sets STATUS.

**Secondary address behavior:**

- SA=0: Relocating load - the file's first two bytes are the load address (PRG format). X and Y on entry are ignored.
- SA=1: Non-relocating load - X/Y on entry specify the destination. The file's first two bytes are still read but discarded.

**Notes:**

- LOAD is a blocking call: it does not return until the entire file is loaded.
- For cassette: the KERNAL displays "SEARCHING FOR name" and "LOADING" messages on screen.
- For disk: no messages are displayed.
- Do not call OPEN before LOAD - LOAD handles the file open internally.
- After LOAD returns, X/Y point to the first byte after the loaded data.

> **ML caveat:** The `$FFD5` jump entry re-parses BASIC and wipes the zero-page parameters (see `system/load.md` — verified by disassembly and a live xpet run). From machine code, enter the low-level LOAD at **`$F3C9`** (past `JSR $F43E`), with `$9D` (VERCK) = 0 for load / 1 for verify. Note that on hard errors (file-not-found, device-not-present) the PET LOAD prints the error and returns to BASIC READY rather than returning to your caller — so unlike the C64 you cannot always trap the error via the carry flag; check `STATUS` after a load that returns.

```asm
; PET does not have SETLFS - use pet_setlfs wrapper (see above)
; PET does not have SETNAM - use pet_setnam wrapper (see above)
LOAD    = $F3C9         ; low-level LOAD past BASIC parse (NOT the $FFD5 jump entry)
VERCK   = $9D           ; 0 = load, 1 = verify
STATUS  = $0096

        lda #6                  ; Step 1: set filename (length 6)
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #1                  ; Step 2: set file parameters (LFN, ignored by LOAD)
        ldx #8                  ; device: disk drive
        ldy #0                  ; SA=0: relocating load (use address from file)
        jsr pet_setlfs

        lda #0                  ; Step 3: VERCK = 0 -> load (not verify)
        sta VERCK
        jsr LOAD                ; enter past parse
        lda STATUS              ; non-zero = error (on hard errors LOAD aborts to BASIC)
        bne load_error
        rts                     ; X/Y now = first byte past end of loaded data

load_error:

        rts                     ; A = error code

fname:

        byte "PLAYER"
```

---

### SAVE - Save Memory to File

**Address:** `$FFD8` (calls through vector at `$0332`)

**Purpose:** Save a range of memory to a file.

Must call pet_setnam and pet_setlfs first.

**Inputs:**

| Register | Value                                                       |
|----------|-------------------------------------------------------------|
| A        | Zero-page address of a 2-byte word containing start address |
| X        | Low byte of end address plus 1                              |
| Y        | High byte of end address plus 1                             |

**Outputs:**

| Register | Value                  |
|----------|------------------------|
| C        | 0 = success, 1 = error |
| A        | Error code if C=1      |

**Registers used:** A, X, Y.

**Side effects:** Writes file to device. Sets STATUS.

> **Critical ML caveat — the A/X/Y convention below is C64, not PET.** On the PET, `$FFD8` SAVE is a BASIC-command entry: it begins with `JSR $F43E` (re-parses BASIC, wipes `$D1`/`$D3`/`$D4`), and the underlying routine is wired to save the **BASIC-program range** — it takes the start/end from the BASIC pointers (`$28/$29` start, `$2A/$2B` end, via `$F68D`/`$FB76`), *not* from `A`/`X`/`Y`. There is no clean single-register PET entry that saves an arbitrary memory range. Verified against `kernal-2.901465-03`.
>
> **To save arbitrary ML data on the PET, use one of:**
> 1. **Recommended — write the file yourself with OPEN + CHKOUT + CHROUT** (see the sequential-file write pattern earlier in this file). This gives full control over the bytes and works from pure ML.
> 2. Temporarily set the BASIC pointers `$28/$29` (start) and `$2A/$2B` (end) to your range, call the low-level SAVE past the parse (`$F6A1`), then restore them — fiddly and clobbers BASIC state; test under VICE before relying on it.
>
> The C64-style block below (`A` = ZP start pointer, `X`/`Y` = end+1) is retained only to show the interface people expect from the C64 — **it does not work as-is from ML on the PET.**

```asm
; NOTE: C64 convention shown for reference -- does NOT work from PET ML.
; For PET, write data with OPEN + CHROUT (see sequential write above).
SAVE    = $FFD8         ; PET: BASIC-command entry, re-parses BASIC text
STATUS  = $0096

save_start = $FB             ; zero page: two bytes for start address

        lda #<$4000             ; Store start address in ZP
        sta save_start
        lda #>$4000
        sta save_start+1

        lda #6                  ; Set filename
        ldx #<sname
        ldy #>sname
        jsr pet_setnam

        lda #1                  ; Set file parameters: logical file number
        ldx #8                  ; device: disk
        ldy #1                  ; SA=1 for save
        jsr pet_setlfs

        lda #save_start         ; (C64 convention) A = ZP ptr, X/Y = end+1
        ldx #<$5000             ; end address + 1 (low)
        ldy #>$5000             ; end address + 1 (high)
        jsr SAVE
        bcs save_error
        rts

save_error:

        rts

sname:

        byte "PLAYER"
```

---

### CLALL - Close All Files

**Address:** `$FFE7` (calls through vector at `$032C`)

**Purpose:** Close all logical files and restore default I/O channels.

**Inputs:** None.

**Outputs:** None.

**Registers used:** A, X.

**Side effects:** Removes all files from the KERNAL table. Restores keyboard input and screen output.

**Notes:**

- CLALL is equivalent to calling CLRCHN followed by CLOSE for every open file.
- Use CLALL on program exit or error recovery to prevent resource leaks.
- CLALL does not send any close commands to disk drives - the drives may leave files in an indeterminate state if you call CLALL without first closing individual files.
- For clean disk shutdown, close each file individually with CLOSE before calling CLALL.

```asm
CLALL   = $FFE7

        jsr CLALL               ; close all files, restore I/O
```

---

### STOP - Test STOP Key

**Address:** `$FFE1` (calls through vector at `$0328`)

**Purpose:** Test whether the STOP (RUN/STOP) key is currently pressed.

**Inputs:** None.

**Outputs:**

| Register | Value                         |
|----------|-------------------------------|
| Z        | 1 (BEQ taken) if STOP pressed |

**Registers used:** None (flags affected).

**Notes:**

- The KERNAL polls STOP automatically during I/O operations.
- For long file operations, poll STOP in your own loop if you want to allow user interruption.
- Pressing STOP during LOAD or SAVE via KERNAL will abort the operation.

```asm
STOP    = $FFE1

write_loop:             ; Poll STOP during a long file write loop

        jsr STOP                ; ... write one byte ...
        beq user_abort          ; STOP pressed, else continue loop
```

## Call Sequences

### Open a File for Reading

The correct sequence for reading a sequential file:

1. Call pet_setnam with filename.
2. Call pet_setlfs with LFN, device, SA.
3. Call OPEN.
4. Call CHKIN with LFN to set as input channel.
5. Loop: call CHRIN, check STATUS after each byte.
6. Call CLRCHN to restore input.
7. Call CLOSE with LFN.

```asm
; PET does not have SETNAM - use pet_setnam wrapper (see above)
; PET does not have SETLFS - use pet_setlfs wrapper (see above)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see above)
CHKIN   = $FFC6
CHRIN   = $FFCF
CLRCHN  = $FFCC
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see above)
STATUS  = $0096

; --- read_file: reads sequential file into dest_buf ---
read_file:              ; Expects: fname/fend defined, dest_buf defined

        lda #fend-fname
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #2                  ; logical file number
        ldx #8                  ; device: disk
        ldy #2                  ; SA=2: sequential data channel
        jsr pet_setlfs

        jsr pet_open
        bcs read_open_err

        ldx #2
        jsr CHKIN
        bcs read_chkin_err

        ldy #0

read_byte:

        jsr CHRIN               ; read one byte into A
        sta dest_buf,y          ; store at dest_buf + y
        iny
        lda STATUS
        bne read_done           ; STATUS != 0 means EOF or error
        cpy #$00                ; wrap at 256 - extend for larger buffers
        bne read_byte

read_done:

        jsr CLRCHN              ; restore keyboard input
        lda #2
        jsr pet_close
        rts

read_open_err:
read_chkin_err:

        jsr CLRCHN
        rts
```

### Open a File for Writing

The correct sequence for writing a sequential file:

1. Call pet_setnam with filename. For disk, include `,S,W` in the filename string (e.g. `"OUTPUT,S,W"`). Without `,W`, CBM DOS defaults to read mode and the write will fail.
2. Call pet_setlfs with LFN, device, SA (use SA 2-14 for sequential).
3. Call OPEN.
4. Call CHKOUT with LFN to set as output channel.
5. Loop: call CHROUT, check STATUS after each byte.
6. Call CLRCHN to restore output.
7. Call CLOSE with LFN.

```asm
; PET does not have SETNAM - use pet_setnam wrapper (see above)
; PET does not have SETLFS - use pet_setlfs wrapper (see above)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see above)
CHKOUT  = $FFC9
CHROUT  = $FFD2
CLRCHN  = $FFCC
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see above)
STATUS  = $0096

write_file:

        lda #wfend-wfname
        ldx #<wfname
        ldy #>wfname
        jsr pet_setnam

        lda #3                  ; logical file number
        ldx #8                  ; device: disk
        ldy #2                  ; SA=2: sequential channel (write creates new file)
        jsr pet_setlfs

        jsr pet_open
        bcs write_open_err

        ldx #3
        jsr CHKOUT
        bcs write_chkout_err

        ldx #0

write_byte:

        lda src_buf,x           ; load byte from source buffer
        jsr CHROUT              ; write to file
        lda STATUS
        bne write_done          ; STATUS != 0 = error
        inx
        cpx #src_len
        bne write_byte

write_done:

        jsr CLRCHN
        lda #3
        jsr pet_close
        rts

write_open_err:
write_chkout_err:

        jsr CLRCHN
        rts
```

### Load a Program File

Do not call OPEN before LOAD.

LOAD handles the file open/close internally.

```asm
        lda #fname_len          ; Set filename
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #1                  ; SA=0: relocating load (use address from file header)
        ldx #8
        ldy #0
        jsr pet_setlfs

        lda #0                  ; VERCK ($9D) = 0 -> load, 1 = verify
        sta $9D
        jsr LOAD                ; LOAD = $F3C9 (low-level, past BASIC parse) -- NOT $FFD5
        bcs load_err            ; loaded successfully; X/Y = end+1
```

### Save a Program File

Do not call OPEN before SAVE.

> **PET:** this is the C64 SAVE convention and does **not** work from PET ML — `$FFD8` re-parses BASIC and saves the BASIC-program range, not an arbitrary A/X/Y range. To save arbitrary data on the PET, write it yourself with OPEN + CHKOUT + CHROUT (see the sequential-file write above). Block kept for C64 reference only.

```asm
save_ptr = $FB                  ; ZP: store start address here

        lda #<start_addr
        sta save_ptr
        lda #>start_addr
        sta save_ptr+1

        lda #fname_len
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #1
        ldx #8
        ldy #1                  ; SA=1 for save
        jsr pet_setlfs

        lda #save_ptr           ; (C64 convention) ZP address (not the value)
        ldx #<end_addr
        ldy #>end_addr
        jsr SAVE                ; PET: $FFD8 re-parses BASIC -- does not save this range
        bcs save_err
```

## EOF Detection

### Disk (IEEE-488) EOF

After each CHRIN call, check STATUS bit 7:

```asm
        jsr CHRIN
        sta byte_buf
        lda STATUS
        and #$80                ; bit 7 = EOI on IEEE-488
        bne eof_reached
```

STATUS may be non-zero for both EOF and errors.

Check bit 7 specifically for clean EOF.

Check bits 0-5 for errors.

### Cassette EOF

After each CHRIN call, check STATUS bit 6:

```asm
        jsr CHRIN
        sta byte_buf
        lda STATUS
        and #$40                ; bit 6 = tape EOT
        bne eof_reached
```

### Combined Check (Disk and Cassette)

```asm
check_eof:

        lda STATUS
        beq read_ok             ; zero = no EOF, no error
        and #$C0                ; bits 6 and 7 = EOF conditions
        bne is_eof
        jmp read_error          ; bits 0-5 set without 6 or 7 = error

is_eof:

        rts                     ; normal end of file

read_ok:

        rts
```

## Error Handling

### OPEN Error Codes

Errors returned in A when OPEN sets C=1:

| Code | Meaning                                          |
|------|--------------------------------------------------|
| 1    | Too many files open (10 max)                     |
| 2    | Logical file number already in use               |
| 3    | File not open (internal error)                   |
| 4    | File not found (cassette)                        |
| 5    | Device not present (no response on IEEE-488)     |
| 6    | File not open for input (wrong SA for direction) |
| 7    | File not open for output                         |
| 8    | Missing filename (disk requires a name)          |
| 9    | Illegal device number                            |

### Detecting Device Not Present

For IEEE-488 devices, if the device does not respond, STATUS bit 1 will be set after a write timeout, or bit 0 after a read timeout.

```asm
        jsr pet_open
        bcs open_failed
        lda STATUS              ; check STATUS for timeout
        and #$03                ; bits 0 and 1: read/write timeout
        bne device_not_present
```

### File Not Found on Disk

Disk drives report file-not-found through the DOS error channel (SA=15), not through the KERNAL STATUS byte on OPEN.

After OPEN, open the command channel and read it to check:

```asm
        lda STATUS              ; After OPEN for a data file
        bne open_hardware_error ; KERNAL-level hardware error

        lda #0                  ; Open command channel; no filename for status read
        jsr pet_setnam
        lda #$0F                ; logical file 15
        ldx #8                  ; same drive
        ldy #$0F                ; SA=15 = command channel
        jsr pet_setlfs
        jsr pet_open                ; then read error string via CHKIN/CHRIN; see system/disk.md
```

### Resource Leak Prevention

Always close files on all code paths, including error paths.

```asm
safe_close:             ; Safe cleanup pattern

        jsr CLRCHN              ; always restore I/O first
        lda #2                  ; close logical file 2
        jsr pet_close               ; even if it wasn't fully opened
        rts                     ; CLOSE is a no-op if file is not open
```

## PETSCII Filename Rules

Filenames on Commodore disk drives follow these rules:

- Maximum 16 characters.
- Characters must be PETSCII uppercase (the default character set).
- Spaces are allowed but may cause issues with some DOS versions.
- Wildcards: `*` matches any sequence of characters; `?` matches one character.
- Drive prefix: `0:` selects drive 0 on a dual-drive unit; `1:` selects drive 1.
- File type suffix for OPEN: `,S` for sequential, `,P` for program, `,R` for relative.
- File mode suffix for OPEN: `,R` for read, `,W` for write.

Full filename format for OPEN:

```
drive:filename,type,mode
```

Examples:

- `"0:MYFILE,S,R"` - read sequential file MYFILE from drive 0
- `"0:OUTPUT,S,W"` - write new sequential file OUTPUT on drive 0
- `"0:PROG,P,R"` - read program file (rarely needed; use LOAD instead)

For LOAD and SAVE, the filename is just the name without type or mode.

## Tape File Notes

Cassette files do not use filenames for addressing.

The KERNAL searches for a file by reading tape until it finds a header matching the given name.

If no name is given (A=0 in pet_setnam), the KERNAL loads the next file regardless of its header name.

Cassette write (SA=1) always appends at the current tape position.

There is no way to overwrite an existing tape file; the old data remains on tape.

## Multiple Open Files

Up to 10 logical files may be open simultaneously.

A common pattern is to have a data channel and a command channel open at the same time:

```asm
; Open data file on LFN 2, SA 2
; Open command channel on LFN 15, SA 15

        lda #5                  ; File 1: data
        ldx #<dfname
        ldy #>dfname
        jsr pet_setnam
        lda #2
        ldx #8
        ldy #2
        jsr pet_setlfs
        jsr pet_open

        lda #0                  ; File 2: command channel (no filename for status)
        jsr pet_setnam
        lda #$0F
        ldx #8
        ldy #$0F
        jsr pet_setlfs
        jsr pet_open                ; LFN 2=data, LFN 15=cmd; CHKIN/CHRIN per channel; CLRCHN after each switch
```

## Chunk-Based Partial Reading

Files larger than available RAM cannot be read in a single pass. CBM-DOS sequential files have no seek command -- the drive delivers bytes in order from the start of the file. To view or process a file in chunks, re-open the file for each chunk and skip forward to the desired offset.

**Pattern: load a chunk at an arbitrary offset**

```asm
; view_chunk_base = byte offset to start reading from
; view_chunk = buffer (e.g. 2048 bytes)
; view_chunk_len = bytes actually read (set by this routine)

load_chunk:

        jsr restore_zp
        jsr CLALL
        lda fname_len
        ldx #<fname
        ldy #>fname
        jsr pet_setnam
        lda #LFN
        ldx #8                  ; device 8
        ldy #0                  ; SA=0 (read)
        jsr pet_setlfs
        jsr restore_zp
        jsr pet_open
        bcc lc_opened
        jmp lc_err
lc_opened:

        jsr restore_zp
        ldx #LFN
        jsr CHKIN

        ; Skip view_chunk_base bytes
        lda view_chunk_base
        sta skip_lo
        lda view_chunk_base+1
        sta skip_hi

lc_skip:

        lda skip_lo
        ora skip_hi
        beq lc_read_init
        jsr CHRIN
        lda STATUS
        bne lc_read_init       ; EOF during skip
        lda skip_lo
        bne lc_skip_dec
        dec skip_hi
lc_skip_dec:

        dec skip_lo
        jmp lc_skip

lc_read_init:

        lda #0
        sta view_chunk_len
        sta view_chunk_len+1
        lda #<view_chunk
        sta sp_lo
        lda #>view_chunk
        sta sp_hi
        ldy #0

lc_read:

        ; Check if buffer is full
        lda view_chunk_len+1
        cmp #>CHUNK_SIZE
        bcc lc_read_byte
        bne lc_done
        lda view_chunk_len
        cmp #<CHUNK_SIZE
        bcs lc_done
lc_read_byte:

        jsr CHRIN
        sta (sp_lo),y
        inc view_chunk_len
        bne lc_chk
        inc view_chunk_len+1
lc_chk:

        lda STATUS
        bne lc_eof             ; EOF or error
        iny
        bne lc_read
        inc sp_hi
        jmp lc_read

lc_eof:

        ; STATUS non-zero: EOF reached
        ; view_chunk_len holds bytes actually read
lc_done:

        jsr restore_zp
        jsr CLRCHN
        lda #LFN
        jsr pet_close
        clc
        rts
lc_err:

        ; set error status, return carry set
        sec
        rts
```

Key points:

- The file is opened and closed for each chunk. No channel stays open between chunks.
- `STATUS` is checked after every `CHRIN`. A non-zero `STATUS` means EOF or error; stop reading.
- `view_chunk_len` records how many bytes were actually read, which may be less than `CHUNK_SIZE` at EOF.
- The skip loop reads and discards bytes one at a time. This is slow for large offsets but is the only way to reach an arbitrary position in a CBM-DOS sequential file.

## No Backward Seek

CBM-DOS sequential files can only be read forward. There is no command to move the read position backward. To scroll backward through a file that was read in chunks, re-open the file and skip forward to the earlier offset.

**Scroll-up pattern:**

```asm
; User scrolled up past the current chunk's start.
; view_top < view_chunk_base, so reload from view_top.

scroll_up_reload:

        lda view_top
        sta view_chunk_base
        lda view_top+1
        sta view_chunk_base+1
        jsr load_chunk         ; re-open, skip to view_chunk_base, read
        rts
```

This is the documented trade-off of chunk-based loading on CBM-DOS:

- Scrolling forward within the current chunk: no disk I/O.
- Scrolling forward past the chunk end: load the next chunk (skip is zero or small if chunks are contiguous).
- Scrolling backward past the chunk start: re-open the file and skip from byte 0 to the new offset. This is expensive for large files.

To minimize backward skips, make the chunk larger than one screenful. A 2048-byte chunk covers many screen rows, so most scrolling stays within the chunk and requires no disk I/O.

## Zero-Page Save and Restore

KERNAL I/O routines (`OPEN`, `CLOSE`, `CHKIN`, `CHKOUT`, `CHRIN`, `CHROUT`, `CLRCHN`, `CLALL`) clobber the tape buffer pointers at `$FB`-`$FE`. If your program uses these zero-page locations for indirect addressing, you must restore them before each KERNAL call and before using them yourself.

**Pattern: save on entry, restore before each KERNAL call**

```asm
; At program start (init):
        lda $FB
        sta saved_fb
        lda $FC
        sta saved_fc
        lda $FD
        sta saved_fd
        lda $FE
        sta saved_fe

; Before every KERNAL I/O call:
        jsr restore_zp          ; restore $FB-$FE from saved values
        jsr CLALL               ; or OPEN, CHKIN, CHRIN, etc.

; restore_zp routine:
restore_zp:

        lda saved_fb
        sta $FB
        lda saved_fc
        sta $FC
        lda saved_fd
        sta $FD
        lda saved_fe
        sta $FE
        rts

; At program exit:
        jsr restore_zp          ; final restore so BASIC keeps working
```

The `$FB`-`$FE` bytes are KERNAL tape pointers, safe to borrow while the tape drive is idle. The save/restore discipline ensures BASIC remains usable after the program exits.

**When to call restore_zp:**

- Before every `pet_open`, `pet_close`, `CHKIN`, `CHKOUT`, `CLRCHN`, `CLALL`, `CHRIN`, `CHROUT` call.
- Before using `$FB`-`$FE` as indirect pointers in your own code (KERNAL may have clobbered them since your last restore).
- At program exit, to leave BASIC in a clean state.

## Troubleshooting

| Symptom                            | Likely cause                                                                                                              |
|------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `?SYNTAX ERROR` after calling OPEN | Used `jsr $FFBD` (SETNAM) or `jsr $FFBA` (SETLFS) — these don't exist on PET. Use pet_setnam/pet_setlfs wrappers instead. |
| `?SYNTAX ERROR` after calling OPEN | Used `jsr $FFC0` (OPEN jump table) from machine code — it includes BASIC parsing. Use pet_open (calls $F524) instead.     |
| OPEN jumps to BASIC error handler  | PET OPEN/CLOSE/CHKIN don't use carry for errors — they jump to $CE03 on failure. If they return, they succeeded.          |
| pet_open returns carry set         | File count ($AE) did not increase — OPEN failed internally. Check device, SA, filename.                                   |
| CHRIN returns garbage after CHKIN  | File not opened for read; wrong SA or file opened for write                                                               |
| STATUS bit 0 set after CHRIN       | IEEE-488 read timeout; drive not responding                                                                               |
| STATUS bit 1 set after CHROUT      | IEEE-488 write timeout; drive not responding                                                                              |
| STATUS bit 4 set                   | Unrecoverable read error or file not found on cassette                                                                    |
| File writes but drive LED flashes  | DOS error; read command channel (SA=15) for error code                                                                    |
| CHROUT goes to screen not file     | CLRCHN was called; call CHKOUT again before writing                                                                       |
| LOAD returns incorrect end address | SA=0 used with non-PRG file; use SA=1 with explicit load address                                                          |
| Program hangs after file operation | CLRCHN not called; KERNAL still reading from file instead of keyboard                                                     |
