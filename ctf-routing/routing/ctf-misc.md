# CTF Misc — Cross-Category Catch-All

Scope: challenges where **no other direction fits** — encodings and esolangs, Python/Bash sandbox escapes, RF/SDR signals, DNS anomalies, game and custom-VM logic, non-memory-corruption Linux privilege escalation, and CTFd platform automation.

Out of scope: anything that fits web / pwn / reverse / forensics / crypto / malware / osint / ai-ml — **go through that direction's routing first** (see "Related Directions" at the end). This direction is a catch-all, not the default starting point.

> This file is the **local decision layer**: it references only **filenames** under the `ctf-misc` skill and does not duplicate their contents.
> Usage: first rule out the other directions using "Related Directions" at the end, then follow the decision tree below and read exactly **one** file.

## File Index

| File | Contents | When to read |
|---|---|---|
| `pyjails.md` | Python jail/sandbox escape, quine context detection, repunit factorization under a restricted character set, `func_globals` module-chain traversal, constructing numbers from restricted characters, class-attribute persistence, f-string config injection through stored eval, Python 3.12+/3.13+ jail surface (PEP 701 f-strings, free-threading, version identification) | Target is a Python interpreter sandbox (any 3.x — incl. 3.12+/3.13+/3.14, PEP 701 f-string injection, free-threaded builds) |
| `bashjails.md` | Bash jail/restricted-shell escape, `HISTFILE` file-read tricks, `bash -v` verbose mode, calling C libraries directly via `ctypes.sh` | Target is a restricted bash/shell |
| `encodings.md` | Encodings, QR codes, esolangs, UTF-16 tricks, BCD, multi-layer automatic decoding, QR reassembly with an index, multi-stage URL-encoding chains | The core of the challenge is encode/decode |
| `encodings-advanced.md` | Verilog/HDL, Gray-code cyclic encoding, RTF custom-tag extraction, SMS PDU decoding, multi-encoding ordering, UTF-9, pixel binary encoding, hex sudoku + QR stitching, TOPKEK, MaxiCode | The encodings above are not enough, or the encoding form is exotic |
| `rf-sdr.md` | RF/SDR/IQ signal processing (QAM-16, carrier recovery, timing synchronization) | IQ samples or a radio signal are provided |
| `dns.md` | DNS exploitation (ECS spoofing, NSEC traversal, IXFR, rebinding, tunneling) | The challenge revolves around DNS behaviour |
| `games-and-vms.md` | WASM patching, Roblox place reversing, PyInstaller, marshal analysis, Python-environment RCE, Z3 (including SAT over boolean-gate networks), K8s RBAC, floating-point precision exploitation, escaping a custom assembly sandbox via the Python MRO chain | Game-logic / custom-VM / sandbox challenges — read this first as the entry point |
| `games-and-vms-2.md` | Cookie-checkpoint game brute forcing, Flask cookie game-state leakage, WebSocket game manipulation, server-side-time-only validation bypass, De Bruijn sequences, Brainfuck instrumentation, WASM linear-memory manipulation, headless browser automation (Playwright/Puppeteer/Selenium, anti-bot bypass) | Search by symptom; challenge asks you to visit/automate a page or ships a headless-browser bot (no exploitation) → Headless Browser Automation |
| `games-and-vms-3.md` | `memfd_create` packed binaries, multi-stage encrypted games (HMAC commit-reveal + GF(256) Nim), ROM-swap state retention in emulators, Python marshal code injection, Benford's-law bypass, parallel-connection oracle relay, nonogram solving pipeline, 100 prisoners problem, emoji-identifier C-jail escape, BuildKit build-secret exploitation, Docker container escape, Levenshtein-distance oracle, type-coercion taint-analysis bypass, shredded-document pixel-edge reassembly | Search by symptom |
| `games-and-vms-4.md` | Part 4 (2018 era): XSLT as a Turing-complete VM, JS `MAX_SAFE_INTEGER` successor equality, binary-search oracle comparing only inside a DSL, scripting-engine timeout errors as blind SQLi, OEIS sequence lookup automation, QR reassembly from format-string constraints, Fibonacci via matrix exponentiation, Tribonacci frog-jump, Selenium+Tesseract dynamic CAPTCHA, Brainfuck→Piet multi-layer polyglot, bytebeat synthesizer code identification | Search by symptom |
| `linux-privesc.md` | Sudo wildcard argument injection (fnmatch), crafting a pcap for `sudoers.d`, monit confcheck process injection, Apache `-d` override, backup cronjob SUID, PostgreSQL `COPY TO PROGRAM` RCE, PostgreSQL backup credential extraction, NFS share exploitation, SSH Unix-socket tunneling, PaperCut privilege escalation, Squid proxy pivoting, resetting a Zabbix admin password via MySQL, WinSSHTerm credential decryption | A shell is already obtained and privilege escalation relies on **service/configuration errors** rather than memory corruption |
| `ctfd-navigation.md` | Browserless CTFd platform API operation: detection, token auth, challenge listing, file download, flag submission, scoreboard, hints, notifications, Python client class | Need scripted challenge fetching / flag submission |

## Decision Tree

1. **Rule out the other directions first** (this direction is the catch-all, see "Related Directions")
2. Python sandbox (any 3.x, incl. 3.12+/3.13+ interpreters) → `pyjails.md`; restricted bash/shell → `bashjails.md`
3. Core is encoding / multi-layer decoding → `encodings.md`; exotic encodings (HDL, Gray, PDU, MaxiCode, UTF-9) → `encodings-advanced.md`
4. Radio / IQ samples → `rf-sdr.md`
5. Anomalous DNS behaviour (ECS, NSEC, IXFR, rebinding, tunneling) → `dns.md`
6. Game logic, custom VM, emulator, sandbox escape → start with `games-and-vms.md`; if it misses, `grep` by symptom across `games-and-vms-2.md` through `games-and-vms-4.md`; pure page/browser automation to flag (headless bot, no exploitation) → `games-and-vms-2.md` Headless Browser Automation
7. A shell is already obtained and privilege escalation is needed **without memory corruption** → `linux-privesc.md` (if it involves kernel/heap exploitation → pivot to `ctf-pwn`)
8. Need bulk CTFd interaction → `ctfd-navigation.md`
9. Still stuck → treat the challenge's one-line description as keywords and `grep` the whole `ctf-misc` skill

## Common Entry Points

- Python escape under a restricted character set → `pyjails.md`
- `HISTFILE` file read / calling C libraries via `ctypes.sh` → `bashjails.md`
- Multi-layer or nested encoding auto-decode → `encodings.md`
- QR block reassembly → `encodings.md`
- QAM-16 demodulation and carrier recovery → `rf-sdr.md`
- DNS tunneling / rebinding / NSEC traversal → `dns.md`
- Z3 solving boolean-gate networks / SAT → `games-and-vms.md`
- WASM patching and linear-memory manipulation → `games-and-vms.md`, `games-and-vms-2.md`
- Docker container escape (no kernel exploit) → `games-and-vms-3.md`
- sudo wildcard injection / cron SUID / PostgreSQL RCE → `linux-privesc.md`
- Scripted CTFd flag submission → `ctfd-navigation.md`

## Related Directions

- HTTP apps, clients, authentication → `ctf-web`
- Memory corruption, heap, ROP, kernel exploitation → `ctf-pwn`
- Need to understand a binary/firmware/VM implementation first → `ctf-reverse`
- Disks, memory, PCAP, image/audio steganography, host artifacts → `ctf-forensics`
- Encryption, signatures, randomness, lattices and number theory → `ctf-crypto`
- Malicious samples, C2, encrypted traffic → `ctf-malware`
- Public-source intelligence and attribution → `ctf-osint`
- Models, weights, adversarial examples, LLM/prompt injection → `ctf-ai-ml`
- Need to produce a writeup → `ctf-writeup`; direction still unclear → `ctf-routing/routing/triage.md`

## Maintenance

- Linked to the `ctf-misc` skill by matching directory name; when files are added or removed upstream, the `## File Index` table in this file must be updated to match.
- **Important**: `games-and-vms.md` and `games-and-vms-2.md` through `games-and-vms-4.md` are **sharded by collection time** (including a 2018-era installment), not classified by topic. To find a specific technique, `grep` across the whole file family — do not guess by number.
- After changing a `SKILL.md` frontmatter, confirm the YAML is valid: invalid frontmatter makes dsh **silently ignore the entire skill**.
