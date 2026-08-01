# Buddy: The Socratic CTF Cyber-Cat 🐈‍⬛💻

A lightweight Python desktop pet that sits on top of your screen and coaches you
through Capture-The-Flag challenges using the **Socratic method** — it never
hands you the flag, it makes you *earn* it.

Buddy is a frameless, always-on-top, draggable cat. Click **[ ASK BUDDY ]**,
paste in a challenge description, terminal dump, error log, or code snippet, and
Buddy replies in a retro-terminal console with a status read, pointed questions,
and a short toolbox of things to try next.

```
   =^.^=      idle & watching
  (=˘ᴥ˘=)     coiled up, thinking (waiting on the API)
   =O.O=      dramatic yawn (errors / alerts)
```

## Features

- **Frameless, transparent, always-on-top** pet — only the cat shows, no window box.
- **Animated & alive** (Comnyang-style) — frame-by-frame sprite animation, and an
  idle life loop where the cat autonomously **strolls along the screen, sits, and
  naps** when you're not using it.
- **Drag anywhere** with left-click (interrupts wandering).
- **Three event states** driven by the app (idle / thinking / alert).
- **Retro-hacker console overlay** — green-on-black monospace, paste large blobs in.
- **LLM-powered coaching** with a baked-in Socratic-mentor system prompt.
- **Non-blocking UI** — API calls run on a background thread and stream into the console.
- **Graceful failure** — connection/timeout/auth errors flip Buddy to the alert
  sprite and print a clean error, never a crash.

## Install

```bash
git clone <this-repo>
cd cybersec
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

On some Linux distros Tkinter is a separate package:

```bash
sudo apt install python3-tk        # Debian/Ubuntu
```

## Configure

Buddy runs on a **local [Ollama](https://ollama.com) model** by default — no API
key, nothing leaves your machine. Install Ollama, then build Buddy's model:

```bash
ollama pull qwen2.5:7b-instruct
ollama create buddy-ctf -f ollama/Modelfile
```

That's it — Buddy talks to Ollama at `http://localhost:11434/v1` out of the box.
See [`ollama/README.md`](ollama/README.md) to fine-tune your own CTF model.

Optional overrides:

| Env var | Default | Purpose |
|---|---|---|
| `BUDDY_PROVIDER` | `local` | `local` (Ollama / OpenAI-compatible) or `cloud` |
| `BUDDY_LOCAL_URL` | `http://localhost:11434/v1` | Local OpenAI-compatible endpoint (Ollama) |
| `BUDDY_LOCAL_MODEL` | `buddy-ctf` | Model name served locally |
| `BUDDY_RAG` | `1` | Set `0` to disable knowledge-base grounding |
| `BUDDY_RAG_TOPK` | `4` | How many knowledge chunks to inject per query |
| `BUDDY_SIZE` | `110` | Sprite size in px (Comnyang-style pets are small) |
| `BUDDY_FPS` | `4` | Animation frame rate |
| `BUDDY_WANDER` | `1` | Set `0` to stop the cat wandering/napping on its own |

### Optional: hosted cloud provider

Prefer a hosted model over local Ollama? Install the optional SDK and switch:

```bash
pip install anthropic
BUDDY_PROVIDER=cloud BUDDY_MODEL=<model-id> python -m buddy_cat
```

## Run

```bash
python -m buddy_cat
```

- **Left-click + drag** — move Buddy around.
- **[ ASK BUDDY ]** — open/close the console.
- **Ctrl+Enter** in the input — transmit your query.
- **Right-click Buddy** — quit.

## CTF specialization

Buddy ships specialized for CTFs in three layers:

### 1. Knowledge grounding (RAG) — on by default, no setup

`buddy_cat/knowledge/` holds category playbooks (pwn, rev, crypto, web,
forensics, misc/OSINT, general). A dependency-free **BM25 retriever**
(`buddy_cat/rag.py`) pulls the most relevant tools/techniques for whatever you
paste and injects them into the prompt, so the model answers with the right
`pwntools`/`sqlmap`/`volatility` context in front of it. Add your own `.md`
files to that folder to teach Buddy more — no code change needed. Disable with
`BUDDY_RAG=0`.

### 2. Coach ⇄ Solver toggle

Click **[ MODE: COACH ]** in the console title bar to switch:

- **COACH** (default) — Socratic mentor; deep CTF knowledge, but never reveals
  the exploit or flag.
- **SOLVER** — direct, worked solutions with commands and scripts, for your
  **own authorized** CTF practice, competitions, and training labs.

### 3. Fine-tune your own CTF model (optional)

The [`training/`](training/) directory builds a CTF-specialized **open** model
(LoRA/QLoRA on Qwen/Llama/Mistral) that Buddy can call instead of the cloud model:

```bash
pip install -r training/requirements-train.txt
python training/build_dataset.py          # dataset from knowledge base + your writeups
python training/train_lora.py             # QLoRA fine-tune (needs a GPU)
python training/serve.py                  # OpenAI-compatible server on :8000
BUDDY_PROVIDER=local python -m buddy_cat  # Buddy now runs on your model
```

Because the local provider speaks the OpenAI API, you can also point Buddy at
**vLLM / Ollama / LM Studio** without `serve.py`. Full walkthrough in
[`training/README.md`](training/README.md).

**Ollama** has its own guide — [`ollama/README.md`](ollama/README.md) — covering
both an instant Modelfile persona (no GPU) and importing a fine-tuned model:

```bash
ollama create buddy-ctf -f ollama/Modelfile                       # instant
BUDDY_PROVIDER=local BUDDY_LOCAL_URL=http://localhost:11434/v1 \
  BUDDY_LOCAL_MODEL=buddy-ctf python -m buddy_cat                  # run Buddy on it
```

## Artwork

The repo ships with crude, animated placeholder sprites so it runs immediately.
Each animation is a *clip* — either a **folder of numbered frames**
(`assets/idle_alert/0.png`, `1.png`, …) for animation, or a single still
(`assets/idle_alert.png`). Clips:

- `idle_alert` — sitting, watching
- `thinking_coil` — curled up tight (while waiting on the API)
- `dramatic_alert` — wide-open yawn (errors)
- `walk` — side-profile walk cycle (draw facing right; auto-flipped)
- `sleep` — curled up napping

Drop your own transparent PNG frames in at those paths and Buddy picks them up —
no code change. See [`assets/README.md`](assets/README.md) for the full layout.

**Only have one still per pose?** Save three stills (`assets/idle_alert.png`,
`assets/dramatic_alert.png`, `assets/sleep.png`) and let Buddy animate them for
you — a gentle breathing bob, all frames derived automatically:

```bash
pip install Pillow
python scripts/animate_from_stills.py     # -> animated frame folders
```

Or regenerate the built-in placeholders:

```bash
python scripts/generate_placeholders.py
```

## Project layout

```
cybersec/
├── buddy_cat/            # the application package
│   ├── __main__.py       # `python -m buddy_cat`
│   ├── app.py            # Tk bootstrap
│   ├── config.py         # model, prompts, modes, provider, states, theme
│   ├── assets.py         # sprite loading (Pillow → Tk PNG → drawn glyph)
│   ├── backend.py        # threaded client (cloud | local) + RAG + event queue
│   ├── rag.py            # dependency-free BM25 retriever over the knowledge base
│   ├── ui.py             # frameless pet + console overlay + mode toggle
│   └── knowledge/        # CTF category playbooks (pwn/rev/crypto/web/...)
├── assets/               # transparent PNG sprites (placeholders included)
├── training/             # LoRA fine-tune pipeline (dataset → train → serve)
│   ├── build_dataset.py
│   ├── train_lora.py
│   ├── serve.py
│   └── README.md
├── scripts/
│   └── generate_placeholders.py
├── requirements.txt
└── README.md
```

## How the concurrency works

Tkinter is single-threaded and unsafe to touch from other threads. Buddy keeps
that rule airtight:

1. On submit, the UI instantly switches the sprite to **THINKING_COIL**.
2. `BuddyBackend.ask()` spawns a **daemon worker thread** that streams the
   model's response and pushes `Delta` / `Done` / `Failure` events onto a
   `queue.Queue`.
3. The Tk main thread drains that queue every 50 ms via `root.after()`,
   appending streamed text, reverting to **IDLE_ALERT** on completion, or
   flipping to **DRAMATIC_ALERT** with a clean error message on failure.

No network or Tk call ever crosses a thread boundary.

## Note on transparency

Per-pixel window transparency is platform-dependent:

- **Windows** — uses `-transparentcolor` (fully supported).
- **macOS** — uses `-transparent`.
- **Linux/X11** — depends on a running compositor; without one you may see a
  solid backdrop behind the cat instead of true transparency.
