"""Tkinter frontend: an animated, wandering desktop pet + the console overlay.

Two timers drive the "alive" feel, in the spirit of Comnyang-style desktop pets:

  * an **animation** ticker cycles the current clip's frames at ``Anim.FPS``;
  * a **behaviour** ticker runs a tiny idle state machine (sit → stroll → nap)
    that walks the cat along the bottom of the screen when it's not busy and
    the console is closed.

Semantic states (idle / thinking / dramatic) always win over ambient behaviour:
while a query is running the cat holds still and shows the thinking clip.
"""

from __future__ import annotations

import random
import sys
import tkinter as tk
from typing import Optional

from . import config
from .assets import SpriteSet
from .backend import BuddyBackend, Delta, Done, Failure
from .config import Anim, Behavior, Mode, State, Theme


class BuddyPet:
    """The frameless, always-on-top, animated, draggable cat window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.backend = BuddyBackend()
        self.sprites = SpriteSet()
        self.state = State.IDLE_ALERT
        self.behavior = Behavior.IDLE
        self.mode = config.DEFAULT_MODE
        self.console: Optional[ConsoleWindow] = None

        # animation / motion state
        self._frame = 0
        self._facing_left = False
        self._behavior_ticks = 0
        self._dragging = False
        self.x = 0
        self.y = 0

        self._configure_window()
        self._build_sprite()
        self._bind_drag()

        self._tick_anim()      # start frame cycling
        self._tick_behavior()  # start the idle life loop
        self._poll_backend()   # start the queue-drain loop

    # ------------------------------------------------------------------ #
    # Window chrome + transparency
    # ------------------------------------------------------------------ #

    def _configure_window(self) -> None:
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg=Theme.TRANSPARENT_KEY)

        try:
            if sys.platform.startswith("win"):
                self.root.wm_attributes("-transparentcolor", Theme.TRANSPARENT_KEY)
            elif sys.platform == "darwin":
                self.root.wm_attributes("-transparent", True)
                self.root.configure(bg="systemTransparent")
        except tk.TclError:
            pass

        self.root.update_idletasks()
        self._sw = self.root.winfo_screenwidth()
        self._sh = self.root.winfo_screenheight()
        self.x = self._sw - Theme.SPRITE_SIZE - 60
        self.y = self._sh - Theme.SPRITE_SIZE - 120
        self.root.geometry(f"+{self.x}+{self.y}")

    def _build_sprite(self) -> None:
        self.canvas = tk.Canvas(
            self.root,
            width=Theme.SPRITE_SIZE,
            height=Theme.SPRITE_SIZE + 26,
            highlightthickness=0,
            bg=Theme.TRANSPARENT_KEY,
        )
        self.canvas.pack()
        self._img_item = self.canvas.create_image(
            Theme.SPRITE_SIZE // 2, Theme.SPRITE_SIZE // 2
        )
        self._render_current()

        self.ask_btn = tk.Button(
            self.root,
            text="[ ASK BUDDY ]",
            command=self.toggle_console,
            font=Theme.BUTTON_FONT,
            fg=Theme.FG,
            bg=Theme.BG,
            activeforeground=Theme.ACCENT,
            activebackground=Theme.PANEL_BG,
            relief="ridge",
            bd=1,
            cursor="hand2",
        )
        self.canvas.create_window(
            Theme.SPRITE_SIZE // 2, Theme.SPRITE_SIZE + 13, window=self.ask_btn
        )
        self.canvas.bind("<Button-3>", lambda _e: self.quit())

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _current_stem(self) -> str:
        """Which clip to display right now (semantic state wins over ambient)."""
        if self.state != State.IDLE_ALERT:
            return config.STATE_CLIP[self.state]
        return config.BEHAVIOR_CLIP[self.behavior]

    def _render_current(self) -> None:
        stem = self._current_stem()
        clip = self.sprites.clip(stem)
        self.canvas.delete("fallback")
        if clip:
            self.canvas.itemconfigure(
                self._img_item,
                image=clip.frame(self._frame, facing_left=self._facing_left),
                state="normal",
            )
            return
        # Drawn-glyph fallback for a clip with no art.
        self.canvas.itemconfigure(self._img_item, state="hidden")
        meta = config.CLIPS.get(stem, {})
        cx = cy = Theme.SPRITE_SIZE // 2
        r = Theme.SPRITE_SIZE // 2 - 8
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, fill=Theme.PANEL_BG,
            outline=meta.get("fallback_color", Theme.FG), width=2, tags="fallback",
        )
        self.canvas.create_text(
            cx, cy, text=meta.get("fallback_glyph", "=^.^="),
            fill=meta.get("fallback_color", Theme.FG),
            font=("Courier New", 18, "bold"), tags="fallback",
        )

    def _tick_anim(self) -> None:
        self._frame += 1
        self._render_current()
        self.root.after(max(1, 1000 // max(1, Anim.FPS)), self._tick_anim)

    def set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            if state != State.IDLE_ALERT:
                self.behavior = Behavior.IDLE  # hold still while busy
            self._frame = 0
            self._render_current()

    # ------------------------------------------------------------------ #
    # Ambient behaviour: sit -> stroll -> nap, along the bottom of the screen
    # ------------------------------------------------------------------ #

    def _wander_allowed(self) -> bool:
        return (
            Anim.WANDER
            and self.state == State.IDLE_ALERT
            and not self._dragging
            and not (self.console and self.console.alive)
            and not self.backend.busy
        )

    def _tick_behavior(self) -> None:
        if self._wander_allowed():
            self._behavior_ticks -= 1
            if self.behavior == Behavior.WALK:
                self._walk_step()
            if self._behavior_ticks <= 0:
                self._pick_behavior()
        self.root.after(Anim.STEP_MS, self._tick_behavior)

    def _pick_behavior(self) -> None:
        if self.behavior in (Behavior.WALK, Behavior.SLEEP):
            # After moving/napping, settle into a sit.
            self.behavior = Behavior.IDLE
            self._behavior_ticks = random.randint(Anim.REST_MIN, Anim.REST_MAX)
        else:  # was idle -> nap or stroll
            if random.random() < Anim.SLEEP_CHANCE and self.sprites.has("sleep"):
                self.behavior = Behavior.SLEEP
                self._behavior_ticks = random.randint(Anim.SLEEP_MIN, Anim.SLEEP_MAX)
            else:
                self.behavior = Behavior.WALK
                self._facing_left = random.random() < 0.5
                self._behavior_ticks = random.randint(Anim.WALK_MIN, Anim.WALK_MAX)
        self._frame = 0
        self._render_current()

    def _walk_step(self) -> None:
        dx = -Anim.WALK_SPEED if self._facing_left else Anim.WALK_SPEED
        nx = self.x + dx
        right_limit = self._sw - Theme.SPRITE_SIZE
        if nx <= 0:
            nx = 0
            self._facing_left = False
        elif nx >= right_limit:
            nx = right_limit
            self._facing_left = True
        self.x = nx
        self.root.geometry(f"+{self.x}+{self.y}")

    # ------------------------------------------------------------------ #
    # Dragging (left-click + drag anywhere on the pet)
    # ------------------------------------------------------------------ #

    def _bind_drag(self) -> None:
        self._drag_dx = 0
        self._drag_dy = 0
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)

    def _start_drag(self, event: tk.Event) -> None:
        self._dragging = True
        self.behavior = Behavior.IDLE
        self._drag_dx = event.x
        self._drag_dy = event.y

    def _on_drag(self, event: tk.Event) -> None:
        self.x = self.root.winfo_pointerx() - self._drag_dx
        self.y = self.root.winfo_pointery() - self._drag_dy
        self.root.geometry(f"+{self.x}+{self.y}")

    def _end_drag(self, _event: tk.Event) -> None:
        self._dragging = False
        self._behavior_ticks = random.randint(Anim.REST_MIN, Anim.REST_MAX)

    # ------------------------------------------------------------------ #
    # Console overlay
    # ------------------------------------------------------------------ #

    def toggle_console(self) -> None:
        if self.console is not None and self.console.alive:
            self.console.close()
            self.console = None
        else:
            self.console = ConsoleWindow(self)

    def submit_query(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt or self.backend.busy:
            return
        self.set_state(State.THINKING_COIL)
        if self.console:
            self.console.begin_response()
        self.backend.ask(prompt, config.MODE_PROMPTS[self.mode])

    def toggle_mode(self) -> None:
        self.mode = Mode.SOLVER if self.mode == Mode.COACH else Mode.COACH
        if self.console:
            self.console.refresh_status()

    # ------------------------------------------------------------------ #
    # Backend queue drain (runs on the Tk main thread)
    # ------------------------------------------------------------------ #

    def _poll_backend(self) -> None:
        try:
            while True:
                event = self.backend.events.get_nowait()
                if isinstance(event, Delta):
                    if self.console:
                        self.console.append_response(event.text)
                elif isinstance(event, Done):
                    self.set_state(State.IDLE_ALERT)
                    if self.console:
                        self.console.end_response()
                elif isinstance(event, Failure):
                    self.set_state(State.DRAMATIC_ALERT)
                    if self.console:
                        self.console.show_error(event.message)
        except Exception:
            pass
        self.root.after(50, self._poll_backend)

    def quit(self) -> None:
        self.root.destroy()


class ConsoleWindow:
    """Borderless, compact console: paste-in on top, Buddy's reply below."""

    def __init__(self, pet: BuddyPet) -> None:
        self.pet = pet
        self.alive = True
        self._streaming = False

        self.win = tk.Toplevel(pet.root)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        self.win.configure(bg=Theme.BG, highlightbackground=Theme.DIM_FG,
                           highlightthickness=1)

        self._place_near_pet()
        self._build()
        self._bind_console_drag()

    def _place_near_pet(self) -> None:
        self.pet.root.update_idletasks()
        px = self.pet.root.winfo_x()
        py = self.pet.root.winfo_y()
        w, h = 380, 440
        x = max(10, px - w - 10)
        y = max(10, py - h + Theme.SPRITE_SIZE)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        bar = tk.Frame(self.win, bg=Theme.PANEL_BG)
        bar.pack(fill="x")
        self._bar = bar
        tk.Label(
            bar, text=" buddy@ctf:~$ ", font=Theme.MONO_FONT_SMALL,
            fg=Theme.ACCENT, bg=Theme.PANEL_BG,
        ).pack(side="left", padx=4, pady=2)
        tk.Button(
            bar, text="✕", command=self.close, font=Theme.MONO_FONT_SMALL,
            fg=Theme.ERROR_FG, bg=Theme.PANEL_BG, relief="flat",
            activebackground=Theme.PANEL_BG, activeforeground=Theme.FG,
            cursor="hand2", bd=0,
        ).pack(side="right", padx=4)
        self.mode_btn = tk.Button(
            bar, text="", command=self.pet.toggle_mode,
            font=Theme.MONO_FONT_SMALL, relief="flat", bd=0, cursor="hand2",
            bg=Theme.PANEL_BG, activebackground=Theme.PANEL_BG,
        )
        self.mode_btn.pack(side="right", padx=4)

        self.status = tk.Label(
            self.win, text="", font=Theme.MONO_FONT_SMALL, fg=Theme.DIM_FG,
            bg=Theme.BG, anchor="w",
        )
        self.status.pack(fill="x", padx=6, pady=(2, 0))

        tk.Label(
            self.win, text=" paste challenge / output / error log:",
            font=Theme.MONO_FONT_SMALL, fg=Theme.DIM_FG, bg=Theme.BG, anchor="w",
        ).pack(fill="x", padx=6, pady=(6, 0))
        self.input = tk.Text(
            self.win, height=6, wrap="word", font=Theme.MONO_FONT,
            fg=Theme.FG, bg=Theme.PANEL_BG, insertbackground=Theme.FG,
            relief="flat", padx=6, pady=4, undo=True,
        )
        self.input.pack(fill="x", padx=6, pady=(2, 4))
        self.input.focus_set()
        self.input.bind("<Control-Return>", self._on_submit)

        tk.Button(
            self.win, text="[ TRANSMIT ▸ ]", command=self._on_submit,
            font=Theme.BUTTON_FONT, fg=Theme.BG, bg=Theme.FG,
            activebackground=Theme.ACCENT, activeforeground=Theme.BG,
            relief="flat", cursor="hand2",
        ).pack(fill="x", padx=6)

        tk.Label(
            self.win, text=" >> buddy says:",
            font=Theme.MONO_FONT_SMALL, fg=Theme.DIM_FG, bg=Theme.BG, anchor="w",
        ).pack(fill="x", padx=6, pady=(6, 0))
        out_frame = tk.Frame(self.win, bg=Theme.BG)
        out_frame.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        scroll = tk.Scrollbar(out_frame)
        scroll.pack(side="right", fill="y")
        self.output = tk.Text(
            out_frame, wrap="word", font=Theme.MONO_FONT, fg=Theme.FG,
            bg="#000000", relief="flat", padx=6, pady=4,
            yscrollcommand=scroll.set, state="disabled",
        )
        self.output.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.output.yview)
        self.output.tag_configure("error", foreground=Theme.ERROR_FG)

        self.refresh_status()
        self._banner("[ Buddy online. Ctrl+Enter to transmit. 🐈 ]")

    def refresh_status(self) -> None:
        if self.pet.mode == Mode.SOLVER:
            self.mode_btn.config(text="[ MODE: SOLVER ]", fg=Theme.ERROR_FG)
        else:
            self.mode_btn.config(text="[ MODE: COACH ]", fg=Theme.FG)
        provider = config.PROVIDER
        model = config.LOCAL_MODEL if provider == config.Provider.LOCAL else config.MODEL
        rag = "grounded" if self.pet.backend.rag_active else "off"
        self.status.config(
            text=f" provider:{provider} · model:{model} · knowledge:{rag}"
        )

    # -- drag the console by its title bar --------------------------------- #

    def _bind_console_drag(self) -> None:
        self._dx = self._dy = 0
        self._bar.bind("<Button-1>", self._start)
        self._bar.bind("<B1-Motion>", self._move)

    def _start(self, event: tk.Event) -> None:
        self._dx, self._dy = event.x, event.y

    def _move(self, event: tk.Event) -> None:
        x = self.win.winfo_pointerx() - self._dx
        y = self.win.winfo_pointery() - self._dy
        self.win.geometry(f"+{x}+{y}")

    # -- response rendering ------------------------------------------------- #

    def _write(self, text: str, tag: Optional[str] = None) -> None:
        self.output.config(state="normal")
        self.output.insert("end", text, tag or ())
        self.output.see("end")
        self.output.config(state="disabled")

    def _clear_output(self) -> None:
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")

    def _banner(self, text: str) -> None:
        self._clear_output()
        self._write(text)

    def _on_submit(self, _event: object = None) -> str:
        self.pet.submit_query(self.input.get("1.0", "end"))
        return "break"

    def begin_response(self) -> None:
        self._streaming = False
        self._clear_output()
        self._write("[ coiling up... thinking... ]\n\n")

    def append_response(self, text: str) -> None:
        if not self._streaming:
            self._clear_output()
            self._streaming = True
        self._write(text)

    def end_response(self) -> None:
        self._streaming = False

    def show_error(self, message: str) -> None:
        self._streaming = False
        self._clear_output()
        self._write(message, "error")

    def close(self) -> None:
        self.alive = False
        if self.win.winfo_exists():
            self.win.destroy()
