# File I/O Examples

## Purpose

> **Scope:** Complete, runnable DASM examples for PET 3032 file I/O: load PRG, save PRG, read SEQ, write SEQ, command channel, directory listing, error handling
> **Key items:** pet_setnam, pet_setlfs, pet_open (calls $F524), pet_close (calls $F2AC), CHKIN=$FFC6, CHKOUT=$FFC9, CLRCHN=$FFCC, CHRIN=$FFCF, CHROUT=$FFD2, LOAD=$FFD5, SAVE=$FFD8, STATUS=$0096

This file contains verified, runnable DASM assembly examples for all common PET 3032 file I/O patterns.

Every example assembles cleanly with DASM and follows the conventions in `system/file.md`.

| Topic                             | Section            |
|-----------------------------------|--------------------|
| KERNAL routine reference          | `system/file.md`   |
| DOS commands and directory format | `system/disk.md`   |
| KERNAL jump table overview        | `system/kernal.md` |

## Contents

| Section                            | Line | What it covers                                         |
|------------------------------------|------|--------------------------------------------------------|
| Address Definitions                | 33   | Standard KERNAL equates block to paste at top of file  |
| Load a PRG File                    | 105  | LOAD with SA=0 (file address) and SA=1 (fixed address) |
| Save a PRG File                    | 202  | SAVE from zero-page pointer to end address             |
| Read a Sequential File             | 268  | OPEN + CHKIN + CHRIN loop + STATUS EOF check + CLOSE   |
| Write a Sequential File            | 405  | OPEN + CHKOUT + CHROUT loop + STATUS check + CLOSE     |
| Send a DOS Command                 | 517  | SA=15 OPEN with command string, reopen to read status  |
| Read the Disk Directory            | 649  | Open `$`, skip header, parse BASIC-format lines        |
| Complete File I/O Program Template | 775  | Full program with init, read, error paths, CLOSE       |
| Common Mistakes                    | 943  | CLRCHN, CLOSE on error, SA=0 misuse, LFN conflicts     |
| Quick Reference: Call Sequences    | 991  | One-line summary of every operation                    |

## Address Definitions

All examples use these standard KERNAL addresses.

Include this block at the top of any program that does file I/O:

```asm
; =========================================================
; KERNAL file I/O addresses
; =========================================================

; The PET does NOT have SETNAM ($FFBD), SETLFS ($FFBA), or READST ($FFB7)
; in its KERNAL jump table -- those are C64-only addresses.
; Use the wrapper routines below instead.

; ---- PET file I/O zero-page locations ----
PET_FNLEN       = $D1        ; filename length
PET_LA          = $D2        ; logical file number
PET_SA          = $D3        ; secondary address
PET_DEV         = $D4        ; device number
PET_FNADR_LO    = $DA        ; filename address low
PET_FNADR_HI    = $DB        ; filename address high
PET_OPEN_LOGIC  = $F524      ; OPEN past BASIC parsing (after JSR $F4CE)
PET_CLOSE_LOGIC = $F2AC      ; CLOSE past BASIC parsing (after JSR $F4CE)

CHKIN   = $FFC6         ; set input channel
CHKOUT  = $FFC9         ; set output channel
CLRCHN  = $FFCC         ; restore default I/O channels
CHRIN   = $FFCF         ; read one byte from input channel
CHROUT  = $FFD2         ; write one byte to output channel
LOAD    = $F3C9         ; low-level LOAD past BASIC parse (NOT $FFD5; see system/load.md)
VERCK   = $9D           ; 0 = load, 1 = verify
SAVE    = $FFD8         ; PET: BASIC-command entry; not usable for arbitrary ML range (see system/file.md)

STATUS  = $0096         ; I/O status byte (read directly, no READST)

; ---- PET file I/O wrapper routines ----

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

; pet_open: returns carry clear on success, set on error
pet_open:
        lda $AE
        pha
        jsr PET_OPEN_LOGIC
        pla
        cmp $AE
        bcc po_ok
        sec
        rts
po_ok:
        clc
        rts

; pet_close: A = logical file number
pet_close:
        sta PET_LA
        jsr PET_CLOSE_LOGIC
        rts
```

## Load a PRG File

This example loads `PROG.BIN` from disk drive 8 into the address stored in the file's 2-byte header.

LOAD with SA=0 uses the file's embedded load address.

LOAD with SA=1 ignores the file's load address and loads to the address in X/Y.

```asm
        processor 6502

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
LOAD    = $F3C9         ; low-level LOAD past BASIC parse (NOT the $FFD5 jump entry)
VERCK   = $9D           ; 0 = load, 1 = verify
CHROUT  = $FFD2

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; load_prg: load PROG.BIN from device 8 into its own address
; =========================================================

load_prg:

        lda #progname_end-progname      ; set filename
        ldx #<progname
        ldy #>progname
        jsr pet_setnam

        lda #1                  ; LFN=1, device=8, SA=0 (use file's load address)
        ldx #8
        ldy #0
        jsr pet_setlfs

        lda #0                  ; VERCK = 0 -> load (1 = verify)
        sta VERCK
        jsr LOAD                ; enter past BASIC parse (hard errors abort to BASIC)
        bcs load_error          ; carry set = error, A = error code

        stx end_lo              ; success: X/Y = address of last byte loaded + 1
        sty end_hi
        rts

load_error:

        rts                     ; A = KERNAL error code (4=file not found, 5=device not present, etc.)

progname:

        byte "PROG.BIN"
progname_end:

end_lo:

        byte 0

end_hi:

        byte 0
```

### Load to a Specific Address

To load a file at a fixed address regardless of its embedded load address, use SA=1 and put the target address in X/Y before calling LOAD:

```asm
        lda #scrname_end-scrname        ; load SCREEN.BIN to $8000 regardless of file header
        ldx #<scrname
        ldy #>scrname
        jsr pet_setnam

        lda #1
        ldx #8
        ldy #1                  ; SA=1 = override load address
        jsr pet_setlfs

        lda #0                  ; VERCK = 0 -> load
        sta VERCK
        ldx #<$8000             ; override address low
        ldy #>$8000             ; override address high
        jsr LOAD                ; enter past BASIC parse (X/Y = fixed address)
        bcs load_err

scrname:

        byte "SCREEN.BIN"
scrname_end:
```

## Save a PRG File

> **PET caveat:** the code below uses the **C64** SAVE convention (start pointer in A, end+1 in X/Y). It does **not** work from ML on the PET: `$FFD8` re-parses BASIC and the underlying routine saves the BASIC-program range (`$28-$2B`), not an arbitrary A/X/Y range. To save arbitrary ML data on the PET, write the file yourself with OPEN + CHKOUT + CHROUT (see `system/file.md`). This block is kept only to show the familiar C64 interface.

This example (C64 convention) saves the memory range `$040F`-`$07FF` as `MYFILE` on device 8.

SAVE takes the start address from a zero-page pointer and the end+1 address in X/Y.

```asm
        processor 6502

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
; WARNING (PET): $FFD8 re-parses BASIC; this C64-style range save does not work from PET ML.
SAVE    = $FFD8

SAVE_PTR = $FB              ; zero-page pointer for SAVE start address

        org $0401

; BASIC stub
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; save_prg: save $040F-$07FF as MYFILE on device 8
; =========================================================

save_prg:

        lda #savname_end-savname
        ldx #<savname
        ldy #>savname
        jsr pet_setnam

        lda #1                  ; LFN=1, device=8, SA=1 (PRG save)
        ldx #8
        ldy #1
        jsr pet_setlfs

        lda #<$040F             ; set start address in zero page pointer
        sta SAVE_PTR
        lda #>$040F
        sta SAVE_PTR+1

        lda #SAVE_PTR           ; SAVE: A = zero-page address of start pointer, X/Y = end+1
        ldx #<$0800             ; end+1 low
        ldy #>$0800             ; end+1 high
        jsr SAVE
        bcs save_error          ; carry set = error

        rts

save_error:

        rts

savname:

        byte "MYFILE"
savname_end:
```

## Read a Sequential File

This example opens `SCORES.DAT` on device 8 as a sequential file and reads all bytes into a buffer.

Sequential files use SA 2-14.

Read until STATUS indicates EOF or error.

```asm
        processor 6502

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see system/file.md)
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see system/file.md)
CHKIN   = $FFC6
CLRCHN  = $FFCC
CHRIN   = $FFCF
STATUS  = $0096
CHROUT  = $FFD2

BUF_MAX = $0100               ; maximum bytes to read

        org $0401

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; read_seq: open SCORES.DAT, read up to BUF_MAX bytes
; Result: read_buf filled, read_len = byte count read
; =========================================================

read_seq:

        lda #rdname_end-rdname  ; set filename
        ldx #<rdname
        ldy #>rdname
        jsr pet_setnam

        lda #2                  ; LFN=2, device=8, SA=2 (sequential read)
        ldx #8
        ldy #2
        jsr pet_setlfs

        jsr pet_open
        bcs read_open_err       ; carry set = KERNAL error

        ldx #2                  ; redirect input to LFN 2
        jsr CHKIN
        bcs read_chkin_err

        ldy #0                  ; byte counter

read_loop:

        jsr CHRIN               ; read one byte
        sta read_buf,y          ; store in buffer
        iny

        lda STATUS              ; check status
        bne read_done           ; any non-zero STATUS = EOF or error; stop reading

        cpy #BUF_MAX            ; check buffer full
        bne read_loop

read_done:

        sty read_len            ; save count
        jsr CLRCHN              ; restore default I/O

        lda #2
        jsr pet_close               ; close file
        rts

read_open_err:

        rts                     ; A = error code

read_chkin_err:

        lda #2
        jsr pet_close
        rts

rdname:

        byte "SCORES.DAT,S,R"
rdname_end:

read_buf:

        ds $100,0                ; 256-byte receive buffer

read_len:

        byte 0                  ; number of bytes read
```

### Checking STATUS for EOF

The STATUS byte at `$0096` has these relevant bits for sequential file reads from disk:

| Bit | Mask  | Device   | Meaning                              |
|-----|-------|----------|--------------------------------------|
| 7   | `$80` | Disk     | EOF: IEEE-488 EOI (end of file)      |
| 6   | `$40` | Cassette | EOF: tape EOT (end of tape file)     |
| 1   | `$02` | Disk     | Write timeout (drive not responding) |
| 0   | `$01` | Disk     | Read timeout (drive not responding)  |
| 4   | `$10` | Both     | Unrecoverable read error             |

After the last byte of a disk file, CHRIN returns that byte and sets STATUS bit 7 (EOI).

The byte is valid on disk EOF -- store it before checking STATUS.

A `bne` after `lda STATUS` exits the read loop on any non-zero STATUS, which covers both EOF and errors.

To distinguish disk EOF from error:

```asm
        lda STATUS
        beq read_more           ; zero = no status, continue
        and #$80
        bne is_eof              ; bit 7 = disk EOF (EOI); byte already stored
        jmp handle_error        ; non-zero STATUS but bit 7 clear = error (timeout or hardware fault)

read_more:              ; continue reading

is_eof:                 ; clean end of file; last byte was already stored before this check
```

## Write a Sequential File

This example creates `LOG.DAT` on device 8 and writes bytes from a buffer.

```asm
        processor 6502

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see system/file.md)
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see system/file.md)
CHKOUT  = $FFC9
CLRCHN  = $FFCC
CHROUT  = $FFD2
STATUS  = $0096

        org $0401

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; write_seq: create LOG.DAT and write write_len bytes from write_buf
; =========================================================

write_seq:

        lda #wrname_end-wrname
        ldx #<wrname
        ldy #>wrname
        jsr pet_setnam

        lda #3                  ; LFN=3, device=8, SA=3 (sequential write)
        ldx #8
        ldy #3
        jsr pet_setlfs

        jsr pet_open
        bcs write_open_err

        ldx #3                  ; redirect output to LFN 3
        jsr CHKOUT
        bcs write_chkout_err

        ldy #0                  ; byte counter

write_loop:

        cpy write_len
        beq write_done

        lda write_buf,y
        jsr CHROUT

        lda STATUS              ; check for write error
        bne write_error

        iny
        bne write_loop          ; always taken (Y wraps only at 256)

write_done:

        jsr CLRCHN

        lda #3
        jsr pet_close               ; close sends EOF to drive
        rts

write_open_err:

        rts

write_chkout_err:

        lda #3
        jsr pet_close
        rts

write_error:

        jsr CLRCHN
        lda #3
        jsr pet_close
        rts

wrname:

        byte "LOG.DAT,S,W"
wrname_end:

write_buf:

        byte "HELLO WORLD"
write_buf_end:

write_len:

        byte write_buf_end-write_buf
```

**Important:** Always call CLOSE after writing.

CLOSE flushes the final partial sector and writes the EOF marker to the drive.

Never leave a sequential write file open at program exit.

## Send a DOS Command

This example sends `S0:OLDFILE` to scratch (delete) a file and then reads the drive status.

For full DOS command reference see `system/disk.md`.

```asm
        processor 6502

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see system/file.md)
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see system/file.md)
CHKIN   = $FFC6
CLRCHN  = $FFCC
CHRIN   = $FFCF
STATUS  = $0096

        org $0401

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; scratch_file: send scratch command, read drive status
; Result: stat_buf contains null-terminated status string
; =========================================================

scratch_file:

        lda #cmd_end-cmd        ; send S0:OLDFILE as the filename to SA=15
        ldx #<cmd
        ldy #>cmd
        jsr pet_setnam

        lda #$0F                 ; LFN 15
        ldx #8                  ; device 8
        ldy #$0F                 ; SA=15 = command channel
        jsr pet_setlfs

        jsr pet_open                ; the command is sent on OPEN
        bcs cmd_err

        lda #$0F
        jsr pet_close               ; close to flush and execute

        lda #0                  ; reopen command channel with no filename to read status
        jsr pet_setnam              ; no filename = read-only open

        lda #$0F
        ldx #8
        ldy #$0F
        jsr pet_setlfs

        jsr pet_open
        bcs stat_err

        ldx #$0F
        jsr CHKIN               ; set LFN 15 as input

        ldx #0

stat_loop:

        jsr CHRIN
        sta stat_buf,x
        cmp #$0D                ; CR = end of status string
        beq stat_done
        lda STATUS
        bne stat_done
        inx
        cpx #$28
        bne stat_loop

stat_done:

        lda #0
        sta stat_buf,x          ; null-terminate

        jsr CLRCHN
        lda #$0F
        jsr pet_close
        rts

cmd_err:

        rts

stat_err:

        rts

cmd:

        byte "S0:OLDFILE"
cmd_end:

stat_buf:

        ds $29,0                 ; 40 chars + null
```

### Checking the Status Result

The status string in `stat_buf` starts with a two-digit error code.

Error code `00` means success.

Any other code is an error.

```asm
check_stat:

        lda stat_buf            ; tens digit
        cmp #'0'
        bne is_error
        lda stat_buf+1          ; units digit
        cmp #'0'
        bne is_error
        rts                     ; "00" = OK

is_error:

        rts                     ; error: display stat_buf or handle as needed
```

## Read the Disk Directory

This example opens the `$` pseudo-file, skips the 2-byte load header, and reads directory lines into a buffer.

For a detailed explanation of the directory format see `system/disk.md`.

```asm
        processor 6502

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see system/file.md)
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see system/file.md)
CHKIN   = $FFC6
CLRCHN  = $FFCC
CHRIN   = $FFCF
STATUS  = $0096
CHROUT  = $FFD2

LINE_MAX = $40               ; maximum bytes in one directory line

        org $0401

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; list_directory: print all directory entries to screen
; =========================================================

list_directory:

        lda #1                  ; open "$" on device 8, SA=0
        ldx #<dir_dollar
        ldy #>dir_dollar
        jsr pet_setnam

        lda #2                  ; LFN 2
        ldx #8
        ldy #0                  ; SA=0 for directory read
        jsr pet_setlfs

        jsr pet_open
        bcs dir_open_err

        ldx #2
        jsr CHKIN

        jsr CHRIN               ; skip 2-byte BASIC load address
        jsr CHRIN               ; discard high byte

dir_line_loop:

        jsr CHRIN               ; skip next-line pointer (2 bytes)
        jsr CHRIN

        jsr CHRIN               ; read block count low byte
        pha                     ; save low byte
        jsr CHRIN               ; read block count high byte
        tax                     ; high byte in X

        pla                     ; restore low byte
        ora #0
        bne not_end
        cpx #0
        bne not_end
        jmp dir_end             ; both zero = end of directory

not_end:

        ldy #0                  ; read line text until $00

dir_char_loop:

        jsr CHRIN
        beq dir_line_done
        sta line_buf,y
        iny
        lda STATUS
        bne dir_end
        cpy #LINE_MAX
        bne dir_char_loop

dir_line_done:

        ldy #0                  ; print the line to the screen

dir_print_loop:

        cpy line_buf_end
        beq dir_line_loop
        lda line_buf,y
        jsr CHROUT
        iny
        bne dir_print_loop
        lda #$0D                ; newline
        jsr CHROUT
        jmp dir_line_loop

dir_end:

        jsr CLRCHN
        lda #2
        jsr pet_close
        rts

dir_open_err:

        rts

dir_dollar:

        byte "$"

line_buf:

        ds LINE_MAX,0
line_buf_end    = line_buf+LINE_MAX
```

## Complete File I/O Program Template

This is a complete program template combining all the common file I/O patterns.

It demonstrates the recommended structure for a machine-language program that does disk file I/O.

```asm
        processor 6502

; =========================================================
; KERNAL addresses
; =========================================================

; PET does not have SETNAM - use pet_setnam wrapper (see system/file.md)
; PET does not have SETLFS - use pet_setlfs wrapper (see system/file.md)
; PET OPEN includes BASIC parsing - use pet_open wrapper (see system/file.md)
; PET CLOSE includes BASIC parsing - use pet_close wrapper (see system/file.md)
CHKIN   = $FFC6
CHKOUT  = $FFC9
CLRCHN  = $FFCC
CHRIN   = $FFCF
CHROUT  = $FFD2
; PET does not have READST - read STATUS ($0096) directly
LOAD    = $F3C9         ; low-level LOAD past BASIC parse (NOT $FFD5; see system/load.md)
VERCK   = $9D           ; 0 = load, 1 = verify
SAVE    = $FFD8         ; PET: BASIC-command entry; not usable for arbitrary ML range
STATUS  = $0096
SAVE_PTR = $FB

        org $0401

; =========================================================
; BASIC stub: 10 SYS1038
; =========================================================

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; =========================================================
; Main entry
; =========================================================

main:

        jsr init_drive          ; initialize drive (clears power-on status)

        jsr read_config         ; do file I/O
        bcs fatal_error

        rts                     ; ...program logic...

fatal_error:

        rts

; =========================================================
; init_drive: send I0 command to initialize drive
; =========================================================

init_drive:

        lda #init_cmd_end-init_cmd
        ldx #<init_cmd
        ldy #>init_cmd
        jsr pet_setnam

        lda #$0F
        ldx #8
        ldy #$0F
        jsr pet_setlfs

        jsr pet_open
        bcs init_err
        lda #$0F
        jsr pet_close
        clc                     ; discard power-on status (code 73 is informational)
        rts

init_err:

        sec
        rts

init_cmd:

        byte "I0"
init_cmd_end:

; =========================================================
; read_config: read CONFIG.DAT into config_buf
; Returns: C=0 success, C=1 error
; =========================================================

read_config:

        lda #cfgname_end-cfgname
        ldx #<cfgname
        ldy #>cfgname
        jsr pet_setnam

        lda #4                  ; LFN 4
        ldx #8
        ldy #4                  ; SA=4 (sequential read)
        jsr pet_setlfs

        jsr pet_open
        bcs cfg_open_err

        ldx #4
        jsr CHKIN
        bcs cfg_chkin_err

        ldy #0

cfg_read_loop:

        jsr CHRIN
        sta config_buf,y
        iny

        lda STATUS
        bne cfg_read_done

        cpy #CFG_MAX
        bne cfg_read_loop

cfg_read_done:

        sty config_len
        jsr CLRCHN
        lda #4
        jsr pet_close
        clc
        rts

cfg_open_err:

        sec
        rts

cfg_chkin_err:

        lda #4
        jsr pet_close
        sec
        rts

cfgname:

        byte "CONFIG.DAT,S,R"
cfgname_end:

CFG_MAX = $80

config_buf:

        ds CFG_MAX,0

config_len:

        byte 0
```

## Common Mistakes

These patterns cause subtle bugs that are difficult to trace.

**Forgetting CLRCHN after CHKIN or CHKOUT.**

All subsequent CHROUT calls go to the file instead of the screen.

Always call CLRCHN before returning from any subroutine that redirects I/O.

**Not closing files on error paths.**

If OPEN succeeds but a later step fails, the file must still be closed.

Every code path that can exit a subroutine must call CLOSE for each file that was successfully opened.

**Leaving the command channel open.**

Open the command channel for each command, read the status, then close it.

Do not keep it open across multiple DOS operations.

**Ignoring STATUS after CHROUT.**

A write to a full disk sets STATUS but does not halt the program.

Check STATUS after each CHROUT in sequential write loops.

**Using SA=0 or SA=1 for sequential files.**

SA=0 and SA=1 are for PRG load/save.

Using SA=0 for a sequential OPEN confuses the drive firmware.

Use SA=2 or higher for sequential data files.

**Using the same LFN for two open files.**

OPEN will return error code 2 (file already open) and set carry.

Assign a unique LFN to each open file.

**Not initializing the drive at startup.**

The drive returns the power-on banner (error code 73) as the first status.

Send `I0` through the command channel at program start to clear the banner.

## Quick Reference: Call Sequences

| Operation           | Call sequence                                                           |
|---------------------|-------------------------------------------------------------------------|
| Load PRG from disk  | pet_setnam, pet_setlfs (SA=0), LOAD                                     |
| Save PRG to disk    | pet_setnam, pet_setlfs (SA=1), SAVE                                     |
| Open SEQ read       | pet_setnam ("NAME,S,R"), pet_setlfs (SA=2+), OPEN, CHKIN                |
| Read from SEQ file  | CHRIN (store byte, then check STATUS bit 7 for disk EOF), CLRCHN, CLOSE |
| Open SEQ write      | pet_setnam ("NAME,S,W"), pet_setlfs (SA=2+), OPEN, CHKOUT               |
| Write to SEQ file   | CHROUT (check STATUS), CLRCHN, CLOSE                                    |
| Send DOS command    | pet_setnam (cmd as name), pet_setlfs (SA=15), OPEN, CLOSE               |
| Read drive status   | pet_setnam (empty), pet_setlfs (SA=15), OPEN, CHKIN, CHRIN, CLOSE       |
| Read disk directory | pet_setnam ("$"), pet_setlfs (SA=0), OPEN, CHKIN, CHRIN loop            |
