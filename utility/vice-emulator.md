# VICE PET Emulator

## Purpose

> **Scope:** Running PET 3032 programs and debugging with the `xpet` command (VICE 3.7+)
> **Key items:** `-model 3032`, `-autostart`, `-drive8type 2031`, `-remotemonitor`, `-limitcycles`, `-warp`, headless screen inspection

| Out of scope               | See instead                 |
|----------------------------|-----------------------------|
| Assembling source to PRG   | `utility/dasm-assembler.md` |
| Loading files at PET BASIC | `system/load.md`            |
| Disk image file formats    | `system/disk.md`            |

## Contents

| Section                             | Line | What it covers                                                             |
|-------------------------------------|------|----------------------------------------------------------------------------|
| Invocation                          | 34   | Minimal command form and model flag                                        |
| PET ROM Setup                       | 44   | How VICE finds ROMs; symlinking on Linux, bindist on Windows               |
| Drive Types on PET                  | 116  | `-drive8type 2031` for D64; never 1541 on PET                              |
| Running a PRG                       | 132  | Autostart modes, why disk autostart is most reliable                       |
| c1541 Disk Image Building           | 171  | Building D64s, "readme" hang bug, interactive mode, filename case folding  |
| Headless Debugging                  | 186  | Remote monitor over TCP, cycle limits, screen dumps, warp timing, Windows  |
| Decoding Screen Codes               | 413  | Reading dumped `$8000-$83E7` bytes back into characters; row arithmetic    |
| Keyboard Buffer Injection           | 466  | Writing to `$026F`/`$009E` to simulate key presses; warp mode and auto-repeat hazards |
| Signal-Byte Tracing                 | 514  | Writing trace bytes to safe RAM to locate crash points                     |
| Memory Landmarks                    | 514  | Addresses worth checking during diagnostics                                |
| Verifying KERNAL Jump Table Entries | 542  | Disassembling `$FFC0-$FFEA`; PET vs C64 entry differences                  |
| Diagnosing Crashes                  | 580  | SYNTAX ERROR from bad KERNAL calls, KERNAL hang, SP depth, VIA PCR hazard  |
| Debugging Workflow                  | 638  | Step-by-step recipe: check if program ran, breakpoint, step, watch, trace, keyboard input logic |
| Built-in Monitor                    | 737  | Opening the monitor, full command reference, register modification, memory |
| Breakpoints                         | 888  | initbreak, break, watch, trace, conditional, warp-mode timing              |
| Monitor Scripts                     | 937  | moncommands file for automated debug sessions                              |
| Useful Flags                        | 963  | warp, speed, keybuf, logging                                               |

## Invocation

```bash
xpet -model 3032
```

Always pass `-model 3032` to emulate the 3032 configuration (32 KiB RAM, 40-column display, BASIC 2, no colour).

Without `-model`, VICE defaults to the 2001 configuration which has a different RAM size and ROM.

## PET ROM Setup

VICE looks for ROM image files using the `Directory` resource, a colon-separated search path list. The default search order depends on the OS:

### Linux

1. The path given by `-directory <base>` (treated as the whole data root)
2. The system path: `/usr/share/vice/PET/`
3. The user path: `~/.local/share/vice/PET/`
4. The boot path: the directory where the `xpet` executable resides, plus its parent (`BOOTPATH/PET/`)

### Windows

1. The path given by `-directory <base>`
2. The user path: `%APPDATA%\vice\PET\`
3. The boot path: the directory where `xpet.exe` resides, plus its parent (`BOOTPATH\..\PET\`)

On Windows, a standard bindist (e.g. `GTK3VICE-3.10-win64`) ships with all ROMs under `BOOTPATH\..\PET\` and `BOOTPATH\..\DRIVES\`. No manual ROM setup is needed -- VICE finds them automatically.

### ROM Files

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

The fix is to leave the data root alone and instead symlink only the missing ROMs into the user path (Linux only):

```bash
mkdir -p ~/.local/share/vice/PET
ln -sf <source>/PET/characters-2.901447-10.bin   ~/.local/share/vice/PET/
ln -sf <source>/PET/basic-2.901465-01-02.bin    ~/.local/share/vice/PET/
ln -sf <source>/PET/kernal-2.901465-03.bin      ~/.local/share/vice/PET/
ln -sf <source>/PET/edit-2-n.901447-24.bin      ~/.local/share/vice/PET/

mkdir -p ~/.local/share/vice/DRIVES
ln -sf <source>/DRIVES/dos2031-901484-03+05.bin  ~/.local/share/vice/DRIVES/
```

On Windows, symlinks require administrator privileges. If ROMs are missing from the user path, copy them instead:

```powershell
$viceUser = "$env:APPDATA\vice"
New-Item -ItemType Directory -Force "$viceUser\PET"
New-Item -ItemType Directory -Force "$viceUser\DRIVES"
Copy-Item "<source>\PET\characters-2.901447-10.bin"   "$viceUser\PET\"
Copy-Item "<source>\PET\basic-2.901465-01-02.bin"    "$viceUser\PET\"
Copy-Item "<source>\PET\kernal-2.901465-03.bin"      "$viceUser\PET\"
Copy-Item "<source>\PET\edit-2-n.901447-24.bin"      "$viceUser\PET\"
Copy-Item "<source>\DRIVES\dos2031-901484-03+05.bin"  "$viceUser\DRIVES\"
```

In practice, a standard Windows bindist already has all ROMs in the boot path, so neither symlinking nor copying is needed.

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

### c1541 "readme" Hang Bug

c1541 (VICE 3.7.1) has a bug where any `-write` argument containing the substring `readme` (case-insensitive, in either the host filename or the CBM-DOS name) causes the tool to hang indefinitely. The command never completes and never produces an error.

**Affected**: both the command-line form (`c1541 -write file.txt "readme,s"`) and the interactive form (`write file.txt readme,s` inside a piped c1541 session).

**Workaround**: write the file with a safe name (e.g. `zreadme,s`), then use c1541's `rename` command (which is not affected by the bug) to rename it on the disk:

```bash
c1541 -format "disk,01" d64 work.d64 \
      -write data.txt "zreadme,s"

printf 'attach work.d64\nrename zreadme README\nquit\n' | c1541
```

### c1541 Interactive Mode

When the command-line form (`c1541 -format ... -write ...`) hangs or behaves unexpectedly, pipe commands into c1541's interactive mode instead. This gives finer control and separates the format and write steps:

```bash
printf 'format "diskname,01" d64 work.d64\nwrite prog.prg program,p\nwrite data.txt data,s\nquit\n' | c1541
```

Each command is processed line by line. Use `quit` or `exit` to terminate the session. This form is also useful for `rename`, `dir`, and `delete` operations that are awkward to express as command-line flags.

### CBM-DOS Filename Case Folding

CBM-DOS uppercases all filenames on disk. Two source names that differ only in case (e.g. `readme,s` and `README,S`) collide and produce a single `README` entry. When adding a new file, check that its uppercased name does not match an existing entry, or c1541 will either overwrite the wrong file or hang.

### Inject Mode Caveats

`-autostartprgmode 1` writes the PRG bytes into RAM and stuffs `RUN` into the keyboard buffer. On C64 this is the fastest dev loop. On PET it can leave BASIC's text/variable pointers in an inconsistent state for some PRG layouts, producing `?SYNTAX ERROR IN 10` on the first line BASIC tries to parse. When that happens, switch to disk autostart.

**Required for machine-code programs that call KERNAL I/O routines**: `-autostartprgmode 1` is needed when the program calls KERNAL `OPEN`/`CLOSE`/`CHKIN`/`CHRIN` directly. Without this flag, VICE uses disk autostart which goes through BASIC's `LOAD`/`RUN` cycle. This can interfere with programs that call KERNAL `OPEN`/`CLOSE` directly, because the PET's `OPEN`/`CLOSE` routines include BASIC parameter parsing that expects `TXTPTR` (`$0077-$0078`) to be valid. With `-autostartprgmode 1`, the PRG is injected directly into RAM and `RUN` is stuffed into the keyboard buffer, which works more reliably for pure machine-code programs.

### Attach Without Autostart

```bash
xpet -model 3032 -drive8type 2031 -8 disk.d64
```

From BASIC, type `LOAD"*",8` then `RUN` to load and run the first program on the disk.

## Headless Debugging

`xpet` always opens a graphical window, but the **remote text monitor** lets a shell script drive it without focusing the GUI. This is the workhorse for verifying programs from CI scripts or for diagnostics when the visible screen looks wrong.

### Recipe: Capture Screen RAM After Boot

**Linux (bash + nc):**

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

**Windows (PowerShell):**

On Windows, `nc` is not available. Use PowerShell's built-in TCP client instead. Launch xpet from `cmd /c` to avoid PowerShell argument-parsing issues with `-remotemonitor`:

```powershell
# 1. Launch xpet via cmd to avoid PowerShell argument mangling
$proc = Start-Process -FilePath cmd -ArgumentList '/c xpet -model 3032 -drive8type 2031 -autostart work.d64 -warp -limitcycles 500000000 -remotemonitor -remotemonitoraddress 127.0.0.1:6502 -logfile xpet.log' -NoNewWindow -PassThru

# 2. Give the autostart sequence wall-clock time to play out
Start-Sleep -Seconds 15

# 3. Connect to the remote monitor and dump screen RAM
$client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 6502)
$stream = $client.GetStream()
$stream.ReadTimeout = 5000
$writer = New-Object System.IO.StreamWriter($stream)
$writer.AutoFlush = $true
$buf = New-Object byte[] 8192
Start-Sleep -Milliseconds 500
$writer.WriteLine('m $8000 $83E7')
Start-Sleep -Milliseconds 1000
$data = ''
while ($stream.DataAvailable) {
    $count = $stream.Read($buf, 0, $buf.Length)
    $data += [System.Text.Encoding]::ASCII.GetString($buf, 0, $count)
}
$writer.WriteLine('q')
Start-Sleep -Milliseconds 200
while ($stream.DataAvailable) {
    $count = $stream.Read($buf, 0, $buf.Length)
    $data += [System.Text.Encoding]::ASCII.GetString($buf, 0, $count)
}
$client.Close()
$data | Out-File -Encoding utf8 screen.txt

# 4. Tear down xpet
Stop-Process -Id $proc.Id -Force
```

When using Git Bash (`sh`) on Windows, the Linux recipe works with minor adjustments: replace `/tmp/` with a Windows-compatible temp path, and use `kill %1` instead of `kill $XPETPID`.

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

### Python Socket Monitor Scripting

The `nc` approach has reliability issues: timing is fragile, and the `-q` flag behaviour varies between `nc` implementations (some ignore it, some treat the argument as seconds, some as a flag). A Python socket script is more robust and portable:

```python
import socket, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 6502))
s.settimeout(3)

def send(cmd):
    s.send((cmd + '\n').encode())
    time.sleep(0.3)
    data = b''
    while True:
        try:
            chunk = s.recv(8192)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    return data.decode()

# Dump screen
print(send('m $8000 $83e7'))
# Check registers
print(send('r'))
# Disassemble KERNAL jump table
print(send('d $ffc0 $ffea'))

s.close()
```

Key advantages over `nc`:

| Issue             | `nc`                              | Python socket                       |
|-------------------|-----------------------------------|-------------------------------------|
| Timing            | Fixed `sleep`/`-q` guesswork      | `settimeout` + recv loop            |
| Output capture    | May truncate on early close       | `recv` loop drains all output       |
| `-q` flag         | Behaviour varies by `nc` variant  | No dependency                       |
| Multiple commands | One-shot pipe, reconnect per call | Persistent connection, reuse socket |

On Windows, `nc` is typically not installed. The PowerShell TCP snippet above and the Python socket script are the recommended alternatives. The Python script works unchanged on both Linux and Windows.

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

## Keyboard Buffer Injection

The PET KERNAL keyboard buffer at `$026F` (10 bytes, count at `$009E`) can be written directly via the remote monitor to simulate key presses. This enables automated UI testing without physical keyboard input.

### Basic Injection

Use the monitor's `>` (memory write) command to place a PETSCII code in the buffer and set the count:

```
> $026F 56
> $009E 01
```

This injects PETSCII `$56` ('V') and sets the buffer count to 1. The program's `GETIN` loop will return this key on the next call.

### Python Helper for Sequential Key Injection

When testing interactive programs (file viewers, menus, dialogs), inject keys one at a time with delays to let the program process each key and redraw:

```python
import socket, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 6512))
s.settimeout(2.0)

def cmd(c):
    s.sendall((c + "\n").encode())
    time.sleep(0.3)
    data = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            data += chunk
    except socket.timeout:
        pass
    return data.decode("ascii", errors="replace")

def inject_key(petscii, delay=3):
    """Inject a single key into the KERNAL keyboard buffer."""
    cmd(f"> $026F {petscii:02X}")
    cmd("> $009E 01")
    time.sleep(delay)  # let the program process the key and redraw

def dump_row(row):
    """Dump a 40-byte screen row as hex."""
    addr = 0x8000 + row * 40
    return cmd(f"m ${addr:04X} ${addr+39:04X}")

# Example: test a file viewer
inject_key(0x56)   # 'V' -- open viewer
print(dump_row(0)) # check header bar
print(dump_row(2)) # check first content row

inject_key(0x48)   # 'H' -- switch to hex mode
print(dump_row(2)) # verify hex layout

inject_key(0x1D)   # cursor RIGHT -- page down
print(dump_row(2)) # verify scrolled content

inject_key(0x45)   # 'E' -- exit viewer
print(dump_row(0)) # verify returned to main screen

s.close()
```

### Timing and Warp Mode

In warp mode (`-warp`), the emulator runs much faster than real time. A 3-second wall-clock delay may correspond to many seconds of emulated time -- usually enough for the program to process a key and redraw. If the program has a long redraw cycle (e.g., decompressing a large frame), increase the delay.

If keys are injected faster than the program can process them, the 10-byte buffer may overflow and keys will be lost. Inject one key at a time and wait for the screen to update before injecting the next.

### Warp Mode and Keyboard Auto-Repeat

The KERNAL 60 Hz IRQ keyboard scan auto-repeats held keys into the keyboard buffer (see `system/keyboard.md` "Auto-Repeat"). Under warp mode, the IRQ runs orders of magnitude faster than real time, so auto-repeat fills the buffer in milliseconds of wall-clock time. This causes three debugging problems:

1. **Toggle key bugs reproduce more aggressively under warp.** A menu that opens and closes on the same key will appear to open and instantly close, because the auto-repeated key is already in the buffer by the time the menu's input loop calls `GETIN`. On real hardware the user releases the key within ~100 ms; under warp the repeat fires before the user can react.

2. **Injected keys can be overwritten by the IRQ scan.** When you inject a key via `> $026F XX` followed by `> $009E 01`, the 60 Hz IRQ scan may fire between your two monitor commands and overwrite `$026F` with an auto-repeated key from the (simulated) held key. The injected key never reaches `GETIN`. If `GETIN` returns an unexpected value after injection, check `$026F` and `$009E` immediately before the `GETIN` call to see whether the injection survived.

3. **Buffer drain loops can hang.** A `flush_keys` routine that loops `GETIN` until `$00` may never terminate under warp if a key is auto-repeating: the IRQ refills the buffer faster than the drain loop empties it. This is not a bug in the drain logic -- it is an artifact of warp mode. Test buffer drain logic with warp off.

**Recommendation**: when debugging keyboard input logic, toggle keys, menu open/close behavior, or any code that calls `GETIN` in a loop, run xpet **without `-warp`**. Use warp only for boot-to-crash tests and screen capture verification. For keyboard logic debugging, connect the remote monitor, set breakpoints, and step through `GETIN` calls in real time.

To toggle warp during a monitor session:

```
warp off
```

Step through the key handling code, then re-enable warp if needed:

```
warp on
```

### Verifying Screen Output After Injection

After injecting a key and waiting, dump the relevant screen rows and decode the screen codes (see Decoding Screen Codes above). Compare the decoded output against the expected UI state.

For reverse-video bars (header/footer), remember that bytes with bit 7 set (`$80`-`$FF`) are reversed. Strip bit 7 before decoding to read the underlying character.

### Common Test Key Codes

| Key          | PETSCII | Hex   |
|--------------|---------|-------|
| Letters A-Z  | A-Z     | `$41`-`$5A` |
| Cursor up    |         | `$91` |
| Cursor down  |         | `$11` |
| Cursor left  |         | `$9D` |
| Cursor right |         | `$1D` |
| HOME         |         | `$13` |
| RETURN       |         | `$0D` |
| RUN/STOP     |         | `$03` |
| RVS ON (Tab) |         | `$12` |
| RVS OFF (Shift+Tab) | | `$92` |

See `system/keyboard.md` "Keyboard Buffer Injection" for the full buffer layout and assembly-level injection techniques.

## Signal-Byte Tracing

When a program crashes and breakpoints are hard to place (warp mode, unknown crash site), **signal-byte tracing** pinpoints how far execution got. Write a unique byte value to a safe RAM address after each significant step in the program. When the program crashes, read the trace byte via the remote monitor to see the last completed step.

**IMPORTANT**: PET 3032 has only 32K RAM (`$0000-$7FFF`). Do NOT use `$9000` or higher for trace bytes -- those addresses are screen RAM or ROM and are not writable. Use `$7F00` or lower, but avoid zero-page (`$0000-$00FF`) and your program's own variables.

Example code pattern:

```asm
; At start of program
lda #$01
sta $7f00       ; trace: reached start

jsr init
lda #$02
sta $7f00       ; trace: init done

jsr load_panel
lda #$03
sta $7f00       ; trace: load_panel done
```

Read the trace byte via the remote monitor:

```
m $7f00 $7f00
```

If the value is `$01`, the crash was during `init`. If `$02`, during `load_panel`. If `$03`, `load_panel` completed and the crash is later.

For finer granularity, nest trace bytes inside subroutines using a separate range (e.g. `$7F01`):

```asm
init:
    lda #$10
    sta $7f01       ; trace: entered init, before OPEN
    jsr pet_open    ; PET OPEN wrapper (never call $FFC0 directly from ML)
    lda #$11
    sta $7f01       ; trace: OPEN done
    ldx #1          ; logical file number
    jsr CHKIN       ; CHKIN is safe to call directly ($FFC6)
    lda #$12
    sta $7f01       ; trace: CHKIN done
    rts
```

This two-level scheme lets the outer trace (`$7F00`) identify which subroutine crashed and the inner trace (`$7F01`) identify which KERNAL call inside it failed.

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

## Verifying KERNAL Jump Table Entries

This was critical for diagnosing the root cause of `?SYNTAX ERROR` crashes. Disassemble the KERNAL jump table to verify which entries actually exist:

```
d $ffc0 $ffea
```

On PET 3032, the jump table starts at `$FFC0` (NOT `$FFB7` like the C64). The region `$FFB7-$FFBF` contains ROM code text (`C. 0978 CBM `) and filler bytes (`$AA` = `TAX`), NOT jump table entries.

If a `jsr $FFBD` (SETNAM) or `jsr $FFBA` (SETLFS) crashes, check whether those addresses actually contain `JMP` instructions. On PET they do not.

PET jump table entries that DO exist:

| Address | KERNAL routine |
|---------|----------------|
| `$FFC0` | OPEN           |
| `$FFC3` | CLOSE          |
| `$FFC6` | CHKIN          |
| `$FFC9` | CHKOUT         |
| `$FFCC` | CLRCHN         |
| `$FFCF` | CHRIN          |
| `$FFD2` | CHROUT         |
| `$FFD5` | LOAD           |
| `$FFD8` | SAVE           |
| `$FFE1` | STOP           |
| `$FFE4` | GETIN          |
| `$FFE7` | CLALL          |
| `$FFEA` | UDTIM          |

The PET does NOT have these C64-only entries:

| Address | C64 routine | PET status                         |
|---------|-------------|------------------------------------|
| `$FFB7` | READST      | Not present; ROM text/filler bytes |
| `$FFBA` | SETLFS      | Not present; bytes are `$AA` (TAX) |
| `$FFBD` | SETNAM      | Not present; bytes are `$AA` (TAX) |

## Diagnosing Crashes

### ?SYNTAX ERROR from Non-Existent KERNAL Entries

If `?SYNTAX ERROR IN 10` appears and the program uses `jsr $FFBD` (SETNAM) or `jsr $FFBA` (SETLFS), those addresses do not exist on the PET KERNAL jump table (see [Verifying KERNAL Jump Table Entries](#verifying-kernal-jump-table-entries)).

The bytes at `$FFBD` are `$AA` (the `TAX` instruction), so `jsr $FFBD` executes `TAX TAX TAX` then falls through into `OPEN` at `$FFC0` with wrong parameters. OPEN fails and jumps to the BASIC error handler at `$CE03`, which prints the syntax error.

| Symptom                                 | Cause                                                     |
|-----------------------------------------|-----------------------------------------------------------|
| `?SYNTAX ERROR IN 10` after `jsr $FFBD` | `$FFBD` is not SETNAM on PET; bytes are `$AA` (TAX)       |
| `?SYNTAX ERROR IN 10` after `jsr $FFBA` | `$FFBA` is not SETLFS on PET; same fall-through into OPEN |
| OPEN hangs or returns garbage           | OPEN received uninitialised filename/length pointers      |

**Fix**: use PET-specific wrappers that set the zero-page locations directly instead of calling non-existent KERNAL entries. On the PET, the filename length goes to `$D1`, the filename address to `$DA/$DB`, the logical file number to `$D2`, the secondary address to `$D3`, and the device number to `$D4`. Set those locations directly in your code before calling the low-level OPEN logic at `$F560` (not the jump table entry at `$FFC0`, which includes BASIC parameter parsing). See `system/kernal.md` for the complete wrapper routines.

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

## Debugging Workflow

When a PET program does not behave correctly, follow this sequence to narrow down the cause.

### Step 1: Check Whether the Program Ran at All

Launch with `-warp` and `-limitcycles`, then dump screen RAM and check VARTAB:

```bash
xpet -model 3032 -drive8type 2031 -warp -limitcycles 100000000 \
     -remotemonitor -remotemonitoraddress 127.0.0.1:6502 \
     -autostart work.d64 > /tmp/xpet.log 2>&1 &
sleep 5
( echo 'm $002A $002B'
  echo 'm $8000 $8027'
  echo 'r'
  echo 'q'
) | nc -w 2 127.0.0.1 6502 > /tmp/probe.txt
kill %1 2>/dev/null
```

Interpret the results:

- VARTAB (`$002A-$002B`) still `$01 $04` (little-endian `$0401`) means LOAD never ran -- autostart failed before RUN.
- Screen RAM at `$8000` is all `$20` (spaces) with `READY.` at the bottom means the program never wrote to the screen.
- Screen RAM shows partial output means the program ran but crashed partway through.

### Step 2: Set a Breakpoint at the Program Entry

Create a monitor script with a breakpoint at the program's first instruction (the address `SYS` jumps to, typically `$040E`):

```bash
cat > debug.mon << 'EOF'
break $040E
x
EOF

xpet -model 3032 -drive8type 2031 -warp -limitcycles 100000000 \
     -remotemonitor -remotemonitoraddress 127.0.0.1:6502 \
     -moncommands debug.mon \
     -autostart work.d64 > /tmp/xpet.log 2>&1 &
sleep 5
```

Connect and verify the breakpoint fired:

```bash
( echo 'r'
  echo 'd $040E'
  echo 'q'
) | nc -w 2 127.0.0.1 6502
```

If the breakpoint never fires, the crash is before `$040E` -- the BASIC stub itself is malformed. Check the disassembly at `$0401` to verify the stub bytes.

### Step 3: Step Through the Program

Once stopped at the entry point, step through instructions one at a time:

```
z          ; step into (follows JSR)
n          ; step over (treats JSR as one step)
ret        ; step out (run until next RTS)
```

After each step, check registers with `r` and relevant memory with `m`.

### Step 4: Set Watchpoints on Suspicious Addresses

If a screen location or zero-page variable gets corrupted, set a watchpoint to catch the write:

```
watch store $8050
x
```

The monitor stops and shows the instruction that wrote to the address, along with the register state.

### Step 5: Use Conditional Breakpoints for Loop Iterations

If a bug only appears on a specific loop iteration, use a condition:

```
break $0420 if X==$0A
x
```

This only stops when the breakpoint at `$0420` is hit with X = `$0A`.

### Step 6: Check the Call Stack

Use `bt` (backtrace) to see the JSR call chain that led to the current PC:

```
bt
```

Output shows stack offsets relative to SP+1, most recent call first. This helps identify unexpected recursion or a subroutine called from the wrong place.

### Step 7: Debug Keyboard Input Logic

When a program's key handling behaves wrong (a key does nothing, or a toggle key opens and immediately closes an element), use the remote monitor to inject keys and trace the dispatch path. This is more reliable than pressing keys in the emulator window, because the monitor gives exact control over timing and lets you inspect the keyboard buffer between key presses.

**Run without warp.** Keyboard auto-repeat runs at the 60 Hz IRQ rate; under warp the buffer fills in milliseconds of wall-clock time, which makes toggle-key bugs reproduce differently than on real hardware. See "Warp Mode and Keyboard Auto-Repeat" above.

```bash
xpet -model 3032 -drive8type 2031 \
     -remotemonitor -remotemonitoraddress 127.0.0.1:6502 \
     -moncommands debug.mon \
     -autostart work.d64 > /tmp/xpet.log 2>&1 &
```

**Set breakpoints at the key dispatch points.** Identify the addresses of the `GETIN` call site, the key comparison chain, and the open/close routines. Put them in a monitor script:

```bash
cat > debug.mon << 'EOF'
break $0440
break $0490
break $0548
x
EOF
```

In this example, `$0440` is the `GETIN` call in `main_loop`, `$0490` is the `GETIN` call in `ml_wait` (the menu input loop), and `$0548` is `do_menu_close`. If both `$0490` and `$0548` fire from a single key injection, the menu is opening and closing on the same key press -- an auto-repeat problem.

**Inject a key and let the breakpoint fire.** Connect to the monitor, inject the key, and wait for the breakpoint:

```
> $026F 4D
> $009E 01
x
```

This injects PETSCII `$4D` ('M') and lets the CPU run. When the breakpoint at the `GETIN` call site fires, check what `GETIN` returned:

```
r
```

The accumulator (A) holds the PETSCII code returned by `GETIN`. If A is `$00`, the buffer was already drained (the IRQ scan may have cleared it, or a previous `GETIN` consumed it). If A matches the injected key, step forward to see which dispatch branch is taken.

**Inspect the keyboard buffer.** After a `GETIN` call, dump the buffer to see whether auto-repeat has already queued another copy of the same key:

```
m $009E
m $026F $0278
```

`$009E` is the buffer count. If it is nonzero after `GETIN` returned the toggle key, the 60 Hz IRQ has already auto-repeated the key into the buffer. The next `GETIN` in the menu's input loop will return the same key and close the menu immediately. This is the definitive diagnosis of the toggle-key auto-repeat bug.

**Trace the dispatch path.** Step through the key comparison chain to confirm which branch fires:

```
z
```

After each `cmp`/`beq` pair, check whether the branch was taken. If the "close menu" branch fires immediately after the "open menu" branch, the auto-repeated key is the cause. The fix is the toggle-key debounce pattern in `system/keyboard.md` "Toggle Key Debounce".

**Compare warp on vs off.** If the bug reproduces under warp but not with warp off, it is likely a timing-dependent auto-repeat or buffer-overflow artifact, not a logic bug. Always confirm keyboard logic fixes with warp off before re-enabling warp for other tests.

**Inject key sequences with delays.** For multi-step interactions (open menu, move selection, close menu), inject one key at a time with a delay between each, re-setting breakpoints as needed:

```
> $026F 4D
> $009E 01
x
```

Wait for the breakpoint, inspect state, then inject the next key. Do not fill the buffer with multiple keys at once -- the 10-byte limit and auto-repeat interaction make the result unpredictable.

## Built-in Monitor

The VICE built-in monitor is a 6502 machine-level debugger.

Open the monitor at any time by pressing **Alt+H** (default hotkey) while the emulator is running, or use the **Machine** menu.

To use the terminal (text) version of the monitor instead of the GTK3 window, add `-nativemonitor` to the command line. The native monitor is easier to script and copy from.

```bash
xpet -model 3032 -nativemonitor -autostart program.prg
```

### Monitor Commands

These are the essential commands for debugging PET programs.

#### Machine State

| Command            | Action                                                 |
|--------------------|--------------------------------------------------------|
| `r`                | Show CPU registers (A, X, Y, SP, PC, flags)            |
| `r A=$42`          | Set accumulator to `$42`                               |
| `r PC=$0400`       | Set program counter to `$0400`                         |
| `r X=$10, Y=$20`   | Set multiple registers at once                         |
| `r FL=$00`         | Set status flags byte (`FL` = flags register)          |
| `d <addr>`         | Disassemble from address                               |
| `m <start> <end>`  | Hex dump memory range                                  |
| `i <start> <end>`  | Display memory as PETSCII text                         |
| `ii <start> <end>` | Display memory as screen code text                     |
| `io`               | Display all I/O register ranges                        |
| `io <addr>`        | Display details for the chip at the given base address |
| `bt`               | Print JSR call chain (backtrace, most recent first)    |
| `chis`             | Print recently executed instructions (CPU history)     |
| `stopwatch`        | Print CPU cycle counter                                |
| `stopwatch reset`  | Reset cycle counter to zero                            |

#### Execution Control

| Command     | Action                                                         |
|-------------|----------------------------------------------------------------|
| `g`         | Resume from current PC (continue)                              |
| `g <addr>`  | Jump to address and run from there                             |
| `z`         | Step into (execute one instruction)                            |
| `z 5`       | Step into 5 instructions                                       |
| `n`         | Step over (treats JSR as one step)                             |
| `n 5`       | Step over 5 instructions                                       |
| `ret`       | Step out (run until next RTS or RTI)                           |
| `un <addr>` | Run until address reached (temporary breakpoint, auto-deleted) |
| `warp on`   | Enable warp mode (max speed)                                   |
| `warp off`  | Disable warp mode                                              |

#### Checkpoints (Breakpoints, Watchpoints, Tracepoints)

| Command                | Action                                             |
|------------------------|----------------------------------------------------|
| `break <addr>`         | Set execution breakpoint at address                |
| `break <start> <end>`  | Set breakpoint for an address range                |
| `watch load <addr>`    | Break on memory read from address                  |
| `watch store <addr>`   | Break on memory write to address                   |
| `trace <addr>`         | Trace: print PC at address, do not stop            |
| `trace exec <addr>`    | Trace only execution at address                    |
| `cond <num> if A==$00` | Add condition to checkpoint `<num>`                |
| `ignore <num> <count>` | Ignore checkpoint `<num>` for `<count>` crossings  |
| `command <num> "r"`    | Run monitor command when checkpoint `<num>` is hit |
| `del <num>`            | Delete checkpoint by number                        |
| `dis <num>`            | Disable checkpoint by number                       |
| `en <num>`             | Enable checkpoint by number                        |
| `bk`                   | List all checkpoints                               |

#### Memory Manipulation

| Command            | Action                                                   |
|--------------------|----------------------------------------------------------|
| `> <addr> <bytes>` | Write bytes to address (e.g. `> $0410 ea ea ea`)         |
| `f <range> <data>` | Fill memory range with data (repeated if shorter)        |
| `t <range> <dest>` | Move (transfer) memory from range to destination         |
| `c <range> <dest>` | Compare memory range with destination, show mismatches   |
| `h <range> <data>` | Hunt (search) for byte pattern in range; `xx` = wildcard |

#### Monitor State

| Command           | Action                                                  |
|-------------------|---------------------------------------------------------|
| `x`               | Exit monitor, resume emulation                          |
| `q`               | Quit VICE / disconnect remote monitor                   |
| `radix H`         | Set default radix to hex (D=decimal, O=octal, B=binary) |
| `keybuf <string>` | Stuff string into keyboard buffer                       |

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

Set the PC to the program entry point and resume:

```
r PC=$040E
g
```

Search screen RAM for the letter sequence "HI" (screen codes `$08` `$09`):

```
h $8000 $83E7 08 09
```

### Conditional Breakpoints

A breakpoint can include a condition so it only fires when the condition is true. This is useful for catching a specific iteration of a loop or a specific register value:

```
break $0420 if A==$00
break $0420 if X==Y
break $8000 if @io:$E84C==$0C
```

The condition expression supports registers (A, X, Y, PC, SP, FL), comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`), arithmetic (`+`, `-`, `*`, `/`), and logical operators (`&&`, `||`). Memory locations can be tested with `@<bank>:$<addr>`.

### Tracepoints

A tracepoint prints the current PC and register state without stopping execution. Use it to log execution flow without interrupting the program:

```
trace $0420
```

Output appears as:

```
#1 (Trace  exec 0420)  .C:0420  A9 20       LDA #$20        - A:00 X:00 Y:00 SP:FF ..-..IZC
```

Delete a tracepoint with `del <num>`, same as a breakpoint.

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
xpet -model 3032 -remotemonitor -remotemonitoraddress 127.0.0.1:6502 -autostart program.prg
```

Connect with `nc` or `telnet` on Linux:

```bash
nc 127.0.0.1 6502
```

On Windows, `nc` is not available. Use PowerShell's TCP client or the Python socket script (see "Headless Debugging" above for both).

**PowerShell argument-parsing note**: when launching xpet with `-remotemonitor` from PowerShell, use `cmd /c` as a wrapper -- PowerShell may mangle arguments that contain colons or start with `-`. From `cmd`, Git Bash (`sh`), or WSL `bash`, the command works directly.

This lets an external script drive the monitor without focus on the emulator window. See "Headless Debugging" above for the full recipe.

### Binary Monitor

`-binarymonitor` opens a TCP port that accepts VICE's binary protocol instead of text commands. Suitable for tooling that speaks the protocol (vice-bridge, vice-emu-protocol clients). For shell/grep work, prefer `-remotemonitor`.
