---
name: ctf-routing
description: 'Sole entry point for CTF work: read routing/<direction>.md for the decision tree and file index, else fall back to the <direction> skill directly, then open only the named file. Start here for every challenge.'
whenToUse: 'Start of any CTF task, before choosing a direction. Always load this skill first; it is the only entry point.'
license: MIT
---

# CTF Routing — Entry Point

This skill is the **single entry point** for all CTF work. It indexes 12 skill directories (9 routable
directions + the `ctf-match-ops` competition-ops skill + the `ctf-writeup` meta skill + this routing
skill), ~62,000 lines of Markdown in total.
**Do not open files one by one** — go through the decision layer first.

> A 13th skill, `solve-challenge`, also ships in this library. It is **not** part of the routing
> architecture: it is the upstream standalone dispatcher, kept for hosts where `ctf-routing` is
> unavailable. When `ctf-routing` is loaded (the normal case), ignore `solve-challenge` — following both
> gives two competing entry points and its flat `/ctf-<category>` table bypasses the decision layer.

> **Path convention**: every relative path in this document is relative to **this skill's base directory**
> (dsh injects a `Base directory for this skill: …` line when the skill is loaded). The decision-layer
> files live under `<base>/routing/`. This skill therefore **does not depend on the current working
> directory** and works from any cwd when installed in the user-level skills directory.

## Workflow

1. **Identify the direction** from the goal, attachments and service the challenge provides.
2. **Read the decision layer**: `<this skill's base directory>/routing/<direction>.md`.
   It contains: scope, `## File Index` (file → contents → when to read), `## Decision Tree`,
   `## Common Entry Points`, `## Related Directions`.
   - If the direction is **not** yet clear, read `routing/triage.md` first — it covers recon,
     category identification, pivot strategy and flag formats.
3. **Fallback**: if `routing/<direction>.md` does not exist, load the `<direction>` skill directly with
   the `skill` tool and read its `SKILL.md`.
4. **Read only the matched file**: load the `<direction>` skill with the `skill` tool to obtain its base
   directory, then read `<that base directory>/<file>.md`.
   **Use grep to locate the section and read locally — do not load whole files.**

## Environment Setup

Tool installation lives in the installer and [README.md](../README.md), not in this skill:

```bash
bash <skills root>/scripts/install_ctf_tools.sh all
bash <skills root>/scripts/install_ctf_tools.sh python   # or: apt | brew | gems | go | manual
```

Each direction's `SKILL.md` also has a **Prerequisites** section listing the tools for that one
direction; the installer aggregates all of them. Pre-installing before a competition is recommended.

## Platform Automation (CTFd)

If the challenge platform runs CTFd, drive it through the REST API instead of a browser. Read
`ctf-misc/ctfd-navigation.md` (detection, token auth, challenge listing, file download, flag
submission, scoreboard, hints, notifications, Python client). **Ask the user for their API token** —
it is not provided by default.

## Directions

| direction | Contents | routing |
|---|---|---|
| `ctf-web` | HTTP apps, clients, authentication (22 files) | ✅ `routing/ctf-web.md` |
| `ctf-pwn` | Binary exploitation (18 files) | ✅ `routing/ctf-pwn.md` |
| `ctf-reverse` | Reverse engineering (19 files) | ✅ `routing/ctf-reverse.md` |
| `ctf-crypto` | Cryptography and mathematics (19 files) | ✅ `routing/ctf-crypto.md` |
| `ctf-forensics` | Forensics, steganography, signals (16 files) | ✅ `routing/ctf-forensics.md` |
| `ctf-misc` | Cross-category catch-all (12 files) | ✅ `routing/ctf-misc.md` |
| `ctf-malware` | Malicious samples and traffic (3 files) | ✅ `routing/ctf-malware.md` |
| `ctf-osint` | Public-source intelligence (4 files) | ✅ `routing/ctf-osint.md` |
| `ctf-ai-ml` | AI/ML attacks (3 files) | ✅ `routing/ctf-ai-ml.md` |
| `ctf-writeup` | Meta skill: write the writeup | fallback to `SKILL.md` |
| `ctf-match-ops` | Meta skill: run a whole live event (triage, timeboxing, flag discipline) | fallback to `SKILL.md` |
| `ctf-routing` | This skill: triage + decision layer | ✅ `routing/triage.md` |

**Writeups** are always handed off to `ctf-writeup` — this skill does not duplicate that meta skill.

**Whole live events** are handled by `ctf-match-ops`: load it *in addition to* this skill when a scoreboard
and a clock are in play, so triage and timeboxing sit above per-challenge solving.

## Maintenance

- The `## File Index` table in `routing/<direction>.md` must list **every** content file in the
  `<direction>` skill (excluding that skill's own `SKILL.md`), and must not reference files that do not
  exist — the two sides correspond by **filename**.
- Adding a direction takes three steps: create `<direction>/SKILL.md` → create
  `routing/<direction>.md` (scope / file index / decision tree / common entry points / related
  directions) → add a row to the Directions table above.
- Content files live under `<direction>/`; local routing judgement lives under `routing/`. The two are
  linked by matching names.
- After editing a `SKILL.md` frontmatter, confirm the YAML is valid: invalid frontmatter makes dsh
  **silently ignore the entire skill**.
