# CTF Web — HTTP applications, clients, and authentication vulnerabilities

Scope: "HTTP-surface" vulnerabilities in web applications, APIs, browser clients, template engines, authentication and authorization, file upload, request smuggling, deserialization, prototype pollution, SSRF/XXE, plus the frontend and backend of Web3/smart contract challenges.

Out of scope: pure cryptographic primitives, native binary memory corruption, standalone executable reverse engineering, disk/memory forensics. If the hard part has moved to one of those directions, pivot to the corresponding direction (see "Related Directions").

> This file is the **local decision layer**: it references only **filenames** under the `ctf-web` skill and does not duplicate their contents. Moving or replacing the skill contents wholesale does not affect this file.
> Usage: read this file first to determine the entry point → then read only the one `.md` that matches; do not open several large files at once.

## File Index

| File | Contents | When to read |
|---|---|---|
| `sql-injection.md` | Authentication bypass, UNION extraction, filter bypass, second-order injection, truncation, race-condition leaks, password change via `ON DUPLICATE KEY UPDATE`, bypassing a WAF with `innodb_table_stats` | SQL errors appear, login behaves oddly, a parameter is controllable and the backend talks to a database |
| `server-side.md` | PHP type juggling, `php://filter` LFI, `str.format` traversal, SSTI (Jinja2/Twig/ERB/Mako/EJS/Vue/Smarty), SSRF basics, `hash_hmac` NULL | Template rendering, file read, a URL fetched by the server |
| `server-side-2.md` | XXE (basic/OOB/DOCX), `X-Forwarded-For` XML injection, PHP variable variables, predictable `uniqid` filenames, ordered regex replacement bypass, command injection (newline/blacklist/sendmail CGI), GraphQL injection | XML/JSON is parsed, filenames are random strings, blacklist-style filtering, GraphQL endpoints |
| `server-side-exec.md` | Ruby code injection and searching memory for the flag with `ObjectSpace`, Perl `open()` RCE, LaTeX injection, JS `eval` blacklist bypass, PHP `preg_replace /e`, backtick length limits, `assert()` string evaluation | Code/expression injection is confirmed and you need to actually execute it |
| `server-side-exec-2.md` | SQLi chunking, path parser discrepancies, polyglot webshell upload, wrapper abuse, filename injection, BMP pixel webshell + filename truncation | Upload/file write is restricted, or you need to chain several primitives |
| `server-side-deser.md` | Java/Python/PHP deserialization, race-condition exploitation, PHP `SoapClient` CRLF SSRF | Serialized data is present, cookies, `rO0`/`gAS`/`O:` signatures |
| `server-side-advanced.md` | Advanced SSRF/traversal/archive/parser/framework issues, Nginx alias traversal | Ordinary SSRF/traversal is blocked and you suspect framework or reverse-proxy layer differences |
| `server-side-advanced-2.md` | Docker API SSRF, Castor/XML, reading files via Apache expression, parser discrepancies, Windows path tricks, reading files with a malicious MySQL server | The target is a container/internal service, or you need a "fake server" to call back to |
| `server-side-advanced-3.md` | WAV polyglot + `.wave` bypass, multi-slash URL bypassing `startswith`, Xalan XSLT `math:random()` seed guessing, `SoapClient` UA CRLF smuggling, `gopher:///` hostless bypass, SSRF credential leakage | Classic 2018-era challenges, old frameworks, need for obscure bypasses |
| `server-side-advanced-4.md` | WeasyPrint SSRF/file read (CVE-2024-28184), MongoDB regex/`$where` blind injection, Pongo2 template injection, ZIP webshell, `basename()` bypass, wget CRLF→SMTP, Gopher→MySQL blind injection, React Server Components Flight RCE (CVE-2025-55182), intercepting AMQP/TLS with sslstrip+arpspoof, CairoSVG XXE | Modern dependency CVEs, PDF/export rendering, Mongo blind injection |
| `client-side.md` | XSS, CSRF, cache poisoning, DOM tricks, admin bot abuse, request smuggling, paywall bypass | Reflected/stored input, a bot visits, frontend routing |
| `client-side-advanced.md` | CSP bypass, Unicode tricks, XSSI, CSS exfiltration, browser normalization quirks, `postMessage` null origin bypass | Strict CSP, no JS execution environment, blind exfiltration needed |
| `auth-and-access.md` | Authentication/authorization bypass, hidden endpoints, IDOR, redirect chains, subdomain takeover, AI chatbot jailbreak (also: weak signature bypass, NoSQL injection, cookie manipulation, Host header bypass, reading `/proc/self/mem` via Range, forging a custom linear MAC, TOTP `srand(time())` recovery, HAProxy regex bypass via URL encoding, Express `%2F` middleware bypass, HTTP TRACE bypass, OAuth email subaddress bypass) | Login/registration/permission decisions behave oddly, an admin panel exists, session or signature is guessable |
| `auth-and-access-2.md` | `std::unordered_set` bucket collision bypass, `nodeprep.prepare` homoglyph username collision, SRP `A=0/A=N` bypass, privilege escalation via ArangoDB AQL MERGE | 2018-era challenges, unconventional authentication protocols, NoSQL graph databases |
| `auth-jwt.md` | JWT/JWE manipulation, weak keys, header injection, key confusion, replay, JWK/JKU injection, `kid` path traversal, balance replay, JWE forgery with an exposed public key, AES cookie length-field truncation + CRC32 swap | A three-part token appears in the `Authorization` header/cookie, or the balance/permissions live in the token |
| `auth-infra.md` | OAuth/OIDC, SAML, CORS misconfiguration, CI/CD secrets, IdP takeover, login page poisoning, credentials leaked in Git history, TeamCity REST RCE, lax Base64 decoding + parameter override to bypass signatures, hash length extension | Third-party login, SSO, CI/CD panels, suspicious signature validation |
| `node-and-prototype.md` | Prototype pollution, JS sandbox escape, Node.js attack chains | The backend is Node, input contains `__proto__`/`constructor`, a VM sandbox is present |
| `web3.md` | Solidity/blockchain: EIP-1967 proxies, ABI coder v1/v2 dirty-address bypass, stripping CBOR metadata to bypass codehash, non-standard calldata encoding, `delegatecall` storage-context abuse, Groth16 proof forgery, transient storage clearing conflicts, reentrancy | The target contains contract addresses, RPC, Foundry/web3.py toolchains |
| `cves.md` | Techniques keyed on CVEs, used to match banners, response headers, dependency leaks, version strings | You have version information and need to find an exploit by CVE |
| `field-notes.md` | Long-accumulated quick-reference index: SQLi/XSS/LFI/JWT/SSTI/SSRF/command injection/XXE/deserialization/race conditions/auth bypass/multi-stage chains | Web is confirmed and you need a broad quick reference (**read last, largest file**) |
| `python-requests.md` | Python Requests toolkit — "Burp Intruder in Python": Intruder-vs-Repeater workflow choice, Session scaffold, proxy/verify setup, concurrent brute force, encoding and error handling | You need high-volume or scripted request automation — fuzzing a parameter, brute-forcing a token, or replaying with variations — rather than clicking through a proxy |
| `pat-reference.md` | PayloadsAllTheThings reference index: how to use it, plus a category map from a local technique to the corresponding PAT path | You know the class of bug and want the matching payload catalogue from PayloadsAllTheThings |
| `ai-agentic-web.md` | Tool-argument injection, MCP tool abuse, browser-agent (WebVoyager-style) hijacking, agent memory/context poisoning, agent-as-SSRF, confused-deputy tool privilege diffusion | A chat/agent UI shows tool-call traces, the API lists `tool`/`action`/`mcp` endpoints, or a bot agent visits submitted URLs |

## Decision Tree

- Login/registration/permissions/session anomalies → `auth-and-access.md`; with a three-part token also add `auth-jwt.md`; third-party login/SSO involved → `auth-infra.md`; unconventional authentication protocols → `auth-and-access-2.md`
- Input is echoed back into the page or reaches the DOM → `client-side.md`; strict CSP or no JS environment → `client-side-advanced.md`
- An admin bot / a bot visits content I submit → the bot section of `client-side.md`
- A URL/parameter is fetched by the server (images, webhooks, exports, PDF) → SSRF in `server-side.md`; advanced bypasses → `server-side-advanced.md`; internal services/containers → `server-side-advanced-2.md`
- XML input or file parsing appears → XXE in `server-side-2.md`; SVG/PDF rendering → `server-side-advanced-4.md`
- Template syntax is controllable → SSTI in `server-side.md`; old frameworks (Xalan/Pongo2, etc.) → `server-side-advanced-3.md` or `server-side-advanced-4.md`
- Serialized data is present (`rO0`/`gAS`/PHP `O:`) → `server-side-deser.md`
- File upload exists but is blocked by type/extension → `server-side-exec-2.md` (polyglot) + `server-side-advanced-3.md` (polyglot)
- You can already execute expressions/code and need to get the results out → `server-side-exec.md`; restricted by length or character set → `server-side-exec-2.md`
- The backend is Node.js and input can reach object properties → `node-and-prototype.md`
- The target contains smart contracts/RPC → `web3.md`
- You only have a version number/banner → `cves.md`
- An LLM agent is in play (chat UI with tool-call echo, MCP/JSON-RPC endpoints, a bot that visits my content) → `ai-agentic-web.md`
- None of the above is clear and you need a broad quick reference → `field-notes.md`

## Common Entry Points

- JWT algorithm confusion (RS256→HS256) → `auth-jwt.md` "Algorithm Confusion"
- JWT `kid` path traversal to read `/dev/null` → empty HMAC key → `auth-jwt.md` "KID Path Traversal"
- SSRF against the internal network/cloud metadata → `server-side.md` "SSRF" + `server-side-advanced-2.md`
- XSS + strict CSP → `client-side-advanced.md`
- SQLi blocked by a WAF → the WAF section of `sql-injection.md` (including the `innodb_table_stats` bypass)
- File upload → RCE → `server-side-exec-2.md`
- Prototype pollution → RCE/sandbox escape → `node-and-prototype.md`
- Hidden endpoint enumeration → `auth-and-access.md` "Hidden API Endpoints"
- IDOR / privilege escalation → `auth-and-access.md` "IDOR on Unauthenticated WIP Endpoints"
- Subdomain takeover → `auth-and-access.md` "Subdomain Takeover"
- Request smuggling → `client-side.md` + `server-side-advanced-4.md`

## Related Directions

- Custom MACs, JWT math, RSA/ECC signatures → `ctf-crypto` (when routing does not cover it, use the `skill` tool to load `ctf-crypto`)
- Privilege escalation after getting a shell, memory corruption, seccomp escape → `ctf-pwn`
- Need to reverse obfuscated JS/WASM/binary payloads → `ctf-reverse`
- Analyzing logs, PCAP, web server forensics → `ctf-forensics`
- Need to first gather intelligence from public sources (domains, people, social media) → `ctf-osint`
- The "web" challenge is an LLM agent (tool calling, MCP, browser agent, persistent memory) — deep dive on the agentic endpoint itself: memory poisoning, MCP resource/tool abuse, multi-agent instruction smuggling, hallucinated tools → `ctf-ai-ml` `llm-attacks.md` (agentic/LLM endpoint attacks; load via the `skill` tool)

## Maintenance

- This file is associated with the `ctf-web` skill through a **directory of the same name**; after files are added/removed upstream, the `## File Index` table in this file must be updated in step, to avoid missing index entries or dangling references.
- File Index parsing convention: in the table under `## File Index`, the first column wraps the filename in backticks.
