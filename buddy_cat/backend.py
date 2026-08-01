"""Backend engine: routes CTF queries to the cloud LLM or a local model.

The GUI never touches a model client directly. It calls
``BuddyBackend.ask(prompt, system_prompt)`` which spawns a worker thread; the
worker retrieves CTF knowledge (RAG), calls the selected provider, streams the
reply, and pushes events onto a thread-safe queue. The GUI drains that queue on
the Tk main thread (see ``ui.py``), so no model/Tk call ever happens off the
main thread — the one hard rule of Tkinter concurrency.

Providers:
  * ``cloud``  — the cloud LLM API (streaming).
  * ``local``  — any OpenAI-compatible ``/chat/completions`` endpoint (your
    fine-tuned model via ``training/serve.py``, vLLM, Ollama, LM Studio, ...).
"""

from __future__ import annotations

import json
import queue
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import config
from .rag import KnowledgeBase

try:
    import anthropic

    _HAVE_ANTHROPIC = True
except ImportError:  # pragma: no cover - depends on the host environment
    _HAVE_ANTHROPIC = False


# --------------------------------------------------------------------------- #
# Events pushed from the worker thread to the GUI
# --------------------------------------------------------------------------- #

@dataclass
class Delta:
    """A chunk of streamed response text."""

    text: str


@dataclass
class Done:
    """The stream finished cleanly."""


@dataclass
class Failure:
    """Something went wrong; ``message`` is safe to show in the console."""

    message: str


Event = object  # Delta | Done | Failure


class BuddyBackend:
    """Owns the model client(s), the knowledge base, and the worker lifecycle."""

    def __init__(self) -> None:
        self.events: "queue.Queue[Event]" = queue.Queue()
        self._client = None  # lazily constructed API client
        self._busy = threading.Event()
        self.kb = KnowledgeBase() if config.RAG_ENABLED else None

    # ------------------------------------------------------------------ #
    # Public API (called from the GUI thread)
    # ------------------------------------------------------------------ #

    @property
    def busy(self) -> bool:
        return self._busy.is_set()

    @property
    def rag_active(self) -> bool:
        return bool(self.kb and self.kb.available)

    def ask(self, prompt: str, system_prompt: str) -> bool:
        """Kick off a request on a background thread.

        Returns ``False`` (and does nothing) if a request is already running.
        """
        if self._busy.is_set():
            return False
        self._busy.set()
        worker = threading.Thread(
            target=self._run,
            args=(prompt, system_prompt),
            name="buddy-api",
            daemon=True,
        )
        worker.start()
        return True

    # ------------------------------------------------------------------ #
    # Worker thread
    # ------------------------------------------------------------------ #

    def _build_user_content(self, prompt: str) -> str:
        """Prepend retrieved CTF knowledge to the user's challenge."""
        if self.kb and self.kb.available:
            block = self.kb.context_block(prompt)
            if block:
                return f"{block}\n\nUSER CHALLENGE:\n{prompt}"
        return prompt

    def _run(self, prompt: str, system_prompt: str) -> None:
        try:
            content = self._build_user_content(prompt)
            if config.PROVIDER == config.Provider.LOCAL:
                self._run_local(content, system_prompt)
            else:
                self._run_cloud(content, system_prompt)
            self.events.put(Done())
        except Exception as exc:  # noqa: BLE001 - map everything to a clean alert
            self.events.put(Failure(self._describe(exc)))
        finally:
            self._busy.clear()

    # -- Cloud provider (streaming) ---------------------------------------- #

    def _get_client(self):
        if self._client is None:
            if not _HAVE_ANTHROPIC:
                raise RuntimeError(
                    "The optional 'anthropic' package is not installed. "
                    "Run: pip install anthropic  (only needed for BUDDY_PROVIDER=cloud)"
                )
            self._client = anthropic.Anthropic(timeout=config.REQUEST_TIMEOUT)
        return self._client

    def _run_cloud(self, content: str, system_prompt: str) -> None:
        if not config.MODEL:
            raise RuntimeError(
                "Set BUDDY_MODEL to a cloud model id to use BUDDY_PROVIDER=cloud "
                "(the default provider is local/Ollama)."
            )
        client = self._get_client()
        with client.messages.stream(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=system_prompt,
            output_config={"effort": config.EFFORT},
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for text in stream.text_stream:
                if text:
                    self.events.put(Delta(text))

    # -- Local provider (OpenAI-compatible, stdlib HTTP) ------------------- #

    def _run_local(self, content: str, system_prompt: str) -> None:
        """Call an OpenAI-compatible /chat/completions endpoint (non-streaming).

        Uses only urllib so the local path adds no dependency. The whole reply
        is delivered as a single Delta, which the console renders identically to
        a streamed one.
        """
        url = config.LOCAL_BASE_URL.rstrip("/") + "/chat/completions"
        body = json.dumps({
            "model": config.LOCAL_MODEL,
            "max_tokens": config.MAX_TOKENS,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LOCAL_API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        if text:
            self.events.put(Delta(text))

    # ------------------------------------------------------------------ #

    @staticmethod
    def _describe(exc: Exception) -> str:
        """Turn any exception into a short, user-safe error line."""
        cause = type(exc).__name__
        if isinstance(exc, (urllib.error.URLError, urllib.error.HTTPError)):
            cause = f"local model unreachable at {config.LOCAL_BASE_URL}"
        elif _HAVE_ANTHROPIC:
            if isinstance(exc, getattr(anthropic, "AuthenticationError", ())):
                cause = "invalid or missing API key"
            elif isinstance(exc, getattr(anthropic, "RateLimitError", ())):
                cause = "rate limited"
            elif isinstance(exc, getattr(anthropic, "APIConnectionError", ())):
                cause = "network / connection failure"
            elif isinstance(exc, getattr(anthropic, "APITimeoutError", ())):
                cause = "request timed out"
        return f"{config.ERROR_MESSAGE}\n\n[detail: {cause}]"
