# VICE PET Emulator

## Purpose

> **Scope:** Running PET 3032 programs and debugging with the `xpet` command (VICE 3.7)
> **Key items:** `-model 3032`, `-autostart`, `-autostartprgmode 1`, `-nativemonitor`, `-initbreak`, `-moncommands`

| Out of scope               | See instead                 |
|----------------------------|-----------------------------|
| Assembling source to PRG   | `utility/dasm-assembler.md` |
| Loading files at PET BASIC | `system/load.md`            |
| Disk image file formats    | `system/disk.md`            |

## Contents

| Section              | Line | What it covers                                    |
|----------------------|------|---------------------------------------------------|
| Invocation           | 25   | Minimal command form and model flag               |
| Running a PRG        | 35   | Autostart modes for machine-code PRG files        |
| Built-in Monitor     | 73   | Opening the monitor and essential commands        |
| Breakpoints          | 127  | initbreak, break, watch                           |
| Monitor Scripts      | 168  | moncommands file for automated debug sessions     |
| Useful Flags         | 194  | warp, speed, keybuf, logging                      |

## Invocation

```bash
xpet -model 3032
```

Always pass `-model 3032` to emulate the 3032 configuration (32 KiB RAM, Business keyboard, no colour).

Without `-model`, VICE defaults to the 2001 configuration which has a different RAM size and ROM.

## Running a PRG

A PRG file is a raw binary prefixed with a 2-byte little-endian load address.

DASM produces this format with the `-f1` flag:

```bash
dasm source.asm -f1 -o program.prg
```

Launch and autostart the PRG:

```bash
xpet -model 3032 -autostartprgmode 1 -autostart program.prg
```

`-autostartprgmode 1` selects **Inject** mode: VICE reads the load address from the PRG header, copies the binary into RAM at that address, then starts execution by synthesising a SYS call.

| Mode | Flag                    | Behaviour                                              |
|------|-------------------------|--------------------------------------------------------|
| 0    | `-autostartprgmode 0`   | VirtualFS -- mounts a virtual disk, loads via KERNAL   |
| 1    | `-autostartprgmode 1`   | Inject -- writes bytes directly into RAM and runs      |
| 2    | `-autostartprgmode 2`   | Disk image -- requires a companion `.d64` image        |

Inject mode is the fastest path for development because it skips disk I/O emulation entirely.

For a program with the standard BASIC stub at `$0401`, the SYS entry point is `$0410` (the first byte after the stub).

### Attach Without Autostart

To attach a disk image and boot manually:

```bash
xpet -model 3032 -8 disk.d64
```

From BASIC, type `LOAD"*",8,1` then `RUN` to load and run the first program on the disk.

## Built-in Monitor

The VICE built-in monitor is a 6502 machine-level debugger.

Open the monitor at any time by pressing **Alt+H** (default hotkey) while the emulator is running, or use the **Machine** menu.

To use the terminal (text) version of the monitor instead of the GTK3 window, add `-nativemonitor` to the command line. The native monitor is easier to script and copy from.

```bash
xpet -model 3032 -nativemonitor -autostart program.prg
```

### Monitor Commands

These are the essential commands for debugging PET programs.

| Command                  | Action                                      |
|--------------------------|---------------------------------------------|
| `r`                      | Show CPU registers (A, X, Y, SP, PC, flags) |
| `d <addr>`               | Disassemble from address                    |
| `m <start> <end>`        | Hex dump memory range                       |
| `g <addr>`               | Go: run from address                        |
| `z`                      | Step into (execute one instruction)         |
| `n`                      | Step over (treats JSR as one step)          |
| `break <addr>`           | Set execution breakpoint at address         |
| `watch load <addr>`      | Break on memory read from address           |
| `watch store <addr>`     | Break on memory write to address            |
| `del <num>`              | Delete breakpoint or watchpoint by number   |
| `bk`                     | List all breakpoints and watchpoints        |
| `x`                      | Exit monitor, resume emulation              |
| `q`                      | Quit VICE                                   |

Address notation in the monitor uses `$` prefix: `d $0410`, `m $8000 $805F`.

Disassemble the BASIC stub area:

```
d $0401
```

Dump the screen RAM:

```
m $8000 $83E7
```

Write a byte directly into RAM (useful for patching without reassembling):

```
> $0410 ea
```

The `>` command writes bytes: `> <addr> <hex bytes...>`.

## Breakpoints

### Initial Breakpoint

`-initbreak <value>` opens the monitor automatically when a condition is hit on first launch.

| Value         | Stops when                              |
|---------------|-----------------------------------------|
| `ready`       | BASIC READY prompt appears              |
| `reset`       | CPU reset vector fires                  |
| `$<addr>`     | PC reaches the given address            |

Stop at BASIC ready and then manually run the program:

```bash
xpet -model 3032 -nativemonitor -initbreak ready -autostart program.prg
```

Stop at the first instruction of the machine-code entry point:

```bash
xpet -model 3032 -nativemonitor -initbreak 0x0410 -autostart program.prg
```

### Breakpoints During a Session

From inside the monitor:

```
break $0450
x
```

This sets a breakpoint at `$0450`, then resumes. The monitor reopens automatically when the PC hits `$0450`.

Keep the monitor open between steps (do not close on `x`):

```bash
xpet -model 3032 -nativemonitor -keepmonopen -autostart program.prg
```

## Monitor Scripts

`-moncommands <file>` executes a text file of monitor commands at startup, before the emulation begins.

This is useful for setting a fixed set of breakpoints and watchpoints without typing them each session.

Example `debug.mon`:

```
break $0450
watch store $8000
x
```

Launch with the script:

```bash
xpet -model 3032 -nativemonitor -moncommands debug.mon -autostart program.prg
```

Log all monitor output to a file:

```bash
xpet -model 3032 -nativemonitor -monlog -monlogname session.log -autostart program.prg
```

## Useful Flags

### Warp Mode

`-warp` runs the emulator at maximum host CPU speed, ignoring the PET's timing.

Use it to skip long load sequences or large BASIC startup delays:

```bash
xpet -model 3032 -warp -autostart program.prg
```

Toggle warp interactively with **Alt+W** while running.

### Speed Limiting

`-speed <percent>` caps emulation speed relative to real hardware.

`-speed 100` is real PET speed (default). `-speed 200` runs at double speed. `-speed 0` means unlimited.

### Keyboard Buffer Injection

`-keybuf <string>` stuffs a string into the keyboard buffer at startup, as if the user typed it.

Pre-type a BASIC command before the program takes control:

```bash
xpet -model 3032 -keybuf "SYS1038\n"
```

### Log File

`-logfile <name>` writes VICE diagnostic output (ROM load messages, drive errors) to a file instead of stderr.

```bash
xpet -model 3032 -logfile vice.log -autostart program.prg
```

### Remote Monitor

`-remotemonitor` opens a TCP port that accepts the same text commands as the native monitor.

```bash
xpet -model 3032 -remotemonitor -remotemonitoraddress 127.0.0.1:6510 -autostart program.prg
```

Connect with `nc` or `telnet`:

```bash
nc 127.0.0.1 6510
```

This lets an external script drive the monitor without focus on the emulator window.
