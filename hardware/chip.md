# PET 3032 Hardware Chips

## Purpose

> **Scope:** VIA 6522, PIA 6520 (x2), CRTC 6545, I/O decoding, screen RAM, character generator, VBLANK
> **Key items:** VIA $E840-$E84F, PIA1 $E810-$E813, PIA2 $E820-$E823, CRTC $E880-$E881, SCREEN=$8000, PCR=$E84C, PCR_U=$0C, PCR_L=$08

This file covers the PET 3032 hardware chips in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need
- **Reference tables & register maps** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                    | See instead        |
|---------------------------------|--------------------|
| 6502 CPU instructions and flags | `hardware/cpu.md`  |
| KERNAL routines and vectors     | `system/kernal.md` |
| Screen I/O and PETSCII          | `system/screen.md` |

## Memory Map Overview

| Region     | Address Range | Size   | Description                  |
|------------|---------------|--------|------------------------------|
| RAM        | $0000 - $7FFF | 32 KB  | Main system RAM              |
| Screen RAM | $8000 - $83E7 | 1000 B | 40 columns by 25 rows        |
| I/O Area   | $E800 - $EFFF | 2 KB   | Memory-mapped I/O devices    |
| ROM        | $F000 - $FFFF | 4 KB   | System ROM (BASIC, KERNAL)   |
| BASIC ROM  | $C000 - $DFFF | 8 KB   | BASIC keywords and operators |
| Editor ROM | $E000 - $E7FF | 2 KB   | Screen editor functions      |

### Screen Memory Layout

- Screen RAM base: `$8000`
- 40 columns, 25 rows = 1000 bytes
- Row 0: `$8000` - `$8027`
- Row 1: `$8028` - `$804F`
- ...
- Row 24: `$83C0` - `$83E7`
- Bytes `$83E8` - `$83FF` are unused video RAM

## I/O Area Decoding ($E800-$E8FF)

The I/O area uses minimal decoding.

Address lines A4-A7 select individual chips:

| Chip  | Address Range | A7  | A6  | A5  | A4  |
|-------|---------------|-----|-----|-----|-----|
| PIA 1 | $E810-$E81F   | 0   | 0   | 0   | 1   |
| PIA 2 | $E820-$E82F   | 0   | 0   | 1   | 0   |
| VIA   | $E840-$E84F   | 0   | 1   | 0   | 0   |
| CRTC  | $E880-$E88F   | 1   | 0   | 0   | 0   |

Multiple chips may be selected simultaneously at overlapping addresses.

Only the normal mappings are described here.

## PIA 1 ($E810-$E813) - Keyboard, Tape, VBLANK

PIA 1 handles keyboard scanning, cassette I/O, and the VBLANK interrupt source.

| Address | Register | Description                                                                                              |
|---------|----------|----------------------------------------------------------------------------------------------------------|
| $E810   | PORT A   | Keyboard row select (bits 3-0), IEEE EOI in (bit 6), cassette sense (bits 5,4), diagnostic sense (bit 7) |
| $E811   | CRA      | Control register A: CA2 = screen blank (old PETs) / IEEE EOI out; CA1 = cassette #1 read                 |
| $E812   | PORT B   | Keyboard row contents (bits 7-0). Usually all or all-but-one bits set.                                   |
| $E813   | CRB      | Control register B: CB2 = cassette #1 motor (0=on, 1=off); CB1 = screen retrace detection in             |

### VBLANK Detection

- PIA 1 CB1 is connected to the screen vertical blank (retrace) signal.
- VIA PB5 is also connected to the same signal.
- The vertical blank generates a 60 Hz IRQ on the PET 3032.

### VBLANK IRQ Acknowledgement

The VBLANK IRQ is level-triggered via PIA 1 CB1.

The interrupt flag remains set until the PIA is acknowledged by **reading PIA 1 CRB ($E813)**.

If a custom IRQ handler does not read $E813, the interrupt re-fires immediately after `RTI`, locking the CPU.

```asm
; Inside a custom VBLANK IRQ handler:
my_vblank_irq:

        bit $E813               ; read PIA1 CRB to acknowledge VBLANK IRQ
        ; ... handler body ...
        rti
```

When chaining to the KERNAL IRQ handler, the KERNAL reads $E813 itself.

If you replace CINV completely, add the read explicitly.

To wait for VBLANK without enabling interrupts:

```asm
wait_vblank:

        lda $E840       ; VIA PORT B
        and #$20        ; mask bit 5 (screen retrace)
        beq wait_vblank ; wait until high
```

### Cassette Motor Control

Motor control uses PIA 1 CRB bit 2 (CB2 output).

Bit 2 low = motor on. Bit 2 high = motor off.

```asm
        lda $E813       ; PIA 1 CRB
        and #$FB        ; clear bit 2 -> motor on
        sta $E813

        ; turn motor off:
        lda $E813
        ora #$04        ; set bit 2 -> motor off
        sta $E813
```

## PIA 2 ($E820-$E823) - IEEE-488

PIA 2 handles the IEEE-488 bus data and control lines.

| Address | Register | Description                                                |
|---------|----------|------------------------------------------------------------|
| $E820   | PORT A   | Input buffer for IEEE data lines                           |
| $E821   | CRA      | Control register A: CA2 = IEEE NDAC out; CA1 = IEEE ATN in |
| $E822   | PORT B   | Output buffer for IEEE data lines                          |
| $E823   | CRB      | Control register B: CB2 = IEEE DAV out; CB1 = IEEE SRQ in  |

## VIA 6522 ($E840-$E84F)

The VIA provides timers, shift register, and the user port.

| Address | Register | Description                                                                    |
|---------|----------|--------------------------------------------------------------------------------|
| $E840   | PORT B   | IEEE control, screen retrace in (PB5), cassette motor, cassette write, ATN out |
| $E841   | PORT A   | User port with CA2 handshake                                                   |
| $E842   | DDRB     | Data direction register B                                                      |
| $E843   | DDRA     | Data direction register A                                                      |
| $E844   | T1C-L    | Timer 1 low counter                                                            |
| $E845   | T1C-H    | Timer 1 high counter                                                           |
| $E846   | T1L-L    | Timer 1 low latch                                                              |
| $E847   | T1L-H    | Timer 1 high latch                                                             |
| $E848   | T2C-L    | Timer 2 low counter                                                            |
| $E849   | T2C-H    | Timer 2 high counter                                                           |
| $E84A   | SR       | Shift register                                                                 |
| $E84B   | ACR      | Auxiliary control register                                                     |
| $E84C   | PCR      | Peripheral control register                                                    |
| $E84D   | IFR      | Interrupt flag register                                                        |
| $E84E   | IER      | Interrupt enable register                                                      |
| $E84F   | PORT A   | User port without CA2 handshake                                                |

### PCR ($E84C) - Peripheral Control Register

Power-on value is `$0C` or `$0E`.

Bits 3-1 control CA2 (character set selection):

- CA2 high (`$0C`): uppercase and graphics charset
- CA2 low (`$08`): lowercase and text charset

Standard equates:

```asm
PCR     = $E84C
PCR_U   = $0C           ; CA2 high: uppercase / graphics charset
PCR_L   = $08           ; CA2 low:  lowercase / text charset
```

### ACR ($E84B) - Auxiliary Control Register

| Bits | Function                                                                             |
|------|--------------------------------------------------------------------------------------|
| 7-6  | Timer 1 control: 00=one-shot, 01=continuous, 10/11=PB7 output                        |
| 5    | Timer 2 control: 0=one-shot, 1=count PB6 pulses                                      |
| 4-2  | Shift register control: 000=disabled, 001=shift in by T2, 100=free run by T2 (sound) |
| 1    | PORT B latch enable                                                                  |
| 0    | PORT A latch enable                                                                  |

### Timer 1 Example

```asm
        lda #$FF
        sta $E844       ; T1C-L = $FF
        sta $E845       ; T1C-H = $FF -> starts countdown
        ; T1 now counting down from $FFFF at 1 MHz
```

### VIA Sound via CB2 and Shift Register

The internal PET speaker is wired to VIA CB2 (user port pin M).

The shift register, clocked by Timer 2, drives CB2 as a serial output without CPU involvement.

| Register | Address | Sound Role                                  |
|----------|---------|---------------------------------------------|
| ACR      | $E84B   | Set to $10 to enable SR free-running on T2  |
| SR       | $E84A   | Bit pattern: $0F (base), $33 (x2), $55 (x4) |
| T2C-L    | $E848   | Pitch divider (lower = higher frequency)    |

Set ACR=$00 to stop sound.

Full documentation in `hardware/sound.md`.

## CRTC 6545 ($E880-$E88F)

Available on PETs with board revisions #3 and above.

The PET 3032 uses board #3.

- Two registers: `$E880` (address) and `$E881` (data)
- The 6545 generates all video timing
- Vertical sync is inverted and connected to PIA1 CB1 for IRQ generation

### Relevant CRTC Internal Registers

| Register | Number | Description               |
|----------|--------|---------------------------|
| R0       | $00    | Horizontal total          |
| R1       | $01    | Horizontal displayed      |
| R2       | $02    | Horizontal sync position  |
| R3       | $03    | Horizontal sync width     |
| R4       | $04    | Vertical total            |
| R5       | $05    | Vertical total adjust     |
| R6       | $06    | Vertical displayed        |
| R7       | $07    | Vertical sync position    |
| R12      | $0C    | Screen start address high |
| R13      | $0D    | Screen start address low  |

### CRTC Register Access

```asm
        lda #$0C        ; select R12 (screen start high)
        sta $E880       ; write to address register
        lda #$80        ; screen high byte
        sta $E881       ; write to data register
```

## Character Generator

- Character ROM is internal to the video hardware
- 128 characters, 8x8 pixels each
- Two character sets selected via VIA CA2 (PCR register):

  - Uppercase + graphics (`$0C`)
  - Lowercase + uppercase (`$08`)

- Bit 7 of screen RAM inverts the character (reverse video)

### Character Set Switching

```asm
        lda PCR
        and #$F7        ; clear bit 3 (CA2 low)
        ora #$08        ; ensure CA2 low -> lowercase/text
        sta PCR

        ; or switch back to uppercase/graphics:
        lda PCR
        ora #$0C        ; CA2 high
        sta PCR
```

## Refresh Rates

| Model     | Refresh Rate | Region         |
|-----------|--------------|----------------|
| PET 3032  | 60 Hz        | North American |
| PET 3032B | 50 Hz        | European       |

The VBLANK signal on PIA1 CB1 corresponds to the refresh rate.

## PET 3032 Specifics

- 32 KB of RAM (`$0000-$7FFF`)
- Screen memory starts at `$8000` and occupies 1000 bytes
- The PET 3032 uses the 6545 CRTC (board #3)
- 4116 DRAM and 2532-compatible 24-pin ROMs
- No hardware sprites, no bitmap modes, no hardware scrolling
- No dedicated sound hardware (except internal beeper)
