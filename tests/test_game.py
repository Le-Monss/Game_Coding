"""Run the assembled instructions in py65, with simulated C64 I/O registers.

This tests real machine code, but does not emulate the VIC/CIA chips or VICE.
Run from the repository root after `make`: python3 -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

from py65.devices.mpu6502 import MPU


class C64Memory(list):
    def __init__(self, lines=312):
        super().__init__([0] * 65536)
        self.cpu = None
        self.lines = lines
        self.cycles_per_line = 63 if lines == 312 else 65
        self.joystick = 0xFF

    def __getitem__(self, address):
        if address == 0xDC00:
            return self.joystick
        if address in (0xD011, 0xD012) and self.cpu is not None:
            raster = (self.cpu.processorCycles // self.cycles_per_line) % self.lines
            if address == 0xD012:
                return raster & 255
            return (super().__getitem__(address) & 0x7F) | (0x80 if raster >= 256 else 0)
        return super().__getitem__(address)


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels = {name: int(value, 16) for name, value in re.findall(
            r"^\s*(\w+)\s*=\s*\$([0-9a-fA-F]+)",
            Path("build/catch-the-star.labels").read_text(), re.MULTILINE)}
        cls.prg = Path("build/catch-the-star.prg").read_bytes()

    def setUp(self):
        self.mem = C64Memory()
        load = int.from_bytes(self.prg[:2], "little")
        self.mem[load:load + len(self.prg) - 2] = self.prg[2:]
        self.cpu = MPU(memory=self.mem, pc=self.labels["start"])
        self.mem.cpu = self.cpu
        self.mem[0x07E8:0x0800] = [0xA5] * 24
        self.mem[0xDBE8:0xDC00] = [0xA5] * 24
        self.run_until(self.labels["main_loop"])

    def run_until(self, address, limit=200000):
        for _ in range(limit):
            if self.cpu.pc == address:
                return
            self.cpu.step()
        self.fail(f"Instruction limit reached at ${self.cpu.pc:04x}")

    def call(self, label):
        sentinel = 0xFF00
        self.cpu.stPushWord(sentinel - 1)
        self.cpu.pc = self.labels[label]
        self.run_until(sentinel)

    def get(self, label):
        return self.mem[self.labels[label]]

    def put(self, label, value):
        self.mem[self.labels[label]] = value

    def position(self):
        return self.get("player_x"), self.get("player_y")

    def digits(self):
        start = self.labels["score_digits"]
        return self.mem[start:start + 4]

    def test_startup_and_screen_codes(self):
        self.assertEqual(self.position(), (10, 12))
        self.assertEqual(self.mem[0x0400:0x0405], [3, 1, 20, 3, 8])  # CATCH
        self.assertEqual(self.mem[0x0400 + 80:0x0400 + 120], [45] * 40)
        self.assertEqual(self.mem[0x0400 + 960:0x0400 + 1000], [45] * 40)
        self.assertEqual(self.mem[0x07E8:0x0800], [0xA5] * 24)
        self.assertEqual(self.mem[0xDBE8:0xDC00], [0xA5] * 24)
        self.assertEqual(self.mem[0xDC02], 0)
        self.assertEqual(self.mem[0xD018], 0x14)
        self.assertEqual(self.mem[0x0400 + 12 * 40 + 10], 0)
        star = 40 * self.get("star_y") + self.get("star_x")
        self.assertEqual(self.mem[0x0400 + star], 42)
        self.assertEqual(self.mem[0xD800 + star], 7)
        self.assertEqual(self.digits(), [0, 0, 0, 0])

    def test_active_low_directions_idle_fire_and_diagonal(self):
        for joystick, expected in [(0xFF, (10, 12)), (0xEF, (10, 12)),
                                   (0xFE, (10, 11)), (0xFD, (10, 12)),
                                   (0xFB, (9, 12)), (0xF7, (10, 12)),
                                   (0xF6, (11, 11))]:
            self.mem.joystick = joystick
            self.call("move_player")
            self.assertEqual(self.position(), expected)

    def test_all_playfield_edges(self):
        for x, y, joystick in [(0, 3, 0xFA), (39, 3, 0xF6),
                                (0, 23, 0xF9), (39, 23, 0xF5)]:
            self.put("player_x", x)
            self.put("player_y", y)
            self.mem.joystick = joystick
            for _ in range(50):
                self.call("move_player")
            self.assertEqual(self.position(), (x, y))

    def test_collection_relocation_and_old_cell_erasure(self):
        self.put("star_x", 11)
        self.put("star_y", 12)
        self.call("draw_star")
        self.mem.joystick = 0xF7
        self.call("move_player")
        self.assertEqual(self.position(), (11, 12))
        self.assertEqual(self.digits(), [0, 0, 0, 1])
        score = self.labels["SCORE_SCREEN"]
        self.assertEqual(self.mem[score:score + 4], list(b"0001"))
        self.assertNotEqual((self.get("star_x"), self.get("star_y")), (11, 12))
        self.assertEqual(self.mem[0x0400 + 12 * 40 + 10], 32)
        self.assertEqual(self.mem[0x0400 + 12 * 40 + 11], 0)
        self.assertEqual(self.mem[0xD800 + 12 * 40 + 11], 1)

    def test_decimal_carries_and_wrap(self):
        start = self.labels["score_digits"]
        for before, after in [([0, 0, 0, 9], [0, 0, 1, 0]),
                              ([0, 0, 9, 9], [0, 1, 0, 0]),
                              ([0, 9, 9, 9], [1, 0, 0, 0]),
                              ([9, 9, 9, 9], [0, 0, 0, 0])]:
            self.mem[start:start + 4] = before
            self.call("increment_score")
            self.assertEqual(self.digits(), after)

    def test_every_random_seed_and_no_player_overlap(self):
        positions = set()
        for seed in range(1, 256):
            self.put("random_state", seed)
            for _ in range(4):
                self.call("new_star")
                x, y = self.get("star_x"), self.get("star_y")
                self.assertTrue(0 <= x <= 39 and 3 <= y <= 23)
                self.assertNotEqual((x, y), self.position())
                positions.add((x, y))
        self.assertGreater(len(positions), 30)
        # Make every generated location the player's location, then retry it.
        for x, y in positions:
            self.put("player_x", x)
            self.put("player_y", y)
            for seed in range(1, 256):
                self.put("random_state", seed)
                self.call("new_star")
                self.assertNotEqual((self.get("star_x"), self.get("star_y")), (x, y))

    def test_full_frame_loop_pal_and_ntsc(self):
        for lines in (312, 263):
            self.mem.lines = lines
            self.mem.cycles_per_line = 63 if lines == 312 else 65
            self.put("player_x", 10)
            self.put("player_y", 12)
            self.put("star_x", 11)
            self.put("star_y", 12)
            self.put("frames_left", 5)
            self.mem.joystick = 0xF7
            self.cpu.pc = self.labels["main_loop"]
            for frame in range(1, 6):
                self.cpu.step()  # enter JSR wait_frame before waiting for main_loop
                self.run_until(self.labels["main_loop"])
                self.assertEqual(self.get("player_x"), 10 if frame < 5 else 11)
            self.assertGreater(self.digits()[-1], 0)


if __name__ == "__main__":
    unittest.main()
