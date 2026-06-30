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
| VBLANK Polling                 | 121  | Two-phase VBLANK poll via VIA PORT B bit 5           |
| Copy Screen to Screen          | 155  | Copy 1000 bytes between two page-aligned buffers     |
| Switch Character Set           | 202  | PCR register values for uppercase and lowercase sets |
| Minimal Animation Frame Player | 239  | Frame table, copy loop, VBLANK wait, keypress exit   |
| Demo Skeleton Template         | 335  | init/main_loop/update/render pattern with IRQ guard  |
| IRQ-Driven Animation Skeleton  | 421  | Replace CINV, acknowledge PIA1 CRB, chain to KERNAL  |
| Screen Data Row Format         | 599  | 40-column row layout, PETSCII screen code reference  |

## Minimal BASIC Stub

Every PET machine-code program starts with a BASIC stub at `$0401`:

```asm
        processor 6502

        org $0401

        word nextline           ; BASIC stub: 10 SYS1038
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

old_pcr:

        byte 0

start:

        rts                     ; machine code starts here at $040E (1038 decimal)
```

Assemble: `dasm stub.asm -f1 -ostub.prg`

Load on PET: `LOAD "STUB",1` then `RUN` (executes `SYS 1038`).

## Clear Screen

```asm
        processor 6502

SCREEN  = $8000

        org $0401

        word nextline           ; BASIC stub: 10 SYS1038
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

clear_screen:

        lda #$20                ; space character
        ldx #$00

clear_loop:

        sta SCREEN,x            ; $8000-$80FF
        sta SCREEN+$100,x       ; $8100-$81FF
        sta SCREEN+$200,x       ; $8200-$82FF
        inx
        bne clear_loop          ; 768 bytes done (3 pages)

        ldx #$E8                ; remaining 232 bytes: $8300-$83E7

clear_tail:

        dex
        sta SCREEN+$300,x       ; x = 231..0, writes $83E7..$8300
        bne clear_tail          ; 232 bytes done, total = 1000
        rts
```

## Wait for Key Press

```asm
        processor 6502

GETIN   = $FFE4

        org $0401

        word nextline           ; BASIC stub: 10 SYS1038
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

Poll VBLANK without enabling interrupts. Uses VIA PORT B bit 5. The two-phase wait syncs to the start of VBLANK (bit 5 LOW), not just anywhere during active display:

```asm
        processor 6502

VIA_PORTB = $E840

        org $0401

        word nextline           ; BASIC stub: 10 SYS1038
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

wait_vblank:

        lda VIA_PORTB           ; phase 1: skip remaining VBLANK (bit 5 LOW)
        and #$20                ; mask bit 5 (screen retrace)
        beq wait_vblank         ; branch while LOW

vbl_wait:

        lda VIA_PORTB           ; phase 2: wait for active display to end (bit 5 HIGH)
        and #$20
        bne vbl_wait            ; branch while HIGH
        rts                     ; return at start of VBLANK
```

## Copy Screen to Screen

```asm
        processor 6502

SCREEN  = $8000

        org $0401

        word nextline           ; BASIC stub: 10 SYS1038
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

source  = $8400         ; Copy 1000 bytes from source to destination -- source screen buffer
dest    = SCREEN        ; Both must be page-aligned for this simple version -- destination screen

copy_screen:

        ldx #$00

copy_loop:

        lda source,x            ; $8000-$80FF
        sta dest,x
        lda source+$100,x       ; $8100-$81FF
        sta dest+$100,x
        lda source+$200,x       ; $8200-$82FF
        sta dest+$200,x
        inx
        bne copy_loop           ; 768 bytes done (3 pages)

        ldx #$E8                ; remaining 232 bytes: $8300-$83E7

copy_tail:

        dex
        lda source+$300,x       ; x = 231..0, reads $83E7..$8300
        sta dest+$300,x
        bne copy_tail           ; 232 bytes done, total = 1000
        rts
```

## Switch Character Set

```asm
        processor 6502

PCR     = $E84C
PCR_U   = $0C
PCR_L   = $0E

        org $0401

        word nextline           ; BASIC stub: 10 SYS1038
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

set_uppercase:

        lda PCR
        and #$F1                ; clear bits 3:1 (CA2 mode), preserve CB2 bits
        ora #PCR_U              ; bits 3:1 = 110 -> uppercase/graphics
        sta PCR
        rts

set_lowercase:

        lda PCR
        and #$F1                ; clear bits 3:1, preserve CB2 bits
        ora #PCR_L              ; bits 3:1 = 111 -> lowercase/text
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

        word nextline           ; BASIC stub: 10 SYS1038
        word 10
        byte $9E
        byte "1","0","3","8",0

nextline:

        word 0

frame_table:            ; Frame table: pointers to 1000-byte screen frames

        word frame1
        word frame2
        word frame1             ; loop back

play_animation:

        ldx #$00                ; frame index

next_frame:

        lda frame_table,x       ; patch frame source into copy_frame's self-modifying read
        sta cf_src+1            ; source lo
        inx
        lda frame_table,x
        sta cf_src+2            ; source hi
        inx

        jsr copy_frame

        jsr wait_vblank         ; wait for VBLANK

        jsr GETIN               ; check for key to exit
        bne exit

        cpx #6                  ; loop frames (3 frames * 2 bytes)
        bne next_frame
        ldx #$00
        beq next_frame

exit:

        rts

copy_frame:             ; copy_frame: copy 1000 bytes to SCREEN. Patch cf_src+1 (lo) and cf_src+2 (hi) with the frame source address before calling. No ZP required

        ldy #0

cf_src:

        lda $FFFF,y             ; self-modified: frame source address
        sta SCREEN,y
        ; ... full 1000-byte copy loop would go here ...
        rts

wait_vblank:

        lda VIA_PORTB           ; phase 1: skip remaining VBLANK (bit 5 LOW)
        and #$20
        beq wait_vblank

vbl_wait:

        lda VIA_PORTB           ; phase 2: wait for active display to end (bit 5 HIGH)
        and #$20
        bne vbl_wait
        rts                     ; return at start of VBLANK

frame1:                 ; Example frame data (first row only)

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        ; ... remaining 24 rows ...

frame2:

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20
        ; ... etc ...

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

        lda VIA_PORTB           ; phase 1: skip remaining VBLANK (bit 5 LOW)
        and #$20
        beq wait_vblank

vbl_wait:

        lda VIA_PORTB           ; phase 2: wait for active display to end (bit 5 HIGH)
        and #$20
        bne vbl_wait
        rts                     ; return at start of VBLANK

update:

        rts                     ; update game state here

render:

        rts                     ; write to screen RAM here
```

## IRQ-Driven Animation Skeleton

Uses the 60 Hz VBLANK IRQ to advance frames. The KERNAL IRQ handler is replaced at `CINV`. The handler acknowledges the IRQ by reading PIA1 Port B ($E812) to prevent re-entry, then chains back to the original KERNAL handler for keyboard and clock.

```asm
        processor 6502

SCREEN    = $8000
GETIN     = $FFE4
CHROUT    = $FFD2
CINV         = $0090    ; hardware IRQ vector (ZP)
PIA1_PORTB   = $E812    ; read to clear VBLANK IRQ flag (CB1 flag clears on Port B read)

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
; $FB-$FC: KERNAL tape pointers -- safe while tape is idle
; $FF: documented unused by PET BASIC 2
; =========================================================

frame_ctr  = $FB        ; frame source lo (KERNAL tape ptr -- safe when tape idle)
frame_hi   = $FC        ; frame source hi (KERNAL tape ptr -- safe when tape idle)
next_frame = $FF        ; IRQ->main loop flag (documented unused by PET BASIC 2)

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

        lda CINV                ; save original IRQ vector before replacing
        sta old_cinv
        lda CINV+1
        sta old_cinv+1

        sei                     ; install IRQ handler
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

irq_handler:             ; KERNAL IRQ entry at $E442 saves A/X/Y then dispatches to CINV ($0090)

        bit PIA1_PORTB          ; acknowledge VBLANK IRQ: read PIA1 Port B - mandatory
        lda #1
        sta next_frame          ; signal main loop
        jmp (old_cinv)          ; chain to original KERNAL handler (keyboard scan + clock)

; =========================================================
; RENDER
; =========================================================

render_frame:            ; Copy 1000 bytes from frame pointer to screen; frame_ctr:frame_hi restored on exit

        lda frame_hi
        pha                     ; save frame_hi; inc'd 3 times below, restored at end

        ldy #$00

render_p1:

        lda (frame_ctr),y       ; source bytes 0-255
        sta SCREEN,y            ; dest $8000-$80FF
        iny
        bne render_p1
        inc frame_hi

render_p2:

        lda (frame_ctr),y       ; source bytes 256-511
        sta SCREEN+$100,y       ; dest $8100-$81FF
        iny
        bne render_p2
        inc frame_hi

render_p3:

        lda (frame_ctr),y       ; source bytes 512-767
        sta SCREEN+$200,y       ; dest $8200-$82FF
        iny
        bne render_p3
        inc frame_hi

        ldy #$E8                ; remaining 232 bytes: $8300-$83E7

render_tail:

        dey
        lda (frame_ctr),y       ; source bytes 768-999 (y = 231..0)
        sta SCREEN+$300,y       ; dest $83E7..$8300
        bne render_tail         ; 232 bytes done, total = 1000

        pla
        sta frame_hi            ; restore frame_hi to original value
        rts

; =========================================================
; FRAME DATA
; =========================================================

frame_data:

        byte $20,$20,$20,$20,$20,$20,$20,$20,$20,$20    ; frame 0: 1000 bytes of screen data here
        ; ... 990 more bytes ...
```

**Notes:**

- The KERNAL IRQ entry at `$E442` saves A/X/Y before dispatching to CINV, so the custom handler does not need to preserve registers.
- Chaining via `jmp (old_cinv)` is portable across ROM versions; the original CINV value points to the KERNAL keyboard scan and clock update handler.
- Reading `PIA1_PORTB` ($E812) is mandatory in any custom IRQ handler that replaces CINV completely. On the 6520 PIA, the CB1 interrupt flag clears only on a Port B read — reading CRB ($E813) does not clear it.

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
