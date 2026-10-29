#!/usr/bin/env python3
"""Validate the BASIC launcher, D64 directory, file chain and allocation map."""

from pathlib import Path
from make_d64 import SECTORS, sector_offset


def verify():
    prg = Path("build/catch-the-star.prg").read_bytes()
    assert prg[:2] == b"\x01\x08", "Wrong PRG load address"
    assert prg[2:14] == b"\x0b\x08\x0a\x00\x9e2064\x00\x00\x00", "Invalid BASIC SYS launcher"
    assert prg[17:19] == b"\x78\xd8", "Expected SEI / CLD at $0810"
    assert len(prg) > 19 and 0x0801 + len(prg) - 2 < 0xA000

    image = Path("build/catch-the-star.d64").read_bytes()
    assert len(image) == 174848, "Wrong 35-track disk size"

    def sector(track, number):
        offset = sector_offset(track, number)
        return image[offset:offset + 256]

    bam = sector(18, 0)
    assert bam[:4] == bytes([18, 1, 0x41, 0])
    directory = sector(*bam[:2])
    assert directory[:3] == bytes([0, 255, 0x82])
    assert directory[5:21].rstrip(b"\xa0") == b"CATCH THE STAR"
    track, number = directory[3:5]
    seen = set()
    recovered = bytearray()
    while track:
        assert (track, number) not in seen, "File chain loops"
        seen.add((track, number))
        block = sector(track, number)
        if block[0]:
            recovered.extend(block[2:])
        else:
            assert 1 <= block[1] <= 255
            recovered.extend(block[2:block[1] + 1])
        track, number = block[:2]
    assert recovered == prg, "Disk file differs from assembled PRG"
    assert len(seen) == int.from_bytes(directory[30:32], "little")
    allocated = seen | {(18, 0), (18, 1)}
    for track in range(1, 36):
        base = 4 + (track - 1) * 4
        free_count = 0
        for number in range(24):
            free = bool(bam[base + 1 + number // 8] & (1 << (number % 8)))
            expected = number < SECTORS[track] and (track, number) not in allocated
            assert free == expected, f"Bad BAM bit at {track}/{number}"
            free_count += free
        assert bam[base] == free_count
    print(f"Verified PRG ({len(prg)} bytes, SYS 2064) and D64 ({len(seen)} file blocks; exact PRG match)")


if __name__ == "__main__":
    verify()
