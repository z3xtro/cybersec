# Reverse Engineering (rev)

> Signals: reverse engineering binary decompile ghidra ida disassemble crackme keygen serial password check strcmp patch anti-debug obfuscation pyinstaller apk dnspy strings ltrace.

## Triage
- `file`, `strings -n 6`, `nm`, `rabin2 -I ./bin` (arch, bits, protections).
- Detect packers: `strings` looking sparse + high entropy → try `upx -d`.
- Identify language/runtime: Go, Rust, .NET, Python (PyInstaller), Java.

## Static analysis
- **Ghidra** (free) / IDA / Binary Ninja — decompile to C-like pseudocode.
- Find `main`, the comparison that gates success, and any `strcmp`/`memcmp` against
  a hardcoded value.
- Rename variables as you understand them; follow the data into the check.

## Dynamic analysis
- `ltrace ./bin` / `strace ./bin` — library and syscall traces (watch `strcmp`).
- GDB with pwndbg/GEF: break on the compare, inspect registers/memory.
- `gdb -ex 'b strcmp' -ex run ./bin` then read the two arguments.

## Common patterns
- **Hardcoded check:** the flag or password sits in `.rodata` — often just `strings`.
- **Transformed check:** input is XORed/added/rotated then compared to a constant.
  Reverse the transform, or brute per-byte if independent.
- **Serial/keygen:** derive the algorithm and write a keygen.
- **Anti-debug:** `ptrace(PTRACE_TRACEME)`, timing checks — patch the jump or NOP it.

## Language-specific
- **Go:** stripped but `strings` + `GoReSym`; symbol recovery helps a lot.
- **.NET:** decompile with dnSpy / ILSpy (near-source).
- **PyInstaller:** `pyinstxtractor.py` then decompile `.pyc` with `decompyle3`/`uncompyle6`.
- **Android APK:** `jadx` for Java, `apktool` for smali/resources.

## Tools
Ghidra, IDA Free, Binary Ninja, radare2/rizin, dnSpy, jadx, angr, ltrace/strace,
GDB (pwndbg/GEF), upx, GoReSym.
