# Install

Three ways to install, in order of preference. All of them end with the same state: the package is
resolvable from the profile and `dsh-ctf` is appended to that profile's `dsh.profile.bundles`.

## 0. Requirements

| Requirement | Notes |
|---|---|
| dsh `0.2.0-rc.2` or newer | `--dump-config`, patch layers and the `skills` provider seam |
| Node `>= 22.19` | the plugin itself has no dependencies |
| `pnpm` on `PATH` | required by `dsh plugin` only; manual install skips it |
| Python 3.12+ | only for `pytest` and the helper scripts |

## 1. From git (recommended)

```bash
dsh plugin --profile web add "git+ssh://git@github.com/Duststar0313/dsh-ctf.git"
```

Private repository, so the URL must be SSH (or a token-bearing HTTPS URL). After the command returns:

```bash
dsh web                       # restart the app
dsh --profile web --dump-config | grep -c 'id: preset-ctf'   # expect 1
```

### If `github.com:443` is blocked, or the repo is private

pnpm resolves git-hosted dependencies over **HTTPS** even when the specifier says `git+ssh://` — it has to
record a URL that works on every machine reading the lockfile. On a host that can only reach GitHub over
SSH, that rewrite fails with:

```
git ls-remote failed: fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

Teach git to substitute the transport locally (the recorded URL stays untouched):

```bash
git config --global url."git@github.com:".insteadOf "https://github.com/"
dsh plugin --profile web add "git+ssh://git@github.com/Duststar0313/dsh-ctf.git"
```

Verified end to end: `dsh plugin add` installs `dsh-ctf 0.1.0` into the profile, reconciles
`dsh.profile.bundles`, composes the layer, and the provider discovers all 13 skills from
`node_modules/dsh-ctf`. No build step runs — the package has no dependencies and no `prepare` script, so
pnpm's `allowBuilds` gate never applies.

## 2. From a local checkout

```bash
git clone git@github.com:Duststar0313/dsh-ctf.git ~/src/dsh-ctf
dsh plugin --profile web add ~/src/dsh-ctf
```

A local install is a `link:` dependency, so edits in the checkout are live after an app restart.

## 3. Manual (no pnpm)

`dsh plugin` is a convenience wrapper around three edits. Do them by hand when pnpm is unavailable:

```bash
PROFILE=~/.dsh/profiles/web
ln -s /path/to/dsh-ctf "$PROFILE/node_modules/dsh-ctf"
```

`$PROFILE/package.json`:

```json
{
  "dependencies": {
    "dsh-ctf": "link:/path/to/dsh-ctf"
  },
  "dsh": {
    "profile": {
      "bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app", "dsh-ctf"]
    }
  }
}
```

`bundles` is an ordered list; put `dsh-ctf` after the app bundle so its patch layer lands on top.

## Verify

```bash
node scripts/verify-plugin.mjs               # 60+ assertions, no harness
python3 -m pytest -q                         # skill corpus
dsh --profile web --dump-config | grep ctf   # composition
dsh --profile web --port 0 --no-open         # boot: no "did not activate" warning
```

## Default preset (optional)

New sessions default to `standard`. To default them to the CTF preset, add to the profile's
`cordis.patch.yml`:

```yaml
- id: agent-preset-registry
  name: '@deepseek-ai/dsh-agent-preset-registry'
  config:
    default: ctf
```

## Uninstall

```bash
dsh plugin --profile web remove dsh-ctf      # or: delete the entry + symlink by hand
rm -rf /path/to/dsh-ctf                      # only for a throwaway checkout
```

No skill content is copied into the profile, so removal leaves nothing behind. Your own skills under
`~/.dsh/skills` are untouched.
