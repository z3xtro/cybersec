"""Application entry point: wire up Tk and launch Buddy."""

from __future__ import annotations

import tkinter as tk

from .ui import BuddyPet


def main() -> None:
    root = tk.Tk()
    root.title("Buddy: The Socratic CTF Cyber-Cat")
    BuddyPet(root)
    root.mainloop()


if __name__ == "__main__":
    main()
