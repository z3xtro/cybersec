#!/usr/bin/env python3
"""Build an instruction dataset to fine-tune Buddy for CTFs.

Produces chat-format JSONL (``{"messages": [...]}`` per line) with BOTH styles
Buddy supports:

  * COACH  — Socratic hints that never reveal the flag.
  * SOLVER — direct, worked solutions for authorized CTF practice.

Two sources are combined:

  1. **Seed examples** synthesized from the app's own knowledge base
     (``buddy_cat/knowledge/*.md``). These bootstrap the model with category
     playbooks and give you a runnable end-to-end pipeline out of the box.
  2. **Your writeups** (optional, and where the real signal is): drop JSONL or
     Markdown into ``training/data/writeups/`` and they get folded in. See the
     format notes in ``training/README.md``.

Usage:
    python training/build_dataset.py                 # seed only
    python training/build_dataset.py --writeups data/writeups
    python training/build_dataset.py --val-split 0.1
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "buddy_cat" / "knowledge"
OUT_DIR = Path(__file__).resolve().parent / "data"

# Keep these in lockstep with buddy_cat/config.py so the fine-tune matches how
# Buddy actually prompts at inference time.
COACH_SYSTEM = (
    "You are \"Buddy,\" a witty CTF coach. Guide via the Socratic method. "
    "NEVER give the direct answer, exploit string, or flag. Assess where the "
    "user is stuck, ask 1-2 targeted questions, then suggest 2-3 tools or "
    "concepts to research next."
)
SOLVER_SYSTEM = (
    "You are \"Buddy\" in solver mode, an elite CTF operator helping with the "
    "user's own authorized challenges. Identify the category and vulnerability, "
    "then give a concrete, worked solution with commands/scripts and reasoning."
)


def _chunks(md_text: str) -> list[tuple[str, str]]:
    """Split a knowledge doc into (title, body) at ## headings."""
    out, title, buf = [], None, []
    for line in md_text.splitlines():
        if line.startswith("## "):
            if title and buf:
                out.append((title, "\n".join(buf).strip()))
            title, buf = line[3:].strip(), []
        elif title:
            buf.append(line)
    if title and buf:
        out.append((title, "\n".join(buf).strip()))
    return out


def _category(filename: str) -> str:
    return {
        "pwn.md": "binary exploitation (pwn)",
        "rev.md": "reverse engineering",
        "crypto.md": "cryptography",
        "web.md": "web exploitation",
        "forensics.md": "forensics / steganography",
        "misc.md": "misc / OSINT",
        "general.md": "general CTF methodology",
    }.get(filename, "CTF")


COACH_USER_TEMPLATES = [
    "I'm stuck on a {cat} challenge about {topic}. Where do I even start?",
    "Give me a hint on {topic} for a {cat} challenge — don't spoil it.",
    "What should I be checking for {topic}? ({cat})",
]
SOLVER_USER_TEMPLATES = [
    "Walk me through solving a {cat} challenge involving {topic}.",
    "How do I actually exploit {topic}? This is my own practice box. ({cat})",
    "Show me the steps and commands for {topic} in {cat}.",
]


def _coach_answer(topic: str, body: str) -> str:
    return (
        f"**Status:** Sounds like you're circling {topic} without a foothold yet. 🐈\n\n"
        f"**Ask yourself:** What have you actually confirmed vs. assumed? "
        f"What's the very first thing the artifacts are telling you?\n\n"
        f"**Research next:**\n{_bullets(body)}\n\n"
        f"Poke at those and report back what you see — don't make me hand you the flag. 🔓"
    )


def _solver_answer(topic: str, body: str) -> str:
    return (
        f"**Recon:** This is a {topic} problem — line up the artifacts first.\n\n"
        f"**Approach & commands:**\n{body}\n\n"
        f"**Next:** run the above, confirm the expected output, then pull the flag. 💻"
    )


def _bullets(body: str, limit: int = 4) -> str:
    lines = [l.strip("-* ").strip() for l in body.splitlines()
             if l.strip().startswith(("-", "*", "`"))]
    lines = [l for l in lines if l][:limit]
    if not lines:
        # fall back to first sentences
        lines = re.split(r"(?<=[.])\s+", body.strip())[:limit]
    return "\n".join(f"- {l}" for l in lines)


def seed_examples() -> list[dict]:
    if not KNOWLEDGE_DIR.exists():
        print(f"! knowledge dir not found: {KNOWLEDGE_DIR}", file=sys.stderr)
        return []
    rows: list[dict] = []
    for md in sorted(KNOWLEDGE_DIR.glob("*.md")):
        cat = _category(md.name)
        for title, body in _chunks(md.read_text(encoding="utf-8")):
            topic = title.lower()
            # one coach + one solver example per chunk
            cu = random.choice(COACH_USER_TEMPLATES).format(cat=cat, topic=topic)
            rows.append(_row(COACH_SYSTEM, cu, _coach_answer(topic, body)))
            su = random.choice(SOLVER_USER_TEMPLATES).format(cat=cat, topic=topic)
            rows.append(_row(SOLVER_SYSTEM, su, _solver_answer(topic, body)))
    return rows


def _row(system: str, user: str, assistant: str) -> dict:
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


def load_writeups(path: Path) -> list[dict]:
    """Fold in user-supplied writeups.

    Accepts:
      * ``*.jsonl`` — lines already in ``{"messages": [...]}`` chat format, or
        ``{"instruction","input","output","mode"}`` records.
      * ``*.md`` — a writeup; treated as a SOLVER example whose user turn is the
        first heading/line and whose answer is the body.
    """
    rows: list[dict] = []
    if not path.exists():
        return rows
    for f in sorted(path.rglob("*")):
        if f.suffix == ".jsonl":
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                rows.append(_normalize(obj))
        elif f.suffix in (".md", ".txt"):
            text = f.read_text(encoding="utf-8").strip()
            if not text:
                continue
            first, _, rest = text.partition("\n")
            title = first.lstrip("# ").strip() or f.stem
            rows.append(_row(SOLVER_SYSTEM,
                             f"Explain and solve this challenge: {title}",
                             rest.strip() or text))
    return rows


def _normalize(obj: dict) -> dict:
    if "messages" in obj:
        return {"messages": obj["messages"]}
    mode = str(obj.get("mode", "solver")).lower()
    system = SOLVER_SYSTEM if mode.startswith("solv") else COACH_SYSTEM
    user = obj.get("instruction", "")
    if obj.get("input"):
        user = f"{user}\n\n{obj['input']}"
    return _row(system, user, obj.get("output", ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build Buddy's CTF fine-tune dataset")
    ap.add_argument("--writeups", type=Path, default=OUT_DIR / "writeups",
                    help="dir of extra writeups (jsonl/md) to fold in")
    ap.add_argument("--val-split", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--no-seed-examples", action="store_true",
                    help="skip the knowledge-base-synthesized seed set")
    args = ap.parse_args()

    random.seed(args.seed)
    rows: list[dict] = []
    if not args.no_seed_examples:
        rows += seed_examples()
    rows += load_writeups(args.writeups)

    if not rows:
        print("no data produced; add writeups or keep seed examples", file=sys.stderr)
        sys.exit(1)

    random.shuffle(rows)
    n_val = max(1, int(len(rows) * args.val_split)) if len(rows) > 10 else 0
    val, train = rows[:n_val], rows[n_val:]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write(OUT_DIR / "train.jsonl", train)
    if val:
        _write(OUT_DIR / "val.jsonl", val)
    print(f"wrote {len(train)} train / {len(val)} val examples to {OUT_DIR}")
    print("next: python training/train_lora.py --data training/data")


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
