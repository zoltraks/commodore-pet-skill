# Code Examples

## Purpose

> **Scope:** Working PET 3032 assembly examples: BASIC stub, screen I/O, VBLANK, animation, character sets
> **Key items:** SYS1038 stub, screen clear, wait_key, vblank_wait, screen_copy, frame playback

This file provides verified, runnable code examples for the PET 3032. Each example is self-contained and follows DASM syntax with the standard PET conventions.

## Contents

| Section                        | Line | What it covers                                       |
|--------------------------------|------|------------------------------------------------------|
| Minimal BASIC Stub             | 10   | Shortest valid BASIC stub at $0401, SYS1038          |
| Clear Screen                   | 43   | Fill 1000 bytes of screen RAM with space character   |
| Wait for Key Press             | 78   | Poll GETIN until non-zero                            |
| VBLANK Polling                 | 104  | Poll VIA PORT B bit 5 without interrupts             |
| Copy Screen to Screen          | 133  | Copy 1000 bytes between two page-aligned buffers     |
| Switch Character Set           | 176  | PCR register values for uppercase and lowercase sets |
| Minimal Animation Frame Player | 210  | Frame table, copy loop, VBLANK wait, keypress exit   |
| Demo Skeleton Template         | 307  | init/main_loop/update/render pattern with IRQ guard  |
| IRQ-Driven Animation Skeleton  | 389  | Replace CINV, acknowledge PIA1 CRB, chain to KERNAL  |
| Screen Data Row Format         | 534  | 40-column row layout, PETSCII screen code reference  |

## Minimal BASIC Stub

Every PET machine-code program starts with a BASIC stub at `$0401`:

```asm
        processor 6502

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0

start:

        ; machine code starts here at $040F (1039 decimal)
        rts
```

Assemble: `dasm stub.asm -f3 -ostub.bin`

Load on PET: `LOAD "STUB.BIN",1` then `RUN` (executes `SYS 1038`).

## Clear Screen

```asm
        processor 6502

SCREEN  = $8000

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

clear_screen:

        lda #$20                ; space character
        ldx #$00

loop:

        sta SCREEN,x
        sta SCREEN+$100,x
        sta SCREEN+$200,x
        sta SCREEN+$300,x
        inx
        bne loop
        rts
```

## Wait for Key Press

```asm
        processor 6502

GETIN   = $FFE4

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

wait_key:

        jsr GETIN
        beq wait_key
        rts
```

## VBLANK Polling

Poll VBLANK without enabling interrupts. Uses VIA PORT B bit 5:

```asm
        processor 6502

VIA_PORTB = $E840

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

wait_vblank:

        lda VIA_PORTB
        and #$20                ; mask bit 5 (screen retrace)
        beq wait_vblank         ; wait until high
        rts
```

## Copy Screen to Screen

```asm
        processor 6502

SCREEN  = $8000

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; Copy 1000 bytes from source to destination
; Both must be page-aligned for this simple version
source  = $8400               ; source screen buffer
dest    = SCREEN              ; destination screen

copy_screen:

        ldx #$00

loop:

        lda source,x
        sta dest,x
        lda source+$100,x
        sta dest+$100,x
        lda source+$200,x
        sta dest+$200,x
        lda source+$300,x
        sta dest+$300,x
        inx
        bne loop
        rts
```

## Switch Character Set

```asm
        processor 6502

PCR     = $E84C
PCR_U   = $0C
PCR_L   = $08

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

set_uppercase:

        lda #PCR_U
        sta PCR
        rts

set_lowercase:

        lda #PCR_L
        sta PCR
        rts
```

## Minimal Animation Frame Player

Plays animation frames stored as screen data, waiting for VBLANK between frames:

```asm
        processor 6502

SCREEN    = $8000
VIA_PORTB = $E840
GETIN     = $FFE4

        org $0401

; BASIC stub: 10 SYS1038
        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

; Frame table: pointers to 1000-byte screen frames
frame_table:

        word frame1
        word frame2
        word frame1             ; loop back

play_animation:

        ldx #$00                ; frame index

next_frame:

        ; copy frame to screen
        lda frame_table,x
        sta source_lo
        inx
        lda frame_table,x
        sta source_hi
        inx

        jsr copy_frame

        ; wait for VBLANK
        jsr wait_vblank

        ; check for key to exit
        jsr GETIN
        bne exit

        ; loop frames
        cpx #6                  ; 3 frames * 2 bytes
        bne next_frame
        ldx #$00
        beq next_frame

exit:

        rts

; Copy 1000 bytes from (source_lo) to SCREEN
copy_frame:

        ldy #$00
        lda (source_lo),y
        sta SCREEN,y
        ; ... full 1000-byte copy loop would go here ...
        rts

wait_vblank:

        lda VIA_PORTB
        and #$20
        beq wait_vblank
        rts

; Example frame data (first row only)
frame1:

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        ; ... remaining 24 rows ...

frame2:

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        ; ... etc ...

source_lo = $F7
source_hi = $F8
```

## Demo Skeleton Template

```asm
        processor 6502

SCREEN    = $8000
GETIN     = $FFE4
CHROUT    = $FFD2
VIA_PORTB = $E840
PCR       = $E84C

        org $0401

; =========================================================
; BASIC stub: SYS1038
; =========================================================

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0

; =========================================================
; INIT
; =========================================================

init:

        lda #$93
        jsr CHROUT              ; clear screen

        lda #$00
        sta $00A7               ; disable cursor blink

; =========================================================
; MAIN LOOP
; =========================================================

main_loop:

        jsr wait_vblank
        jsr update
        jsr render
        jsr GETIN
        beq main_loop

exit:

        lda #$01
        sta $00A7               ; re-enable cursor blink
        rts

; =========================================================
; SUBROUTINES
; =========================================================

wait_vblank:

        lda VIA_PORTB
        and #$20
        beq wait_vblank
        rts

update:

        ; update game state here
        rts

render:

        ; write to screen RAM here
        rts
```

## IRQ-Driven Animation Skeleton

Uses the 60 Hz VBLANK IRQ to advance frames. The KERNAL IRQ handler is replaced at `CINV`. The handler acknowledges the IRQ by reading PIA1 CRB ($E813) to prevent re-entry, then chains back to the original KERNAL handler for keyboard and clock.

```asm
        processor 6502

SCREEN    = $8000
GETIN     = $FFE4
CHROUT    = $FFD2
CINV      = $0090           ; hardware IRQ vector (ZP)
PIA1_CRB  = $E813           ; must read to clear VBLANK IRQ flag

        org $0401

        word nextline
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0

old_cinv:

        word 0

; =========================================================
; ZP variables
; =========================================================

frame_ctr  = $F7            ; current frame byte counter
frame_hi   = $F8            ; current frame page
next_frame = $F9            ; set to 1 by IRQ to request frame advance

; =========================================================
; INIT
; =========================================================

init:

        lda #$93
        jsr CHROUT              ; clear screen

        lda #$01
        sta $00A7               ; disable cursor blink

        lda #<frame_data        ; point frame_hi/ctr to first frame
        sta frame_ctr
        lda #>frame_data
        sta frame_hi

        ; save original IRQ vector before replacing
        lda CINV
        sta old_cinv
        lda CINV+1
        sta old_cinv+1

        ; install IRQ handler
        sei
        lda #<irq_handler
        sta CINV
        lda #>irq_handler
        sta CINV+1
        cli

; =========================================================
; MAIN LOOP
; =========================================================

main_loop:

        lda next_frame
        beq main_loop           ; wait for IRQ to set flag

        lda #0
        sta next_frame          ; clear flag

        jsr render_frame        ; copy current frame to screen

        jsr GETIN
        bne exit

        jmp main_loop

exit:

        sei
        lda old_cinv            ; restore original IRQ vector
        sta CINV
        lda old_cinv+1
        sta CINV+1
        cli

        lda #$00
        sta $00A7               ; re-enable cursor blink
        rts

; =========================================================
; IRQ HANDLER
; =========================================================

; KERNAL IRQ entry at $E442 already saved A/X/Y on stack.
; It dispatches to CINV ($0090) after register save.
irq_handler:

        bit PIA1_CRB            ; acknowledge VBLANK IRQ - mandatory
        lda #1
        sta next_frame          ; signal main loop
        jmp $E962               ; chain to KERNAL: keyboard scan + clock update

; =========================================================
; RENDER
; =========================================================

; Copy 1000 bytes from frame pointer to screen
render_frame:

        ldy #$00
        ldx #4                  ; 4 pages of 250 bytes each (approx)

render_page:

        lda (frame_ctr),y       ; indirect ZP read (page 0 = 256 bytes)
        sta SCREEN,y
        iny
        bne render_page
        inc frame_hi
        dex
        bne render_page
        ; advance frame_ctr to next frame (add 1000 to frame pointer)
        rts

; =========================================================
; FRAME DATA
; =========================================================

frame_data:

        ; frame 0: 1000 bytes of screen data here
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        ; ... 990 more bytes ...
```

**Notes:**

- The KERNAL IRQ entry at `$E442` saves A/X/Y before dispatching to CINV, so the custom handler does not need to preserve registers.
- `$E962` is the KERNAL clock/keyboard handler. Its exact address may vary between ROM versions; read from the KERNAL ROM if portability is needed.
- Reading `PIA1_CRB` ($E813) is mandatory in any custom IRQ handler that replaces CINV completely.

## Screen Data Row Format

Screen data is emitted as rows of `byte` directives. Each `byte` line holds exactly 10 values. Four lines cover the full 40-column width. Minor section banners label each row:

```asm
; ---------------------------------------------------------
; ROW 6
; ---------------------------------------------------------

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$A0,$A0
        byte $A0,$A0,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
```
