# PetAY Sound Board

## Purpose

> **Scope:** PetAY extension card: dual AY-8910 stereo sound, I/O addresses, register map, frequency calculation, programming
> **Key items:** `$A000`-`$A003`, AY-8910 register map, 1 MHz clock, frequency divider, mixer, envelope, stereo left/right

| Out of scope              | See instead         |
|---------------------------|---------------------|
| Internal VIA CB2 speaker  | `hardware/sound.md` |
| VIA/PIA/CRTC registers    | `hardware/chip.md`  |
| Memory map and safe zones | `system/memory.md`  |

## Overview

The PetAY is an unofficial expansion card for the Commodore PET 3032 that adds two AY-8910 sound chips, providing stereo music playback. The left channel is AY 1, the right channel is AY 2. Each chip has 3 tone channels, 1 noise generator, and a per-channel volume/envelope system.

The AY-8910 chips run at a 1 MHz internal clock. This clock frequency determines the frequency divider values needed to produce specific musical notes.

## I/O Addresses

The board occupies 4 memory-mapped addresses at `$A000`-`$A003`. This region is otherwise the expansion ROM area (`$A000`-`$AFFF`); the PetAY board decodes only the first 4 bytes.

| Address | Register | Chip         | Role                             |
|---------|----------|--------------|----------------------------------|
| `$A000` | AY_REG_L | AY 1 (left)  | Select AY register (0-15)        |
| `$A001` | AY_VAL_L | AY 1 (left)  | Write value to selected register |
| `$A002` | AY_REG_R | AY 2 (right) | Select AY register (0-15)        |
| `$A003` | AY_VAL_R | AY 2 (right) | Write value to selected register |

Each AY chip has 16 internal registers. To write a value, first write the register number to the select register, then write the value to the value register. Both writes take effect immediately.

## AY-8910 Register Map

| Offset | Name        | Description                              |
|--------|-------------|------------------------------------------|
| `$00`  | FREQ_FINE_A | Channel A frequency fine (low byte)      |
| `$01`  | FREQ_HIGH_A | Channel A frequency coarse (high byte)   |
| `$02`  | FREQ_FINE_B | Channel B frequency fine (low byte)      |
| `$03`  | FREQ_HIGH_B | Channel B frequency coarse (high byte)   |
| `$04`  | FREQ_FINE_C | Channel C frequency fine (low byte)      |
| `$05`  | FREQ_HIGH_C | Channel C frequency coarse (high byte)   |
| `$06`  | NOISE       | Noise generator frequency (5-bit)        |
| `$07`  | MIXER       | Tone and noise enable per channel        |
| `$08`  | VOLUME_A    | Channel A volume (0-15) or envelope mode |
| `$09`  | VOLUME_B    | Channel B volume (0-15) or envelope mode |
| `$0A`  | VOLUME_C    | Channel C volume (0-15) or envelope mode |
| `$0B`  | ENV_FINE    | Envelope frequency fine (low byte)       |
| `$0C`  | ENV_HIGH    | Envelope frequency coarse (high byte)    |
| `$0D`  | ENV_SHAPE   | Envelope shape (4-bit)                   |
| `$0E`  | IO_A        | I/O port A (not used for sound)          |
| `$0F`  | IO_B        | I/O port B (not used for sound)          |

Registers `$0E` and `$0F` are general-purpose I/O ports on the AY-8910. The PetAY board does not expose them for sound; they are not used in typical music programming.

## Frequency Calculation

Each tone channel has a 12-bit frequency divider split across two registers: fine (low 8 bits) and coarse (high 4 bits). The output frequency is:

```
f = clock / (16 * divider)
```

With the PetAY's 1 MHz clock:

```
f = 1000000 / (16 * divider)
divider = 1000000 / (16 * f)
```

The divider is `coarse * 256 + fine`, giving a range of 1-4095. The minimum frequency is `1000000 / (16 * 4095)` = 15.3 Hz. The maximum practical frequency at divider 1 is 62500 Hz.

### Note Frequency Table

Divider values for equal-temperament notes, calculated for 1 MHz clock:

| Note | Freq (Hz) | Divider | Fine  | Coarse |
|------|-----------|---------|-------|--------|
| C3   | 130.81    | 478     | `$DE` | `$01`  |
| D3   | 146.83    | 426     | `$AA` | `$01`  |
| E3   | 164.81    | 379     | `$7B` | `$01`  |
| F3   | 174.61    | 358     | `$66` | `$01`  |
| G3   | 196.00    | 319     | `$3F` | `$01`  |
| A3   | 220.00    | 284     | `$1C` | `$01`  |
| B3   | 246.94    | 253     | `$FD` | `$00`  |
| C4   | 261.63    | 239     | `$EF` | `$00`  |
| D4   | 293.66    | 213     | `$D5` | `$00`  |
| E4   | 329.63    | 190     | `$BE` | `$00`  |
| F4   | 349.23    | 179     | `$B3` | `$00`  |
| G4   | 392.00    | 159     | `$9F` | `$00`  |
| A4   | 440.00    | 142     | `$8E` | `$00`  |
| B4   | 493.88    | 127     | `$7F` | `$00`  |
| C5   | 523.25    | 119     | `$77` | `$00`  |
| D5   | 587.33    | 106     | `$6A` | `$00`  |
| E5   | 659.25    | 95      | `$5F` | `$00`  |
| F5   | 698.46    | 89      | `$59` | `$00`  |
| G5   | 783.99    | 80      | `$50` | `$00`  |
| A5   | 880.00    | 71      | `$47` | `$00`  |
| B5   | 987.77    | 63      | `$3F` | `$00`  |
| C6   | 1046.50   | 60      | `$3C` | `$00`  |

## Mixer Register ($07)

The mixer register controls which channels produce tone and which produce noise. A bit value of 0 enables the function, 1 disables it.

| Bit | 0 = Enable      | 1 = Disable         |
|-----|-----------------|---------------------|
| 0   | Channel A tone  | Channel A tone off  |
| 1   | Channel B tone  | Channel B tone off  |
| 2   | Channel C tone  | Channel C tone off  |
| 3   | Channel A noise | Channel A noise off |
| 4   | Channel B noise | Channel B noise off |
| 5   | Channel C noise | Channel C noise off |
| 6-7 | (unused)        | (unused)            |

To enable only channel A tone: set bits 0-5 to `111110` = `$FE`. To enable all three tone channels: `$F8`. To enable channel A tone and noise: `$3E`.

## Volume Registers ($08-$0A)

Each volume register uses bits 0-3 for the volume level (0-15, where 15 is maximum). Bit 4 enables the envelope generator for that channel -- when set, the volume bits are ignored and the envelope generator controls the amplitude.

| Bit | Role                                               |
|-----|----------------------------------------------------|
| 4   | Envelope mode (1 = use envelope, 0 = fixed volume) |
| 3-0 | Volume level (0-15)                                |

## Envelope Generator

The envelope generator produces automatic volume changes (attack, decay, sustain, release patterns). It has its own 16-bit frequency divider (`$0B` fine, `$0C` coarse) and a shape register (`$0D`).

The envelope frequency uses the same formula as tone channels but with a different divisor:

```
f_env = clock / (256 * divider)
```

### Envelope Shape Register ($0D)

| Bit | Role                                          |
|-----|-----------------------------------------------|
| 0   | Continue (0 = one-shot, 1 = repeat)           |
| 1   | Attack/Decay (0 = decay, 1 = attack)          |
| 2   | Alternate (0 = normal, 1 = alternate up/down) |
| 3   | Hold (0 = cycle, 1 = hold at end)             |

Common envelope shapes:

| Shape | Bits | Description          |
|-------|------|----------------------|
| `$00` | 0000 | Sawtooth decay       |
| `$04` | 0100 | Triangle, no hold    |
| `$08` | 1000 | Sawtooth attack      |
| `$0C` | 1100 | Triangle attack      |
| `$0A` | 1010 | Attack-decay (pluck) |

To use the envelope on a channel, set bit 4 of that channel's volume register and write the envelope shape to `$0D`. The shape register is edge-triggered -- writing to it restarts the envelope.

## Writing to a Register

To write a value to an AY register, write the register number to the select register, then the value to the value register:

```asm
AY_REG_L = $A000         ; left AY select register
AY_VAL_L  = $A001         ; left AY value register

        lda #$08              ; register 8 = VOLUME_A
        sta AY_REG_L
        lda #$0F              ; volume 15 (maximum)
        sta AY_VAL_L
```

## Register Write Subroutine

A reusable subroutine that writes A to register X on the left AY chip. The caller saves and restores X; the routine clobbers nothing else.

```asm
AY_REG_L = $A000
AY_VAL_L  = $A001

ay_write_l:            ; X = register number (0-15), A = value; clobbers nothing.

        stx AY_REG_L
        sta AY_VAL_L
        rts
```

For the right AY chip, use `$A002`/`$A003`:

```asm
AY_REG_R = $A002
AY_VAL_R  = $A003

ay_write_r:            ; X = register number (0-15), A = value; clobbers nothing.

        stx AY_REG_R
        sta AY_VAL_R
        rts
```

## Playing a Tone

Play A4 (440 Hz) on channel A of the left AY chip. The divider for A4 at 1 MHz is 142 (`$8E` fine, `$00` coarse).

```asm
AY_REG_L = $A000
AY_VAL_L  = $A001

play_a4_left:

        ldx #$00              ; FREQ_FINE_A
        lda #$8E              ; 142 = A4 at 1 MHz
        stx AY_REG_L
        sta AY_VAL_L

        ldx #$01              ; FREQ_HIGH_A
        lda #$00
        stx AY_REG_L
        sta AY_VAL_L

        ldx #$07              ; MIXER: enable channel A tone only
        lda #$FE              ; 11111110 -> A tone on, B/C off, all noise off
        stx AY_REG_L
        sta AY_VAL_L

        ldx #$08              ; VOLUME_A
        lda #$0F              ; maximum volume
        stx AY_REG_L
        sta AY_VAL_L
        rts
```

## Silencing a Channel

Set the mixer bit for the channel to 1 (disabled), or set its volume to 0:

```asm
        ldx #$08              ; VOLUME_A
        lda #$00              ; volume 0
        stx AY_REG_L
        sta AY_VAL_L
```

## Silencing Both Chips

To silence all output on both AY chips, disable all tone and noise channels via the mixer register:

```asm
AY_REG_L = $A000
AY_VAL_L  = $A001
AY_REG_R = $A002
AY_VAL_R  = $A003

silence_both:

        ldx #$07              ; MIXER register
        lda #$FF              ; all tone and noise off
        stx AY_REG_L
        sta AY_VAL_L
        stx AY_REG_R
        sta AY_VAL_R
        rts
```

Always silence both chips before returning to BASIC.

## BASIC Example

The following BASIC program plays A4 (440 Hz) on the left AY and a higher tone on the right AY:

```basic
10 POKE 40960,0:POKE 40961,142
20 POKE 40960,1:POKE 40961,0
30 POKE 40960,7:POKE 40961,254
40 POKE 40960,8:POKE 40961,15
50 POKE 40962,0:POKE 40963,125
60 POKE 40962,1:POKE 40963,0
70 POKE 40962,7:POKE 40963,254
80 POKE 40962,8:POKE 40963,15
```

`40960` = `$A000` (left control), `40961` = `$A001` (left value), `40962` = `$A002` (right control), `40963` = `$A003` (right value).

Lines 10-40 set the left AY: channel A divider = 142 (A4), mixer = `$FE` (channel A tone on), volume = 15. Lines 50-80 set the right AY: channel A divider = 125, mixer = `$FE`, volume = 15.

To stop the sound, run:

```basic
10 POKE 40960,7:POKE 40961,255
20 POKE 40962,7:POKE 40963,255
```
