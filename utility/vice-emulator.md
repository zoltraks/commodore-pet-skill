# VICE PET Emulator

## Purpose

> **Scope:** Running PET 3032 programs and debugging with the `xpet` command (VICE 3.7)
> **Key items:** `-model 3032`, `-autostart`, `-drive8type 2031`, `-remotemonitor`, `-limitcycles`, `-warp`, headless screen inspection

| Out of scope               | See instead                 |
|----------------------------|-----------------------------|
| Assembling source to PRG   | `utility/dasm-assembler.md` |
| Loading files at PET BASIC | `system/load.md`            |
| Disk image file formats    | `system/disk.md`            |

## Contents

| Section               | Line | What it covers                                                          |
|-----------------------|------|-------------------------------------------------------------------------|
| Invocation            | 25   | Minimal command form and model flag                                     |
| PET ROM Setup         | 35   | How VICE finds ROMs; symlinking from a known location                   |
| Drive Types on PET    | 80   | `-drive8type 2031` for D64; never 1541 on PET                           |
| Running a PRG         | 105  | Autostart modes, why disk autostart is most reliable                    |
| Headless Debugging    | 165  | Remote monitor over TCP, cycle limits, screen dumps, warp timing        |
| Decoding Screen Codes | ~260 | Reading dumped `$8000-$83E7` bytes back into characters; row arithmetic |
| Memory Landmarks      | ~300 | Addresses worth checking during diagnostics                             |
| Diagnosing Crashes    | ~340 | KERNAL hang, SP depth, breakpoint silence, VIA PCR hazard               |
| Built-in Monitor      | ~395 | Opening the monitor and essential commands                              |
| Breakpoints           | ~450 | initbreak, break, watch, warp-mode timing                               |
| Monitor Scripts       | ~510 | moncommands file for automated debug sessions                           |
| Useful Flags          | ~535 | warp, speed, keybuf, logging                                            |

## Invocation

```bash
xpet -model 3032
```

Always pass `-model 3032` to emulate the 3032 configuration (32 KiB RAM, 40-column display, BASIC 2, no colour).

Without `-model`, VICE defaults to the 2001 configuration which has a different RAM size and ROM.

## PET ROM Setup

VICE looks for ROM image files in three places, in order:

1. The path given by `-directory <base>` (treated as the whole data root)
2. The system path: `/usr/share/vice/PET/` on Linux
3. The user path: `~/.local/share/vice/PET/`

PET 3032 needs four ROM files:

| File                         | Purpose                          |
|------------------------------|----------------------------------|
| `characters-2.901447-10.bin` | 8x8 character ROM                |
| `basic-2.901465-01-02.bin`   | BASIC 2.0 interpreter            |
| `kernal-2.901465-03.bin`     | KERNAL ROM (I/O, IEEE-488, tape) |
| `edit-2-n.901447-24.bin`     | Editor ROM (screen, keyboard)    |

For D64 disk access, the 2031 drive ROM is also needed under a sibling `DRIVES/` directory:

| File                       | Purpose                     |
|----------------------------|-----------------------------|
| `dos2031-901484-03+05.bin` | CBM 2031 IEEE-488 drive DOS |

### Why not just use `-directory`

`-directory <base>` redirects the WHOLE data root, including `<base>/GLSL/` where VICE keeps its rendering shaders (`viewport.vert`, `builtin.frag`, etc.). If the redirect target has the ROMs but lacks the GLSL shaders, xpet fails with:

```
Error - Could not open vertex shader: viewport.vert
```

The fix is to leave the data root alone and instead symlink only the missing ROMs into the user path:

```bash
mkdir -p ~/.local/share/vice/PET
ln -sf <source>/PET/characters-2.901447-10.bin   ~/.local/share/vice/PET/
ln -sf <source>/PET/basic-2.901465-01-02.bin    ~/.local/share/vice/PET/
ln -sf <source>/PET/kernal-2.901465-03.bin      ~/.local/share/vice/PET/
ln -sf <source>/PET/edit-2-n.901447-24.bin      ~/.local/share/vice/PET/

mkdir -p ~/.local/share/vice/DRIVES
ln -sf <source>/DRIVES/dos2031-901484-03+05.bin  ~/.local/share/vice/DRIVES/
```

VICE picks the ROMs up automatically and keeps using the system path for shaders and palettes.

## Drive Types on PET

PET uses the parallel **IEEE-488** bus. C64-era serial-IEC drives (1541, 1571, 1581) are physically incompatible.

| `-drive8type` | Bus        | Native disk | Reads D64?                              |
|---------------|------------|-------------|-----------------------------------------|
| `1541`        | Serial IEC | D64         | -- not usable on PET                    |
| `2031`        | IEEE-488   | D64         | Yes (single-drive IEEE sibling of 1541) |
| `4040`        | IEEE-488   | D64         | Yes (dual-drive)                        |
| `8050`        | IEEE-488   | D80         | No (different sector layout)            |
| `8250`        | IEEE-488   | D82         | No (different sector layout)            |

If a D64 image is attached with `-drive8type 1541` on PET, `LOAD"*",8` hangs forever at `SEARCHING FOR *` because the drive never answers on the IEEE-488 bus.

For PET 3032 with a D64 file, use `-drive8type 2031`. The 2031 is an IEEE-488 mechanism that reads the same sector format as the 1541 and works natively over the PET bus.

## Running a PRG

A PRG file is a raw binary prefixed with a 2-byte little-endian load address. DASM produces this format with the `-f1` flag:

```bash
dasm source.asm -f1 -o program.prg
```

For a program with the standard `org $0401` BASIC stub, `SYS 1038` is the entry point. 1038 decimal is `$040E`, the byte immediately after the BASIC end-of-program marker. Place a `JMP your_start` at `$040E` (or put your code label there directly) so the SYS lands on real instructions.

### Autostart Modes

`-autostart` accepts either a PRG file or a disk image. With a PRG file, `-autostartprgmode` selects how VICE delivers it:

| Mode | Flag                  | Behaviour                                            |
|------|-----------------------|------------------------------------------------------|
| 0    | `-autostartprgmode 0` | VirtualFS -- mounts a virtual disk, loads via KERNAL |
| 1    | `-autostartprgmode 1` | Inject -- writes bytes directly into RAM and runs    |
| 2    | `-autostartprgmode 2` | Disk image -- requires a companion `.d64` image      |

### Autostart From a Disk Image (recommended for PET)

The most reliable path on PET is to put the PRG inside a D64 and pass the disk image to `-autostart`:

```bash
xpet -model 3032 -drive8type 2031 -autostart work.d64
```

VICE issues `LOAD"*",8` followed by `RUN:` through BASIC's real LOAD routine, which sets every BASIC pointer correctly (TXTTAB, VARTAB, ARYTAB, STREND). The same disk stays mounted as drive 8 for the program to read.

Build a D64 with `c1541` (ships with VICE):

```bash
c1541 -format "diskname,01" d64 work.d64 \
      -write program.prg "program,p" \
      -write data.txt    "data,s"
```

The first program file on the disk is what `LOAD"*",8` loads.

### Inject Mode Caveats

`-autostartprgmode 1` writes the PRG bytes into RAM and stuffs `RUN` into the keyboard buffer. On C64 this is the fastest dev loop. On PET it can leave BASIC's text/variable pointers in an inconsistent state for some PRG layouts, producing `?SYNTAX ERROR IN 10` on the first line BASIC tries to parse. When that happens, switch to disk autostart.

### Attach Without Autostart

```bash
xpet -model 3032 -drive8type 2031 -8 disk.d64
```

From BASIC, type `LOAD"*",8` then `RUN` to load and run the first program on the disk.

## Headless Debugging

`xpet` always opens a graphical window, but the **remote text monitor** lets a shell script drive it without focusing the GUI. This is the workhorse for verifying programs from CI scripts or for diagnostics when the visible screen looks wrong.

### Recipe: Capture Screen RAM After Boot

```bash
# 1. Launch xpet with remote monitor on a TCP port, warp on, hard cycle limit
xpet -model 3032 -drive8type 2031 \
     -autostart work.d64 \
     -warp -limitcycles 500000000 \
     -remotemonitor -remotemonitoraddress 127.0.0.1:6502 \
     > /tmp/xpet.log 2>&1 &
XPETPID=$!

# 2. Give the autostart sequence wall-clock time to play out
sleep 15

# 3. Drive the monitor over TCP; dump screen RAM and quit cleanly
( echo 'm $8000 $83E7'
  echo 'q'
) | nc -q 1 127.0.0.1 6502 > /tmp/screen.txt

# 4. Tear down xpet
kill $XPETPID 2>/dev/null
wait 2>/dev/null
```

`-limitcycles N` caps total CPU cycles, killing xpet if the test script forgets to. At PET's 1 MHz, 500,000,000 cycles is 500 emulated seconds; warp lets the host burn through that as fast as it can.

`-warp` runs the CPU at maximum host speed. The autostart key-buffer stuffing still uses real wall-clock pacing, so the `sleep` step is required no matter how fast the CPU runs.

### Useful Monitor Commands Over TCP

The remote monitor speaks the same text protocol as `-nativemonitor`. Pipe a sequence of commands followed by `q` (quit) through `nc`:

| Command             | Purpose                                        |
|---------------------|------------------------------------------------|
| `m S E`             | Dump memory range `S..E` as hex + ASCII        |
| `d S E`             | Disassemble range `S..E`                       |
| `r`                 | Show CPU state (PC, A, X, Y, SP, flags, cycle) |
| `break $addr`       | Set execution breakpoint                       |
| `watch store $addr` | Break on memory write                          |
| `bk`                | List active breakpoints and hit counts         |
| `q`                 | Disconnect (resumes CPU)                       |

Each `m` line on the response carries one 16-byte row prefixed with `>C:<addr>`:

```
>C:8000  20 20 20 20  20 20 20 20  20 20 20 20  20 20 20 20                   
>C:8010  20 20 20 20  20 20 20 20  20 20 20 20  20 20 20 20                   
>C:8020  20 20 20 20  20 20 20 20  3f 13 19 0e  14 01 18 20           ?...... 
```

The trailing characters in each line are VICE's ASCII translation, NOT the screen characters -- screen RAM uses screen codes (next section).

### Scripting Many Probes

For multi-probe sessions, write a here-doc into `nc`:

```bash
( cat <<'EOF'
m $0028 $002F
m $0090 $0096
m $00FB $00FE
m $8000 $80FF
r
q
EOF
) | nc -q 1 127.0.0.1 6502 > /tmp/probe.txt
```

`nc -q 1` waits one second after EOF before closing, so the monitor's last reply has time to arrive.

### Tracking the Autostart Sequence

VICE prints AUTOSTART progress lines to stderr (or to `-logfile`). Grep them to see how far the boot got:

```bash
grep -i AUTOSTART /tmp/xpet.log
```

Typical sequence on a successful disk autostart:

```
AUTOSTART: Autodetecting image type of `work.d64'.
AUTOSTART: Attached file `work.d64' as a disk image.
AUTOSTART: Resetting drive 8
AUTOSTART: Resetting the machine to autostart '*'
AUTOSTART: Loading program '*'
AUTOSTART: Searching for ...
AUTOSTART: Loading
AUTOSTART: Ready
AUTOSTART: Starting program.
AUTOSTART: Done.
```

If the sequence stops at `Searching for ...` and never reaches `Loading`, the drive type and the disk image format do not match (see Drive Types on PET).

### Warp Mode Timing: Why Breakpoints Miss

With `-warp`, the CPU runs orders of magnitude faster than real time. A PET program that would take 30 real seconds to reach a breakpoint address can do so in under one wall-clock second. This collapses the window for connecting a remote monitor:

**Problem**: `sleep 3; nc 127.0.0.1 6502` after launching xpet with `-warp` typically arrives after the program has already crashed. Breakpoints sent at that point will never fire -- the code already ran past them.

**Rule**: In warp mode, breakpoints must be installed _before_ the CPU starts, via `-moncommands`.

```bash
# debug.mon  -- loaded before any instruction runs
bk load $0442   # break at program entry
bk load $09AF   # break at first KERNAL OPEN call
x               # resume emulation
```

```bash
xpet -model 3032 -drive8type 2031 \
     -warp -limitcycles 500000000 \
     -remotemonitor -remotemonitoraddress 127.0.0.1:6502 \
     -moncommands debug.mon \
     -autostart work.d64 > /tmp/xpet.log 2>&1 &
```

The remote monitor delivers breakpoint notifications on the TCP socket as:

```
BREAK: 09AF  (Stop on exec)
```

Keep `nc` open with a long `sleep` after sending `g` so the connection survives until the notification arrives:

```bash
( printf 'g\n'; sleep 30 ) | nc -q 1 127.0.0.1 6502 > /tmp/mon_out.txt
```

`g` with no address resumes from the current PC (it does NOT jump to `$0000`). `g $addr` jumps to a specific address.

If no breakpoint line appears in the output after 30 seconds of warp, the crash is before the earliest breakpoint. Move the first breakpoint to an earlier address and repeat.

## Decoding Screen Codes

Screen RAM (`$8000-$83E7`, 40x25) stores **screen codes**, not PETSCII. To read a dump back into text:

| Screen range | Mapping                                                          |
|--------------|------------------------------------------------------------------|
| `$00`        | `@`                                                              |
| `$01-$1A`    | `A`-`Z` (subtract from PETSCII letter: `A`=`$41` -> `$01`)       |
| `$1B-$1F`    | `[ \ ] _ <-`                                                     |
| `$20`        | space                                                            |
| `$21-$3F`    | PETSCII symbols passed through unchanged (`!`,`"`, digits, etc.) |
| `$40-$5F`    | Block graphics                                                   |
| `$80-$FF`    | Reverse video of `$00-$7F` (bit 7 set)                           |

Key bytes to recognise quickly during diagnostics:

| Byte      | Glyph                                |
|-----------|--------------------------------------|
| `$20`     | space                                |
| `$2D`     | `-`                                  |
| `$2E`     | `.`                                  |
| `$2C`     | `,`                                  |
| `$3A`     | `:`                                  |
| `$3F`     | `?`                                  |
| `$22`     | `"`                                  |
| `$30-$39` | digits 0-9                           |
| `$A0`     | reverse space (solid block / cursor) |

Example: the bytes at the start of a SYNTAX-error row decode as

```
3f 13 19 0e 14 01 18 20 05 12 12 0f 12 20 09 0e 20 20 31 30
?  S  Y  N  T  A  X     E  R  R  O  R     I  N        1  0
```

When the dumped screen does not match what the program is supposed to draw, the visible content is almost always BASIC's banner, `READY.`, or one of `?SYNTAX ERROR`/`?ILLEGAL QUANTITY`/`?DEVICE NOT PRESENT` -- meaning execution never reached the program, or returned to BASIC before drawing.

### Screen Row Arithmetic

Each row is 40 bytes. Row N starts at `$8000 + N * 40` (`$28` per row):

| Row | Address |
|-----|---------|
| 0   | `$8000` |
| 1   | `$8028` |
| 2   | `$8050` |
| 3   | `$8078` |
| 24  | `$83C0` |

A `?SYNTAX ERROR IN 10` message at row 1 (`$8028`) but not row 0 means the program ran long enough to clear the screen (moving cursor to row 0), then returned to BASIC which printed the error on the next line. The clear-screen happened; the crash came _after_ init.

A `?SYNTAX ERROR IN 10` at row 0 means the screen was never cleared -- BASIC parsed and rejected the BASIC stub without the program's init ever running.

## Memory Landmarks

Useful zero-page and low-RAM addresses to dump during diagnostics:

| Address       | Name                                                 | Tells you                                                                                                                               |
|---------------|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `$0028-$0029` | TXTTAB                                               | Start of BASIC program (should be `$0401`)                                                                                              |
| `$002A-$002B` | VARTAB                                               | One past loaded program end; non-`$0401` value confirms LOAD ran                                                                        |
| `$002C-$002D` | ARYTAB                                               | Start of array storage                                                                                                                  |
| `$002E-$002F` | STREND                                               | End of array storage                                                                                                                    |
| `$0077-$0078` | TXTPTR                                               | BASIC's current text-parse pointer                                                                                                      |
| `$0090-$0091` | CINV                                                 | IRQ vector (default `$E62E` after KERNAL boot)                                                                                          |
| `$0092-$0093` | CBINV                                                | BRK handler                                                                                                                             |
| `$0094-$0095` | NMINV                                                | NMI vector                                                                                                                              |
| `$0096`       | STATUS                                               | KERNAL I/O status byte                                                                                                                  |
| `$00A7`       | BLNSW                                                | Cursor blink (`$00` = blink, `$01` = solid)                                                                                             |
| `$00FB-$00FE` | KERNAL tape pointers (commonly borrowed for ZP work) |                                                                                                                                         |
| `$0326-$0327` | IBSOUT                                               | Indirect CHROUT vector                                                                                                                  |
| `$01F0-$01FF` | Top of the 6502 hardware stack                       |                                                                                                                                         |
| `$8000-$83E7` | Screen RAM (40x25 screen codes)                      |                                                                                                                                         |
| `$E84C`       | PCR                                                  | VIA peripheral control; bits 7:5 = CB2 mode (CB2 = IEEE-488 NDAC); writing `$0C` puts CB2 in input mode and breaks all OPEN/CHKIN/CHRIN |

Useful checks:

- `VARTAB` still equal to `TXTTAB` (`$0401`) means LOAD never ran -- autostart did not reach RUN.
- A program writing past its declared end will show up as bytes past the load address that differ from the on-disk PRG.
- `STATUS` non-zero after a KERNAL file call indicates an I/O error -- bit 7 is IEEE-488 EOI, bits 0-1 are timeouts.

## Diagnosing Crashes

### No Breakpoint Ever Fires

If you set breakpoints across a range of addresses and none fires in 30+ seconds of warp-mode execution, the crash occurs _before_ the earliest breakpoint. Connect the remote monitor, send `r`, and read the PC:

```
r
  PC   AC XR YR SP  NV-BDIZC
; E698 00 08 00 EC  00100101
```

Use the PC to locate the crash site:

| PC range      | Interpretation                                            |
|---------------|-----------------------------------------------------------|
| `$0000-$7FFF` | Crashed in RAM -- your code or the BASIC interpreter      |
| `$8000-$8FFF` | Executing screen RAM (almost certainly a pointer bug)     |
| `$E000-$FFFF` | Executing KERNAL ROM -- usually stuck in a KERNAL routine |

### KERNAL Hang: I=1 and PC in ROM

When `r` shows PC in the KERNAL ROM (`$E000-$FFFF`) and the `I` flag = 1 (interrupt disable), the CPU is stuck inside a KERNAL critical section. The most common cause on PET 3032 is an IEEE-488 bus deadlock in the byte-transfer handshake loop (around `$E698`).

What to check:
1. SP: `SP=$FF` is an empty stack; `SP=$EF` = 16 bytes pushed (8 JSR frames); `SP=$EC` = 19 bytes (≈9 JSR frames). A depth of 9 is consistent with the KERNAL `OPEN`→`LISTEN`→byte-receive chain.
2. `STATUS` at `$0096`: non-zero value means the KERNAL already logged an I/O error flag but is still looping.
3. VIA PCR (see below).

### VIA PCR and the IEEE-488 Bus

The VIA 6522 at `$E840` controls the IEEE-488 handshake lines through its Peripheral Control Register (PCR) at `$E84C`.

| PCR bits | Lines controlled | Notes                                                                  |
|----------|------------------|------------------------------------------------------------------------|
| 7:5      | CB2 mode         | `000` = CB2 as **input**; on PET 3032, CB2 **is NDAC**                 |
| 3:1      | CA2 mode         | `110` = manual output low; selects uppercase/graphics charset ROM half |

Writing `$0C` to PCR sets bits 7:5 = `000` → CB2 in **input** mode. With NDAC in input mode, the PET can never signal "Not Data Accepted" to the drive. The drive keeps waiting; the KERNAL loops forever; interrupts are disabled. Every subsequent `OPEN`, `CHKIN`, or `CHRIN` call hangs permanently.

**Hazard**: if your program saves and restores PCR to switch character sets (a common technique), verify the value you write. `$0C` looks like "set bit 3 and 2" but puts CB2 into input mode. Use `$4C` (CB2 output high) or `$08` (CA2 low only, CB2 default output) instead, depending on which charset the PET was in at startup.

**Diagnosis**: if OPEN hangs and the PCR contains `$0C`, this is the cause.

## Built-in Monitor

The VICE built-in monitor is a 6502 machine-level debugger.

Open the monitor at any time by pressing **Alt+H** (default hotkey) while the emulator is running, or use the **Machine** menu.

To use the terminal (text) version of the monitor instead of the GTK3 window, add `-nativemonitor` to the command line. The native monitor is easier to script and copy from.

```bash
xpet -model 3032 -nativemonitor -autostart program.prg
```

### Monitor Commands

These are the essential commands for debugging PET programs.

| Command              | Action                                      |
|----------------------|---------------------------------------------|
| `r`                  | Show CPU registers (A, X, Y, SP, PC, flags) |
| `d <addr>`           | Disassemble from address                    |
| `m <start> <end>`    | Hex dump memory range                       |
| `g`                  | Resume from current PC (continue)           |
| `g <addr>`           | Jump to address and run from there          |
| `z`                  | Step into (execute one instruction)         |
| `n`                  | Step over (treats JSR as one step)          |
| `break <addr>`       | Set execution breakpoint at address         |
| `watch load <addr>`  | Break on memory read from address           |
| `watch store <addr>` | Break on memory write to address            |
| `del <num>`          | Delete breakpoint or watchpoint by number   |
| `bk`                 | List all breakpoints and watchpoints        |
| `x`                  | Exit monitor, resume emulation              |
| `q`                  | Quit VICE / disconnect remote monitor       |

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

| Value     | Stops when                   |
|-----------|------------------------------|
| `ready`   | BASIC READY prompt appears   |
| `reset`   | CPU reset vector fires       |
| `$<addr>` | PC reaches the given address |

Stop at BASIC ready and then manually run the program:

```bash
xpet -model 3032 -nativemonitor -initbreak ready -autostart program.prg
```

Stop at the first instruction of the machine-code entry point:

```bash
xpet -model 3032 -nativemonitor -initbreak 0x040E -autostart program.prg
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

### Breakpoint Timing Gotcha

Breakpoints set after connecting via `-remotemonitor` only catch the program if it has not already passed them. If your code runs from `$0442` and enters a `JSR GETIN` loop, by the time you connect a second later there's no chance to catch entry. Use `-initbreak` or `-moncommands` to install breakpoints before the CPU starts running.

With `-warp` the window is even smaller -- often under one wall-clock second for the entire boot + program run. See "Warp Mode Timing" in the Headless Debugging section for the correct recipe.

**Diagnosing a missed breakpoint**: connect with `nc`, send `r`, read the PC. If PC is somewhere you did not expect (e.g., stuck in KERNAL ROM at `$E698`), the breakpoints were passed or the program is hung. Set a new breakpoint at the current PC or an earlier address, then send `g` to resume and observe.

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

### Cycle Limit

`-limitcycles <N>` terminates the emulator after `N` host-CPU cycles. Essential for headless tests so a stuck program does not hang the host shell forever.

At PET 1 MHz, 10,000,000 cycles is 10 emulated seconds. With `-warp`, that may finish in well under a second of wall-clock time.

```bash
xpet -model 3032 -warp -limitcycles 100000000 -autostart program.prg
```

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

`-logfile <name>` writes VICE diagnostic output (ROM load messages, drive errors, AUTOSTART progress) to a file instead of stderr.

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

This lets an external script drive the monitor without focus on the emulator window. See "Headless Debugging" above for the full recipe.

### Binary Monitor

`-binarymonitor` opens a TCP port that accepts VICE's binary protocol instead of text commands. Suitable for tooling that speaks the protocol (vice-bridge, vice-emu-protocol clients). For shell/grep work, prefer `-remotemonitor`.
