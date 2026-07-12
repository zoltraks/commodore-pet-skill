# Disk Drives & DOS Commands

## Purpose

> **Scope:** Commodore IEEE-488 disk drives, DOS commands, command channel, directory listing, drive error messages, disk images, emulator workflows, BASIC vs KERNAL vs direct comparison
> **Key items:** Device 8, SA=15 command channel, `$` directory pseudo-file, D64/D80/D82 image formats, VICE xpet, "scratch/rename/format" commands

This file covers Commodore DOS disk operations for the PET 3032.

All disk access uses the IEEE-488 bus (GPIB).

The PET KERNAL communicates with the drive using logical files and secondary addresses.

The drive's firmware (Commodore DOS) interprets commands and manages the file system.

| Out of scope                    | See instead        |
|---------------------------------|--------------------|
| KERNAL file routine reference   | `system/file.md`   |
| Complete DASM file I/O examples | `example/file.md`  |
| KERNAL jump table               | `system/kernal.md` |

## Contents

| Section                          | Line | What it covers                                                |
|----------------------------------|------|---------------------------------------------------------------|
| Supported Disk Drives            | 35   | 2031, 2040, 4040, 8050, 8250, SFD-1001 specs and DOS versions |
| The Command Channel              | 58   | SA=15 open, read status string, send DOS command pattern      |
| DOS Commands                     | 184  | Initialize, scratch, rename, copy, format, validate           |
| Reading the Directory            | 323  | `$` pseudo-file, BASIC-format encoding, parsing loop          |
| DOS Error Messages               | 486  | Full error code table (00-74), checking CC field              |
| Disk Images and Emulators        | 548  | D64/D80/D82 formats, D64 on PET caveats, VICE xpet workflow   |
| Comparing File Access Approaches | 664  | BASIC vs KERNAL routines vs direct IEEE-488                   |
| Best Practices                   | 731  | CLRCHN, CLOSE, STATUS, command channel, LFN limits            |

## Supported Disk Drives

The PET 3032 uses IEEE-488 (GPIB) to communicate with disk drives.

These drives are native PET hardware:

| Drive    | Sides | Capacity | DOS     | Notes                                |
|----------|-------|----------|---------|--------------------------------------|
| 2031     | 1     | 170 KB   | DOS 2.6 | Single drive, same DOS as 4040       |
| 2040     | 1     | 170 KB   | DOS 2.0 | Oldest dual drive (read only compat) |
| 4040     | 2x1   | 340 KB   | DOS 2.6 | Dual single-density drives           |
| 8050     | 2x1   | 1 MB     | DOS 2.7 | Dual drives, D80 image format        |
| 8250     | 2x2   | 2 MB     | DOS 2.7 | Dual double-density, D82 format      |
| SFD-1001 | 1     | 1 MB     | DOS 2.7 | Single drive, same ROM as 8250       |

The 2031 and 4040 use the same DOS and are interchangeable for most purposes.

The 8050 and 8250 use a newer DOS and support larger disks.

**Note:** These drives use the parallel IEEE-488 connector.

They are not compatible with the serial IEC connector used by C64-era drives (1541, 1571).

## The Command Channel

Every disk operation beyond simple file read/write goes through the command channel.

The command channel uses secondary address 15 (SA=15).

Opening SA=15 with a command string sends that command to the drive.

Opening SA=15 with no filename opens the channel for reading drive status.

**Always open the command channel to check drive status after any operation.**

### Opening the Command Channel for Status

```asm
; PET does not have SETNAM - use pet_setnam wrapper
; PET does not have SETLFS - use pet_setlfs wrapper
; PET OPEN includes BASIC parsing - use pet_open wrapper

; Open command channel with no command (read-only)
open_cmd_ch:

        lda #0                  ; no filename
        jsr pet_setnam
        lda #$0F                 ; logical file 15
        ldx #8                  ; device 8
        ldy #$0F                 ; SA=15 = command channel
        jsr pet_setlfs
        jsr pet_open                ; open
        rts
```

### Reading Drive Status

After opening the command channel, redirect input to it and read the status string.

The status is a CR-terminated ASCII string in the form: `CC,MESSAGE,TT,SS`

| Field   | Meaning                      |
|---------|------------------------------|
| CC      | Two-digit decimal error code |
| MESSAGE | English text description     |
| TT      | Track number (or 0)          |
| SS      | Sector number (or 0)         |

A clean drive returns: `00,OK,00,00`

```asm
CHKIN   = $FFC6
CHRIN   = $FFCF
CLRCHN  = $FFCC
STATUS  = $0096
CHROUT  = $FFD2

; read_status: reads drive status into status_buf, CR-terminated
; Assumes command channel is open as LFN 15
read_status:

        ldx #$0F
        jsr CHKIN               ; set LFN 15 as input

        ldx #0

read_stat_loop:

        jsr CHRIN               ; read one character
        sta status_buf,x        ; store
        cmp #$0D                ; CR = end of status string
        beq read_stat_done
        inx
        lda STATUS
        bne read_stat_done      ; EOF or error
        cpx #$28                 ; safety: max 40 chars
        bne read_stat_loop

read_stat_done:

        lda #$00
        sta status_buf,x        ; null-terminate
        jsr CLRCHN
        rts

status_buf:

        byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        byte 0,0,0,0,0,0,0,0,0,0
```

### Sending a DOS Command

To send a command, open the command channel with the command as the filename:

```asm
; Send "S0:OLDNAME" to scratch (delete) a file
send_cmd:

        lda #cmd_end-cmd        ; command length
        ldx #<cmd
        ldy #>cmd
        jsr pet_setnam

        lda #$0F                 ; logical file 15
        ldx #8                  ; device 8
        ldy #$0F                 ; SA=15 = command channel
        jsr pet_setlfs

        jsr pet_open                ; sending the command happens on OPEN
        bcs cmd_error

        lda #$0F
        jsr pet_close               ; close sends the command and waits

        jsr open_cmd_ch         ; Reopen command channel to read status
        jsr read_status
        rts                     ; check status_buf[0..1] for "00" = success

cmd:

        byte "S0:OLDNAME"

cmd_end:
```

**Important:** After each DOS command, always reopen the command channel and read the status to clear the drive's error LED and verify success.

## DOS Commands

All commands are sent as the filename string when opening SA=15.

Commands use PETSCII uppercase.

### Initialize Drive

Reads the BAM (Block Availability Map) from disk into drive RAM.

Call after inserting a new disk or after a power-on.

```
I
```

Or with explicit drive number:

```
I0
```

```asm
init_cmd:

        byte "I0"

init_end:
```

### Read Drive Status

Open SA=15 with no filename, then read.

No command string needed - the drive always has a status ready.

### Scratch (Delete) File

```
S0:FILENAME
```

The `0:` prefix specifies drive 0 (use `1:` for drive 1 on dual drives).

```asm
scratch_cmd:

        byte "S0:MYFILE"

scratch_end:
```

The status response after scratching includes the count of files deleted.

For example: `01,FILES SCRATCHED,02,00` means 2 files were deleted.

### Rename File

```
R0:NEWNAME=0:OLDNAME
```

```asm
rename_cmd:

        byte "R0:NEWNAME=0:OLDNAME"

rename_end:
```

### Copy File Within Same Drive

```
C0:DEST=0:SOURCE
```

```asm
copy_cmd:

        byte "C0:BACKUP=0:ORIGINAL"

copy_end:
```

Copying between drives on a dual-drive unit:

```
C1:DEST=0:SOURCE
```

### Format Disk (New)

Creates a new directory and writes a disk header.

**Destructive: erases all data on the disk.**

```
N0:DISKNAME,ID
```

The disk ID is a two-character identifier stored in the disk header.

```asm
format_cmd:

        byte "N0:MY DISK,01"

format_end:
```

### Validate (Collect) Disk

Rebuilds the BAM by scanning all allocated sectors.

Use after an incomplete write or suspected corruption.

```
V0
```

```asm
validate_cmd:

        byte "V0"

validate_end:
```

### DOS Command Summary

| Command      | Format                 | Description                   |
|--------------|------------------------|-------------------------------|
| Initialize   | `I0`                   | Read BAM, reset drive state   |
| Scratch      | `S0:FILENAME`          | Delete a file                 |
| Rename       | `R0:NEWNAME=0:OLDNAME` | Rename a file                 |
| Copy         | `C0:DEST=0:SOURCE`     | Copy within or between drives |
| Format (new) | `N0:DISKNAME,ID`       | Format and create directory   |
| Validate     | `V0`                   | Rebuild BAM                   |

## Reading the Directory

The directory is exposed as a pseudo-file named `$` (dollar sign).

Opening `$` causes the drive to send the directory as a BASIC-program-format byte stream.

This is a historical design: Commodore BASIC 2.0 had no directory command, so `LOAD "$",8` loaded the directory as a BASIC program that could then be `LIST`ed.

Reading the directory programmatically requires parsing this BASIC-program format.

### Directory Format (BASIC Program Encoding)

The drive sends the directory as a tokenized BASIC program in memory-image format.

Each line follows this structure:

```
[2 bytes: next-line pointer (LE)] [2 bytes: line number (LE)] [text bytes] [00: end of line]
```

The end of the program is marked by a two-byte zero word `$00 $00`.

The first line contains the disk name and disk ID.

Each subsequent line contains one directory entry: block count, filename, and file type.

**Skip the first 4 bytes** (load address + first next-pointer) before parsing line content.

### Opening the Directory

```asm
; PET does not have SETNAM - use pet_setnam wrapper
; PET does not have SETLFS - use pet_setlfs wrapper
; PET OPEN includes BASIC parsing - use pet_open wrapper
CHKIN   = $FFC6
CHRIN   = $FFCF
CLRCHN  = $FFCC
; PET CLOSE includes BASIC parsing - use pet_close wrapper
STATUS  = $0096

open_directory:

        lda #1                  ; filename length = 1
        ldx #<dir_name
        ldy #>dir_name
        jsr pet_setnam

        lda #2                  ; LFN 2 (any unused number)
        ldx #8                  ; device 8
        ldy #0                  ; SA=0 for directory read
        jsr pet_setlfs

        jsr pet_open
        bcs dir_open_err

        ldx #2
        jsr CHKIN               ; set as input channel
        rts

dir_name:

        byte "$"
```

### Skipping the BASIC Load Header

The drive prepends 2 bytes (the BASIC load address).

Skip these before parsing entries:

```asm
skip_header:

        jsr CHRIN               ; skip load address low
        jsr CHRIN               ; skip load address high
        rts
```

### Reading a Single Directory Line

After skipping the header, each entry consists of:

1. Two bytes: next-line pointer (skip)
2. Two bytes: line number (= block count)
3. Text bytes: the visible line content (filename, type, etc.)
4. One byte: `$00` end-of-line

```asm
; read_dir_line: reads one directory line
; Returns: Y = number of bytes in line_buf (0 = end of directory)
; Trashes A

read_dir_line:

        jsr CHRIN               ; Skip next-line pointer (2 bytes)
        jsr CHRIN               ; skip low and high of next pointer

        jsr CHRIN               ; Check for end-of-directory: block count low
        pha
        jsr CHRIN               ; block count high
        tax
        pla
        ora #0
        bne not_end
        cpx #0
        bne not_end
        ldy #0                  ; both zero = end of directory
        rts

not_end:
        ldy #0                  ; Store block count (low byte in A, high in X) if needed; read text bytes until 00

read_line_loop:

        jsr CHRIN
        beq line_done           ; 00 = end of line
        sta line_buf,y
        iny
        lda STATUS
        bne dir_eof
        cpy #$40                 ; safety limit
        bne read_line_loop

line_done:

        lda #$0D                ; CR for display
        sta line_buf,y
        iny
        rts

dir_eof:

        ldy #0
        rts

line_buf:

        byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        byte 0
```

### Closing the Directory

```asm
        jsr CLRCHN
        lda #2
        jsr pet_close
```

### LOAD "$" vs Programmatic Directory Read

| Approach          | Result                                        | BASIC program overwritten? |
|-------------------|-----------------------------------------------|----------------------------|
| `LOAD "$",8`      | Directory loads into BASIC RAM at `$0401`     | Yes                        |
| Programmatic read | Reads one byte at a time into your own buffer | No                         |

Use the programmatic approach in machine-language programs.

Use `LOAD "$",8` only from BASIC or when you want to display the directory and do not need BASIC RAM.

## DOS Error Messages

Drive errors are reported through the command channel (SA=15) in the format:

```
CC,MESSAGE,TT,SS
```

Where CC is the error code, MESSAGE is text, TT is track, SS is sector.

### Common Error Codes

| Code | Message            | Meaning                                      |
|------|--------------------|----------------------------------------------|
| 00   | OK                 | No error                                     |
| 01   | FILES SCRATCHED    | Informational: n files deleted (TT=count)    |
| 20   | READ ERROR         | Block header not found                       |
| 21   | READ ERROR         | Sync character not found                     |
| 22   | READ ERROR         | Data block not present                       |
| 23   | READ ERROR         | Checksum error in data                       |
| 24   | READ ERROR         | Byte decoding error                          |
| 25   | WRITE ERROR        | Write-verify failure                         |
| 26   | WRITE PROTECT ON   | Disk is write-protected                      |
| 27   | READ ERROR         | Checksum error in header                     |
| 29   | DISK ID MISMATCH   | Wrong disk inserted                          |
| 30   | SYNTAX ERROR       | Invalid DOS command format                   |
| 31   | SYNTAX ERROR       | Unrecognized command                         |
| 33   | SYNTAX ERROR       | Invalid filename                             |
| 34   | SYNTAX ERROR       | No filename given                            |
| 62   | FILE NOT FOUND     | Named file does not exist on disk            |
| 63   | FILE EXISTS        | Cannot write: file already exists            |
| 64   | FILE TYPE MISMATCH | SA/type mismatch with existing file          |
| 70   | NO CHANNEL         | All drive buffers in use; close a file first |
| 71   | DIR ERROR          | BAM checksum error; run Validate             |
| 72   | DISK FULL          | No more free blocks on disk                  |
| 73   | DOS MISMATCH       | Drive power-on or incompatible format        |
| 74   | DRIVE NOT READY    | No disk inserted or drive door open          |

Error code 73 is also returned as the power-on banner.

The message text includes the DOS version (for example: `73,CBM DOS V2.6 4040,00,00`).

Check for code 73 on first open and discard it - it is not an error.

### Checking for Errors After File Operations

```asm
; After an OPEN or file close, check drive status:
check_drive_error:

        lda status_buf          ; Read first two chars: tens digit of error code
        cmp #'0'                ; ASCII '0'
        bne has_error
        lda status_buf+1        ; units digit
        cmp #'0'
        bne has_error
        rts                     ; "00" = no error

has_error:
        rts                     ; error: status_buf contains the full string
```

## Disk Images and Emulators

This section describes disk image formats and how to use them in PET emulators.

**Important:** Disk image mounting is performed by the emulator or host environment.

No PET KERNAL code is needed to mount an image.

Once an image is mounted, all normal KERNAL file operations work without modification.

### Disk Image Formats

| Format | Drive | Computer    | Capacity | Tracks | Native to PET? |
|--------|-------|-------------|----------|--------|----------------|
| D64    | 1541  | C64, VIC-20 | 170 KB   | 35     | No             |
| D71    | 1571  | C128        | 340 KB   | 70     | No             |
| D81    | 1581  | C64, C128   | 800 KB   | 80     | No             |
| D80    | 8050  | PET, CBM    | 500 KB   | 77     | Yes            |
| D82    | 8250  | PET, CBM    | 1 MB     | 154    | Yes            |

D80 and D82 are the native formats for PET disk drives.

D64 images are native to the 1541/1540 (C64-era serial IEC drives) and are not natively supported by physical PET IEEE-488 drives.

### D64 Compatibility on PET

D64 images were created for 1541/1540 drives which use a serial IEC interface.

Physical PET drives (2031, 4040, 8050) use the parallel IEEE-488 interface.

A physical 4040 drive **cannot** read D64 disks directly.

However, many emulators (including VICE xpet) can mount D64 images and expose them to emulated PET hardware as if they were compatible disks.

This works because the emulator translates the D64 format at the emulator layer - the emulated PET KERNAL sees a normal IEEE-488 drive.

The DOS version string returned by the drive (code 73) will reveal the actual emulated drive type.

### VICE xpet Emulator

VICE (Versatile Commodore Emulator) includes `xpet`, a full PET emulator.

VICE supports D64, D80, and D82 image formats for the emulated IEEE-488 drive.

**Mounting a disk image in VICE xpet:**

1. Start VICE xpet with the desired PET model.
2. Open the Drive settings (menu or F12 in some builds).
3. Attach the image file to Drive 8 (or Drive 9 for a second drive).
4. Select the correct drive type for the image (8050 for D80, 8250 for D82, 2031 for D64).
5. The image is now accessible from PET code as device 8.

From the command line:

```
xpet -model 3032 -drive8type 2031 -8 myfile.d64
```

Or for a D80 image on an 8050:

```
xpet -model 3032 -drive8type 8050 -8 myfile.d80
```

Once mounted, use normal KERNAL calls - no emulator-specific assembly is needed.

### Mass:Werk PET Emulator

The Mass:Werk (Michael Steil) PET emulator supports D64 and D80 images.

Disk images are attached via the emulator configuration or command-line parameters.

After attachment, the emulated drive responds as device 8 on the IEEE-488 bus.

No changes to PET KERNAL code are required.

### Typical Emulator Workflow

This is a complete workflow for working with disk files in an emulator:

**Step 1: Prepare the disk image on the host.**

Use a host-side tool (cbmconvert, cc1541, DirMaster, or similar) to put your files into a D64, D80, or D82 image.

**Step 2: Mount the image in the emulator.**

Use the emulator's drive-attach feature.

No PET code involved.

**Step 3: Access files from PET code.**

Use standard KERNAL routines as documented in `system/file.md` and `example/file.md`.

The emulator transparently handles the IEEE-488 protocol simulation.

**Example sequence in PET code after image is mounted:**

```asm
        lda #6                  ; Load a file from the mounted image
        ldx #<fname
        ldy #>fname
        jsr pet_setnam

        lda #1
        ldx #8                  ; emulated drive 8
        ldy #0
        jsr pet_setlfs

        lda #0                  ; VERCK ($9D) = 0 -> load
        sta $9D
        jsr LOAD                ; LOAD = $F3C9 (low-level, past BASIC parse) -- NOT $FFD5
        bcs error
```

This code works identically on real hardware with a real IEEE-488 drive and in an emulator with a mounted image.

## Comparing File Access Approaches

| Approach               | Complexity | Use when                                     |
|------------------------|------------|----------------------------------------------|
| BASIC `LOAD/SAVE/OPEN` | Low        | Prototyping, small programs, interactive use |
| KERNAL routines (ML)   | Medium     | Production code, games, utilities            |
| Direct IEEE-488 (ML)   | High       | Custom protocols, non-file bus operations    |

### BASIC File Operations

BASIC handles OPEN/CLOSE/INPUT#/PRINT# with simple syntax.

BASIC is slow (interpreted) and ties up the BASIC interpreter.

Use BASIC when speed is not critical and the program is short.

```basic
OPEN 1,8,2,"0:MYFILE,S,R"
INPUT#1, A$
CLOSE 1
```

### KERNAL Routines

KERNAL routines give full control from machine language.

They are the standard approach for ML programs.

All KERNAL calls are documented in `system/file.md`.

```asm
        jsr pet_setnam
        jsr pet_setlfs
        jsr pet_open
        ldx #2
        jsr CHKIN
        jsr CHRIN               ; read bytes
        jsr CLRCHN
        lda #2
        jsr pet_close
```

### Direct IEEE-488 Bus Access

The KERNAL implements the IEEE-488 handshake internally to build the higher-level file routines.

Direct bus access is rarely needed from application code.

Use it only for:

- Custom IEEE-488 devices that do not use Commodore DOS.
- Debugging bus timing issues.
- Implementing non-standard file protocols.

> **Not the C64 addresses.** The C64/serial-IEC entries `TALK` ($FFB4), `LISTEN` ($FFB1), `TKSA` ($FF96), `SECOND` ($FF93), `ACPTR` ($FFA5), `CIOUT` ($FFA8), `UNTALK` ($FFAB), `UNLSN` ($FFAE) **do not exist on the PET**. On the PET jump table (which only spans `$FFC0-$FFEA`) those addresses fall in the machine-language monitor and the copyright string — the bytes at `$FFB1-$FFBF` are the ASCII text `"C. 0978 CBM "`, not a JMP. Verified against `kernal-2.901465-03`.

The PET's IEEE-488 primitives live in the KERNAL body at these **new-ROM-specific** addresses (not a stable jump table — wrong on BASIC 1 and BASIC 4 machines; reach them only when the standard file routines cannot do the job):

| PET routine                                    | Address | Description                                       |
|------------------------------------------------|---------|---------------------------------------------------|
| Set up IEEE for Talk/Listen                    | $F0B6   | Address the bus and assert ATN                    |
| Send byte to IEEE (deferred)                   | $F0EE   | Output a data byte on the bus                     |
| Send byte to IEEE (immediate)                  | $F128   | Output a command byte with ATN                    |
| Send Listen + secondary address (immediate)    | $F164   | Address a listener and its SA                     |
| Drop IEEE channel (Unlisten / Untalk)          | $F17F   | Release the current talker/listener               |
| Receive byte from IEEE                          | $F18C   | Input one data byte from the bus                  |

## Best Practices

**Always restore I/O channels.**

Call CLRCHN after every CHKIN/CHRIN or CHKOUT/CHROUT sequence.

Failing to do so leaves subsequent CHROUT calls writing to the file instead of the screen.

**Always close files.**

Call CLOSE for each open file.

Use a consistent error-handling pattern that closes files on all exit paths.

**Check STATUS after every CHRIN and CHROUT.**

Do not assume a read or write succeeded without checking STATUS.

**Check the command channel after disk operations.**

After any disk write, open SA=15 and read the status string.

A flashing drive LED means an error occurred and the command channel must be read to clear it.

**Never leave more than 9 files open.**

The KERNAL logical-file table holds 10 entries (at $0251-$025A).

Reserve one entry for the command channel.

Use at most 9 data files simultaneously.

**Use SA 2-14 for sequential files.**

SA 0 and SA 1 are reserved for PRG load/save.

Using SA 0 for a sequential write will confuse the DOS.

**Initialize the drive on program start.**

Send `I0` through the command channel before first file access.

This ensures the drive BAM is current.

**Handle code 73 at startup.**

The first status read after power-on returns `73,DOS VERSION,00,00`.

This is informational, not an error.

Discard it or display it as a version banner.
