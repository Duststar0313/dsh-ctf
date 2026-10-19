# Architecture

`dsh-ctf` is a *bundle*: a small npm package that contributes one patch layer to a profile and exports one
Cordis plugin. Nothing is forked, and no skill file is copied into the profile.

## Layers

```
@deepseek-ai/dsh-base            host services (skills registry, tools, sessions)
@deepseek-ai/dsh-web-app         the web app bundle (four shipped presets)
        ↓
dsh.profile.bundles: [ ..., "dsh-ctf" ]
        ↓
dsh-ctf/cordis.patch.yml         this package's layer: one inserted preset row
        ↓
~/.dsh/profiles/web/cordis.patch.yml    the user's own layer (wins)
```

A patch layer is an ordered YAML entry list. `insert:` appends rows; an `id:`-targeted entry overrides a
row in place. This package only ever inserts, so the host's `standard`/`ptc`/`minimal`/`cordis` presets and
the user's own overrides keep working.

## The `ctf` preset

`@deepseek-ai/dsh-agent-preset` turns a declarative row into a preset: an id, a label, an order, and a
`plugins:` list mounted as that preset's standing composition. Every row in the list is a normal loader
entry, so a preset is just a scoped mini-profile.

| Row | Role |
|---|---|
| `persona` | Chinese CTF persona; `ctf-routing` is the mandatory first step, `ctf-match-ops` only for live events |
| `agent-instructions` | loads `AGENTS.md` with a byte budget |
| `skill-filesystem` | the user's own skill roots: `~/.dsh/skills` (rank 400) |
| `ctf-skills` | **this package** — provider `ctf-bundle` (rank 600) over the bundled skill folders |
| `tool-skill` | the `skill` tool that loads a skill body on demand |
| `tool-bash` / `tool-pwsh` | platform-selected shell |
| `tool-fs` `tool-fs-search` `tool-jobs` `tool-web` `tool-ask-user` `tool-todo` `present` | recon and exploitation surface |
| `delegation` group | `subagent`, `subagent_fork`, `workflow` — parallel recon and long solvers |
| `compaction` group | basic compaction, `/compact`, tool-result pruner — the corpus is ~62k lines |

Because the preset's rows are ordinary loader entries, `ctf-skills` is resolved by name from the profile's
package graph. That is why the package needs no absolute path in any config file.

## The provider

`lib/index.js` exports `{ name, inject, apply }`. `inject: ['skills']` hands it the registry; `apply`
calls `ctx.skills.registerProvider(() => provider)` once during mount. The provider implements the whole
contract with two methods:

- `list({ cwd, signal })` — shallow-scans each root (`<root>/*/SKILL.md`), parses frontmatter, and returns
  candidates. Non-skill folders (`lib/`, `tests/`, `scripts/`, `node_modules/`) are skipped because they
  carry no `SKILL.md`, so there is no blocklist to maintain.
- `get(candidate, { signal })` — re-reads the file and returns the body plus metadata, so edits on disk are
  visible without re-registration.

Each candidate carries:

| Field | Value | Why |
|---|---|---|
| `source` | `bundled` | prompt-visible origin bucket |
| `rank` | `600` | `BUNDLED_SKILL_RANK`: a user copy at rank 400 wins a same-layer collision |
| `path` | `<skill>/SKILL.md` | absolute instruction file |
| `resourceBase` | `{ kind: 'directory', path: <skill> }` | the host renders it as "Base directory for this skill: …" so `routing/<direction>.md` links resolve |
| `locator` | `{ directory }` | opaque handle handed back to `get` |

Registry layering matters: providers registered inside a preset's standing mount land in that preset's
layer, and a read merges the global layer with the viewing scope's chain, nearest layer first. So the
preset's own skills shadow same-named skills registered globally.

## Why the plugin has no dependencies

A plugin installed into a profile's `node_modules` sits outside the dsh installation. Resolving a host
package from there depends on the profile resolver's fallback chain, which is version-sensitive. The
provider contract is small (`list` + `get`), so implementing it against `node:fs` and a restricted YAML
subset is cheaper — and more durable — than depending on
`@deepseek-ai/dsh-skill-filesystem`. `tests/test_plugin_provider.py` cross-checks every parse against
PyYAML, so the subset cannot silently drift.

## Self-checks

| Command | Covers |
|---|---|
| `node scripts/verify-plugin.mjs` | manifest, patch wiring, no absolute paths, provider registration, catalog, bodies, resource bases, config overrides |
| `python3 -m pytest -q` | frontmatter schema, cross-references, routing index, snippet hygiene, provider contract |
| `dsh --profile web --dump-config` | the layer composes in the real loader |
| boot without `did not activate` | every row imports and applies |
