# Commodore PET Agentic Programming Skills

<p align="center">
  <b>Agent Skill</b> for Windsurf | Cursor | Claude Code | Gemini CLI | OpenCode | GitHub Copilot CLI
</p>

> Commodore PET 3032 6502 assembly programming, hardware reference, and working code examples. Drop-in skill for any AI coding agent that supports SKILL.md.

This is an [Agent Skill](https://www.mintlify.com/blog/skill-md) - a folder of instructions any compatible AI coding agent loads on demand. When you ask about Commodore PET programming, 6502 assembly, DASM syntax, or PET hardware, this skill provides verified reference material and working code patterns.

---

## What you get

Each topic file is self-contained and follows the same four-layer structure:

- **Quick-lookup table** - scan for the fact or pattern you need
- **Reference tables** - dense lookup layer (register maps, instruction sets, vector tables)
- **Working code examples** - verified ASM snippets for DASM, ready to assemble and run
- **Deep reference notes** - edge cases, caveats, and implementation rules

Assembly examples target the **Commodore PET** (Model 3032, 32 KB RAM, 1 MHz 6502) and use **DASM** syntax.
Values are hexadecimal (`$NN`) unless noted decimal.

---

## When to use this skill

| Situation                                   | Use this skill?                                      |
|---------------------------------------------|------------------------------------------------------|
| "Write a 6502 assembly program for the PET" | **Yes**                                              |
| "How do I clear the screen on a PET?"       | **Yes**                                              |
| "What are the VIA 6522 registers?"          | **Yes**                                              |
| "How do I load data from tape?"             | **Yes**                                              |
| "Build an animation player for PET"         | **Yes**                                              |
| "Generate a BASIC stub with SYS1038"        | **Yes**                                              |
| "How does PETSCII differ from ASCII?"       | **Yes**                                              |
| "How do I scan the keyboard matrix?"        | **Yes** - use `system/keyboard.md`                   |
| "Optimize this 6502 loop"                   | **Yes** - use `code/optimization.md`                 |
| "How do I read a file from disk?"           | **Yes** - use `system/file.md` + `example/file.md` |
| "How do I send a DOS command to the drive?" | **Yes** - use `system/disk.md`                       |
| "How do I read the disk directory?"         | **Yes** - use `system/disk.md` + `example/file.md` |
| "General 6502 questions (not PET-specific)" | Partially - `hardware/cpu.md` covers the CPU broadly |
| "C64-specific programming"                  | No - this skill is PET 3032 focused                  |

---

## Install

### Windsurf / Cursor / VS Code (Cline, Roo Code)

Project install - committed to a repo, shared with your team:

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill .windsurf/skills/commodore-pet
```

Or use the cross-tool `.agents/skills/` path:

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill .agents/skills/commodore-pet
```

### Claude Code - manual clone

Personal install (available in all your projects):

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill \
  ~/.claude/skills/commodore-pet
```

Project install:

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill \
  .claude/skills/commodore-pet
```

### Gemini CLI

```bash
gemini skills install https://github.com/YOURNAME/commodore-pet-skill
```

Or manual:

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill /tmp/pet-skill
cp -r /tmp/pet-skill ~/.gemini/skills/commodore-pet
```

### OpenCode

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill ~/.config/opencode/skills/commodore-pet
```

Or use the Claude-compatible path:

```bash
git clone https://github.com/YOURNAME/commodore-pet-skill ~/.claude/skills/commodore-pet
```

### GitHub Copilot CLI

```bash
gh skill install YOURNAME/commodore-pet-skill commodore-pet
```

---

## Example prompts

**Write a BASIC stub**
> Write a PET 3032 BASIC stub at $0401 that starts with SYS1038 and includes a small machine-code program.

**Screen I/O**
> How do I write directly to PET screen memory? Show me the assembly code to print a character at a specific row and column.

**Animation skeleton**
> Build an IRQ-driven animation skeleton for the PET 3032. It should wait for VBLANK, copy a frame from RAM to screen, and loop. Include the BASIC stub.

**Sound generation**
> Write a PET 3032 assembly routine that plays a tone using the VIA shift register and CB2 speaker. Include start and stop functions.

**Data loading**
> Show me how to load animation frame data from cassette tape into PET memory using KERNAL routines.

**Compression**
> Explain the $00-escape RLE format used for PET screen codes and provide a decompressor in 6502 assembly.

**File I/O**
> Write a PET 3032 assembly routine that opens a sequential file on device 8, reads all bytes into a buffer, and closes the file. Show the complete DASM code.

**Disk commands**
> How do I delete a file on a PET disk drive from assembly code? Show me how to send a scratch command through the command channel and read the drive status.

---

## What's inside

```
commodore-pet-skill/
├── SKILL.md                       # Root router - load this first
├── STYLE.md                       # Formatting rules for all skill documents
├── hardware/
│   ├── cpu.md                     # 6502 registers, flags, instructions, interrupts
│   ├── chip.md                    # VIA, PIA, CRTC registers, I/O decoding, VBLANK
│   └── sound.md                   # VIA shift register sound, CB2 speaker, frequency table
├── system/
│   ├── memory.md                  # PET 3032 RAM layout, zero page, safe zones
│   ├── kernal.md                  # KERNAL jump table, indirect vectors, I/O routines
│   ├── irq.md                     # VBLANK IRQ setup, CINV vector, handler template, polling
│   ├── load.md                    # PRG loading from tape/disk, LOAD call, tape file format
│   ├── screen.md                  # Screen RAM, PETSCII, cursor, reverse video
│   ├── keyboard.md                # Keyboard matrix, PIA 1 scan, GETIN, multi-key detection
│   ├── file.md                    # KERNAL file I/O: SETNAM/SETLFS/OPEN/CLOSE/CHKIN/CHKOUT/CHRIN/CHROUT/LOAD/SAVE
│   └── disk.md                    # DOS commands, command channel, directory, error codes, disk images, emulators
├── code/
│   ├── bit.md                     # Bit ops, masks, pointers, stack tricks
│   ├── optimization.md            # Size/speed trade-offs, unrolled loops, branch tuning
│   └── compression.md             # $00-escape RLE, byte-run, frame-delta
├── utility/
│   └── dasm-assembler.md          # DASM syntax, directives, macros, conventions
└── example/
    ├── general.md                 # BASIC stub, screen clear, VBLANK, IRQ skeleton
    └── file.md                  # Complete DASM file I/O examples: load/save/read/write/command/directory
```

The skill activates automatically when you ask about Commodore PET programming, 6502 assembly, DASM, PET hardware, or related topics.

---

## License

MIT - see [LICENSE](./LICENSE).

---

## Credits

Built by Filip Golewski.

If you use this skill in a project, a link back is appreciated but not required.
