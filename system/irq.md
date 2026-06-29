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

The KERNAL IRQ entry at `$E442` saves A/X/Y, then dispatches through CINV. The clock/keyboard handler lives at approximately `$E455` in Editor ROM, but this address varies between ROM versions. The safest way to chain is through the saved original CINV value.

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

## VBLANK Polling (No IRQ)

To synchronize to VBLANK without enabling interrupts, poll VIA PORT B bit 5:

```asm
wait_vblank:

        lda $E840               ; VIA PORT B
        and #$20                ; bit 5 = screen retrace signal
        beq wait_vblank         ; wait until high
```

This is simpler than IRQ setup for single-threaded programs that only need frame sync.

The polling approach does not require reading `$E813`.

## Common Mistakes

| Mistake                          | Consequence                           | Fix                                     |
|----------------------------------|---------------------------------------|-----------------------------------------|
| Skip `$E812` read                | IRQ re-fires, CPU locked              | Always read `$E812` (PIA1 Port B) in VBLANK handler |
| Skip `CLD`                       | Wrong ADC/SBC results in handler      | Add `CLD` after register saves          |
| No `SEI`/`CLI` around CINV write | IRQ fires during partial vector write | Always bracket CINV update with SEI/CLI |
| Don't restore CINV on exit       | KERNAL broken after program exits     | Save `old_cinv`, restore in cleanup     |
| Use `JSR` to chain               | `RTI` returns to wrong address        | Use `JMP` to chain to KERNAL handler    |
