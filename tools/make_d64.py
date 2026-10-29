#!/usr/bin/env python3
"""Create a standard 35-track D64 with one closed PRG; Python stdlib only."""

import argparse
from pathlib import Path

SECTORS = [0] + [21] * 17 + [19] * 7 + [18] * 6 + [17] * 5


def sector_offset(track, sector):
    if not 1 <= track <= 35 or not 0 <= sector < SECTORS[track]:
        raise ValueError(f"Invalid track/sector: {track}/{sector}")
    return (sum(SECTORS[1:track]) + sector) * 256


def make_disk(prg):
    if not prg.startswith(b"\x01\x08"):
        raise ValueError("Expected a C64 PRG with load address $0801")
    image = bytearray(sum(SECTORS) * 256)
    blocks = (len(prg) + 253) // 254
    available = [(t, s) for t in range(1, 36) if t != 18
                 for s in range(SECTORS[t])]
    if blocks > len(available):
        raise ValueError("PRG does not fit on a 35-track disk")
    chain = available[:blocks]
    used = set(chain) | {(18, 0), (18, 1)}

    # BAM = Block Availability Map: one free count + three bitmap bytes per track.
    bam = bytearray(256)
    bam[:4] = bytes([18, 1, 0x41, 0])
    for track in range(1, 36):
        free = [s for s in range(SECTORS[track]) if (track, s) not in used]
        base = 4 + (track - 1) * 4
        bam[base] = len(free)
        for sector in free:
            bam[base + 1 + sector // 8] |= 1 << (sector % 8)
    bam[0x90:0xA0] = b"CATCH THE STAR".ljust(16, b"\xa0")
    bam[0xA0:0xAB] = b"\xa0\xa0CS\xa02A\xa0\xa0\xa0\xa0"
    offset = sector_offset(18, 0)
    image[offset:offset + 256] = bam

    directory = bytearray(256)
    directory[:2] = bytes([0, 255])  # last directory sector
    directory[2] = 0x82            # closed PRG
    directory[3:5] = bytes(chain[0])
    directory[5:21] = b"CATCH THE STAR".ljust(16, b"\xa0")
    directory[30:32] = blocks.to_bytes(2, "little")
    offset = sector_offset(18, 1)
    image[offset:offset + 256] = directory

    for index, (track, sector) in enumerate(chain):
        chunk = prg[index * 254:(index + 1) * 254]
        block = bytearray(256)
        # Last sector: byte 1 counts data bytes PLUS one, as required by DOS.
        block[:2] = bytes(chain[index + 1]) if index + 1 < blocks else bytes([0, len(chunk) + 1])
        block[2:2 + len(chunk)] = chunk
        offset = sector_offset(track, sector)
        image[offset:offset + 256] = block
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prg", type=Path)
    parser.add_argument("d64", type=Path)
    args = parser.parse_args()
    args.d64.write_bytes(make_disk(args.prg.read_bytes()))
    print(f"Created {args.d64} (174848 bytes)")


if __name__ == "__main__":
    main()
