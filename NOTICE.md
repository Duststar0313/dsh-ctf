# NOTICE

## This repository

The `dsh-ctf` plugin — `lib/index.js`, `cordis.patch.yml`, `scripts/verify-plugin.mjs`, the packaging,
the routing layer (`ctf-routing/`), `ctf-match-ops/`, `ctf-writeup/`, `solve-challenge/` and the
documentation — is MIT licensed, Copyright (c) 2026 dsh-ctf contributors.

## Third-party skill content

The direction libraries (`ctf-web/`, `ctf-pwn/`, `ctf-reverse/`, `ctf-crypto/`, `ctf-forensics/`,
`ctf-misc/`, `ctf-malware/`, `ctf-osint/`, `ctf-ai-ml/`) contain material derived from

> **ctf-skills** — <https://github.com/ljagiello/ctf-skills>
> MIT License, Copyright (c) 2026 Lukasz Jagiello

The upstream license text is reproduced verbatim in [`LICENSES/ctf-skills-MIT.txt`](LICENSES/ctf-skills-MIT.txt).

Local changes relative to upstream (all under the same MIT terms):

- added the routing layer, `ctf-match-ops`, `ctf-writeup` and the `solve-challenge` wiring;
- restored and expanded technique files that the local snapshot had trimmed;
- added `ctf-osint/china-sources.md` and time-sensitivity annotations in `ctf-malware`/`ctf-osint`;
- added the packaging, tests and CI in this repository.

## DeepSeek Harness

`dsh` itself is not vendored here. The patch layer targets public package names and the documented
`skills` provider seam; the host is MIT licensed, Copyright (c) 2026 DeepSeek.
