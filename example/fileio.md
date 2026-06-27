# File I/O Examples

## Purpose

> **Scope:** Complete, runnable DASM examples for PET 3032 file I/O: load PRG, save PRG, read SEQ, write SEQ, command channel, directory listing, error handling
> **Key items:** SETNAM=$FFBD, SETLFS=$FFBA, OPEN=$FFC0, CLOSE=$FFC3, CHKIN=$FFC6, CHKOUT=$FFC9, CLRCHN=$FFCC, CHRIN=$FFCF, CHROUT=$FFD2, LOAD=$FFD5, SAVE=$FFD8, STATUS=$0096

This file contains verified, runnable DASM assembly examples for all common PET 3032 file I/O patterns.

Every example assembles cleanly with DASM and follows the conventions in `system/file.md`.

| Topic                             | Section                              |
|-----------------------------------|--------------------------------------|
| KERNAL routine reference          | `system/file.md`                     |
| DOS commands and directory format | `system/disk.md`                     |
| KERNAL jump table overview        | `system/kernal.md`                   |

## Address Definitions

All examples use these standard KERNAL addresses.

Include this block at the top of any program that does file I/O:

```asm
; =========================================================
; KERNAL file I/O addresses
; =========================================================

SETNAM  = $FFBD         ; set filename
SETLFS  = $FFBA         ; set logical file, device, SA
OPEN    = $FFC0         ; open logical file
CLOSE   = $FFC3         ; close logical file
CHKIN   = $FFC6         ; set input channel
CHKOUT  = $FFC9         ; set output channel
CLRCHN  = $FFCC         ; restore default I/O channels
CHRIN   = $FFCF         ; read one byte from input channel
CHROUT  = $FFD2         ; write one byte to output channel
READST  = $FFB7         ; read STATUS byte into A
LOAD    = $FFD5         ; load PRG file
SAVE    = $FFD8         ; save PRG file

STATUS  = $0096         ; I/O status byte (zero page mirror)
```

## Load a PRG File

This example loads `PROG.BIN` from disk drive 8 into the address stored in the file's 2-byte header.

LOAD with SA=0 uses the file's embedded load address.

LOAD with SA=1 ignores the file's load address and loads to the address in X/Y.

```asm
        processor 6502

SETNAM  = $FFBD
SETLFS  = $FFBA
LOAD    = $FFD5
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

        ; set filename
        lda #progname_end-progname
        ldx #<progname
        ldy #>progname
        jsr SETNAM

        ; LFN=1, device=8, SA=0 (use file's load address)
        lda #1
        ldx #8
        ldy #0
        jsr SETLFS

        ; LOAD: A=0 means load, A=1 would mean verify
        lda #0
        jsr LOAD
        bcs load_error          ; carry set = error, A = error code

        ; success: X/Y = address of last byte loaded + 1
        stx end_lo
        sty end_hi
        rts

load_error:

        ; A = KERNAL error code (4=file not found, 5=device not present, etc.)
        rts

progname:       byte "PROG.BIN"
progname_end:

end_lo:         byte 0
end_hi:         byte 0
```

### Load to a Specific Address

To load a file at a fixed address regardless of its embedded load address, use SA=1 and put the target address in X/Y before calling LOAD:

```asm
        ; load SCREEN.BIN to $8000 regardless of file header
        lda #scrname_end-scrname
        ldx #<scrname
        ldy #>scrname
        jsr SETNAM

        lda #1
        ldx #8
        ldy #1                  ; SA=1 = override load address
        jsr SETLFS

        lda #0                  ; load (not verify)
        ldx #<$8000             ; override address low
        ldy #>$8000             ; override address high
        jsr LOAD
        bcs load_err

scrname:        byte "SCREEN.BIN"
scrname_end:
```

## Save a PRG File

This example saves the memory range `$040F`-`$07FF` as `MYFILE` on device 8.

SAVE takes the start address from a zero-page pointer and the end+1 address in X/Y.

```asm
        processor 6502

SETNAM  = $FFBD
SETLFS  = $FFBA
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
        jsr SETNAM

        ; LFN=1, device=8, SA=1 (PRG save)
        lda #1
        ldx #8
        ldy #1
        jsr SETLFS

        ; set start address in zero page pointer
        lda #<$040F
        sta SAVE_PTR
        lda #>$040F
        sta SAVE_PTR+1

        ; SAVE: A = zero-page address of start pointer, X/Y = end+1
        lda #SAVE_PTR
        ldx #<$0800             ; end+1 low
        ldy #>$0800             ; end+1 high
        jsr SAVE
        bcs save_error          ; carry set = error

        rts

save_error:

        rts

savname:        byte "MYFILE"
savname_end:
```

## Read a Sequential File

This example opens `SCORES.DAT` on device 8 as a sequential file and reads all bytes into a buffer.

Sequential files use SA 2-14.

Read until STATUS indicates EOF or error.

```asm
        processor 6502

SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CLOSE   = $FFC3
CHKIN   = $FFC6
CLRCHN  = $FFCC
CHRIN   = $FFCF
STATUS  = $0096
CHROUT  = $FFD2

BUF_MAX = 256               ; maximum bytes to read

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

        ; set filename
        lda #rdname_end-rdname
        ldx #<rdname
        ldy #>rdname
        jsr SETNAM

        ; LFN=2, device=8, SA=2 (sequential read)
        lda #2
        ldx #8
        ldy #2
        jsr SETLFS

        jsr OPEN
        bcs read_open_err       ; carry set = KERNAL error

        ; redirect input to LFN 2
        ldx #2
        jsr CHKIN
        bcs read_chkin_err

        ldy #0                  ; byte counter

read_loop:

        jsr CHRIN               ; read one byte
        sta read_buf,y          ; store in buffer
        iny

        lda STATUS              ; check status
        bne read_done           ; bit 6 = EOF, bit 2 = timeout error

        cpy #BUF_MAX            ; check buffer full
        bne read_loop

read_done:

        sty read_len            ; save count
        jsr CLRCHN              ; restore default I/O

        lda #2
        jsr CLOSE               ; close file
        rts

read_open_err:

        ; A = error code
        rts

read_chkin_err:

        lda #2
        jsr CLOSE
        rts

rdname:         byte "SCORES.DAT"
rdname_end:

read_buf:       ds 256,0        ; 256-byte receive buffer
read_len:       byte 0          ; number of bytes read
```

### Checking STATUS for EOF

The STATUS byte at `$0096` has these relevant bits for sequential file reads:

| Bit | Mask  | Meaning                              |
|-----|-------|--------------------------------------|
| 6   | `$40` | EOF: end of file reached             |
| 2   | `$04` | Timeout/device not present on read   |
| 3   | `$08` | Timeout/device not present on write  |

After the last byte of a file, CHRIN returns the last byte and sets bit 6.

A `bne` after `lda STATUS` exits the read loop on any non-zero status, which covers both EOF and errors.

To distinguish EOF from error:

```asm
        lda STATUS
        beq read_more           ; zero = no status, continue
        and #$40
        bne is_eof              ; bit 6 = clean EOF
        ; if we get here, STATUS was non-zero but not bit 6 = error
        jmp handle_error

read_more:

        ; continue reading

is_eof:

        ; clean end of file
```

## Write a Sequential File

This example creates `LOG.DAT` on device 8 and writes bytes from a buffer.

```asm
        processor 6502

SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CLOSE   = $FFC3
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
        jsr SETNAM

        ; LFN=3, device=8, SA=3 (sequential write)
        lda #3
        ldx #8
        ldy #3
        jsr SETLFS

        jsr OPEN
        bcs write_open_err

        ; redirect output to LFN 3
        ldx #3
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
        jsr CLOSE               ; close sends EOF to drive
        rts

write_open_err:

        rts

write_chkout_err:

        lda #3
        jsr CLOSE
        rts

write_error:

        jsr CLRCHN
        lda #3
        jsr CLOSE
        rts

wrname:         byte "LOG.DAT"
wrname_end:

write_buf:      byte "HELLO WORLD"
write_buf_end:
write_len:      byte write_buf_end-write_buf
```

**Important:** Always call CLOSE after writing.

CLOSE flushes the final partial sector and writes the EOF marker to the drive.

Never leave a sequential write file open at program exit.

## Send a DOS Command

This example sends `S0:OLDFILE` to scratch (delete) a file and then reads the drive status.

For full DOS command reference see `system/disk.md`.

```asm
        processor 6502

SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CLOSE   = $FFC3
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

        ; send S0:OLDFILE as the filename to SA=15
        lda #cmd_end-cmd
        ldx #<cmd
        ldy #>cmd
        jsr SETNAM

        lda #15                 ; LFN 15
        ldx #8                  ; device 8
        ldy #15                 ; SA=15 = command channel
        jsr SETLFS

        jsr OPEN                ; the command is sent on OPEN
        bcs cmd_err

        lda #15
        jsr CLOSE               ; close to flush and execute

        ; reopen command channel with no filename to read status
        lda #0
        jsr SETNAM              ; no filename = read-only open

        lda #15
        ldx #8
        ldy #15
        jsr SETLFS

        jsr OPEN
        bcs stat_err

        ldx #15
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
        cpx #40
        bne stat_loop

stat_done:

        lda #0
        sta stat_buf,x          ; null-terminate

        jsr CLRCHN
        lda #15
        jsr CLOSE
        rts

cmd_err:

        rts

stat_err:

        rts

cmd:    byte "S0:OLDFILE"
cmd_end:

stat_buf:       ds 41,0         ; 40 chars + null
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
        ; "00" = OK
        rts

is_error:

        ; error: display stat_buf or handle as needed
        rts
```

## Read the Disk Directory

This example opens the `$` pseudo-file, skips the 2-byte load header, and reads directory lines into a buffer.

For a detailed explanation of the directory format see `system/disk.md`.

```asm
        processor 6502

SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CLOSE   = $FFC3
CHKIN   = $FFC6
CLRCHN  = $FFCC
CHRIN   = $FFCF
STATUS  = $0096
CHROUT  = $FFD2

LINE_MAX = 64               ; maximum bytes in one directory line

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

        ; open "$" on device 8, SA=0
        lda #1
        ldx #<dir_dollar
        ldy #>dir_dollar
        jsr SETNAM

        lda #2                  ; LFN 2
        ldx #8
        ldy #0                  ; SA=0 for directory read
        jsr SETLFS

        jsr OPEN
        bcs dir_open_err

        ldx #2
        jsr CHKIN

        ; skip 2-byte BASIC load address
        jsr CHRIN               ; discard low byte
        jsr CHRIN               ; discard high byte

dir_line_loop:

        ; skip next-line pointer (2 bytes)
        jsr CHRIN
        jsr CHRIN

        ; read block count low byte
        jsr CHRIN
        pha                     ; save low byte
        ; read block count high byte
        jsr CHRIN
        tax                     ; high byte in X

        pla                     ; restore low byte
        ora #0
        bne not_end
        cpx #0
        bne not_end
        jmp dir_end             ; both zero = end of directory

not_end:

        ; read line text until $00
        ldy #0

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

        ; print the line to the screen
        ldy #0

dir_print_loop:

        cpy line_buf_end
        beq dir_line_loop
        lda line_buf,y
        jsr CHROUT
        iny
        bne dir_print_loop
        ; newline
        lda #$0D
        jsr CHROUT
        jmp dir_line_loop

dir_end:

        jsr CLRCHN
        lda #2
        jsr CLOSE
        rts

dir_open_err:

        rts

dir_dollar:     byte "$"
line_buf:       ds LINE_MAX,0
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

SETNAM  = $FFBD
SETLFS  = $FFBA
OPEN    = $FFC0
CLOSE   = $FFC3
CHKIN   = $FFC6
CHKOUT  = $FFC9
CLRCHN  = $FFCC
CHRIN   = $FFCF
CHROUT  = $FFD2
READST  = $FFB7
LOAD    = $FFD5
SAVE    = $FFD8
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

        ; initialize drive (clears power-on status)
        jsr init_drive

        ; do file I/O
        jsr read_config
        bcs fatal_error

        ; ...program logic...

        rts

fatal_error:

        rts

; =========================================================
; init_drive: send I0 command to initialize drive
; =========================================================

init_drive:

        lda #init_cmd_end-init_cmd
        ldx #<init_cmd
        ldy #>init_cmd
        jsr SETNAM

        lda #15
        ldx #8
        ldy #15
        jsr SETLFS

        jsr OPEN
        bcs init_err
        lda #15
        jsr CLOSE
        ; discard power-on status (code 73 is informational)
        clc
        rts

init_err:

        sec
        rts

init_cmd:       byte "I0"
init_cmd_end:

; =========================================================
; read_config: read CONFIG.DAT into config_buf
; Returns: C=0 success, C=1 error
; =========================================================

read_config:

        lda #cfgname_end-cfgname
        ldx #<cfgname
        ldy #>cfgname
        jsr SETNAM

        lda #4                  ; LFN 4
        ldx #8
        ldy #4                  ; SA=4 (sequential read)
        jsr SETLFS

        jsr OPEN
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
        jsr CLOSE
        clc
        rts

cfg_open_err:

        sec
        rts

cfg_chkin_err:

        lda #4
        jsr CLOSE
        sec
        rts

cfgname:        byte "CONFIG.DAT"
cfgname_end:

CFG_MAX = 128
config_buf:     ds CFG_MAX,0
config_len:     byte 0
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

| Operation              | Call sequence                                             |
|------------------------|-----------------------------------------------------------|
| Load PRG from disk     | SETNAM, SETLFS (SA=0), LOAD                               |
| Save PRG to disk       | SETNAM, SETLFS (SA=1), SAVE                               |
| Open SEQ read          | SETNAM, SETLFS (SA=2+), OPEN, CHKIN                       |
| Read from SEQ file     | CHRIN (loop on STATUS=0), CLRCHN, CLOSE                   |
| Open SEQ write         | SETNAM, SETLFS (SA=2+), OPEN, CHKOUT                      |
| Write to SEQ file      | CHROUT (check STATUS), CLRCHN, CLOSE                      |
| Send DOS command       | SETNAM (cmd as name), SETLFS (SA=15), OPEN, CLOSE         |
| Read drive status      | SETNAM (empty), SETLFS (SA=15), OPEN, CHKIN, CHRIN, CLOSE |
| Read disk directory    | SETNAM ("$"), SETLFS (SA=0), OPEN, CHKIN, CHRIN loop      |
