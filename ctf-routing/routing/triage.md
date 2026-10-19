# CTF Triage — Recon, Categorization, Pivoting and Flags

Scope: the generic front end of **any** challenge — used when the direction is not yet obvious. This is the
shared first pass before a direction is chosen.

Out of scope: direction-specific technique. Once the direction is known, go to `routing/<direction>.md` and
read only the file named there.

> This file is the **triage layer** of `ctf-routing`. It complements `routing/<direction>.md`, which is the
> **decision layer** for a specific direction. Use this file when you cannot yet name the direction.

## Step 0 — Identify the platform

If the CTF platform URL is known, check whether it runs CTFd and switch to API-driven navigation:

```bash
curl -s "$CTF_URL/api/v1/" | head -5      # CTFd exposes a REST/Swagger API here
curl -s "$CTF_URL" | grep -oE '/themes/core/'
```

If CTFd is detected, **ask the user for their API token** (generated from CTFd Settings > Access Tokens) —
it is not provided by default. Then read `ctf-misc/ctfd-navigation.md` for the full API reference, the
Python client class, hints, notifications and troubleshooting.

```bash
export CTF_URL="https://ctf.example.com"
export CTF_TOKEN="ctfd_..."   # ask the user for this
```

## Step 1 — Recon

1. **Explore the files** — list the challenge directory and run `file *` on everything.
2. **Triage binaries** — `strings`, `xxd | head`, `binwalk`, `checksec` on binaries.
3. **Fetch the links** — if the challenge mentions URLs, fetch them FIRST for context.
4. **Connect** — try the remote service (`nc`) to understand what it expects.
5. **Read the hints** — the description, filenames and comments often contain clues.

## Step 2 — Categorize

Determine the primary category, then route to the matching direction.

**By file type:**

| Artifact | Direction |
|---|---|
| `.pcap`, `.pcapng`, `.evtx`, `.raw`, `.dd`, `.E01` | `ctf-forensics` |
| `.elf`, `.exe`, `.so`, `.dll`, or a binary with no extension | `ctf-reverse` or `ctf-pwn` — if a remote service is provided, likely `ctf-pwn` |
| `.py`, `.sage`, `.txt` containing numbers | `ctf-crypto` |
| `.apk`, `.wasm`, `.pyc` | `ctf-reverse` |
| `.pt`, `.pth`, `.safetensors`, `.onnx`, `.bin` model weights, or a notebook / inference API / LLM endpoint | `ctf-ai-ml` |
| A web URL, or source with HTML/JS/PHP/templates | `ctf-web` |
| Images, audio, PDFs with no obvious content | `ctf-forensics` (steganography) |

> `.bin` is ambiguous — it also appears for firmware and raw disk images. Run `file` first: model weights
> are typically huge, start with a magic like `\x93NUMPY`/`PK`, or sit next to a `config.json`.

**By description keywords:**

| Keywords | Direction |
|---|---|
| "buffer overflow", "ROP", "shellcode", "libc", "heap" | `ctf-pwn` |
| "RSA", "AES", "cipher", "encrypt", "prime", "modulus", "lattice", "LWE", "GCM" | `ctf-crypto` |
| "XSS", "SQL", "injection", "cookie", "JWT", "SSRF" | `ctf-web` |
| "disk image", "memory dump", "packet capture", "registry", "power trace", "side-channel", "spectrogram", "audio tracks", "MKV" | `ctf-forensics` |
| "find", "locate", "identify", "who", "where" | `ctf-osint` |
| "obfuscated", "packed", "C2", "malware", "beacon" | `ctf-malware` |
| "model", "weights", "adversarial", "prompt injection", "LoRA", "embedding", "jailbreak", "classifier" | `ctf-ai-ml` |
| "jail", "sandbox", "escape", "encoding", "signal", "game", "Nim", "commitment", "Gray code" | `ctf-misc` |

**By service behaviour:**

| Behaviour | Direction |
|---|---|
| Interactive prompt, crashes on long input | `ctf-pwn` |
| HTTP service | `ctf-web` |
| netcat with math/crypto puzzles | `ctf-crypto` |
| netcat with a restricted shell or eval | `ctf-misc` (jail) |

## Step 3 — Read the direction decision layer

Once the direction is identified, read `<ctf-routing base>/routing/<direction>.md`, then read **only** the
single file it names:

| Direction | Decision layer | Scope |
|---|---|---|
| Web | `routing/ctf-web.md` | XSS, SQLi, SSTI, SSRF, JWT, file uploads, prototype pollution |
| Pwn | `routing/ctf-pwn.md` | Buffer overflow, format string, heap, ROP, sandbox escape |
| Crypto | `routing/ctf-crypto.md` | RSA, AES, ECC, PRNG, ZKP, classical ciphers |
| Reverse | `routing/ctf-reverse.md` | Binary analysis, game clients, VMs, obfuscated code |
| Forensics | `routing/ctf-forensics.md` | Disk images, memory dumps, event logs, stego, network captures |
| OSINT | `routing/ctf-osint.md` | Social media, geolocation, DNS, public records |
| Malware | `routing/ctf-malware.md` | Obfuscated scripts, C2 traffic, PE/.NET analysis |
| AI/ML | `routing/ctf-ai-ml.md` | Adversarial examples, model extraction, prompt injection, LoRA |
| Misc | `routing/ctf-misc.md` | Jails, encodings, RF/SDR, esoteric languages, constraint solving |

## Step 4 — Pivot when stuck

1. **Re-examine your assumptions** — is this really the category you think? A "web" challenge may need
   crypto for JWT forgery; a "forensics" PCAP may contain a pwn exploit to replay.
2. **Try a second direction's decision layer** — many challenges span multiple categories.
3. **Look for what you missed** — hidden files, alternate ports, response headers, source comments, image metadata.
4. **Simplify** — if the exploit is too complex, check for a simpler path (default credentials, a known CVE, a logic bug).
5. **Check edge cases** — off-by-one, race conditions, integer overflow, encoding mismatches.

**Common multi-category patterns:**

- Forensics + Crypto: encrypted data inside a PCAP/disk image, needs crypto to decrypt
- Web + Reverse: WASM or obfuscated JS in a web challenge
- Web + Crypto: JWT forgery, custom MAC/signature schemes
- Reverse + Pwn: reverse the binary first, then exploit the vulnerability
- Forensics + OSINT: recover data from a dump, then trace it through public sources
- Misc + Crypto: a jail escape requires building crypto primitives under constraints
- OSINT + Stego: social-media posts using unicode homoglyph steganography (Cyrillic lookalikes encode bits)
- Web + Forensics: paywall bypass (curl reveals content hidden by CSS overlays)
- Misc + Crypto + Game Theory: multi-phase interactive challenges with AES decryption → HMAC commitment → combinatorial game solving (GF(256) Nim)
- Crypto + Geometry + Lattice: multi-layer challenges progressing from spatial reconstruction → subspace recovery → LWE solving → AES-GCM decryption
- Forensics + Signal Processing: power traces / side-channel analysis requiring statistical analysis of measurement data
- Forensics + Network + Encoding: timing-based encoding in a PCAP (inter-packet intervals encode binary data)

## Step 5 — Write up

After solving the challenge, hand off to the `ctf-writeup` skill to generate a standardized
submission-style writeup — concise, reproducible and ready for organizers or teammates to validate.

## Flag formats

Flags vary by CTF. Common formats:

- `flag{...}`, `FLAG{...}`, `CTF{...}`, `TEAM{...}`
- Custom prefixes: check the challenge description or the CTF rules for the format
  (for example `ENO{...}`, `HTB{...}`, `picoCTF{...}`)
- Sometimes just a plaintext string with no wrapper

**Validation rule (important):**

- If you find multiple flag-like strings, treat them as candidates and validate before finalizing.
- Prefer the token tied to the intended artifact/workflow, not random metadata noise or an obvious decoy.
- Do a corpus-wide uniqueness check and include the source file/path when reporting.

```bash
# Search for common flag patterns in files.
# The prefix list is deliberately broad: a narrow list silently misses formats
# the challenge actually uses (e.g. TEAM{...} is documented above yet was not
# matched by an earlier, shorter pattern). Add the event's own prefix when known.
grep -rniE '[A-Za-z0-9_]{2,20}\{[^}]{4,80}\}' . | grep -viE '\.(png|jpg|jpeg|gif|pdf|zip|gz|so|dll):'
# Search inside binary/memory output
strings output.bin | grep -iE '\{.*\}'
```

## Quick reference

```bash
# Recon
file *                                    # Identify file types
strings binary | grep -i flag             # Quick string search
xxd binary | head -20                     # Hex dump header
binwalk -e firmware.bin                   # Extract embedded files
checksec --file=binary                    # Check binary protections

# Connect
nc host port                              # Connect to the challenge
echo -e "answer1\nanswer2" | nc host port # Scripted input
curl -v http://host:port/                 # HTTP recon
```

```python
# Python exploit template
from pwn import *
r = remote('host', port)
r.interactive()
```

## Related Directions

All nine routable directions are listed in the table in Step 3. This file is the shared entry to them; it
holds no direction-specific technique of its own.

## Maintenance

- Keep the Step 3 table in sync with the rows of the Directions table in `SKILL.md`.
- This file is intentionally direction-agnostic: add technique here only if it applies to **every**
  direction. Direction-specific judgement belongs in `routing/<direction>.md`.
- After changing a `SKILL.md` frontmatter, confirm the YAML is valid: invalid frontmatter makes dsh
  **silently ignore the entire skill**.
