#!/usr/bin/env python3
"""Headless VICE 3.6+ check of BASIC boot, simulated port-2 input and scoring.

Run from the repository root. Requires x64sc and its normal C64 ROMs.
"""

import argparse
import os
import re
import socket
import struct
import subprocess
import time
from pathlib import Path


class Monitor:
    """Minimal client for VICE's documented binary monitor protocol (API 2)."""

    def __init__(self, connection):
        self.connection = connection
        self.request_id = 0
        self.stopped = []

    def exact(self, length):
        result = bytearray()
        while len(result) < length:
            part = self.connection.recv(length - len(result))
            if not part:
                raise EOFError("VICE closed the connection; see work/vice-check.log")
            result.extend(part)
        return result

    def receive(self):
        marker, version, length, kind, error, request_id = struct.unpack(
            "<BBIBBI", self.exact(12))
        if marker != 2 or version != 2:
            raise RuntimeError("Unsupported VICE monitor protocol")
        body = self.exact(length)
        if kind == 0x62:
            self.stopped.append(int.from_bytes(body[:2], "little"))
        return kind, error, request_id, body

    def command(self, kind, body=b""):
        self.request_id += 1
        self.connection.sendall(struct.pack(
            "<BBIIB", 2, 2, len(body), self.request_id, kind) + body)
        while True:
            _, error, request_id, response = self.receive()
            if request_id == self.request_id:
                if error:
                    raise RuntimeError(f"VICE command ${kind:02x} failed: ${error:02x}")
                return response

    def until(self, address):
        self.command(0x12, struct.pack("<HHBBBB", address, address, 1, 1, 4, 1))
        # Notifications may arrive before the resume acknowledgement.
        self.stopped.clear()
        self.command(0xAA)
        while address not in self.stopped:
            self.receive()

    def read(self, address, length=1):
        return self.command(1, struct.pack(
            "<BHHBH", 0, address, address + length - 1, 0, 0))[2:]

    def write(self, address, values):
        self.command(2, struct.pack(
            "<BHHBH", 0, address, address + len(values) - 1, 0, 0) + bytes(values))

    def joystick(self, value):
        # Monitor joyport indices are zero based: 1 = physical C64 port 2.
        self.command(0xA2, struct.pack("<HH", 1, value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vice", default="x64sc", help="VICE executable")
    parser.add_argument("--directory", help="Optional VICE system data directory")
    parser.add_argument("--image", type=Path, default=Path("build/catch-the-star.prg"))
    parser.add_argument("--ntsc", action="store_true")
    args = parser.parse_args()
    labels = {name: int(value, 16) for name, value in re.findall(
        r"^\s*(\w+)\s*=\s*\$([0-9a-fA-F]+)",
        Path("build/catch-the-star.labels").read_text(), re.MULTILINE)}
    env = os.environ.copy()
    for name, subdir in [("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"),
                         ("XDG_STATE_HOME", "state")]:
        path = Path("work/xdg", subdir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        env[name] = str(path)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    disk = args.image.suffix.lower() == ".d64"
    command = [args.vice, "-console", "+sound", "-warp", "-drive8type", "1541" if disk else "0",
               "-autostartprgmode", "1", "-autostart-delay", "3",
               "-autostart", str(args.image), "-binarymonitor",
               "-binarymonitoraddress", f"ip4://127.0.0.1:{port}",
               "-controlport2device", "37", "-limitcycles", "60000000" if disk else "20000000",
               "-monlogname", str(Path("work/vice-monitor.log").resolve())]
    if args.directory:
        command += ["-directory", str(Path(args.directory).resolve())]
    if args.ntsc:
        command += ["-ntsc"]
    with Path("work/vice-check.log").open("w") as log:
        process = subprocess.Popen(command, env=env, stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    connection = socket.create_connection(("127.0.0.1", port), timeout=0.2)
                    break
                except OSError:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("VICE monitor unavailable; see work/vice-check.log")
                    time.sleep(0.05)
            with connection:
                connection.settimeout(15)
                monitor = Monitor(connection)
                monitor.until(labels["main_loop"])
                assert monitor.read(0x0400, 5) == bytes([3, 1, 20, 3, 8]), "Bad heading"
                assert monitor.read(labels["player_x"], 2) == bytes([10, 12]), "Bad start"
                # Put a target next to the player so the check is deterministic.
                monitor.write(labels["star_x"], [11, 12])
                monitor.joystick(0xF7)
                for _ in range(5):
                    monitor.until(labels["main_loop"])
                assert monitor.read(labels["player_x"], 2) == bytes([11, 12]), "No movement"
                assert monitor.read(labels["score_digits"], 4) == bytes([0, 0, 0, 1]), "No catch"
                assert monitor.read(labels["SCORE_SCREEN"], 4) == b"0001", "Bad score display"
                star = tuple(monitor.read(labels["star_x"], 2))
                assert 0 <= star[0] <= 39 and 3 <= star[1] <= 23 and star != (11, 12)
                monitor.joystick(0xFF)
                for _ in range(5):
                    monitor.until(labels["main_loop"])
                assert monitor.read(labels["player_x"], 2) == bytes([11, 12]), "Release failed"
                monitor.command(0xBB)
                process.wait(timeout=10)
            print(f"PASS: {args.image}, {'NTSC' if args.ntsc else 'PAL'}: BASIC boot, port-2 input, "
                  "catch, score, star relocation and release")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            process.stdin.close()


if __name__ == "__main__":
    main()
