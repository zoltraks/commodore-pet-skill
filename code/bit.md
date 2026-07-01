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
        lda value               ; Set bit 7
        ora #$80
        sta value

        lda value               ; Clear bit 3
        and #$F7
        sta value

        lda value               ; Toggle bit 0
        eor #$01
        sta value
```

### Bit Test Without Load (BIT instruction)

```asm
        bit $E84D               ; test VIA IFR against A without changing A
        bvs timer1_irq          ; branch if bit 6 (V flag) set
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
        rol value_hi            ; C shifts into bit 0 of high byte
```

### 16-Bit Right Shift

```asm
        lsr value_hi
        ror value_lo            ; C shifts into bit 7 of low byte
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
        asl                     ; shift high nibble to low via C
        adc #$80
        asl
        adc #$80
        asl
        adc #$80
        asl
        adc #$80                ; A now has nibbles swapped
```

### Table-Driven Bit Reverse

```asm
        tax
        lda bit_reverse_table,x

bit_reverse_table:

        byte $00,$80,$40,$C0,$20,$A0,$60,$E0
        byte $10,$90,$50,$D0,$30,$B0,$70,$F0    ; ... (256 bytes total)
```

## Stack Tricks

### Fast A/X/Y Save/Restore

```asm
save_regs:

        sta save_a
        stx save_x
        sty save_y
        lda save_a              ; ... work ...
        ldx save_x
        ldy save_y
        rts
```

## Byte-to-Hex Conversion

Converting a byte to two hex digit characters is needed for debug displays, hex viewers, and offset formatting. The conversion splits the byte into two nibbles and maps each to a character.

### Nibble to Screen Code

On the PET, screen codes differ from PETSCII. Digits `0`-`9` map to screen codes `$30`-`$39` (same as PETSCII). Letters `A`-`F` map to screen codes `$01`-`$06` (PETSCII `$41`-`$46` minus `$40`).

```asm
; nibble_to_sc: A = nibble (0-15) -> A = screen code for hex digit
; 0-9 -> $30-$39, 10-15 -> $01-$06 (screen codes for A-F)

nibble_to_sc:

        cmp #10
        bcc nts_digit
        sbc #9                  ; carry set: 10->1='A', 15->6='F'
        rts
nts_digit:

        clc
        adc #$30                ; 0-9 -> $30-$39
        rts
```

For PETSCII output instead of screen codes, add `$40` to the letter branch: `sbc #9` becomes `sbc #$41-1` then `adc #$41`, or simply use a lookup table.

### Byte to Two Hex Digits

```asm
; byte_to_hex: A = byte -> A = high nibble screen code, Y = low nibble
; Clobbers: A, Y

byte_to_hex:

        sta bth_tmp
        and #$0F
        jsr nibble_to_sc
        tay                     ; Y = low nibble
        lda bth_tmp
        lsr                     ; shift high nibble into low position
        lsr
        lsr
        lsr
        jsr nibble_to_sc        ; A = high nibble
        rts

bth_tmp:        byte 0
```

**Important:** use bare `lsr` (accumulator mode), not `lsr a`. See `utility/dasm-assembler.md` "Accumulator-Mode Syntax".

### Writing Two Hex Digits to Screen

```asm
; write_hex_byte: A = byte, (sp_lo) = screen row, Y = column
; Writes 2 hex screen codes, Y advanced by 2

write_hex_byte:

        sta whb_tmp
        lsr                     ; high nibble first
        lsr
        lsr
        lsr
        jsr nibble_to_sc
        sta (sp_lo),y
        iny
        lda whb_tmp
        and #$0F
        jsr nibble_to_sc
        sta (sp_lo),y
        iny
        rts

whb_tmp:        byte 0
```

### Hex Offset (4-Digit)

To display a 16-bit offset as 4 hex digits, call `write_hex_byte` twice -- high byte first, then low byte:

```asm
        lda offset_hi
        jsr write_hex_byte
        lda offset_lo
        jsr write_hex_byte
```
