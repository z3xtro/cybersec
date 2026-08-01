#!/usr/bin/env python3
"""Generate transparent, ANIMATED placeholder sprites for Buddy.

Stdlib only (``zlib`` + ``struct``) — no Pillow required. Emits, per clip, a
folder of numbered frames (``assets/<clip>/0.png`` …) plus a single
``assets/<clip>.png`` still as a fallback. The frames are intentionally crude —
simple pixel-cat poses that bob/breathe/walk — meant to be replaced with real
art in the same layout (see ``assets/README.md``).

Clips produced:
  idle_alert    (2 frames, gentle bob)      thinking_coil (2 frames, breathing)
  dramatic_alert(2 frames, yawn pulse)      walk          (4 frames, leg cycle)
  sleep         (2 frames, drifting Zzz)

Run:  python scripts/generate_placeholders.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

SIZE = 256
ASSETS = Path(__file__).resolve().parent.parent / "assets"
RGBA = tuple[int, int, int, int]


class Canvas:
    def __init__(self, size: int) -> None:
        self.size = size
        self.px = bytearray([0, 0, 0, 0]) * (size * size)

    def _set(self, x: int, y: int, c: RGBA) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            i = (y * self.size + x) * 4
            self.px[i:i + 4] = bytes(c)

    def disk(self, cx: float, cy: float, r: float, c: RGBA) -> None:
        r2 = r * r
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    self._set(x, y, c)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, c: RGBA) -> None:
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    self._set(x, y, c)

    def rect(self, x0, y0, x1, y1, c: RGBA) -> None:
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                self._set(x, y, c)

    def triangle(self, p1, p2, p3, c: RGBA) -> None:
        xs, ys = [p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            for x in range(int(min(xs)), int(max(xs)) + 1):
                if _in_tri((x, y), p1, p2, p3):
                    self._set(x, y, c)

    def to_png(self, path: Path) -> None:
        raw = bytearray()
        stride = self.size * 4
        for y in range(self.size):
            raw.append(0)
            raw.extend(self.px[y * stride:(y + 1) * stride])
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        ihdr = struct.pack(">IIBBBBB", self.size, self.size, 8, 6, 0, 0, 0)
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
        )


def _sign(a, b, c):
    return (a[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (a[1] - c[1])


def _in_tri(p, a, b, c) -> bool:
    d1, d2, d3 = _sign(p, a, b), _sign(p, b, c), _sign(p, c, a)
    return not (((d1 < 0) or (d2 < 0) or (d3 < 0)) and ((d1 > 0) or (d2 > 0) or (d3 > 0)))


def _c(rgb, a=255) -> RGBA:
    return (rgb[0], rgb[1], rgb[2], a)


GREEN, AMBER, RED, BLUE = (57, 255, 20), (255, 176, 0), (255, 49, 49), (95, 168, 211)


def idle_alert(frame: int) -> Canvas:
    """Sitting cat; gentle vertical bob + tail twitch."""
    c = Canvas(SIZE)
    body = _c(GREEN)
    m = SIZE / 2
    dy = -2 if frame % 2 else 2
    c.ellipse(m, 175 + dy, 55, 66, body)
    c.triangle((m - 55, 118 + dy), (m - 30, 62 + dy), (m - 8, 115 + dy), body)
    c.triangle((m + 55, 118 + dy), (m + 30, 62 + dy), (m + 8, 115 + dy), body)
    c.disk(m, 108 + dy, 46, body)
    tail_x = 62 if frame % 2 else 68
    c.ellipse(m + tail_x, 190, 13, 40, body)
    c.disk(m - 16, 104 + dy, 6, (0, 0, 0, 255))
    c.disk(m + 16, 104 + dy, 6, (0, 0, 0, 255))
    return c


def thinking_coil(frame: int) -> Canvas:
    """Coiled cat; slow breathing (radius pulse)."""
    c = Canvas(SIZE)
    body = _c(AMBER)
    m = SIZE / 2
    r = 78 + (2 if frame % 2 else -2)
    c.disk(m, m, r, body)
    c.disk(m, m, 40, (0, 0, 0, 0))
    for t in range(0, 200):
        ang = t / 200 * math.pi * 1.4
        c.disk(m + 70 * math.cos(ang), m + 70 * math.sin(ang), 8, body)
    c.disk(m - 40, m - 34, 26, body)
    c.disk(m - 46, m - 40, 4, (0, 0, 0, 255))
    return c


def dramatic_alert(frame: int) -> Canvas:
    """Yawning cat; mouth pulses wider."""
    c = Canvas(SIZE)
    body = _c(RED)
    m = SIZE / 2
    c.ellipse(m, 180, 58, 62, body)
    c.disk(m, 110, 62, body)
    c.triangle((m - 62, 118), (m - 34, 48), (m - 6, 112), body)
    c.triangle((m + 62, 118), (m + 34, 48), (m + 6, 112), body)
    mouth = 34 if frame % 2 else 26
    c.ellipse(m, 132, 22, mouth, (10, 10, 10, 255))
    c.ellipse(m, 140, 12, mouth - 12, (200, 40, 60, 255))
    c.disk(m - 22, 96, 9, (255, 255, 255, 255))
    c.disk(m + 22, 96, 9, (255, 255, 255, 255))
    c.disk(m - 22, 96, 4, (0, 0, 0, 255))
    c.disk(m + 22, 96, 4, (0, 0, 0, 255))
    return c


def walk(frame: int) -> Canvas:
    """Side-profile cat; 4-frame leg cycle + slight bob (faces right)."""
    c = Canvas(SIZE)
    body = _c(GREEN)
    m = SIZE / 2
    dy = -2 if frame in (1, 3) else 0
    c.ellipse(m - 6, m + 6 + dy, 70, 40, body)          # body (horizontal)
    c.disk(m + 66, m - 6 + dy, 34, body)                 # head to the right
    c.triangle((m + 46, m - 34 + dy), (m + 60, m - 66 + dy),
               (m + 74, m - 34 + dy), body)              # ear
    c.ellipse(m - 78, m - 4 + dy, 12, 30, body)          # tail up-left
    c.disk(m + 80, m - 8 + dy, 4, (0, 0, 0, 255))        # eye
    # legs: alternate the pairs each frame for a trot
    phase = frame % 4
    front = 10 if phase in (0, 1) else 22
    back = 22 if phase in (0, 1) else 10
    c.rect(m + 30, m + 40 + dy, m + 42, m + 40 + dy + front, body)   # front leg
    c.rect(m - 40, m + 40 + dy, m - 28, m + 40 + dy + back, body)    # back leg
    return c


def sleep(frame: int) -> Canvas:
    """Curled napping cat + drifting Zzz."""
    c = Canvas(SIZE)
    body = _c(BLUE)
    m = SIZE / 2
    c.ellipse(m, m + 24, 84, 54, body)                   # curled loaf
    for t in range(0, 200):
        ang = t / 200 * math.pi * 1.2
        c.disk(m + 60 * math.cos(ang), m + 24 + 30 * math.sin(ang), 7, body)
    c.disk(m - 54, m + 10, 22, body)                     # tucked head
    # closed eye
    c.rect(m - 64, m + 6, m - 48, m + 9, (0, 0, 0, 255))
    # drifting "z"s rise with the frame
    zy = 70 - frame * 10
    for i, s in enumerate((10, 7, 5)):
        c.rect(m + 40 + i * 16, zy + i * 8, m + 40 + i * 16 + s, zy + i * 8 + 3,
               (255, 255, 255, 255))
        c.rect(m + 40 + i * 16, zy + i * 8 + s, m + 40 + i * 16 + s, zy + i * 8 + s + 3,
               (255, 255, 255, 255))
    return c


CLIPS = {
    "idle_alert": (idle_alert, 2),
    "thinking_coil": (thinking_coil, 2),
    "dramatic_alert": (dramatic_alert, 2),
    "walk": (walk, 4),
    "sleep": (sleep, 2),
}


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, (builder, n) in CLIPS.items():
        folder = ASSETS / name
        folder.mkdir(exist_ok=True)
        for f in range(n):
            builder(f).to_png(folder / f"{f}.png")
        # single still fallback = frame 0
        builder(0).to_png(ASSETS / f"{name}.png")
        print(f"wrote {name}/ ({n} frames) + {name}.png")


if __name__ == "__main__":
    main()
