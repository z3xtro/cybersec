"""Offline retrieval over the CTF knowledge base.

A dependency-free BM25 keyword retriever. No embeddings, no network, no GPU —
it just reads the markdown under ``knowledge/``, splits each file into
heading-delimited chunks, and ranks them against the user's query. This is what
"specializes" Buddy for CTFs without any training: the top chunks are injected
into the prompt so the model (cloud or local) answers with the right tools and
techniques in front of it.

If the knowledge directory is missing, retrieval degrades to a no-op and Buddy
still works.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Common English + markdown noise that shouldn't drive relevance.
_STOPWORDS = frozenset(
    """a an the and or of to in on for with is are be this that it as at by from
    you your can use using try look find get the0 if then when what how""".split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class Chunk:
    source: str          # filename, e.g. "web.md"
    title: str           # heading text
    text: str            # full chunk incl. heading
    tokens: list[str] = field(default_factory=list)


class KnowledgeBase:
    """Loads knowledge chunks and answers BM25 queries."""

    # BM25 tuning constants.
    _K1 = 1.5
    _B = 0.75

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self._dir = knowledge_dir or config.KNOWLEDGE_DIR
        self.chunks: list[Chunk] = []
        self._df: dict[str, int] = {}
        self._avg_len = 0.0
        self._load()

    @property
    def available(self) -> bool:
        return bool(self.chunks)

    def _load(self) -> None:
        if not self._dir.exists():
            return
        for md in sorted(self._dir.glob("*.md")):
            try:
                raw = md.read_text(encoding="utf-8")
            except OSError:
                continue
            for chunk in self._split(raw, md.name):
                chunk.tokens = _tokenize(chunk.text)
                if chunk.tokens:
                    self.chunks.append(chunk)
        self._index()

    @staticmethod
    def _split(raw: str, source: str) -> list[Chunk]:
        """Split a markdown doc into chunks at ``##`` headings."""
        chunks: list[Chunk] = []
        current_title = source
        buf: list[str] = []

        def flush() -> None:
            body = "\n".join(buf).strip()
            if body:
                chunks.append(Chunk(source=source, title=current_title, text=body))

        for line in raw.splitlines():
            if line.startswith("## "):
                flush()
                current_title = line[3:].strip()
                buf = [line]
            else:
                buf.append(line)
        flush()
        return chunks

    def _index(self) -> None:
        if not self.chunks:
            return
        for chunk in self.chunks:
            for term in set(chunk.tokens):
                self._df[term] = self._df.get(term, 0) + 1
        self._avg_len = sum(len(c.tokens) for c in self.chunks) / len(self.chunks)

    def _idf(self, term: str) -> float:
        n = len(self.chunks)
        df = self._df.get(term, 0)
        # BM25 idf with +1 to stay positive.
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def _score(self, query_terms: list[str], chunk: Chunk) -> float:
        if not chunk.tokens:
            return 0.0
        freqs: dict[str, int] = {}
        for t in chunk.tokens:
            freqs[t] = freqs.get(t, 0) + 1
        length = len(chunk.tokens)
        score = 0.0
        for term in query_terms:
            tf = freqs.get(term, 0)
            if tf == 0:
                continue
            idf = self._idf(term)
            denom = tf + self._K1 * (1 - self._B + self._B * length / self._avg_len)
            score += idf * (tf * (self._K1 + 1)) / denom
        return score

    def retrieve(self, query: str, top_k: int | None = None,
                 max_chars: int | None = None) -> list[Chunk]:
        """Return the top-scoring chunks for ``query`` (highest first)."""
        if not self.chunks:
            return []
        top_k = top_k or config.RAG_TOP_K
        max_chars = max_chars or config.RAG_MAX_CHARS
        query_terms = _tokenize(query)
        if not query_terms:
            return []
        scored = [(self._score(query_terms, c), c) for c in self.chunks]
        scored = [sc for sc in scored if sc[0] > 0]
        scored.sort(key=lambda sc: sc[0], reverse=True)

        picked: list[Chunk] = []
        budget = max_chars
        for _score, chunk in scored[:top_k]:
            if budget - len(chunk.text) < 0 and picked:
                break
            picked.append(chunk)
            budget -= len(chunk.text)
        return picked

    def context_block(self, query: str) -> str:
        """Render retrieved chunks as a prompt-injectable knowledge block.

        Returns an empty string when nothing relevant is found, so callers can
        skip injection cleanly.
        """
        hits = self.retrieve(query)
        if not hits:
            return ""
        parts = [f"# from {h.source}\n{h.text}" for h in hits]
        return (
            "<ctf_knowledge>\n"
            "Reference material retrieved for this challenge (tools, techniques, "
            "syntax). Use it to ground your guidance; cite tools by name.\n\n"
            + "\n\n---\n\n".join(parts)
            + "\n</ctf_knowledge>"
        )
