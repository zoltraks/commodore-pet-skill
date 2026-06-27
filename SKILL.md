---
name: commodore-pet
description: >-
  Commodore PET 6502 assembly programming skill. Covers MOS 6502 CPU architecture,
  DASM assembler syntax, PET 3032 hardware (VIA 6522, PIA 6520, CRTC 6545),
  memory map, KERNAL jump table, screen I/O, PETSCII, keyboard matrix, compression patterns,
  file I/O, disk operations, and working code examples. Use whenever the user asks about
  Commodore PET programming, 6502 assembly, DASM, PET hardware registers, screen memory,
  KERNAL routines, tape/disk loading, sound generation, animation frames, IRQ handling,
  VBLANK timing, file I/O, sequential files, disk drives, DOS commands, IEEE-488 bus,
  directory listing, or disk images. Triggers: 'PET 3032', 'Commodore PET',
  '6502 assembly', 'DASM', 'PETSCII', 'KERNAL', 'VIA 6522', 'PIA 6520',
  'screen memory', 'BASIC stub', 'SYS1038', 'animation player', 'VBLANK',
  'tape loading', 'IEEE-488', 'shift register sound', 'frame delta',
  'RLE compression', 'zero page', 'IRQ hook', 'keyboard matrix', 'key scan',
  'SETNAM', 'SETLFS', 'OPEN', 'CLOSE', 'CHKIN', 'CHKOUT', 'sequential file',
  'disk directory', 'DOS command', 'scratch', 'format disk', 'D64', 'D80', 'D82',
  '4040', '8050', 'command channel', 'drive status'.
---

# Commodore PET Agentic Programming Skills

> **Type:** Root router and taxonomy
> **Purpose:** Route Commodore PET programming, hardware, and tooling questions to the smallest useful English skill file.

Use progressive disclosure:

1. Read this router.
2. Open exactly one or two topic files that match the task.
3. Use additional topic files only when the task crosses domains.

This skill is self-contained. The topic files below are the available reference material in this repository.

## `hardware/` - Silicon Reference

- **`hardware/cpu.md`** - 6502 registers, flags, instruction set, addressing modes, cycle counts, stack operations, interrupts, and zero-page idioms.
- **`hardware/chip.md`** - VIA 6522, PIA 6520 (x2), CRTC 6545 registers, I/O decoding, screen memory, character generator, VBLANK, and IRQ acknowledgement.
- **`hardware/sound.md`** - VIA shift register sound via CB2, frequency table, ACR/SR/T2 control, tone start/stop routines.

## `system/` - OS, Memory, I/O

- **`system/memory.md`** - PET 3032 32 KB RAM layout, zero page, BASIC workspace, screen RAM, ROM regions, and safe memory zones for machine code.
- **`system/kernal.md`** - KERNAL jump table ($FFB7-$FFEA), indirect vectors, CHROUT/GETIN/CLALL, safe IRQ hook patterns.
- **`system/screen.md`** - Screen RAM layout, PETSCII vs screen codes, PETSCII control codes, graphics characters, direct screen writing, cursor control, and scrolling.
- **`system/loading.md`** - KERNAL tape and IEEE-488 disk loading (SETNAM/SETLFS/LOAD), byte-stream reading, STATUS word, and animation data load sequences.
- **`system/keyboard.md`** - PET keyboard matrix layout, PIA 1 row/column scan, KERNAL GETIN vs direct scan, special keys, and multi-key detection patterns.
- **`system/file.md`** - Complete KERNAL file I/O system: logical files, device numbers, secondary addresses, SETNAM/SETLFS/OPEN/CLOSE/CHKIN/CHKOUT/CLRCHN/CHRIN/CHROUT/LOAD/SAVE/READST reference, STATUS byte, and error handling.
- **`system/disk.md`** - Commodore DOS commands (scratch, rename, copy, format, validate), command channel (SA=15), directory reading, drive error codes, disk image formats (D64/D80/D82), emulator workflows (VICE xpet), and BASIC vs KERNAL vs direct IEEE-488 comparison.

## `code/` - Code Patterns

- **`code/bit.md`** - Bit shifts, rotates, flag testing, mask building, INC/DEC 16-bit pointers, and zero-page idioms.
- **`code/optimization.md`** - 6502 size/speed trade-offs for PET, unrolled loops, compare-free countdown, stack tricks, and branch tuning.
- **`code/compression.md`** - `$00`-escape RLE for full-range screen codes (including inverse video), byte-run, and frame-delta patterns for PET screen-memory animation.

## `utility/` - Build Tools

- **`utility/dasm-assembler.md`** - DASM syntax, directives, macros, segments, PET-specific conventions, and command-line options.

## `example/` - General Examples

- **`example/general.md`** - Ready-to-read PET 3032 examples: BASIC stub, clear screen, wait-key, screen copy, VBLANK polling, IRQ-driven animation skeleton, and screen data row format.
- **`example/fileio.md`** - Complete DASM file I/O examples: load PRG, save PRG, read sequential file, write sequential file, send DOS command, read disk directory, full program template, common mistakes, and quick-reference call sequences.

## Navigation Rules

- Hardware-register behavior belongs in `hardware/`; software rendering recipes belong in `system/screen.md`.
- OS/vector/I/O questions belong in `system/`; build tools belong in `utility/`; runnable examples belong in `example/`.
- Sound generation belongs in `hardware/sound.md`; tape or disk loading belongs in `system/loading.md`.
- Keyboard matrix scanning belongs in `system/keyboard.md`; KERNAL GETIN is also documented there.
- KERNAL file routine reference (SETNAM/SETLFS/OPEN/CLOSE/CHKIN/CHKOUT/CLRCHN/CHRIN/CHROUT/LOAD/SAVE) belongs in `system/file.md`.
- DOS commands, command channel, directory reading, drive error codes, disk images, and emulator workflows belong in `system/disk.md`.
- Complete runnable DASM file I/O examples belong in `example/fileio.md`.
- Prefer the narrowest topic file that directly matches the request.
- If a task needs both hardware facts and implementation guidance, load the hardware topic first, then the system or utility topic that covers the code path.
- For file I/O tasks: start with `system/file.md` for routine reference, `system/disk.md` for DOS and directory, `example/fileio.md` for ready-to-use code.
- For animation player generation: start with `example/general.md` for skeletons, `hardware/chip.md` for VBLANK/IRQ, `system/loading.md` for data loading, `hardware/sound.md` for audio.
