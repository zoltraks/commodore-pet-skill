# CPU Architecture

## Purpose

> **Scope:** MOS 6502: registers, flags, instruction set, addressing modes, cycle timing, stack, interrupts
> **Key items:** A/X/Y/SP/PC/P registers; N/V/C/D/I/Z/B flags; immediate/ZP/absolute/indexed/indirect modes; 7-cycle BRK/IRQ; 60 Hz PET VBLANK IRQ via PIA1 CB1

This file covers the 6502 CPU as used in the Commodore PET 3032 in four progressive layers:

- **Quick-lookup table** - scan or search for the fact you need; jump to the section directly
- **Reference tables & register maps** - the dense lookup layer most frequently referenced
- **Working code examples** - verified ASM snippets for PET
- **Deep reference notes** - edge cases, caveats, implementation rules

| Out of scope                          | See instead        |
|---------------------------------------|--------------------|
| PET-specific I/O chips (VIA/PIA/CRTC) | `hardware/chip.md` |
| KERNAL routines and vectors           | `system/kernal.md` |

All values hex ($NN) unless noted decimal.

The PET 3032 uses a 1 MHz NMOS 6502.

## Quick-Lookup

| Need                                | Section                            |
|-------------------------------------|------------------------------------|
| Register descriptions               | Registers                          |
| Flag bits / P-register layout       | Flag Bits (P Register)             |
| Which instructions affect flags     | Flag Update Reference              |
| Load and store instructions         | Load and Store                     |
| Arithmetic and logical instructions | Arithmetic and Logical             |
| Branch and jump instructions        | Branch and Jump                    |
| Stack and transfer instructions     | Stack and Transfers                |
| Shift/rotate and flag ops           | Shift, Rotate, and Flag Operations |
| Addressing mode syntax and cycles   | Addressing Modes                   |
| IRQ / NMI / BRK dispatch            | Interrupts                         |
| Zero-page idioms for PET            | Zero-Page Idioms for PET           |

## Registers

| Register | Size   | Description                        |
|----------|--------|------------------------------------|
| A        | 8-bit  | Accumulator                        |
| X        | 8-bit  | Index register X                   |
| Y        | 8-bit  | Index register Y                   |
| SP       | 8-bit  | Stack pointer ($0100-$01FF)        |
| PC       | 16-bit | Program counter                    |
| P        | 8-bit  | Processor status (N V - B D I Z C) |

## Flag Bits (P Register)

| Bit | Flag | Description                                               |
|-----|------|-----------------------------------------------------------|
| 7   | N    | Negative (sign bit of last operation)                     |
| 6   | V    | Overflow                                                  |
| 5   | -    | Unused (always 1 on stack, 0 when read in some contexts)  |
| 4   | B    | Break (set by BRK, cleared by IRQ; not directly readable) |
| 3   | D    | Decimal mode                                              |
| 2   | I    | Interrupt disable                                         |
| 1   | Z    | Zero (set if result was zero)                             |
| 0   | C    | Carry                                                     |

**Critical nuance:** NMOS 6502 does NOT auto-clear D on IRQ entry.

Always `CLD` in interrupt handlers that use ADC/SBC.

### Flag Update Reference

Branch instructions test flags set by the **most recent instruction that updates flags**. Many instructions do not affect flags at all -- placing them between a flag-setting instruction and a branch changes which flags the branch tests.

| Instruction(s)             | Flags Affected    |
|----------------------------|-------------------|
| `lda`, `ldx`, `ldy`        | N, Z              |
| `sta`, `stx`, `sty`        | none              |
| `inx`, `dex`, `iny`, `dey` | N, Z              |
| `inc`, `dec` (memory)      | N, Z              |
| `asl`, `lsr`, `rol`, `ror` | N, Z, C           |
| `adc`, `sbc`               | N, V, Z, C        |
| `cmp`, `cpx`, `cpy`        | N, Z, C           |
| `and`, `ora`, `eor`        | N, Z              |
| `tax`, `txa`, `tay`, `tya` | N, Z              |
| `jsr`, `rts`, `jmp`, `rti` | none              |
| `pha`, `pla`, `php`, `plp` | N, Z (`pla` only) |
| `txs`, `tsx`               | N, Z (`tsx` only) |
| `clc`, `sec`, `cld`, `sed` | C or D (single)   |
| `clv`                      | V                 |
| `bit`                      | N, V, Z           |

The most common bug from misunderstanding flag updates is the branch-after-load pattern, where `sta` (which affects no flags) between `dex` and `bne` causes the branch to test the loaded value instead of the counter. See `code/standard.md` for the full bug pattern and decision rule.

## Load and Store

| Instruction | Description       | Example        |
|-------------|-------------------|----------------|
| LDA         | Load accumulator  | `lda #$00`     |
| LDX         | Load X register   | `ldx #$00`     |
| LDY         | Load Y register   | `ldy #$00`     |
| STA         | Store accumulator | `sta SCREEN,x` |
| STX         | Store X register  | `stx $F7`      |
| STY         | Store Y register  | `sty $F8`      |

## Arithmetic and Logical

| Instruction | Description         | Example         |
|-------------|---------------------|-----------------|
| ADC         | Add with carry      | `adc #$01`      |
| SBC         | Subtract with carry | `sbc #$01`      |
| INC         | Increment memory    | `inc $F7`       |
| INX         | Increment X         | `inx`           |
| INY         | Increment Y         | `iny`           |
| DEC         | Decrement memory    | `dec $F8`       |
| DEX         | Decrement X         | `dex`           |
| DEY         | Decrement Y         | `dey`           |
| AND         | Logical AND         | `and #$0F`      |
| ORA         | Logical OR          | `ora #$20`      |
| EOR         | Exclusive OR        | `eor #$FF`      |
| CMP         | Compare accumulator | `cmp #$84`      |
| CPX         | Compare X           | `cpx #$0F`      |
| CPY         | Compare Y           | `cpy #$00`      |

## Branch and Jump

| Instruction | Description              | Condition | Example     |
|-------------|--------------------------|-----------|-------------|
| BNE         | Branch if not equal      | Z=0       | `bne loop`  |
| BEQ         | Branch if equal          | Z=1       | `beq done`  |
| BPL         | Branch if plus           | N=0       | `bpl skip`  |
| BMI         | Branch if minus          | N=1       | `bmi error` |
| BCC         | Branch if carry clear    | C=0       | `bcc next`  |
| BCS         | Branch if carry set      | C=1       | `bcs retry` |
| BVC         | Branch if overflow clear | V=0       | `bvc ok`    |
| BVS         | Branch if overflow set   | V=1       | `bvs fail`  |
| JMP         | Jump to address          | -         | `jmp start` |
| JSR         | Jump to subroutine       | -         | `jsr GETIN` |
| RTS         | Return from subroutine   | -         | `rts`       |
| RTI         | Return from interrupt    | -         | `rti`       |
| BRK         | Force break              | -         | `brk`       |

**Branch timing:** Taken, same page = 3 cycles. Taken, cross page = 4 cycles. Not taken = 2 cycles.

## Stack and Transfers

| Instruction | Description                 | Example |
|-------------|-----------------------------|---------|
| PHA         | Push accumulator            | `pha`   |
| PLA         | Pull accumulator            | `pla`   |
| PHP         | Push processor status       | `php`   |
| PLP         | Pull processor status       | `plp`   |
| TXS         | Transfer X to stack pointer | `txs`   |
| TSX         | Transfer stack pointer to X | `tsx`   |
| TAX         | Transfer A to X             | `tax`   |
| TXA         | Transfer X to A             | `txa`   |
| TAY         | Transfer A to Y             | `tay`   |
| TYA         | Transfer Y to A             | `tya`   |

## Shift, Rotate, and Flag Operations

| Instruction | Description             | Example |
|-------------|-------------------------|---------|
| LSR         | Logical shift right     | `lsr`   |
| ASL         | Arithmetic shift left   | `asl`   |
| ROR         | Rotate right            | `ror`   |
| ROL         | Rotate left             | `rol`   |
| CLC         | Clear carry             | `clc`   |
| SEC         | Set carry               | `sec`   |
| CLI         | Clear interrupt disable | `cli`   |
| SEI         | Set interrupt disable   | `sei`   |
| CLD         | Clear decimal mode      | `cld`   |
| SED         | Set decimal mode        | `sed`   |
| CLV         | Clear overflow          | `clv`   |

## Addressing Modes

| Mode                  | Syntax    | Cycles            | Example       |
|-----------------------|-----------|-------------------|---------------|
| Implied / accumulator | none      | 2                 | `inx`, `rts`  |
| Immediate             | `#$value` | 2                 | `lda #$FF`    |
| Zero page             | `$zp`     | 3                 | `lda $F7`     |
| Zero page,X           | `$zp,x`   | 4                 | `lda $F7,x`   |
| Zero page,Y           | `$zp,y`   | 4                 | `lda $F7,y`   |
| Absolute              | `$addr`   | 4                 | `lda $8000`   |
| Absolute,X            | `$addr,x` | 4 (+1 page cross) | `lda $8000,x` |
| Absolute,Y            | `$addr,y` | 4 (+1 page cross) | `lda $8000,y` |
| Indirect              | `($addr)` | 5                 | `jmp ($0300)` |
| Indexed indirect      | `($zp,x)` | 6                 | `lda ($F7,x)` |
| Indirect indexed      | `($zp),y` | 5 (+1 page cross) | `lda ($F7),y` |
| Relative              | label     | 2/3/4             | `bne loop`    |

**NMOS 6502 page-cross penalty:**

- Read ops (`LDA abs,X`, `AND abs,Y`, `(zp),Y`) speculate fetch: +1 cycle if page crossed.
- Write ops (`STA abs,X`, `STA abs,Y`) always 5 cycles; no speculative write.
- `JMP ($xxFF)` bug: high byte fetched from `$xx00` instead of `$xx+1`.

## Interrupts

### IRQ (Maskable)

- Level-triggered. The 6502 responds when I-flag is clear.
- IRQ must be cleared at the device before `CLI`, or handler re-enters immediately.
- **PET source:** PIA1 CB1 (VBLANK from screen retrace, 60 Hz on PET 3032).
- Entry: 7 cycles. Stacks PC (low, high) then P (with B=0).
- NMOS 6502 does NOT auto-clear D. Always `CLD` in IRQ handlers using ADC/SBC.

### NMI (Non-Maskable)

- Edge-triggered on PET. Pressing NMI button asserts it once.
- Entry: same 7-cycle sequence as IRQ, but B=0 on stacked P.
- Cannot be disabled by SEI.

### BRK

- 7 cycles. B=1 on stacked P.
- PC+2 is stacked; vector fetched from `$FFFE/$FFFF`.
- Often used as software breakpoint or system call mechanism.

**PET interrupt hook example:**

```asm
        sei                     ; disable IRQs during hook install
        lda #<my_irq
        sta CINV                ; $0090: hardware IRQ vector
        lda #>my_irq
        sta CINV+1
        cli                     ; re-enable

my_irq:

        pha                     ; save A
        txa
        pha                     ; save X
        tya
        pha                     ; save Y
        cld                     ; mandatory for ADC/SBC safety
        ; ... handler body ...
        pla
        tay
        pla
        tax
        pla
        rti
```

## Zero-Page Idioms for PET

| Idiom               | Example                                       | Notes                              |
|---------------------|-----------------------------------------------|------------------------------------|
| 16-bit increment    | `INC ptr / BNE skip / INC ptr+1`              | 5c + 2c + 2c; skip if no carry     |
| 16-bit decrement    | `LDA ptr / BNE dohi / DEC ptr+1`              | test low byte first                |
| Bit flag set        | `ORA #$80`                                    | set bit 7                          |
| Bit flag clear      | `AND #~$80`                                   | clear bit 7                        |
| Negative-index loop | `LDY #-n` ... `DEY / BPL loop`                | counts n+1 times through 0         |
| Fast save/restore   | `STA zp / STX zp+1`                           | faster than stack for repeated use |
| 16-bit load         | `LDA #<val / STA ptr / LDA #>val / STA ptr+1` | standard PET pattern               |

