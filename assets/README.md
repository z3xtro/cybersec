# Buddy — Sprite Assets

Buddy is an **animated, wandering** desktop pet (Comnyang-style). Each animation
is a *clip*, identified by a filename stem. The files checked in are crude,
stdlib-generated **placeholders** (see `scripts/generate_placeholders.py`) —
replace them with real artwork at the same paths and Buddy picks them up
automatically (no code change).

## Clips

| Clip stem | When it shows | Pose | Reference photo |
|-----------|---------------|------|-----------------|
| `idle_alert` | default / sitting | Cat sitting attentively, watching | `IMG20241116172646.jpg` |
| `thinking_coil` | waiting on the API | Cat tightly coiled up | `7FCEDB47-51C7-461E-881E-30D6D7415095.jpg` |
| `dramatic_alert` | errors / dramatic actions | Wide-open jaw yawn | `IMG20250610192200.jpg` |
| `walk` | strolling across the screen | Side-profile walk cycle (faces right; auto-flipped when walking left) | — |
| `sleep` | napping while idle | Curled up asleep | — |

`walk` and `sleep` are optional — if absent, Buddy falls back to `idle_alert` /
`thinking_coil`.

## Two layouts per clip (either works)

1. **Animated — a folder of numbered frames** (preferred):
   ```
   assets/idle_alert/0.png  assets/idle_alert/1.png  ...
   assets/walk/0.png ... assets/walk/3.png
   ```
   Frames cycle at `Anim.FPS` (default 4; set `BUDDY_FPS`).
2. **Still — a single file:** `assets/idle_alert.png`. Used if no frame folder
   exists. Buddy still walks/sleeps by moving the window, just without a frame cycle.

A folder takes priority over the single file of the same stem.

## Requirements for the artwork

- **Format:** PNG with a real alpha channel (transparent background), so only the
  cat shows and there's no square window box.
- **Size:** any square-ish size; Buddy scales the longest edge down to
  `Theme.SPRITE_SIZE` (110 px by default — set `BUDDY_SIZE` or edit config).
- **Framing:** keep the cat centered with a little padding; keep frames aligned
  so it doesn't jitter.
- **`walk`:** draw it **facing right**. With Pillow installed, Buddy auto-flips
  it for leftward walking.

## Animate your own stills automatically

Have a single still per pose but no frame-by-frame animation? Drop three stills
in and let the animator derive breathing/idle frames for you (needs Pillow):

```
assets/idle_alert.png       <- alert cat watching the screen
assets/dramatic_alert.png   <- wide-open yawn
assets/sleep.png            <- curled-up sleeping cat
```

```bash
pip install Pillow
python scripts/animate_from_stills.py
```

This writes `assets/idle_alert/`, `assets/dramatic_alert/`, `assets/sleep/`,
`assets/thinking_coil/` (from the curled cat) and `assets/walk/` (reuses the
idle cat) — each a folder of transparent frames with a gentle breathing bob.
Tune with `--frames`, `--size`, `--no-walk`.

## Regenerating the built-in placeholders

```bash
python scripts/generate_placeholders.py
```

## Missing files?

If any PNG is absent or fails to decode, Buddy falls back to a coloured circle
and a text glyph for that state, so the app always runs.
