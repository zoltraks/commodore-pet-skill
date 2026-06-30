# Sound Generation

## Purpose

> **Scope:** VIA 6522 shift register sound, CB2 speaker output, frequency table, tone control
> **Key items:** ACR=$10, SR=$E84A, T2=$E848, CB2 speaker, $0F/$33/$55 patterns, disable with ACR=$00

Two methods are available.

The shift register method is preferred: it runs without CPU involvement and survives interrupts.

| Out of scope          | See instead        |
|-----------------------|--------------------|
| VIA register map      | `hardware/chip.md` |
| IRQ timing and VBLANK | `hardware/chip.md` |

## Hardware Background

The PET 3032 has no dedicated sound chip.

The internal speaker is wired to the CB2 output of the VIA 6522.

For the PetAY expansion card (dual AY-8910 stereo sound at `$A000`-`$A003`), see `expansion/petay.md`.

CB2 is also the shift register serial output.

When the shift register is configured to run free from Timer 2, it clocks a bit pattern onto CB2 continuously without CPU involvement.

Three registers control tone output:

| Register | Address | Role                                      |
|----------|---------|-------------------------------------------|
| ACR      | $E84B   | Enable/disable shift register output mode |
| SR       | $E84A   | Bit pattern - determines octave           |
| T2C-L    | $E848   | Timer 2 low byte - determines pitch       |

## Enabling Tone Output

```asm
ACR     = $E84B
SR      = $E84A
T2_LO   = $E848

        lda #$10                ; ACR bits 4-2 = 100: shift out free running at T2 rate
        sta ACR
        lda #$0F                ; square wave pattern, lowest octave
        sta SR
        lda #$EE                ; T2 divider: approx 261 Hz (middle C)
        sta T2_LO
```

The tone starts immediately and plays until ACR is cleared.

## Stopping Tone Output

```asm
        lda #$00
        sta ACR                 ; disable shift register -> CB2 goes idle -> no sound
```

Always stop the tone before returning to BASIC or the sound will continue.

## Bit Pattern and Octave

The SR register value determines the waveform shape and the effective octave.

| SR Value | Pattern    | Octave   | Frequency multiplier |
|----------|------------|----------|----------------------|
| $0F      | `00001111` | 0 (base) | x1                   |
| $33      | `00110011` | +1       | x2                   |
| $55      | `01010101` | +2       | x4                   |

Use $F0, $CC, $AA for the inverted equivalents - they produce the same pitch.

## Frequency Formula

```
f = 500000 / (T2_LO * 8)     for SR = $0F
f = 500000 / (T2_LO * 4)     for SR = $33
f = 500000 / (T2_LO * 2)     for SR = $55
```

The VIA runs at 1 MHz on the PET 3032.

The shift clock is PHI2 / (2 * T2_LO).

Minimum frequency: `500000 / (255 * 8)` = 245 Hz (B3).

Lower notes require software synthesis.

## Frequency Table (SR = $0F, Base Octave)

| T2        | Freq (Hz) | Note          |
|-----------|-----------|---------------|
| $FF (255) | 245       | B3            |
| $F0 (240) | 260       | C4            |
| $EE (238) | 263       | C4 (middle C) |
| $D5 (213) | 293       | D4            |
| $BE (190) | 329       | E4            |
| $B5 (181) | 345       | F4            |
| $A2 (162) | 386       | G4            |
| $90 (144) | 434       | A4            |
| $81 (129) | 484       | B4            |
| $78 (120) | 521       | C5            |
| $6B (107) | 584       | D5            |
| $5F (95)  | 658       | E5            |
| $5A (90)  | 694       | F5            |
| $51 (81)  | 772       | G5            |
| $48 (72)  | 868       | A5            |
| $40 (64)  | 977       | B5            |

For SR = $33 multiply frequency by 2.

For SR = $55 multiply by 4.

## Simple Tone Subroutine

```asm
ACR     = $E84B
SR_REG  = $E84A
T2_LO   = $E848

play_tone:              ; A = T2 divider, X = SR pattern; call once; tone plays until stop_tone

        pha
        lda #$10
        sta ACR
        stx SR_REG
        pla
        sta T2_LO
        rts

stop_tone:              ; silence CB2

        lda #$00
        sta ACR
        rts
```

Usage:

```asm
        lda #$EE                ; middle C
        ldx #$0F                ; base octave
        jsr play_tone

        ; ... do animation frame work ...

        jsr stop_tone
```

## Timed Beep

A blocking beep using a delay loop:

```asm
        lda #$D5                ; D4
        ldx #$0F
        jsr play_tone

        ldx #$20                ; delay ~100ms at 1 MHz

delay_outer:

        ldy #$00

delay_inner:

        dey
        bne delay_inner
        dex
        bne delay_outer

        jsr stop_tone
```

## Non-Blocking Sound with VBLANK Counter

For animation players, trigger a beep at a specific frame and stop after N frames:

```asm
sound_frames = $FF      ; $FF is documented unused by PET BASIC 2 -- safe to allocate

check_sound:

        lda sound_frames        ; In VBLANK handler or main loop:
        beq no_sound
        dec sound_frames
        bne no_sound
        jsr stop_tone

no_sound:

        rts
```

## PCR and CA2 Interaction

The PCR register ($E84C) controls both CA2 (character set) and CB2 (speaker).

The ACR method above controls CB2 via the SR path and does not affect CA2 or the character set.

Do not modify PCR bits 7-4 for sound; use ACR and SR only.

```asm
PCR     = $E84C
PCR_U   = $0C
PCR_L   = $0E
```

Changing PCR bits 3-1 switches the character set.

Changing ACR does not affect PCR.

Both can be active simultaneously.

## Bit-Bashing Method (Reference Only)

A simpler but CPU-blocking method: toggle CB2 via PCR directly.

```asm
PCR_CB2_HIGH = $CC      ; PCR CB2 output: $CC = CB2 high (off), $EC = CB2 low (on); Combined with CA2 high (uppercase charset): CA2 high, CB2 high
PCR_CB2_LOW  = $EC      ; CA2 high, CB2 low

beep_toggle:

        lda #PCR_CB2_LOW
        sta PCR
        ; delay here for desired half-period
        lda #PCR_CB2_HIGH
        sta PCR
        ; delay
        rts
```

This method ties the CPU and is disrupted by interrupts.

Use the shift register method for animation players.
