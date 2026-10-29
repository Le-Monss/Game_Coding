# Validation results

Verified in the cloud on 2026-10-29. All game source, tools and build files are
in this repository. Temporary tool installations, ROMs and logs are under the
ignored `work/` directory; no emulator ROMs are included in the game download.

## Build and binary checks

- ACME 0.96.4, built from `https://github.com/meonwax/acme`, commit
  `99fae48b1fc44a3fc25b84d51857d36c1d6967e1`.
- Assembly completed without game-source errors or warnings.
- PRG: 622 bytes, two-byte load address `$0801`, valid BASIC line
  `10 SYS2064`, machine-code entry at `$0810` (2064).
- D64: standard 35 tracks / 174,848 bytes. Its directory contains one closed
  PRG named `CATCH THE STAR`, occupying three blocks; 661 blocks free.
- `tools/verify_build.py` validates the BASIC bytes, disk directory, sector
  chain and allocation bitmap, and compares the disk's program to the PRG.
- VICE 3.9 `c1541` independently recognized the disk, listed it and extracted
  its program. The extracted file was byte-for-byte identical to the PRG.

## Executed machine-code tests

All **seven** py65 1.2.0 tests passed:

1. Initialization, readable screen codes, colors and screen-clear boundaries.
2. Active-low up/down/left/right, idle, unused fire and diagonal input.
3. Movement clamped at all four playfield corners.
4. Collection, relocation, displayed score and erasing the previous player cell.
5. Decimal carries through 9/99/999 and wrapping 9999 to 0000.
6. All 255 nonzero PRNG states produce valid positions and avoid the player;
   generated locations are also tested as player positions to exercise retries.
7. Full frame-loop movement and collection with simulated PAL/NTSC raster timing.

Command used:

```sh
PYTHONPATH=work/python make test ACME=work/tools/acme/src/acme
```

## VICE emulator checks

VICE **3.9 x64sc** passed automated headless checks for:

- PRG autostart through BASIC, PAL and NTSC.
- D64 autostart through BASIC, with an emulated 1541 drive, PAL.
- Correct initial heading and player coordinates.
- Simulated joystick-port-2 right input read through the emulated CIA.
- A star placed next to the player is collected after five frames.
- Score storage and the visible score bytes change to `0001`.
- The new star is inside the playfield and separate from the player.
- Releasing the joystick stops movement.

The checks use the real assembled instructions and VICE's joyport simulation
device. The test sets a star's coordinates to make collection deterministic.
The reusable script is `tools/check_vice.py`. Cloud command example:

```sh
python3 tools/check_vice.py \
  --vice work/tools/vice-trixie/usr/bin/x64sc \
  --directory work/tools/vice-trixie/usr/share/vice
```

Add `--ntsc` for NTSC or `--image build/catch-the-star.d64` for the disk.

## Limits

These are automated checks, not a manual play session. No physical joystick,
gamepad, real C64, RetroPie frontend or the user's Ubuntu VirtualBox VM was
available for testing. Visual output was checked through screen/color memory;
no interactive window was inspected. Confirm the controller is assigned to
**C64 joystick port 2** when playing locally.

## SHA-256 checksums

```text
d9e449b369563dbad51a44bfdb60c76c95f4d3aa36c33854af3629f2748ecb2a  build/catch-the-star.prg
4a85dda9f7269dded9a7a268edc90cee1284e8073042477c99237d35f70f8a66  build/catch-the-star.d64
```
