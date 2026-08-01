# Cryptography (crypto)

> Signals: crypto cipher rsa aes xor encryption decrypt hash key public private modulus exponent factor ecb cbc padding oracle vigenere caesar base64 ciphertext plaintext sagemath.

## Identify first
- Ciphertext shape: hex, base64, decimal ints, PEM key, big integers `(n, e, c)`.
- Classical vs modern: short readable alphabet → classical; blocks/keys → modern.
- Tools to fingerprint: CyberChef "Magic", `hash-identifier`, entropy checks.

## Classical
- Caesar/ROT: brute all 25 shifts. Vigenère: find key length (Kasiski/IC) then solve.
- Substitution: frequency analysis (`quipqiup` online, or scripted).
- XOR single-byte: brute 0..255, score by English frequency; multi-byte: `xortool`.

## RSA (very common)
- Given `(n, e, c)`. Attacks depend on the weakness:
  - **Small e (e=3):** if `m^e < n`, `m = iroot(c, 3)` (no modulus wrap).
  - **Factorable n:** try `factordb`, Fermat (close primes), Pollard's rho.
  - **Shared/known factor:** `gcd(n1, n2)` across multiple keys.
  - **Wiener:** small private `d` → continued fractions.
  - **Common modulus:** same `n`, two `e` with `gcd(e1,e2)=1` → combine.
- Decrypt: `d = inverse(e, phi)`, `m = pow(c, d, n)`, then `long_to_bytes(m)`.
```python
from Crypto.Util.number import long_to_bytes, inverse
phi = (p-1)*(q-1); d = inverse(e, phi); m = pow(c, d, n)
print(long_to_bytes(m))
```

## Symmetric (AES etc.)
- **ECB:** identical plaintext blocks → identical ciphertext blocks (ECB detection,
  byte-at-a-time decryption when you control input).
- **CBC bit-flipping:** flip a byte in ciphertext block N to control plaintext block N+1.
- **Padding oracle:** decrypt CBC without the key if the server leaks padding validity.
- **Nonce reuse (CTR/GCM):** keystream reuse → XOR out the key.

## Tools
CyberChef, SageMath, `pycryptodome`, `sympy`, RsaCtfTool, factordb, xortool,
hashcat/john (for hashes), z3 (constraint solving).
