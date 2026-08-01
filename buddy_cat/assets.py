"""Animated sprite loading with graceful fallbacks.

A *clip* is one animation, named by a filename stem (see ``config.CLIPS``). Each
clip resolves in priority order:

  1. ``assets/<stem>/`` — a folder of numbered PNG frames (``0.png``, ``1.png``…)
     → an animated clip.
  2. ``assets/<stem>.png`` — a single still → a one-frame clip.
  3. a semantic ``fallback_clip`` (ambient clips only).
  4. a drawn glyph so the app always runs.

Pillow is used when available for clean transparency, scaling, and generating
horizontally-flipped frames (so the cat can face the way it walks). Without it
we fall back to Tk's native PNG loader (no flipping).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Optional

from . import config

try:  # Pillow: best transparency + enables flipping.
    from PIL import Image, ImageTk  # type: ignore

    _HAVE_PIL = True
except ImportError:  # pragma: no cover - depends on the host environment
    _HAVE_PIL = False


class Clip:
    """An ordered list of frames plus its (optional) left-facing variant."""

    def __init__(self, frames: list[tk.PhotoImage],
                 flipped: Optional[list[tk.PhotoImage]] = None) -> None:
        self.frames = frames
        self.flipped = flipped or frames  # fall back to unflipped if no Pillow

    def __bool__(self) -> bool:
        return bool(self.frames)

    def frame(self, index: int, facing_left: bool = False) -> tk.PhotoImage:
        seq = self.flipped if facing_left else self.frames
        return seq[index % len(seq)]

    def __len__(self) -> int:
        return len(self.frames)


class SpriteSet:
    """Loads and caches every clip. Holds references so Tk keeps the images."""

    def __init__(self, size: int = config.Theme.SPRITE_SIZE) -> None:
        self._size = size
        self._clips: dict[str, Clip] = {}
        self._missing: set[str] = set()
        for stem in config.CLIPS:
            clip = self._load_clip(stem)
            if clip:
                self._clips[stem] = clip

    # -- loading ---------------------------------------------------------- #

    def _frame_paths(self, stem: str) -> list[Path]:
        folder = config.ASSETS_DIR / stem
        if folder.is_dir():
            frames = sorted(
                folder.glob("*.png"),
                key=lambda p: (len(p.stem), p.stem),  # 0,1,2..10 not 0,1,10,2
            )
            if frames:
                return frames
        single = config.ASSETS_DIR / f"{stem}.png"
        if single.exists():
            return [single]
        return []

    def _load_clip(self, stem: str) -> Optional[Clip]:
        paths = self._frame_paths(stem)
        if not paths:
            self._missing.add(stem)
            return None
        frames: list[tk.PhotoImage] = []
        flipped: list[tk.PhotoImage] = []
        try:
            for path in paths:
                if _HAVE_PIL:
                    img = Image.open(path).convert("RGBA")
                    img.thumbnail((self._size, self._size), Image.LANCZOS)
                    frames.append(ImageTk.PhotoImage(img))
                    flipped.append(
                        ImageTk.PhotoImage(img.transpose(Image.FLIP_LEFT_RIGHT))
                    )
                else:
                    frames.append(tk.PhotoImage(file=str(path)))
        except Exception:  # noqa: BLE001 - any decode failure -> fallback
            self._missing.add(stem)
            return None
        return Clip(frames, flipped if _HAVE_PIL else None)

    # -- lookup ----------------------------------------------------------- #

    def clip(self, stem: str) -> Optional[Clip]:
        """Resolve a clip, following ambient ``fallback_clip`` if needed."""
        if stem in self._clips:
            return self._clips[stem]
        fallback = config.CLIPS.get(stem, {}).get("fallback_clip")
        if fallback:
            return self._clips.get(fallback)
        return None

    def has(self, stem: str) -> bool:
        return self.clip(stem) is not None

    @property
    def any_art(self) -> bool:
        return bool(self._clips)

    @property
    def missing(self) -> set[str]:
        return set(self._missing)
