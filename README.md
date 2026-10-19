# dsh-ctf

CTF capability for [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — packaged as one
installable plugin.

`dsh plugin --profile web add <this package>` adds:

- a **`ctf` agent preset** ("CTF 解题"): persona, tool surface, delegation and compaction wiring;
- **13 skills**: the `ctf-routing` entry point, nine direction libraries, `ctf-match-ops` (live-event
  operations) and `ctf-writeup`, plus the standalone `solve-challenge` dispatcher;
- **`scripts/install_ctf_tools.sh`**, one installer for every prerequisite the skills mention.

Nothing is forked: the plugin is a patch layer plus a `skills` provider, and it resolves its own files at
runtime, so it works from any profile directory, on any machine, without hardcoded paths.

## Install

```bash
# from git (SSH; the repository is private)
dsh plugin --profile web add "git+ssh://git@github.com/Duststar0313/dsh-ctf.git"

# from a local checkout
dsh plugin --profile web add /path/to/dsh-ctf
```

Restart the app (`dsh web`). The preset list now offers **CTF 解题**.

Optional — make it the default preset for new sessions, in the profile's `cordis.patch.yml`:

```yaml
- id: agent-preset-registry
  name: '@deepseek-ai/dsh-agent-preset-registry'
  config:
    default: ctf
```

## Verify an installation

```bash
node scripts/verify-plugin.mjs          # provider + manifest self-check, no harness needed
python3 -m pytest -q                    # skill corpus tests (links, frontmatter, routing index)

dsh --profile web --dump-config | grep -n ctf      # the bundle layer is composed
```

A boot with a broken row prints `warning: 1 entry did not activate`; a working installation boots with no
such warning.

## Use

Open the web UI, create a session, pick **CTF 解题**, then hand over a challenge (a URL, an archive, a
binary, or an event with a scoreboard). The preset's persona makes `ctf-routing` the mandatory first step
and keeps the nine direction libraries behind that router.

Toolchain, before or during an event:

```bash
bash scripts/install_ctf_tools.sh --verify   # present vs missing, installs nothing
bash scripts/install_ctf_tools.sh all        # everything applicable to this platform
bash scripts/install_ctf_tools.sh crypto     # one direction only
```

## What is in the box

| Path | Purpose |
|---|---|
| `cordis.patch.yml` | Bundle layer: inserts the `ctf` preset (persona, tools, delegation, compaction) |
| `lib/index.js` | The whole runtime: a dependency-free Cordis plugin registering provider `ctf-bundle` |
| `ctf-routing/` | Sole entry point: `routing/<direction>.md` decision layer + `routing/triage.md` |
| `ctf-web/` `ctf-pwn/` `ctf-reverse/` `ctf-crypto/` `ctf-forensics/` `ctf-misc/` `ctf-malware/` `ctf-osint/` `ctf-ai-ml/` | Direction content libraries (technique notes, scripts) |
| `ctf-match-ops/` `ctf-writeup/` | Live-event operations; submission-style writeups |
| `solve-challenge/` | Upstream standalone dispatcher (kept for other hosts) |
| `scripts/` | Toolchain installer, catalog generator, security auditor, verify script |
| `tests/` | Corpus tests: frontmatter, cross-references, routing index, snippets, provider contract |
| `docs/` | [Install](docs/INSTALL.md), [architecture](docs/ARCHITECTURE.md), [AGENTS.md snippet](docs/agents-md-snippet.md) |

## Design notes

- **No hardcoded paths.** The provider resolves the package root with `import.meta.url`, so the same
  package works from `~/.dsh/profiles/web/node_modules` or a linked checkout.
- **No runtime dependencies.** `lib/index.js` imports `node:` builtins only; the provider contract is
  `list` + `get`, so no host package has to be resolvable from the plugin.
- **Rank 600 (`bundled`).** A user copy of a skill under `~/.dsh/skills` (rank 400) still wins a name
  collision inside the same layer. If you previously synced the skills by hand, remove that copy to see
  the packaged version.
- **`resourceBase`.** Each skill advertises its directory, so the host can tell the model "Base directory
  for this skill: …" and relative links inside a `SKILL.md` keep resolving.
- **Patch layers, not forks.** `insert:` only ever adds a row; the shipped `standard`/`ptc`/`minimal`/
  `cordis` presets are untouched.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `warning: N entry did not activate` | The package is not resolvable from the profile — reinstall with `dsh plugin`, check `node_modules/dsh-ctf` |
| `a skill provider named "ctf-bundle" is already registered` | Two copies mounted in one scope; keep one, or set `providerName` in the `ctf-skills` row |
| Skills show stale text | An older copy wins in `~/.dsh/skills` (rank 400) — delete it |
| `spawn pnpm ENOENT` | `dsh plugin` needs pnpm on `PATH` |
| `could not read Username for 'https://github.com'` | pnpm resolves git dependencies over HTTPS even for a `git+ssh://` specifier — add `git config --global url."git@github.com:".insteadOf "https://github.com/"`, see [install from git](docs/INSTALL.md#1-from-git-recommended) |
| No **CTF 解题** in the preset list | The bundle is not in `dsh.profile.bundles`; restart the app after installing |

## Credits and license

- Plugin code, routing layer, `ctf-match-ops`, `ctf-writeup`, `solve-challenge` wiring: MIT, this
  repository.
- Skill content is derived from [`ljagiello/ctf-skills`](https://github.com/ljagiello/ctf-skills)
  (MIT, Copyright (c) 2026 Lukasz Jagiello), extended locally — see [NOTICE.md](NOTICE.md).

MIT. See [LICENSE](LICENSE).
