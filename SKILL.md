---
name: commodore-pet
description: >-
  Expert reference for Commodore PET 3032 6502 assembly programming, hardware
  registers, and working DASM code examples. Always use this skill whenever
  the conversation involves anything related to the Commodore PET, 6502 or
  65xx assembly, DASM assembler, PET hardware chips (VIA 6522, PIA 6520,
  CRTC 6545), PETSCII, screen RAM, KERNAL routines, tape or disk I/O, file
  operations, DOS commands, IEEE-488, keyboard matrix scanning, sound
  generation, IRQ or VBLANK, compression or animation on the PET, or
  anything that mentions PET 3032, SYS1038, BASIC stub, CBM DOS, or
  Commodore disk drives. Do not skip this skill just because a question
  seems simple -- even short 6502 questions benefit from verified PET-specific
  addresses and hardware facts.
---

# Commodore PET Programming Reference

This skill is the root router for all Commodore PET 3032 programming tasks.

## How to Use This Skill

Read this file first.

Then open **exactly one or two** topic files that match the task.

Do not load all topic files -- pick the narrowest match.

Load additional files only when the task genuinely crosses two domains.

After reading the relevant topic file(s), answer using the verified facts and code patterns from those files.

All addresses and register values are PET 3032 specific. Do not substitute C64 addresses.

## Topic Files

### Hardware

Read these files for chip register behavior, timing, and hardware-level facts.

| File                | Read when the task involves                                                             |
|---------------------|-----------------------------------------------------------------------------------------|
| `hardware/cpu.md`   | 6502 registers, flags, instruction set, addressing modes, cycle counts, interrupts, BRK |
| `hardware/chip.md`  | VIA 6522, PIA 6520, CRTC 6545, I/O addresses, VBLANK signal, IRQ acknowledgement        |
| `hardware/sound.md` | VIA CB2 speaker, shift register tone generation, frequency table, T2 timer setup        |

### System Software

Read these files for OS routines, memory layout, and I/O protocols.

| File                 | Read when the task involves                                                                                                          |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `system/memory.md`   | RAM layout, zero page map, BASIC workspace, screen RAM range, safe zones for machine code                                            |
| `system/kernal.md`   | KERNAL jump table ($FFC0-$FFEA), indirect vectors, CHROUT/GETIN/CLALL, PET vs C64 differences                                        |
| `system/irq.md`      | VBLANK IRQ setup, CINV vector, PIA1 CRB acknowledgement, handler template, VBLANK polling                                            |
| `system/screen.md`   | Screen RAM, PETSCII, character sets, reverse video, cursor, scrolling                                                                |
| `system/graphics.md` | Semigraphics characters, box drawing styles, window/line/rect routines, screen scrolling                                             |
| `system/load.md`     | Loading PRG files from tape or disk, LOAD call sequence, tape file format                                                            |
| `system/keyboard.md` | PIA 1 keyboard matrix scan, physical key layout, GETIN vs direct scan, special keys, multi-key detection                             |
| `system/file.md`     | Full file I/O: pet_setnam/pet_setlfs/pet_open/pet_close wrappers, CHKIN/CHKOUT/CLRCHN/CHRIN/CHROUT/LOAD/SAVE, PET vs C64 differences |
| `system/disk.md`     | DOS commands, command channel (SA=15), directory reading, drive errors, disk images                                                  |

### Code Patterns

Read these files for implementation techniques and algorithmic patterns.

| File                   | Read when the task involves                                                                                                        |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `code/standard.md`     | File structure, formatting, labels, comments, section headers, naming, column alignment, flag semantics, screen RAM 1000-byte rule |
| `code/bit.md`          | Bit shifts, rotates, masking, flag testing, 16-bit pointer increment/decrement                                                     |
| `code/optimization.md` | Loop unrolling, branch tuning, size/speed trade-offs, compare-free countdown                                                       |
| `code/compression.md`  | $00-escape RLE, byte-run encoding, frame-delta, LZ4 block format for animation                                                     |

### Build and Utility Tools

| File                        | Read when the task involves                                                                                                                                                             |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `utility/dasm-assembler.md` | DASM syntax, directives, macros, segments, command-line options                                                                                                                         |
| `utility/vice-emulator.md`  | Running PRG files in xpet, VICE monitor, breakpoints, watchpoints, tracepoints, conditional breakpoints, register modification, headless debugging, signal-byte tracing, Python socket scripting, KERNAL table verification, crash diagnosis, debugging workflow |

### Examples

Read these files when you need a complete, runnable starting point.

| File                 | Read when the task involves                                                              |
|----------------------|------------------------------------------------------------------------------------------|
| `example/general.md` | BASIC stub, screen clear, wait-key, VBLANK polling, IRQ skeleton, animation frame player |
| `example/file.md`    | Load PRG, save PRG, read/write sequential file, DOS command, directory, error handling   |

## Common Task Routing

Use this table to pick the right file without reading every option above.

| Task                                        | Open first                  | Open second if needed       |
|---------------------------------------------|-----------------------------|-----------------------------|
| Write or explain a 6502 instruction         | `hardware/cpu.md`           |                             |
| Use VIA, PIA, or CRTC registers             | `hardware/chip.md`          |                             |
| Generate a tone on the PET speaker          | `hardware/sound.md`         |                             |
| Find a safe memory address for code/data    | `system/memory.md`          |                             |
| Call a KERNAL routine by address            | `system/kernal.md`          |                             |
| PET vs C64 KERNAL differences               | `system/kernal.md`          | `system/file.md`            |
| ?SYNTAX ERROR from KERNAL calls             | `system/kernal.md`          | `utility/vice-emulator.md`  |
| Set up a VBLANK IRQ or poll VBLANK          | `system/irq.md`             |                             |
| Write to the screen or use PETSCII          | `system/screen.md`          |                             |
| Draw UI with semigraphics (boxes, lines)    | `system/graphics.md`        | `hardware/chip.md`          |
| Switch between uppercase and lowercase      | `system/screen.md`          | `hardware/chip.md`          |
| Load a PRG or data file from tape or disk   | `system/load.md`            |                             |
| Scan the keyboard or detect keypresses      | `system/keyboard.md`        |                             |
| Identify a physical key or its keycap label | `system/keyboard.md`        |                             |
| Open, read, or write a sequential file      | `system/file.md`            | `example/file.md`           |
| Send a DOS command or read the directory    | `system/disk.md`            | `example/file.md`           |
| Structure or format a DASM source file      | `code/standard.md`          | `utility/dasm-assembler.md` |
| Label, comment, or section header rules     | `code/standard.md`          |                             |
| Check which instructions affect flags       | `hardware/cpu.md`           | `code/standard.md`          |
| Clear, fill, or copy screen RAM             | `system/screen.md`          | `code/standard.md`          |
| Compress screen data or do frame-delta      | `code/compression.md`       |                             |
| Decompress LZ4 block data                   | `code/compression.md`       | `code/standard.md`          |
| Optimize a loop or reduce code size         | `code/optimization.md`      |                             |
| Write DASM source with macros or segments   | `utility/dasm-assembler.md` |                             |
| Run or debug a PRG in the VICE emulator     | `utility/vice-emulator.md`  |                             |
| Diagnose a crash or hang in xpet            | `utility/vice-emulator.md`  | `hardware/chip.md`          |
| Headless screen capture or scripted test    | `utility/vice-emulator.md`  |                             |
| Set breakpoints or watchpoints in xpet      | `utility/vice-emulator.md`  |                             |
| Build a complete animation player           | `example/general.md`        | `hardware/chip.md`          |
| Build a complete file I/O program           | `example/file.md`           | `system/file.md`            |
| BASIC stub + SYS1038                        | `example/general.md`        | `code/standard.md`          |

## Extending This Skill

When adding or editing files, follow the conventions in `STYLE.md`.

It covers file header structure, table alignment, code block layout, inline formatting, and how to register new files in this routing table.

## Note on Large Reference Files

These files are long and have their own table of contents at the top.

Use the table of contents to jump to the relevant section rather than reading the whole file.

| File                       | Lines  |
|----------------------------|--------|
| `system/file.md`           | ~1200  |
| `utility/vice-emulator.md` | ~1030  |
| `example/file.md`          | ~1000  |
| `system/disk.md`           | ~780   |
| `code/compression.md`      | ~680   |
| `example/general.md`       | ~595   |
| `system/graphics.md`        | ~750   |
