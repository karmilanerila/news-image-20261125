#!/usr/bin/env python3
"""News image for Wednesday 25 November 2026.

Draws a newspaper front page that sums up the day's world news in one
1024x1024 PNG, using only the Python standard library. The picture is
built pixel by pixel: a masthead, a big Strait of Hormuz lead story with
two tankers and a mine explosion, three side panels (AI sell-off, space,
Cartagena) and a news ticker at the bottom. The program is fully
deterministic: it writes the same bytes on every run.
"""

import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- font
# Hand-drawn 5x7 bitmap font. Each glyph is 7 rows of 5 characters,
# '#' is ink, '.' is empty. Uppercase letters, digits and punctuation.

FONT = {
    "A": ("..#..", ".#.#.", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
}


def text_width(text, scale):
    """Pixel width of text drawn at the given scale."""
    return len(text) * 6 * scale


# ------------------------------------------------------------ PNG writer

def _chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(
        ">I", zlib.crc32(body) & 0xFFFFFFFF)


def encode_png(width, height, pixels):
    """Encode RGB pixels (bytes, row-major) as a deterministic PNG."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: none
        raw += pixels[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------- canvas

class Canvas:
    """A plain RGB pixel buffer with simple shape and text drawing."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(background * (width * height))

    def put(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, color)

    def border(self, x, y, w, h, color, thick=3):
        self.rect(x, y, w, thick, color)
        self.rect(x, y + h - thick, w, thick, color)
        self.rect(x, y, thick, h, color)
        self.rect(x + w - thick, y, thick, h, color)

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.put(xx, yy, color)

    def ring(self, cx, cy, r, color, thick=2):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - thick) ** 2 <= d <= r * r:
                    self.put(xx, yy, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            for ty in range(thick):
                for tx in range(thick):
                    self.put(x + tx, y + ty, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        # Filled triangle by scanline interpolation.
        pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        for y in range(ay, cy + 1):
            if y < by:
                t1 = (y - ay) / max(1, by - ay)
                xa = ax + (bx - ax) * t1
            else:
                xa = bx
            t2 = (y - ay) / max(1, cy - ay)
            xb = ax + (cx - ax) * t2
            lo, hi = sorted((int(xa), int(xb)))
            for x in range(lo, hi + 1):
                self.put(x, y, color)

    def glyph(self, x, y, ch, color, scale):
        rows = FONT.get(ch)
        if rows is None:
            rows = FONT[" "]
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "#":
                    self.rect(x + rx * scale, y + ry * scale,
                              scale, scale, color)

    def text(self, x, y, string, color, scale, align="left"):
        if align == "center":
            x -= text_width(string, scale) // 2
        elif align == "right":
            x -= text_width(string, scale)
        for ch in string.upper():
            self.glyph(x, y, ch, color, scale)
            x += 6 * scale


# ---------------------------------------------------------------- colors
PAPER = (246, 241, 229)
INK = (22, 22, 22)
NAVY = (18, 33, 61)
GOLD = (238, 214, 150)
RED = (178, 34, 34)
BRICK = (122, 42, 32)
SEA = (13, 62, 94)
SKY = (196, 219, 231)
WAVE = (88, 150, 182)
ORANGE = (240, 118, 18)
YELLOW = (250, 198, 40)
SMOKE = (48, 48, 48)
WHITE = (255, 255, 255)
GREEN = (34, 139, 34)
GREY = (120, 120, 120)
LIGHTGREY = (214, 214, 208)


def draw_masthead(cv):
    cv.rect(0, 0, WIDTH, 96, NAVY)
    cv.text(WIDTH // 2, 14, "Wednesday 25 November 2026", GOLD, 3,
            align="center")
    cv.text(WIDTH // 2, 46, "The World in One Image", WHITE, 5,
            align="center")
    cv.rect(0, 96, WIDTH, 5, RED)


def draw_headline(cv):
    cv.text(WIDTH // 2, 116, "Mines in the Strait", INK, 8, align="center")
    cv.text(WIDTH // 2, 180, "of Hormuz", RED, 8, align="center")
    cv.text(WIDTH // 2, 248,
            "Two tankers hit - oil and shipping on edge",
            INK, 3, align="center")


def draw_tanker(cv, x, y, w, hull, funnel):
    """A simple oil tanker: hull, deckhouse, funnel, portholes."""
    h = 52
    cv.rect(x, y, w, h, hull)
    cv.rect(x, y + h - 8, w, 8, (0, 0, 0))
    cv.rect(x + 14, y - 30, 110, 30, WHITE)
    cv.border(x + 14, y - 30, 110, 30, INK, 2)
    for i in range(4):
        cv.rect(x + 26 + i * 26, y - 22, 14, 12, NAVY)
    cv.rect(x + w - 130, y - 46, 34, 46, funnel)
    cv.rect(x + w - 130, y - 46, 34, 8, INK)
    cv.rect(x + 150, y - 12, 60, 12, LIGHTGREY)


def draw_explosion(cv, cx, cy):
    # Radiating spikes, then layered fireball.
    for k in range(12):
        import math
        ang = k * math.pi / 6
        x1 = cx + int(58 * math.cos(ang))
        y1 = cy + int(58 * math.sin(ang))
        cv.line(cx, cy, x1, y1, ORANGE, 5)
    cv.circle(cx, cy, 52, ORANGE)
    cv.circle(cx, cy, 36, YELLOW)
    cv.circle(cx, cy, 20, RED)
    cv.circle(cx - 10, cy - 8, 8, WHITE)


def draw_smoke(cv, cx, cy):
    cv.circle(cx - 26, cy + 6, 24, SMOKE)
    cv.circle(cx + 24, cy - 2, 26, SMOKE)
    cv.circle(cx, cy - 22, 18, SMOKE)
    cv.circle(cx - 8, cy - 34, 10, GREY)


def draw_sea_scene(cv):
    x0, x1 = 24, 1000
    # Sky and sea.
    cv.rect(x0, 290, x1 - x0, 80, SKY)
    cv.circle(120, 320, 22, WHITE)
    cv.circle(150, 314, 28, WHITE)
    cv.circle(880, 318, 24, WHITE)
    cv.circle(912, 312, 30, WHITE)
    cv.rect(x0, 370, x1 - x0, 195, SEA)
    # Wave lines.
    for wy in (392, 420, 448, 540):
        for wx in range(x0 + 10, x1 - 60, 90):
            cv.line(wx, wy, wx + 52, wy, WAVE, 3)
    # Mine with spikes floating near the first tanker.
    cv.circle(300, 528, 10, INK)
    for k in range(8):
        import math
        ang = k * math.pi / 4
        cv.line(300, 528,
                300 + int(18 * math.cos(ang)),
                528 + int(18 * math.sin(ang)), INK, 3)
    # The two tankers.
    draw_tanker(cv, 70, 452, 360, BRICK, (200, 62, 40))
    draw_tanker(cv, 620, 466, 340, (32, 32, 38), (250, 198, 40))
    # Mine blasts: a big one between the tankers, a small one by the second.
    draw_explosion(cv, 515, 348)
    draw_smoke(cv, 515, 316)
    cv.circle(700, 440, 20, ORANGE)
    cv.circle(700, 440, 12, YELLOW)
    cv.circle(700, 440, 6, RED)


def draw_panel(cv, x, title):
    cv.rect(x, 584, 320, 284, WHITE)
    cv.border(x, 584, 320, 284, NAVY, 3)
    cv.text(x + 160, 598, title, NAVY, 4, align="center")
    cv.rect(x + 20, 636, 280, 3, RED)


def draw_panel_ai(cv, x):
    draw_panel(cv, x, "AI Sell-Off")
    # Falling chart line.
    pts = [(x + 40, 664), (x + 100, 656), (x + 160, 686),
           (x + 220, 716), (x + 280, 748)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, RED, 4)
    cv.line(x + 30, 650, x + 30, 756, INK, 3)
    cv.line(x + 30, 756, x + 300, 756, INK, 3)
    # Green chip with pins.
    cv.rect(x + 236, 648, 52, 30, GREEN)
    cv.border(x + 236, 648, 52, 30, INK, 2)
    for py in (656, 668, 680):
        cv.line(x + 228, py, x + 236, py, INK, 2)
        cv.line(x + 288, py, x + 296, py, INK, 2)
    cv.text(x + 160, 772, "NVIDIA -7%", RED, 2, align="center")
    cv.text(x + 160, 796, "NIKKEI -2.76%", INK, 2, align="center")
    cv.text(x + 160, 820, "AI boom doubts", INK, 2, align="center")


def draw_panel_space(cv, x):
    draw_panel(cv, x, "Space")
    cx = x + 160
    # Stars.
    for sx, sy in ((x + 60, 660), (x + 90, 700), (x + 250, 668),
                   (x + 268, 716), (x + 70, 740)):
        cv.line(sx - 6, sy, sx + 6, sy, NAVY, 2)
        cv.line(sx, sy - 6, sx, sy + 6, NAVY, 2)
    # Rocket: nose, body, fins, flame.
    cv.triangle(cx - 18, 676, cx + 18, 676, cx, 646, RED)
    cv.rect(cx - 18, 676, 36, 62, WHITE)
    cv.border(cx - 18, 676, 36, 62, INK, 2)
    cv.circle(cx, 700, 7, SKY)
    cv.ring(cx, 700, 7, INK, 2)
    cv.triangle(cx - 18, 738, cx - 38, 756, cx - 18, 720, RED)
    cv.triangle(cx + 18, 738, cx + 38, 756, cx + 18, 720, RED)
    cv.triangle(cx - 10, 738, cx + 10, 738, cx, 764, ORANGE)
    cv.text(x + 160, 772, "Pakistan's first", INK, 2, align="center")
    cv.text(x + 160, 796, "astronaut reaches", INK, 2, align="center")
    cv.text(x + 160, 820, "China's space station", INK, 2, align="center")


def draw_panel_cartagena(cv, x):
    draw_panel(cv, x, "Cartagena")
    # Supermarket storefront with striped awning.
    cv.rect(x + 40, 684, 240, 72, LIGHTGREY)
    cv.border(x + 40, 684, 240, 72, INK, 3)
    for i in range(8):
        col = RED if i % 2 == 0 else WHITE
        cv.rect(x + 40 + i * 30, 660, 30, 24, col)
    cv.rect(x + 40, 660, 240, 3, INK)
    cv.rect(x + 140, 700, 40, 56, NAVY)
    cv.rect(x + 60, 700, 56, 30, SKY)
    cv.border(x + 60, 700, 56, 30, INK, 2)
    cv.rect(x + 204, 700, 56, 30, SKY)
    cv.border(x + 204, 700, 56, 30, INK, 2)
    cv.text(x + 160, 772, "All hostages freed", INK, 2, align="center")
    cv.text(x + 160, 796, "after supermarket siege", INK, 2, align="center")
    cv.text(x + 160, 820, "in Cartagena", INK, 2, align="center")


def draw_ticker(cv):
    cv.rect(0, 880, WIDTH, 4, NAVY)
    cv.text(WIDTH // 2, 898,
            "Australia-Solomon Islands treaty - Ukraine hits",
            INK, 2, align="center")
    cv.text(WIDTH // 2, 922,
            "Russian warship off Libya - COP31 collapses",
            INK, 2, align="center")
    cv.text(WIDTH // 2, 946,
            "Huawei convicted - Bangladesh wage +36%",
            INK, 2, align="center")
    cv.rect(0, 984, WIDTH, 6, NAVY)
    cv.rect(0, 990, WIDTH, 34, NAVY)
    cv.text(WIDTH // 2, 1000, "Make.fun - 25 November 2026", GOLD, 2,
            align="center")


# ------------------------------------------------------------------ main

def build_image():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.border(0, 0, WIDTH, HEIGHT, NAVY, 6)
    draw_masthead(cv)
    draw_headline(cv)
    draw_sea_scene(cv)
    cv.rect(0, 572, WIDTH, 4, NAVY)
    draw_panel_ai(cv, 24)
    draw_panel_space(cv, 352)
    draw_panel_cartagena(cv, 680)
    draw_ticker(cv)
    return encode_png(WIDTH, HEIGHT, cv.pixels)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = build_image()
    with open(path, "wb") as fh:
        fh.write(data)
    os.chmod(path, 0o644)


if __name__ == "__main__":
    main()
