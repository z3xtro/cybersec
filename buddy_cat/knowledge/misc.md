# Misc, OSINT & Jails

> Signals: misc encoding decode base64 base32 morse binary qr barcode jail sandbox escape pyjail osint reverse image exif gps username programming ppc netcat cyberchef esolang brainfuck.

## Encoding / decoding ladder
- Recognize and peel layers: base64, base32, base85, hex, URL, HTML entities, ROT13/47,
  Morse, binary, decimal, brainfuck, Ook!, esolangs.
- CyberChef "Magic" auto-detects layered encodings; build a recipe to peel them.
- Weird alphabets: base58 (crypto addresses), base62, custom substitution.

## QR / barcodes / visual
- `zbarimg image.png` for QR/barcodes. Broken QR: repair finder/alignment patterns.
- Look for data in EXIF GPS, aztec codes, DataMatrix.

## Python / shell jails (escape a sandbox)
- Blocked keywords? Use `__import__`, `getattr`, `builtins`, `().__class__.__bases__`.
- `().__class__.__mro__[1].__subclasses__()` → find `subprocess.Popen`/`os` gadget.
- `breakpoint()`, f-string tricks, `chr()`/`ord()` to rebuild blocked strings.
- Shell: `$IFS` for spaces, `${PATH:0:1}` for `/`, wildcards, `cat<flag`.

## OSINT
- Reverse image search (Google Lens, Yandex, TinEye).
- EXIF GPS → map coordinates; sun/shadow, license plates, signage, languages.
- Usernames across platforms (sherlock), WHOIS, DNS history, Wayback Machine.
- Social graph: linked accounts, metadata in uploaded docs.

## Programming / ppc
- Solve automatically with a script; many are timed servers over `nc host port`.
- pwntools `remote()` to interact; parse the challenge, compute, send fast.

## Tools
CyberChef, zbarimg, sherlock, exiftool, pwntools, Python, Wayback Machine,
Yandex/Google reverse image search.
