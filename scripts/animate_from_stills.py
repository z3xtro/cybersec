#!/usr/bin/env python3
"""Turn Buddy's still cat art into animated frame clips — with per-pose motion.

You provide the stills (your real pixel-art cats); this derives animation frames
from each. Beyond a plain breathing bob, each pose gets character-appropriate
motion, synthesized from a single still via localized image warps:

  * idle_alert    — ear twitch (top band wobble) + gentle body sway + bob
  * dramatic_alert— jaw pulse (mid band stretches open) + bob
  * sleep         — slow, shallow sway + bob (calm napping)
  * thinking_coil — slow sway (from the curled cat)
  * walk          — a leg cycle (bottom band scissors) + brisk bob

These are procedural approximations from ONE still — great for bringing static
art to life without hand-drawing frames. For a true frame-by-frame animation,
just drop numbered frames straight into the clip folders instead.

Requires Pillow:  pip install Pillow

Save your stills first (overwriting the placeholders):
    assets/idle_alert.png       <- alert cat watching the screen
    assets/dramatic_alert.png   <- wide-open yawn
    assets/sleep.png            <- curled-up sleeping cat
    assets/walk.png             <- (optional) a SIDE-PROFILE cat, facing right

Then run:
    python scripts/animate_from_stills.py
    # side-profile walk from a dedicated still:
    python scripts/animate_from_stills.py --walk-src assets/walk.png
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def load_pillow():
    try:
        from PIL import Image  # type: ignore
        return Image
    except ImportError:
        sys.exit("Pillow is required: pip install Pillow")


# --------------------------------------------------------------------------- #
# Localized warps (each takes an RGBA image, returns a same-size RGBA image)
# --------------------------------------------------------------------------- #

def _shift_band(Image, im, y0f: float, y1f: float, dx: int):
    """Shift the horizontal band [y0f, y1f) sideways by dx px (ear twitch)."""
    if dx == 0:
        return im
    w, h = im.size
    y0, y1 = int(h * y0f), int(h * y1f)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(im.crop((0, 0, w, y0)), (0, 0))          # above
    out.alpha_composite(im.crop((0, y0, w, y1)), (dx, y0))       # shifted band
    out.alpha_composite(im.crop((0, y1, w, h)), (0, y1))         # below
    return out


def _vstretch_band(Image, im, y0f: float, y1f: float, extra: int):
    """Stretch band [y0f, y1f) vertically by `extra` px, pushing lower content
    down (constant canvas size — the jaw opens without moving the head)."""
    if extra <= 0:
        return im
    w, h = im.size
    y0, y1 = int(h * y0f), int(h * y1f)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(im.crop((0, 0, w, y0)), (0, 0))          # head (fixed)
    band = im.crop((0, y0, w, y1)).resize((w, (y1 - y0) + extra), Image.LANCZOS)
    out.alpha_composite(band, (0, y0))                           # stretched jaw
    out.alpha_composite(im.crop((0, y1, w, h)), (0, y1 + extra))  # pushed down
    return out


def _sway(Image, im, deg: float):
    """Rotate slightly about the bottom-center (whole-body sway)."""
    if abs(deg) < 1e-3:
        return im
    w, h = im.size
    return im.rotate(deg, resample=Image.BICUBIC, expand=False, center=(w / 2, h))


def _legs(Image, im, dx: int, y0f: float = 0.6):
    """Scissor the bottom band's two halves in opposite directions (a step)."""
    if dx == 0:
        return im
    w, h = im.size
    y0 = int(h * y0f)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(im.crop((0, 0, w, y0)), (0, 0))          # body (fixed)
    band = im.crop((0, y0, w, h))
    half = w // 2
    left = band.crop((0, 0, half, h - y0))
    right = band.crop((half, 0, w, h - y0))
    out.alpha_composite(left, (dx, y0))                          # front leg fwd
    out.alpha_composite(right, (half - dx, y0))                  # back leg back
    return out


# --------------------------------------------------------------------------- #
# Per-clip motion styles. Each effect is (name, fn(Image, im, phase)).
# phase runs a smooth cycle in [-1, 1] across the frames.
# --------------------------------------------------------------------------- #

def style_idle(Image, im, phase):
    im = _shift_band(Image, im, 0.0, 0.33, round(2 * phase))     # ear twitch
    im = _sway(Image, im, 1.0 * phase)
    return im


def style_dramatic(Image, im, phase):
    open_amt = max(0, round(6 * (phase * 0.5 + 0.5)))            # 0..6 px jaw
    return _vstretch_band(Image, im, 0.35, 0.58, open_amt)


def style_sleep(Image, im, phase):
    return _sway(Image, im, 0.6 * phase)


def style_think(Image, im, phase):
    return _sway(Image, im, 0.8 * phase)


def style_walk(Image, im, phase):
    return _legs(Image, im, round(3 * phase))


# clip -> (source still, style fn, bob px, speed multiplier)
PLAN = {
    "idle_alert":     ("idle_alert.png",     style_idle,     3, 1.0),
    "thinking_coil":  ("sleep.png",          style_think,    2, 0.8),
    "dramatic_alert": ("dramatic_alert.png", style_dramatic, 2, 1.2),
    "sleep":          ("sleep.png",          style_sleep,    2, 0.6),
}


# --------------------------------------------------------------------------- #

def autocrop(im):
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def fit(Image, im, size: int, bob: int):
    im = autocrop(im.convert("RGBA"))
    pad = bob + 6  # headroom for bob + sway/warp overshoot
    target = size - 2 * pad
    w, h = im.size
    scale = target / max(w, h)
    return im.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                     Image.LANCZOS)


def make_frames(Image, still, *, style, frames: int, size: int, bob: int,
                speed: float) -> list:
    base = fit(Image, still, size, bob)
    out = []
    for f in range(frames):
        phase = math.sin(2 * math.pi * speed * f / frames)
        warped = style(Image, base, phase)
        dy = round(bob * phase)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        cx = (size - warped.size[0]) // 2
        cy = (size - warped.size[1]) // 2 + dy
        canvas.alpha_composite(warped, (cx, cy))
        out.append(canvas)
    return out


def write_clip(frames: list, stem: str) -> None:
    folder = ASSETS / stem
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    for i, frame in enumerate(frames):
        frame.save(folder / f"{i}.png")
    frames[0].save(ASSETS / f"{stem}.png")
    print(f"  {stem}/  ({len(frames)} frames)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Animate Buddy's stills into clips")
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--size", type=int, default=0, help="0 = use BUDDY_SIZE/110")
    ap.add_argument("--no-walk", action="store_true")
    ap.add_argument("--walk-src", type=Path, default=None,
                    help="a SIDE-PROFILE still (facing right) for the walk clip; "
                         "defaults to reusing assets/idle_alert.png")
    args = ap.parse_args()

    Image = load_pillow()

    size = args.size
    if size <= 0:
        import os
        size = int(os.environ.get("BUDDY_SIZE", "110"))

    made = 0
    for stem, (src_name, style, bob, speed) in PLAN.items():
        src = ASSETS / src_name
        if not src.exists():
            print(f"! skip {stem}: missing source {src}", file=sys.stderr)
            continue
        with Image.open(src) as im:
            frames = make_frames(Image, im, style=style, frames=args.frames,
                                 size=size, bob=bob, speed=speed)
        write_clip(frames, stem)
        made += 1

    if not args.no_walk:
        walk_src = args.walk_src or (ASSETS / "idle_alert.png")
        if walk_src.exists():
            with Image.open(walk_src) as im:
                frames = make_frames(Image, im, style=style_walk,
                                     frames=max(4, args.frames), size=size,
                                     bob=4, speed=1.5)
            write_clip(frames, "walk")
            made += 1
            note = "" if args.walk_src else "  (reused idle cat; pass --walk-src for a side pose)"
            print(f"    walk{note}")

    if made == 0:
        sys.exit("no clips made — save your stills into assets/ first (see --help)")
    print(f"\n✓ animated {made} clips from your stills. Launch: python -m buddy_cat")


if __name__ == "__main__":
    main()
