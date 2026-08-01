# CTF General Methodology

> Signals: ctf flag start begin methodology triage file strings hexdump magic bytes category unknown help stuck approach general first steps enumerate.

## First moves on any challenge
- Read the prompt carefully; the category and flavor text are hints.
- Note the flag format (e.g. `flag{...}`, `CTF{...}`) — it tells you when you're done.
- Identify the category: pwn, rev, crypto, web, forensics, misc, osint, hardware.
- Enumerate what you're given: a URL, a binary, a pcap, a ciphertext, source code.

## Universal triage commands
- `file <target>` — identify type (ELF, PE, image, archive, script).
- `strings -n 8 <target>` — printable strings; grep for `flag`, `key`, `password`, `http`.
- `xxd <target> | head` / `hexdump -C` — inspect magic bytes and headers.
- `binwalk <target>` — find embedded files/archives; `binwalk -e` to extract.
- `exiftool <target>` — metadata (often hides hints or flags).

## Flag hunting shortcuts
- `grep -rniaE 'flag\{|ctf\{' .` across extracted files.
- Try common encodings when you see suspicious blobs: base64, hex, ROT13, URL, base32.
- `base64 -d`, `xxd -r -p`, `tr 'A-Za-z' 'N-ZA-Mn-za-m'` (ROT13).

## Mindset
- Low-hanging fruit first: strings, metadata, obvious encodings.
- One hypothesis at a time; verify before pivoting.
- Keep notes of what you tried — CTFs reward systematic elimination.
