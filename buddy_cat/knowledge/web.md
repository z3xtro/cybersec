# Web Exploitation (web)

> Signals: website url http login form register admin cookie session token jwt
> sqli sql injection sqlmap union select xss script alert ssti template jinja
> lfi rfi path traversal etc passwd ssrf metadata command injection rce idor
> parameter tampering upload deserialization api endpoint burp header.

## Recon
- View source, JS files, comments; check `/robots.txt`, `/sitemap.xml`, `/.git/`.
- Enumerate: `gobuster`/`ffuf`/`feroxbuster` for dirs and files.
- Inspect requests in DevTools / Burp Suite; note cookies, headers, params.
- Fingerprint stack: `whatweb`, response headers, error pages, framework tells.

## Common vulnerability classes
- **SQL injection:** `' OR '1'='1`, `UNION SELECT`, error/boolean/time-based blind.
  Automate with `sqlmap -u <url> --dbs`. Watch for auth bypass and data dump.
- **XSS:** reflected/stored/DOM. `<script>`, `<img src=x onerror=...>`; steal cookies
  or trigger admin-bot actions.
- **SSTI (template injection):** test `{{7*7}}` / `${7*7}` / `#{7*7}`. Jinja2 →
  `{{ config }}`, `{{ ''.__class__.__mro__ }}` to reach RCE.
- **LFI/path traversal:** `?file=../../../../etc/passwd`, PHP wrappers
  `php://filter/convert.base64-encode/resource=index.php`.
- **SSRF:** make the server fetch `http://169.254.169.254/` (cloud metadata) or
  internal services.
- **Command injection:** `; id`, `| id`, `$(id)`, backticks in params that hit a shell.
- **IDOR / broken access control:** change an `id`/`user` param to reach other data.
- **Auth/JWT:** `alg:none`, weak HMAC secret (crack with `hashcat`), `kid` injection.
- **Deserialization:** PHP `unserialize`, Python `pickle`, Java gadget chains.

## Useful tricks
- Cookie/JWT tampering; inspect base64url segments of a JWT.
- `Content-Type` and verb tampering (GET↔POST, add `X-Forwarded-For`).
- Race conditions on state-changing endpoints.

## Tools
Burp Suite, ffuf/gobuster, sqlmap, nikto, whatweb, jwt_tool, wfuzz, curl,
Python requests, Chrome DevTools.
