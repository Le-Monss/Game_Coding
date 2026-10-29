# Catch the Star — your first Commodore 64 assembly game

Move the white **@** toward the yellow **\*** using **joystick port 2**.
Each star gives you one point and appears somewhere else. The score goes from
0000 to 9999, then wraps to 0000. There are no enemies or time limit.

The game is real 6502/6510 assembly built with **ACME**. It uses the C64's
40 × 25 text screen. Python is only used for build helpers and tests;
Python is **not** required on the C64 or in RetroPie.

## Files

| File | Purpose |
| --- | --- |
| `src/catch_the_star.asm` | Complete assembly game with beginner comments |
| `build/catch-the-star.prg` | Ready-to-run program with BASIC `10 SYS2064` launcher |
| `build/catch-the-star.d64` | Standard 35-track disk containing `CATCH THE STAR` |
| `build/catch-the-star.labels` | Label addresses for VICE's monitor |
| `build/catch-the-star.report` | Listing of source, addresses and machine bytes |
| `Makefile` | Build, disk creation, verification and test commands |
| `tools/make_d64.py` | Creates the disk using Python's standard library |
| `tools/verify_build.py` | Checks the launcher and disk structure/content |
| `tools/check_vice.py` | Optional automated headless VICE check |
| `tests/test_game.py` | Tests the assembled instructions using py65 |
| `VALIDATION.md` | Results and limits of cloud testing |
| `.gitignore` | Keeps local tools, caches and scratch files out of Git |

Prebuilt PRG and D64 files are included; building is optional if you just want
to play. The 622-byte PRG occupies three disk blocks. The D64 is 174,848 bytes.

## Get the game into your Ubuntu VirtualBox VM

**From a downloaded project ZIP:** download it to your host computer, then use
a VirtualBox shared folder to copy it into Ubuntu. In the VM settings, add the
download folder under **Shared Folders** and enable auto-mount. With Guest
Additions installed, Ubuntu commonly mounts it at `/media/sf_NAME`. Copy the
ZIP into a normal folder in Ubuntu and extract it there. If the shared folder
gives a permission error, add your Ubuntu user to `vboxsf` and log in again:

```sh
sudo usermod -aG vboxsf "$USER"
```

Alternatively, download and extract the ZIP using the browser **inside Ubuntu**.
You can also copy just `build/catch-the-star.prg` or `.d64`; either plays by itself.

**From GitHub after these changes have been committed and pushed:**

```sh
git clone https://github.com/Le-Monss/Game_Coding.git
cd Game_Coding
```

If you already cloned it, enter that checkout and run `git pull`. If the game
was saved on a separate branch, select that branch first. Local cloud edits do
not appear on GitHub until committed and pushed.

## Play in VICE

Open a terminal in the extracted/cloned project directory:

```sh
x64sc -joydev2 1 -autostart build/catch-the-star.prg
```

`-joydev2 1` selects the numeric keypad for **C64 port 2**. Normally keypad
**8 / 2 / 4 / 6** move up / down / left / right. Use the actual numeric keypad,
not the number row. Fire is unused. Diagonal movement also works.

If your VICE executable is `x64`, substitute `x64` for `x64sc`. You can also
use VICE's **Autostart image** menu to open the PRG or D64.

For a laptop without a numeric keypad, use VICE's joystick settings to define
a keyboard keyset and assign it to **port 2**. For a gamepad, select that device
for port 2; VirtualBox may also need to pass the USB controller into Ubuntu.
The C64 keyboard cursor keys alone do not control this game.

The disk can autostart too:

```sh
x64sc -joydev2 1 -autostart build/catch-the-star.d64
```

Or attach the disk to drive 8 and enter these lines at the C64 BASIC prompt:

```basic
LOAD"CATCH THE STAR",8,1
RUN
```

The included BASIC line calls machine code with `SYS2064`; you don't need to
type it yourself. The game runs continuously and disables the usual keyboard
IRQ scanning, so RUN/STOP will not exit it. Use VICE's reset/autostart controls
to restart, or close the emulator to stop. There is no sound or saved score.

If VICE reports missing BASIC/KERNAL/character ROMs, fix that VICE installation
first. The project does not bundle C64 ROMs; your existing working VICE setup
should already have them.

## Play in RetroPie

From the project directory **inside Ubuntu**:

```sh
mkdir -p ~/RetroPie/roms/c64
cp build/catch-the-star.d64 ~/RetroPie/roms/c64/
```

Restart EmulationStation or refresh its game list, then launch **Catch the Star**
from the Commodore 64 system. Select an installed VICE emulator/core if asked.
Configure the emulated joystick for **C64 port 2** in that emulator's settings
or core options. Menu names vary between standalone VICE and `lr-vice`.
EmulationStation's controller setup alone may not select the right C64 port.
If your RetroPie ROM directory is customized, use that location instead.

## Build on Ubuntu

Install ACME, Make and Python 3:

```sh
sudo apt update
sudo apt install acme make python3
make
```

`make` assembles the PRG, creates the D64, then verifies both. No disk utility,
VICE installation, or third-party Python module is required for this build.

To assemble just the program without Make:

```sh
mkdir -p build
acme -f cbm -o build/catch-the-star.prg src/catch_the_star.asm
```

`-f cbm` writes the two-byte load address expected by a C64 PRG. Renaming a raw
binary to `.prg` would not add that header. To create a disk from this PRG:

```sh
python3 tools/make_d64.py build/catch-the-star.prg build/catch-the-star.d64
python3 tools/verify_build.py
```

In this cloud checkout ACME was built locally, so the equivalent command is:

```sh
make ACME=work/tools/acme/src/acme
```

The ignored `work/` folder holds local tools, downloaded emulator files and
scratch logs. These are not needed to play or to build with an installed ACME.
`make clean` removes only the four generated game build files; `make` recreates them.

## Understand the assembly through Python

The 6510 in a C64 runs the ordinary 6502 instructions used here. Think of its
**A, X and Y registers** as three small variables. Each holds only 0–255. Memory
is a large numbered collection of bytes. A label names an address rather than
creating a Python object.

| Assembly | Simple Python comparison |
| --- | --- |
| `lda #10` | `a = 10` — `#` means the number itself |
| `lda player_x` | `a = memory[address_of_player_x]` |
| `sta player_x` | `memory[address_of_player_x] = a` |
| `ldx #0`, `ldy #3` | `x = 0`, `y = 3` |
| `inc player_x` / `dec player_x` | Increase / decrease the stored coordinate |
| `inx` / `dex` | Increase / decrease X; byte values wrap at the ends |
| `cmp #39`, `beq label` | Compare A with 39; jump if equal |
| `bne label` | Jump if the previous result/comparison was not zero/equal |
| `and #8` | `a = a & 8` — keep only bit 3 |
| `ora #3` / `eor #$1d` | Bitwise `a \| 3` / `a ^ 0x1d` |
| `clc`, `adc #48` | Clear carry, then add 48; otherwise carry adds an extra 1 |
| `jsr draw_player`, `rts` | Call a function and return |
| `jmp main_loop` | Jump unconditionally; useful for `while True` |
| `pha`, `pla` | Temporarily save/restore A on the CPU's stack |

`$0400` means hexadecimal, like `0x0400` in Python. `!byte`, `!word`, `!scr`
and `!for` are **assembler directives**: ACME processes them while building;
the CPU does not execute them as instructions. `!word` emits two bytes, low
byte first. `!scr` emits screen codes. With ACME's default encoding, lowercase
letters in these source strings become uppercase letters in the selected C64 font.

### Follow one trip through the game

1. `start` sets the text screen, clears 1,000 cells, draws headings and borders,
   and initializes the score, player and star.
2. `main_loop` waits for raster line 250. The VIC-II draws the screen one line
   at a time; watching its raster register gives us one tick per video frame.
   Every fifth frame, the game calls `move_player` (10 moves/sec PAL, 12 NTSC).
3. `move_player` reads `$dc00`, the joystick port-2 register. Up/down/left/right
   are bits 0/1/2/3. **Pressed means 0**: conceptually,
   `if (joystick & 8) == 0: move_right()`. Coordinates stop at columns 0–39
   and rows 3–23 so the player cannot overwrite the heading/borders.
4. Matching player/star coordinates means a catch. `increment_score` updates
   a four-element decimal digit array, carrying to the left just as you do
   when adding on paper. `show_score` converts digits to visible characters.
5. `new_star` advances a small deterministic pseudorandom generator, rejecting
   out-of-range coordinates and the player's location. The starting seed uses
   timer/raster values. It is a simple game generator, not uniform randomness
   over every screen cell or a security feature.
6. `plot` writes a character to `$0400 + row*40 + column`. Precomputed row
   tables avoid doing multiplication on this CPU. The matching color byte
   lives at `$d800 + row*40 + column`. Then execution loops forever.

`PTR` uses two zero-page bytes, `$fb/$fc`, to hold an address. `sta (PTR),y`
means “follow that address, add Y, then store A there,” similar to writing
`memory[row_address + column] = a` in Python.

Try changing `MOVE_FRAMES` to 8 for slower movement, or change the player's
color in `draw_player`. Rebuild and reopen the new PRG after each edit.

## Optional automated checks

The standard build verification uses only Python's standard library:

```sh
make check
```

To execute the assembled instructions in a 6502 CPU emulator, install py65 in
a local virtual environment:

```sh
sudo apt install python3-venv
python3 -m venv work/test-env
work/test-env/bin/pip install py65==1.2.0
make test PYTHON=work/test-env/bin/python
```

For the cloud's already-downloaded py65:

```sh
PYTHONPATH=work/python make test ACME=work/tools/acme/src/acme
```

To run a headless check with your installed VICE 3.6 or later:

```sh
python3 tools/check_vice.py
python3 tools/check_vice.py --ntsc
python3 tools/check_vice.py --image build/catch-the-star.d64
```

This launches a separate VICE process, boots through BASIC, places a test star
next to the player, supplies simulated port-2 input, and checks movement,
collection, score display, relocation and input release. It uses a temporary
monitor bound to localhost. Logs and VICE state directories stay in `work/`.
It does not test your real gamepad, VirtualBox input passthrough or RetroPie setup.
The D64 check also needs VICE's 1541 drive ROM installed.
