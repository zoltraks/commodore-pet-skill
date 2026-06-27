# Bit Operations & Idioms

## Purpose

> **Scope:** 6502 bit manipulation, flag testing, pointer arithmetic, 16-bit INC/DEC, zero-page idioms
> **Key items:** ASL/LSR/ROL/ROR, bit masks, 16-bit pointers, compare-free loops, stack tricks

This file covers bit-operation patterns for the PET 3032 in four progressive layers:

- **Quick-lookup table** - scan or search for the pattern you need
- **Reference tables** - dense lookup layer
- **Working code examples** - verified ASM snippets
- **Deep reference notes** - edge cases, caveats, implementation rules

## Bit Manipulation

### Set/Clear/Toggle Bits

| Operation    | Pattern                    | Cycles |
|--------------|----------------------------|--------|
| Set bit N    | `ORA #(1<<N)`              | 2      |
| Clear bit N  | `AND #(255^(1<<N))`        | 2      |
| Toggle bit N | `EOR #(1<<N)`              | 2      |
| Test bit N   | `AND #(1<<N)` then check Z | 2      |

```asm
; Set bit 7
        lda value
        ora #$80
        sta value

; Clear bit 3
        lda value
        and #$F7
        sta value

; Toggle bit 0
        lda value
        eor #$01
        sta value
```

### Bit Test Without Load (BIT instruction)

```asm
        bit $E84D       ; test VIA IFR against A without changing A
        bvs timer1_irq  ; branch if bit 6 (V flag) set
```

## Shifts and Rotates

| Instruction | Action                              | Use Case                 |
|-------------|-------------------------------------|--------------------------|
| ASL         | Shift left, 0 into LSB, MSB into C  | Multiply by 2, pack bits |
| LSR         | Shift right, 0 into MSB, LSB into C | Divide by 2, unpack bits |
| ROL         | Rotate left through C               | 16-bit shift, serial I/O |
| ROR         | Rotate right through C              | 16-bit shift, serial I/O |

### 16-Bit Left Shift

```asm
        asl value_lo
        rol value_hi    ; C shifts into bit 0 of high byte
```

### 16-Bit Right Shift

```asm
        lsr value_hi
        ror value_lo    ; C shifts into bit 7 of low byte
```

## 16-Bit Pointer Arithmetic

### Increment 16-Bit Pointer

```asm
inc_ptr:

        inc ptr_lo
        bne done
        inc ptr_hi

done:

        rts
```

### Decrement 16-Bit Pointer

```asm
dec_ptr:

        lda ptr_lo
        bne skip
        dec ptr_hi

skip:

        dec ptr_lo
        rts
```

### Add 8-Bit Offset to 16-Bit Pointer

```asm
add_offset:

        clc
        lda ptr_lo
        adc offset
        sta ptr_lo
        bcc done
        inc ptr_hi

done:

        rts
```

## Mask and Lookup Patterns

### Nibble Swap

```asm
        asl             ; shift high nibble to low via C
        adc #$80
        asl
        adc #$80
        asl
        adc #$80
        asl
        adc #$80
        ; A now has nibbles swapped
```

### Table-Driven Bit Reverse

```asm
        ldx A
        lda bit_reverse_table,x

bit_reverse_table:

        byte $00,$80,$40,$C0,$20,$A0,$60,$E0
        byte $10,$90,$50,$D0,$30,$B0,$70,$F0
        ; ... (256 bytes total)
```

## Stack Tricks

### Fast A/X/Y Save/Restore

```asm
save_regs:

        sta save_a
        stx save_x
        sty save_y
        ; ... work ...
        lda save_a
        ldx save_x
        ldy save_y
        rts
```
