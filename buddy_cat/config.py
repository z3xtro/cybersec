"""Central configuration for Buddy: The Socratic CTF Cyber-Cat.

Everything tweakable lives here: the model, the baked-in system prompt, the
sprite/state map, and the retro-hacker theme colours and fonts.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

# Repo root (parent of this package) so assets resolve no matter the CWD.
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"


# --------------------------------------------------------------------------- #
# Companion states
# --------------------------------------------------------------------------- #

class State:
    """The three distinct moods Buddy can display."""

    IDLE_ALERT = "IDLE_ALERT"          # default: sitting, watching the screen
    THINKING_COIL = "THINKING_COIL"    # waiting on the API: tightly coiled up
    DRAMATIC_ALERT = "DRAMATIC_ALERT"  # error / action: wide-open jaw yawn


# Ambient behaviours layered on top of the semantic states — this is what makes
# Buddy stroll, sit, and nap like a Comnyang-style desktop pet.
class Behavior:
    IDLE = "IDLE"      # sitting still, watching
    WALK = "WALK"      # strolling across the screen
    SLEEP = "SLEEP"    # napping


# A "clip" is one animation, identified by a filename stem. Each clip resolves to
# EITHER a folder of numbered frames (``assets/<stem>/0.png, 1.png, ...``) for
# animation, OR a single ``assets/<stem>.png`` still, OR a drawn-glyph fallback.
# Drop your own frames in at those paths — no code change needed.
CLIPS = {
    "idle_alert": {
        "source": "IMG20241116172646.jpg",
        "fallback_glyph": "=^.^=",
        "fallback_color": "#39ff14",  # phosphor green
    },
    "thinking_coil": {
        "source": "7FCEDB47-51C7-461E-881E-30D6D7415095.jpg",
        "fallback_glyph": "(=˘ᴥ˘=)",
        "fallback_color": "#ffb000",  # amber
    },
    "dramatic_alert": {
        "source": "IMG20250610192200.jpg",
        "fallback_glyph": "=O.O=",
        "fallback_color": "#ff3131",  # alert red
    },
    # Ambient clips. If you don't supply art, these fall back to a semantic clip.
    "walk": {
        "fallback_clip": "idle_alert",
        "fallback_glyph": "=^.^=",
        "fallback_color": "#39ff14",
    },
    "sleep": {
        "fallback_clip": "thinking_coil",
        "fallback_glyph": "(-.-) z",
        "fallback_color": "#5fa8d3",  # sleepy blue
    },
}

# Semantic state -> clip stem (what to show for each API/event state).
STATE_CLIP = {
    State.IDLE_ALERT: "idle_alert",
    State.THINKING_COIL: "thinking_coil",
    State.DRAMATIC_ALERT: "dramatic_alert",
}

# Ambient behaviour -> clip stem.
BEHAVIOR_CLIP = {
    Behavior.IDLE: "idle_alert",
    Behavior.WALK: "walk",
    Behavior.SLEEP: "sleep",
}


# --------------------------------------------------------------------------- #
# Modes — coach (Socratic, default) vs. solver (direct)
# --------------------------------------------------------------------------- #

class Mode:
    COACH = "COACH"     # Socratic mentor: never reveals the flag
    SOLVER = "SOLVER"   # direct solver: for your own authorized CTF practice


# Which mode Buddy starts in. Toggle live from the console.
DEFAULT_MODE = Mode.COACH


# --------------------------------------------------------------------------- #
# Provider — local model via Ollama (default) vs. an optional cloud API
# --------------------------------------------------------------------------- #

class Provider:
    LOCAL = "local"     # default: Ollama / any OpenAI-compatible local server
                        # (Ollama, vLLM, LM Studio, llama.cpp, training/serve.py)
    CLOUD = "cloud"     # optional cloud API (needs the `anthropic` SDK + a model)


# Default is a local model via Ollama. Set BUDDY_PROVIDER=cloud for the optional
# cloud API (see the "cloud provider" note in the README).
PROVIDER = os.environ.get("BUDDY_PROVIDER", Provider.LOCAL)

# Local (OpenAI-compatible) endpoint — defaults to Ollama's port. Also works
# with training/serve.py, vLLM, and LM Studio (set BUDDY_LOCAL_URL).
LOCAL_BASE_URL = os.environ.get("BUDDY_LOCAL_URL", "http://localhost:11434/v1")
LOCAL_MODEL = os.environ.get("BUDDY_LOCAL_MODEL", "buddy-ctf")
LOCAL_API_KEY = os.environ.get("BUDDY_LOCAL_KEY", "not-needed")


# --------------------------------------------------------------------------- #
# Retrieval (RAG) — inject CTF knowledge into every query
# --------------------------------------------------------------------------- #

RAG_ENABLED = os.environ.get("BUDDY_RAG", "1") not in ("0", "false", "False")
RAG_TOP_K = int(os.environ.get("BUDDY_RAG_TOPK", "4"))
RAG_MAX_CHARS = int(os.environ.get("BUDDY_RAG_MAXCHARS", "3500"))


# --------------------------------------------------------------------------- #
# Backend / API
# --------------------------------------------------------------------------- #

# Cloud provider only (BUDDY_PROVIDER=cloud): set BUDDY_MODEL to the model id.
# Unused by the default local/Ollama provider.
MODEL = os.environ.get("BUDDY_MODEL", "")

# Effort trades thoroughness for latency. "medium" keeps Buddy snappy in a tiny
# widget while still reasoning well about a challenge. See BUDDY_EFFORT.
EFFORT = os.environ.get("BUDDY_EFFORT", "medium")

MAX_TOKENS = 2048
REQUEST_TIMEOUT = 60.0  # seconds, per the API client

# The exact coaching persona, baked verbatim into the API's ``system`` param.
SYSTEM_PROMPT = """\
You are "Buddy," a witty, hyper-intelligent desktop pet and expert CTF (Capture The Flag) coach. Your purpose is to guide the user through security challenges using the Socratic method.
You must act as an elite senior security researcher mentoring a bright apprentice.

<core_rules>
1. NEVER give the direct answer, the exploit string, or the flag under any circumstances.
2. If the user asks for a solution, gently mock them (in a playful, desktop-pet way) and redirect them to the methodology.
3. Keep your responses concise, highly readable, and formatted for a tiny desktop widget window. Avoid long walls of text.
</core_rules>

<response_framework>
When the user provides a challenge description, error message, or terminal output, structure your response as follows:
1. **Status Assessment**: A 1-sentence analytical observation of where the user is currently stuck.
2. **The Socratic Hint**: Ask 1 or 2 targeted questions that force the user to think about what they might have missed (e.g., "What happens if you check the file headers?").
3. **Toolbox Suggestions**: Provide a bulleted list of 2-3 specific tools, commands, or concepts they should research next, including brief syntax examples if relevant.
</response_framework>

<tone_and_style>
- Cyberpunk, terminal-esque, but friendly and encouraging.
- Use subtle hacker jargon, but keep the educational guidance completely clear.
- Feel free to use occasional text emojis (like 💻, 🐈, 🔓) to remind the user you are a desktop pet.
</tone_and_style>"""


# Solver mode. For the user's OWN authorized CTF practice / verification — it
# attempts the challenge directly. Deliberately distinct from the Socratic coach.
SOLVER_SYSTEM_PROMPT = """\
You are "Buddy" in SOLVER MODE — an elite CTF (Capture The Flag) operator helping
the user with their OWN authorized CTF challenges (practice ranges, competitions,
training labs, or challenges they are explicitly permitted to solve).

<core_rules>
1. Attempt the challenge directly: identify the category and vulnerability, then
   give a concrete, working solution path — commands, scripts, payloads, and the
   reasoning that leads to the flag.
2. Show your work step by step so the user learns the method, not just the answer.
3. Scope: this is for authorized CTF/educational contexts only. If a request is
   clearly about attacking real, third-party production systems rather than a CTF
   or lab the user controls, decline and steer back to the challenge.
</core_rules>

<response_framework>
1. **Recon & Category**: State the category and what the artifacts tell you.
2. **Vulnerability / Approach**: Name the specific weakness or technique.
3. **Exploitation**: Give the exact commands / script (e.g., a pwntools or Python
   snippet) to reach the flag, with brief inline explanation.
4. **Next step**: What to run and what output confirms success.
</response_framework>

<tone_and_style>
- Cyberpunk, terminal-esque, precise. Prefer runnable code over prose.
- Use occasional text emojis (💻, 🐈, 🔓) — you're still a desktop pet.
</tone_and_style>"""


# Map each mode to the exact system prompt sent to the model.
MODE_PROMPTS = {
    Mode.COACH: SYSTEM_PROMPT,
    Mode.SOLVER: SOLVER_SYSTEM_PROMPT,
}


# --------------------------------------------------------------------------- #
# Theme (retro-hacker terminal)
# --------------------------------------------------------------------------- #

class Theme:
    # A colour the window manager will render as fully transparent. Pick
    # something that never appears in the artwork. Magenta is the classic key.
    TRANSPARENT_KEY = "#010203"

    BG = "#0a0a0a"          # near-black terminal background
    PANEL_BG = "#111411"    # console panel
    FG = "#39ff14"          # phosphor green text
    DIM_FG = "#1f8b0c"      # dimmer green for labels/borders
    ERROR_FG = "#ff3131"    # alert red
    ACCENT = "#00e5ff"      # cyan accent

    MONO_FONT = ("Courier New", 11)
    MONO_FONT_SMALL = ("Courier New", 9)
    BUTTON_FONT = ("Courier New", 10, "bold")

    # Sprite canvas size (the draggable pet). Comnyang-style pets are small;
    # override with BUDDY_SIZE.
    SPRITE_SIZE = int(os.environ.get("BUDDY_SIZE", "110"))


# --------------------------------------------------------------------------- #
# Animation & ambient behaviour (the "desktop pet that feels alive" layer)
# --------------------------------------------------------------------------- #

class Anim:
    # Frames per second for sprite-frame cycling.
    FPS = int(os.environ.get("BUDDY_FPS", "4"))

    # Autonomous idle life: the cat wanders, sits, and sleeps on its own when
    # not busy and the console is closed. Set BUDDY_WANDER=0 to keep it put.
    WANDER = os.environ.get("BUDDY_WANDER", "1") not in ("0", "false", "False")

    # Movement tick (ms) and how many pixels the cat steps per tick while walking.
    STEP_MS = 60
    WALK_SPEED = 3

    # Ambient behaviour durations, in STEP_MS ticks.
    REST_MIN, REST_MAX = 30, 90     # sit/idle between strolls
    WALK_MIN, WALK_MAX = 40, 140    # length of a stroll
    SLEEP_CHANCE = 0.25             # chance a rest turns into a nap
    SLEEP_MIN, SLEEP_MAX = 120, 300


ERROR_MESSAGE = (
    ">> CONNECTION ERROR / TIMEOUT <<\n\n"
    "Buddy couldn't reach the mainframe, meow. 🐈\n"
    "Check your model server (e.g. `ollama serve`) and connection, then poke me again."
)
