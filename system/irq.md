# IRQ & VBLANK

## Purpose

> **Scope:** 6502 IRQ mechanism, CINV vector, PET VBLANK source (PIA1 CB1), handler setup/teardown, VBLANK polling
> **Key items:** CINV=$0090, PIA1 CRB=$E813, VIA PB5=$E840 bit 5, 60 Hz VBLANK, CLD mandatory

| Out of scope                      | See instead        |
|-----------------------------------|--------------------|
| IRQ instruction timings and flags | `hardware/cpu.md`  |
| VIA/PIA register maps             | `hardware/chip.md` |
| KERNAL jump table                 | `system/kernal.md` |

## VBLANK Source

The PET 3032 generates a 60 Hz interrupt from the screen vertical retrace.

The CRTC 6545 generates vertical sync, which is inverted and connected to PIA 1 CB1.

The CB1 interrupt flag stays set until the PIA is acknowledged by reading PIA 1 Port B (`$E812`). On the 6520 PIA, CB1's flag is cleared only by reading the Port B data register — reading Control Register B ($E813) does not clear it.

If your IRQ handler does not read `$E812`, the interrupt re-fires immediately after `RTI`, locking the CPU in an infinite interrupt loop.

VIA PORT B bit 5 (`$E840` bit 5) carries the same VBLANK signal and is used for polling without enabling IRQs.

## IRQ Vectors

| Address     | Name  | Role                              |
|-------------|-------|-----------------------------------|
| $0090-$0091 | CINV  | Hardware IRQ vector (your target) |
| $0092-$0093 | CBINV | BRK vector                        |
| $0094-$0095 | NMINV | NMI vector                        |

The 6502 IRQ vector at `$FFFE`/`$FFFF` points into the KERNAL, which then jumps through CINV.

Replacing CINV is the standard way to install a custom IRQ handler on the PET.

## Installing a Custom IRQ Handler

Always save the original CINV value and restore it on exit.

```asm
CINV    = $0090

old_cinv:

        word 0

install_irq:

        sei
        lda CINV
        sta old_cinv
        lda CINV+1
        sta old_cinv+1
        lda #<my_irq
        sta CINV
        lda #>my_irq
        sta CINV+1
        cli
        rts

restore_irq:

        sei
        lda old_cinv
        sta CINV
        lda old_cinv+1
        sta CINV+1
        cli
        rts
```

## IRQ Handler Template

```asm
my_irq:

        pha                     ; save A
        txa
        pha                     ; save X
        tya
        pha                     ; save Y
        cld                     ; mandatory: NMOS 6502 does not clear D on IRQ entry
        bit $E812               ; read PIA1 Port B -- acknowledges VBLANK IRQ
        ; ... your handler code here ...
        pla
        tay
        pla
        tax
        pla
        rti
```

The `bit $E812` read is mandatory.

Without it, the VBLANK IRQ remains asserted and the handler re-enters immediately after `rti`.

The `cld` is mandatory.

The NMOS 6502 does not clear the decimal flag on IRQ entry.

`ADC`/`SBC` inside an IRQ handler produce wrong results in decimal mode.

## Chaining to the KERNAL Handler

The hardware IRQ vector (`$FFFE`) points to the KERNAL IRQ entry at `$E61B`, which saves A/X/Y and then dispatches through CINV (`$0090`). The default clock/keyboard handler that CINV points to is at `$E62E` in Editor ROM. Both addresses are specific to BASIC 2 (new ROM); the safest, version-independent way to chain is through the saved original CINV value rather than a hard-coded address.

To run your code first then pass control to the KERNAL:

```asm
old_cinv:

        word 0                  ; save original CINV here before install

my_irq:

        pha
        txa
        pha
        tya
        pha
        cld
        bit $E812               ; acknowledge VBLANK: read PIA1 Port B
        ; ... your code here ...
        pla
        tay
        pla
        tax
        pla
        jmp (old_cinv)          ; chain to original KERNAL handler (ends with RTI)
```

Do not use `jsr` to chain. The KERNAL handler ends with `rti`, which returns from the interrupt correctly.

When chaining via old_cinv, the KERNAL also reads `$E812` during its own processing, so a double-read is harmless.

## Replacing the KERNAL Handler Completely

If you replace CINV entirely and do not chain, you must:

- Read `$E812` (PIA 1 Port B) yourself to acknowledge the VBLANK IRQ.
- Call UDTIM (`$FFEA`) yourself if you need the jiffy clock to advance.
- Scan the keyboard yourself if you need GETIN to work.

Most programs should chain rather than replace, unless they have very tight timing requirements.

### 60 Hz IRQ and Keyboard Auto-Repeat

The KERNAL keyboard scan that runs in the 60 Hz IRQ handler does more than just detect keypresses -- it also **auto-repeats** held keys into the keyboard buffer. Each scan cycle that finds a key still pressed appends its PETSCII code to the buffer (up to the 10-byte limit).

This means:

- If you replace CINV and do not chain to the KERNAL handler, `GETIN` will return nothing -- the keyboard buffer is never filled. You must implement your own keyboard scan, including repeat logic if you want it.
- If you chain to the KERNAL handler (the normal case), auto-repeat is always active. Programs that use `GETIN` to toggle UI elements on a single key must debounce the toggle key themselves. See `system/keyboard.md` "Toggle Key Debounce".
- Under VICE warp mode, the 60 Hz IRQ runs much faster than real time, so auto-repeat fills the buffer in milliseconds of wall-clock time. See `utility/vice-emulator.md` "Warp Mode and Keyboard Auto-Repeat".

## VBLANK Polling (No IRQ)

To synchronize to VBLANK without enabling interrupts, poll VIA PORT B bit 5. The signal is LOW during VBLANK (vertical retrace) and HIGH during active display.

A single-phase wait that only checks for HIGH returns at an arbitrary point during active display -- the worst moment to update screen RAM. To sync to the **start** of VBLANK, use a two-phase wait:

1. If already in VBLANK (bit 5 LOW), wait for it to end.
2. Wait for active display to end (bit 5 goes LOW again).
3. Return at the exact start of VBLANK.

```asm
VIA_PORTB   = $E840
RETRACE_BIT = $20

wait_vblank:

        lda VIA_PORTB           ; phase 1: wait while VBLANK active (bit 5 LOW)
        and #RETRACE_BIT
        beq wait_vblank         ; branch while LOW -- skip remaining VBLANK

vbl_wait:

        lda VIA_PORTB           ; phase 2: wait while active display (bit 5 HIGH)
        and #RETRACE_BIT
        bne vbl_wait            ; branch while HIGH -- wait for next VBLANK
        rts                     ; return at start of VBLANK
```

This is simpler than IRQ setup for single-threaded programs that only need frame sync.

The polling approach does not require reading `$E813`.

### Emulator Limitation: VICE xpet

VICE 3.7 xpet does not mirror the VBLANK signal onto VIA PB5 (`$E840` bit 5). The unbounded two-phase poll above loops forever under VICE because the retrace bit never toggles. The program appears frozen with the initial screen visible and keyboard input stops responding.

The KERNAL IRQ handler (driven by PIA1 CB1) still fires correctly under VICE, so `GETIN` works as long as the CPU is not stuck in a polling loop. The problem is exclusively the VIA PB5 poll.

Use a bounded poll that gives up after a fixed number of iterations per phase. On real hardware the bound is never reached. On VICE the bound expires and the caller proceeds without sync:

```asm
VIA_PORTB   = $E840
RETRACE_BIT = $20

wait_vblank:

        ldx #$00

wv_p1:

        lda VIA_PORTB
        and #RETRACE_BIT
        bne wv_p2               ; bit HIGH: VBLANK ended -> phase 2
        dex
        bne wv_p1
        rts                     ; phase 1 bound exhausted: give up (no sync)

wv_p2:

        ldx #$00

wv_p2_loop:

        lda VIA_PORTB
        and #RETRACE_BIT
        beq wv_done             ; bit LOW: VBLANK started
        dex
        bne wv_p2_loop
        rts                     ; phase 2 bound exhausted: give up (no sync)

wv_done:

        rts                     ; at start of VBLANK
```

A 256-iteration bound per phase is approximately 2 ms at 1 MHz. See `system/screen.md` for the full double-buffering present routine that uses this bounded poll.

## Common Mistakes

| Mistake                           | Consequence                               | Fix                                                                                    |
|-----------------------------------|-------------------------------------------|----------------------------------------------------------------------------------------|
| Skip `$E812` read                 | IRQ re-fires, CPU locked                  | Always read `$E812` (PIA1 Port B) in VBLANK handler                                    |
| Skip `CLD`                        | Wrong ADC/SBC results in handler          | Add `CLD` after register saves                                                         |
| No `SEI`/`CLI` around CINV write  | IRQ fires during partial vector write     | Always bracket CINV update with SEI/CLI                                                |
| Don't restore CINV on exit        | KERNAL broken after program exits         | Save `old_cinv`, restore in cleanup                                                    |
| Use `JSR` to chain                | `RTI` returns to wrong address            | Use `JMP` to chain to KERNAL handler                                                   |
| Unbounded PB5 poll under VICE     | Program hangs -- bit never toggles        | Bound each phase to 256 iterations                                                     |
| No debounce on a GETIN toggle key | Auto-repeat closes UI element immediately | Store toggle key + set countdown timer; see `system/keyboard.md` "Toggle Key Debounce" |
