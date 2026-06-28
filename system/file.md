# KERNAL File I/O

## Purpose

> **Scope:** PET file architecture, logical files, device numbers, secondary addresses, all KERNAL file routines, call sequences, STATUS byte, error handling
> **Key items:** SETNAM=$FFBD, SETLFS=$FFBA, OPEN=$FFC0, CLOSE=$FFC3, CHKIN=$FFC6, CHKOUT=$FFC9, CLRCHN=$FFCC, CHRIN=$FFCF, CHROUT=$FFD2, LOAD=$FFD5, SAVE=$FFD8, READST=$FFB7, STATUS=$0096

This file covers the complete PET 3032 KERNAL file I/O system.

The PET 3032 runs BASIC 2.0 and uses a KERNAL that was the ancestor of the C64 KERNAL.

All KERNAL routine addresses for the PET 3032 are documented here.

Do not use C64 addresses - they differ.

| Out of scope               | See instead        |
|----------------------------|--------------------|
| DOS commands and directory | `system/disk.md`   |
| Complete DASM examples     | `example/file.md`  |
| KERNAL jump table overview | `system/kernal.md` |
| Safe memory zones          | `system/memory.md` |

## Contents

| Section                    | Line | What it covers                                                                                     |
|----------------------------|------|----------------------------------------------------------------------------------------------------|
| File Architecture Overview | 23   | Logical files, device numbers, secondary addresses, file types                                     |
| KERNAL Routine Reference   | 122  | SETNAM, SETLFS, OPEN, CLOSE, CHKIN, CHKOUT, CLRCHN, CHRIN, CHROUT, READST, LOAD, SAVE, CLALL, STOP |
| Call Sequences             | 781  | Open-read, open-write, load PRG, save PRG patterns                                                 |
| EOF Detection              | 973  | STATUS bit 6 (disk), STATUS bit 4 (cassette)                                                       |
| Error Handling             | 1025 | OPEN error codes, device not present, file not found                                               |
| PETSCII Filename Rules     | 1093 | Uppercase, wildcards, drive prefix                                                                 |
| Tape File Notes            | 1119 | Cassette SA values, sequential vs PRG                                                              |
| Multiple Open Files        | 1131 | Table limits, safe LFN allocation                                                                  |
| Troubleshooting            | 1167 | Common bugs and their causes                                                                       |

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

Up to 10 logical files may be open simultaneously (limited by KERNAL internal tables at $0251-$0270).

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

| BASIC Statement        | KERNAL calls used             |
|------------------------|-------------------------------|
| `OPEN n,dev,sa,"name"` | SETNAM, SETLFS, OPEN          |
| `CLOSE n`              | CLOSE                         |
| `INPUT# n, var`        | CHKIN, CHRIN (loop), CLRCHN   |
| `PRINT# n, data`       | CHKOUT, CHROUT (loop), CLRCHN |
| `GET# n, var`          | CHKIN, CHRIN, CLRCHN          |
| `LOAD "name", dev`     | SETNAM, SETLFS, LOAD          |
| `SAVE "name", dev`     | SETNAM, SETLFS, SAVE          |

## KERNAL Routine Reference

### SETNAM - Set Filename

**Address:** `$FFBD`

**Purpose:** Store a pointer to the filename and its length in KERNAL workspace.

Must be called before OPEN, LOAD, or SAVE.

**Inputs:**

| Register | Value                         |
|----------|-------------------------------|
| A        | Filename length (0 = no name) |
| X        | Low byte of filename address  |
| Y        | High byte of filename address |

**Outputs:** None.

**Registers used:** None (A, X, Y are inputs, not modified).

**Side effects:** Stores length at `$D1` and address at `$DA-$DB` in KERNAL workspace.

**Notes:**

- The filename must be in PETSCII uppercase.
- For cassette files with no name, call with A=0; X and Y are ignored.
- For disk files the filename must always be provided.
- The filename string does not need a null terminator.

```asm
        processor 6502

SETNAM  = $FFBD

fname:

        byte "MYDATA"

fend:

        lda #fend-fname         ; length = 6
        ldx #<fname             ; low byte of filename address
        ldy #>fname             ; high byte of filename address
        jsr SETNAM
```

---

### SETLFS - Set Logical File Parameters

**Address:** `$FFBA`

**Purpose:** Store the logical file number, device number, and secondary address.

Must be called after SETNAM and before OPEN, LOAD, or SAVE.

**Inputs:**

| Register | Value               |
|----------|---------------------|
| A        | Logical file number |
| X        | Device number       |
| Y        | Secondary address   |

**Outputs:** None.

**Registers used:** None (A, X, Y are inputs).

**Side effects:** Stores parameters at `$D2` (LFN), `$D3` (device), `$D4` (SA) in KERNAL workspace.

**Notes:**

- The logical file number must be unique among all currently open files.
- For LOAD and SAVE the LFN is ignored by some KERNAL versions; still provide a valid value.
- SA 255 ($FF) is sometimes used as "no secondary address" for certain devices.

```asm
SETLFS  = $FFBA

        lda #2                  ; logical file number 2
        ldx #8                  ; device 8 (disk drive)
        ldy #2                  ; secondary address 2 (sequential data channel)
        jsr SETLFS
```

---

### OPEN - Open Logical File

**Address:** `$FFC0` (calls through vector at `$031A`)

**Purpose:** Open a logical file using parameters set by SETLFS and SETNAM.

**Inputs:** None (uses KERNAL workspace set by SETNAM and SETLFS).

**Outputs:**

| Register | Value                         |
|----------|-------------------------------|
| C        | 0 = success, 1 = error        |
| A        | Error code if C=1 (see below) |

**Registers used:** A, X, Y.

**Side effects:**

- Adds the file to the KERNAL logical file table.
- For disk: sends OPEN message over IEEE-488 to the drive.
- For cassette: prepares tape I/O buffers.

**Error codes (when C=1):**

| Code | Meaning               |
|------|-----------------------|
| 1    | Too many files open   |
| 2    | File already open     |
| 3    | File not open         |
| 4    | File not found        |
| 5    | Device not present    |
| 6    | Not an input file     |
| 7    | Not an output file    |
| 8    | Missing filename      |
| 9    | Illegal device number |

**Notes:**

- Always call SETNAM and SETLFS before OPEN.
- OPEN does not set the input or output channel - call CHKIN or CHKOUT next.
- For SA=15 (command channel), OPEN sends the filename string as a DOS command.
- After OPEN with SA=15 and no filename, the channel is open for reading drive status.

```asm
OPEN    = $FFC0

        jsr OPEN                ; open the file
        bcc open_ok             ; carry clear = no error
        jmp open_error          ; A = error code

open_ok:
```

---

### CLOSE - Close Logical File

**Address:** `$FFC3` (calls through vector at `$031C`)

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
CLOSE   = $FFC3

        lda #2                  ; close logical file 2
        jsr CLOSE
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

### READST - Read I/O Status

**Address:** `$FFB7`

**Purpose:** Return the current value of the STATUS byte.

**Inputs:** None.

**Outputs:**

| Register | Value               |
|----------|---------------------|
| A        | STATUS byte ($0096) |

**Registers used:** A.

**Side effects:** None.

**Notes:**

- STATUS is also directly readable at zero page address `$0096`.
- STATUS is set by CHRIN, CHROUT, LOAD, and SAVE.
- STATUS is cleared at the start of CHKIN and CHKOUT.
- Reading via READST does not clear STATUS.

```asm
READST  = $FFB7

        jsr READST              ; A = STATUS byte
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

Must call SETNAM and SETLFS first.

**Inputs:**

| Register | Value                                      |
|----------|--------------------------------------------|
| A        | 0 = load, 1 = verify (compare to memory)   |
| X        | Load address low byte (if SA=1 on SETLFS)  |
| Y        | Load address high byte (if SA=1 on SETLFS) |

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

```asm
SETLFS  = $FFBA
SETNAM  = $FFBD
LOAD    = $FFD5
STATUS  = $0096

        lda #6                  ; Step 1: set filename (length 6)
        ldx #<fname
        ldy #>fname
        jsr SETNAM

        lda #1                  ; Step 2: set file parameters (LFN, ignored by LOAD)
        ldx #8                  ; device: disk drive
        ldy #0                  ; SA=0: relocating load (use address from file)
        jsr SETLFS

        lda #0                  ; Step 3: load (0 = LOAD, not VERIFY)
        jsr LOAD
        bcs load_error          ; C=1 = error
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

Must call SETNAM and SETLFS first.

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

**Notes:**

- A must contain a zero-page address, not the start address itself.
- Store the start address as two bytes in zero page, then pass that zero-page address in A.
- The file is written in PRG format: first two bytes are the start address (little-endian), followed by the data.
- End address is exclusive: the byte at address (X/Y) is not written.
- Do not call OPEN before SAVE.
- SA=1 is used automatically for PRG save.

```asm
SETLFS  = $FFBA
SETNAM  = $FFBD
SAVE    = $FFD8
STATUS  = $0096

save_start = $FB             ; zero page: two bytes for start address

        lda #<$4000             ; Store start address in ZP
        sta save_start
        lda #>$4000
        sta save_start+1

        lda #6                  ; Set filename
        ldx #<sname
        ldy #>sname
        jsr SETNAM

        lda #1                  ; Set file parameters: logical file number
        ldx #8                  ; device: disk
        ldy #1                  ; SA=1 for save
        jsr SETLFS

        lda #save_start         ; Save: A = ZP ptr, X/Y = end+1
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

1. Call SETNAM with filename.
2. Call SETLFS with LFN, device, SA.
3. Call OPEN.
4. Call CHKIN with LFN to set as input channel.
5. Loop: call CHRIN, check STATUS after each byte.
6. Call CLRCHN to restore input.
7. Call CLOSE with LFN.

```asm
SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CHKIN   = $FFC6
CHRIN   = $FFCF
CLRCHN  = $FFCC
CLOSE   = $FFC3
STATUS  = $0096

; --- read_file: reads sequential file into dest_buf ---
read_file:              ; Expects: fname/fend defined, dest_buf defined

        lda #fend-fname
        ldx #<fname
        ldy #>fname
        jsr SETNAM

        lda #2                  ; logical file number
        ldx #8                  ; device: disk
        ldy #2                  ; SA=2: sequential data channel
        jsr SETLFS

        jsr OPEN
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
        jsr CLOSE
        rts

read_open_err:
read_chkin_err:

        jsr CLRCHN
        rts
```

### Open a File for Writing

The correct sequence for writing a sequential file:

1. Call SETNAM with filename. For disk, include `,S,W` in the filename string (e.g. `"OUTPUT,S,W"`). Without `,W`, CBM DOS defaults to read mode and the write will fail.
2. Call SETLFS with LFN, device, SA (use SA 2-14 for sequential).
3. Call OPEN.
4. Call CHKOUT with LFN to set as output channel.
5. Loop: call CHROUT, check STATUS after each byte.
6. Call CLRCHN to restore output.
7. Call CLOSE with LFN.

```asm
SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CHKOUT  = $FFC9
CHROUT  = $FFD2
CLRCHN  = $FFCC
CLOSE   = $FFC3
STATUS  = $0096

write_file:

        lda #wfend-wfname
        ldx #<wfname
        ldy #>wfname
        jsr SETNAM

        lda #3                  ; logical file number
        ldx #8                  ; device: disk
        ldy #2                  ; SA=2: sequential channel (write creates new file)
        jsr SETLFS

        jsr OPEN
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
        jsr CLOSE
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
        jsr SETNAM

        lda #1                  ; SA=0: relocating load (use address from file header)
        ldx #8
        ldy #0
        jsr SETLFS

        lda #0                  ; 0=load, 1=verify
        jsr LOAD
        bcs load_err            ; loaded successfully; X/Y = end+1
```

### Save a Program File

Do not call OPEN before SAVE.

```asm
save_ptr = $FB                  ; ZP: store start address here

        lda #<start_addr
        sta save_ptr
        lda #>start_addr
        sta save_ptr+1

        lda #fname_len
        ldx #<fname
        ldy #>fname
        jsr SETNAM

        lda #1
        ldx #8
        ldy #1                  ; SA=1 for save
        jsr SETLFS

        lda #save_ptr           ; ZP address (not the value)
        ldx #<end_addr
        ldy #>end_addr
        jsr SAVE
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
        jsr OPEN
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
        jsr SETNAM
        lda #$0F                ; logical file 15
        ldx #8                  ; same drive
        ldy #$0F                ; SA=15 = command channel
        jsr SETLFS
        jsr OPEN                ; then read error string via CHKIN/CHRIN; see system/disk.md
```

### Resource Leak Prevention

Always close files on all code paths, including error paths.

```asm
safe_close:             ; Safe cleanup pattern

        jsr CLRCHN              ; always restore I/O first
        lda #2                  ; close logical file 2
        jsr CLOSE               ; even if it wasn't fully opened
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

If no name is given (A=0 in SETNAM), the KERNAL loads the next file regardless of its header name.

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
        jsr SETNAM
        lda #2
        ldx #8
        ldy #2
        jsr SETLFS
        jsr OPEN

        lda #0                  ; File 2: command channel (no filename for status)
        jsr SETNAM
        lda #$0F
        ldx #8
        ldy #$0F
        jsr SETLFS
        jsr OPEN                ; LFN 2=data, LFN 15=cmd; CHKIN/CHRIN per channel; CLRCHN after each switch
```

## Troubleshooting

| Symptom                            | Likely cause                                                          |
|------------------------------------|-----------------------------------------------------------------------|
| OPEN returns C=1, A=5              | Device not present; check IEEE-488 cable and drive power              |
| OPEN returns C=1, A=1              | Too many files open; close unused files first                         |
| CHRIN returns garbage after CHKIN  | File not opened for read; wrong SA or file opened for write           |
| STATUS bit 0 set after CHRIN       | IEEE-488 read timeout; drive not responding                           |
| STATUS bit 1 set after CHROUT      | IEEE-488 write timeout; drive not responding                          |
| STATUS bit 4 set                   | Unrecoverable read error or file not found on cassette                |
| File writes but drive LED flashes  | DOS error; read command channel (SA=15) for error code                |
| CHROUT goes to screen not file     | CLRCHN was called; call CHKOUT again before writing                   |
| LOAD returns incorrect end address | SA=0 used with non-PRG file; use SA=1 with explicit load address      |
| Program hangs after file operation | CLRCHN not called; KERNAL still reading from file instead of keyboard |
