#!/usr/bin/env node
/**
 * Self-check for the `dsh-ctf` plugin, runnable on any machine with Node.
 *
 * It exercises the real runtime surface — the Cordis plugin entry, the skill
 * provider and the patch manifest — without booting a harness:
 *
 *   1. `package.json` declares the bundle patch and it exists.
 *   2. The patch is a YAML entry list whose rows target real packages and whose
 *      `ctf-skills` row points at this package.
 *   3. `apply()` registers exactly one provider under the configured name.
 *   4. `list()` returns the expected skill set, with resource bases that exist.
 *   5. `get()` returns a body without frontmatter, for every skill.
 *
 * Usage: `node scripts/verify-plugin.mjs [--quiet]`
 */

import { readFile, readdir, stat } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const QUIET = process.argv.includes('--quiet')

/** Every skill this package is expected to ship, plus the directions it routes to. */
const EXPECTED_SKILLS = [
  'ctf-ai-ml',
  'ctf-crypto',
  'ctf-forensics',
  'ctf-malware',
  'ctf-match-ops',
  'ctf-misc',
  'ctf-osint',
  'ctf-pwn',
  'ctf-reverse',
  'ctf-routing',
  'ctf-web',
  'ctf-writeup',
  'solve-challenge',
]

const failures = []

/**
 * Record one assertion.
 * @param label - what was checked.
 * @param condition - whether it held.
 * @param detail - extra context printed on failure.
 */
function check(label, condition, detail = '') {
  if (condition) {
    if (!QUIET) console.log(`  ok   ${label}`)
    return true
  }
  failures.push(`${label}${detail === '' ? '' : ` — ${detail}`}`)
  console.error(`  FAIL ${label}${detail === '' ? '' : ` — ${detail}`}`)
  return false
}

/**
 * Read and parse a JSON file.
 * @param path - absolute path.
 * @returns the parsed value.
 */
async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'))
}

/** Validate the package manifest and its patch wiring. */
async function checkManifest() {
  console.log('manifest')
  const pkg = await readJson(join(ROOT, 'package.json'))
  check('package name is dsh-ctf', pkg.name === 'dsh-ctf', `got ${String(pkg.name)}`)
  check('package is ESM', pkg.type === 'module')
  check('main entry is lib/index.js', pkg.main === 'lib/index.js')
  check('exports the plugin entry', pkg.exports?.['.'] === './lib/index.js')
  check('dsh.bundle.patch is declared', pkg.dsh?.bundle?.patch === './cordis.patch.yml')
  check('no runtime dependencies', Object.keys(pkg.dependencies ?? {}).length === 0)

  const patchPath = join(ROOT, 'cordis.patch.yml')
  const patch = await readFile(patchPath, 'utf8')
  const patchBody = patch
    .split('\n')
    .filter((line) => !line.trimStart().startsWith('#'))
    .join('\n')
    .trimStart()
  check('patch exists and is an entry list', patchBody.startsWith('- insert:'))

  // The patch is YAML; this script stays dependency-free, so validate the
  // structural facts the harness relies on rather than re-implementing YAML.
  const hostRows = [...patch.matchAll(/name:\s*'(@deepseek-ai\/[^']+)'/g)].map((match) => match[1])
  check('patch mounts host packages', hostRows.length > 5, `found ${hostRows.length}`)
  check('patch mounts this package', /name:\s*'dsh-ctf'/.test(patch))
  check('patch declares the ctf preset', /id:\s*preset-ctf/.test(patch) && /id:\s*ctf\b/.test(patch))
  check('patch carries no absolute /root path', !patch.includes('/root/'))
  check('patch carries no ~/.dsh/skills path', !patch.includes('.dsh/skills'))

  const compat = await readJson(join(ROOT, 'compatibility.json'))
  check('compatibility lists the host', Array.isArray(compat.supportedHosts) && compat.supportedHosts.length > 0)
}

/** Exercise the plugin entry exactly the way the harness does. */
async function checkProvider() {
  console.log('provider')
  const module = await import(join(ROOT, 'lib/index.js'))
  check('exports a plugin name', module.name === 'dsh-ctf', `got ${String(module.name)}`)
  check('injects the skills registry', Array.isArray(module.inject) && module.inject.includes('skills'))

  /** @type {Array<{name: string, provider: unknown}>} */
  const registered = []
  const ctx = {
    skills: {
      registerProvider(factory) {
        const provider = factory({ signal: new AbortController().signal, invalidate() {} })
        registered.push({ name: provider.name, provider })
        return () => {}
      },
    },
  }
  module.apply(ctx, {})
  check('registers exactly one provider', registered.length === 1, `got ${registered.length}`)
  check('provider name is ctf-bundle', registered[0]?.name === 'ctf-bundle', `got ${String(registered[0]?.name)}`)

  const provider = registered[0]?.provider
  const candidates = await provider.list({})
  const names = candidates.map((candidate) => candidate.name)
  check(
    'discovers the full skill set',
    EXPECTED_SKILLS.every((skill) => names.includes(skill)),
    `missing ${EXPECTED_SKILLS.filter((skill) => !names.includes(skill)).join(', ') || 'none'}`,
  )
  check('discovers no extra skills', names.length === EXPECTED_SKILLS.length, `got ${names.join(', ')}`)
  check('catalog is sorted by name', names.join(',') === [...names].sort().join(','))

  for (const candidate of candidates) {
    const label = `skill ${candidate.name}`
    check(`${label} has a description`, typeof candidate.description === 'string' && candidate.description.length > 0)
    check(`${label} has whenToUse`, typeof candidate.whenToUse === 'string' && candidate.whenToUse.length > 0)
    check(`${label} exposes a directory resource base`, candidate.resourceBase?.kind === 'directory')
    check(`${label} ranks below user skills`, candidate.rank === 600, `got ${String(candidate.rank)}`)
    const base = candidate.resourceBase?.path
    const baseOk = typeof base === 'string' && (await stat(base).catch(() => undefined))?.isDirectory() === true
    check(`${label} resource base exists`, baseOk, String(base))
    const body = await provider.get(candidate, {})
    check(`${label} loads a body`, typeof body?.content === 'string' && body.content.length > 0)
    check(`${label} body excludes frontmatter`, body?.content?.startsWith('---') !== true)
    check(`${label} keeps its path`, typeof body?.path === 'string' && body.path.endsWith('SKILL.md'))
  }

  // Extra roots are additive and keep package skills reachable.
  const extra = module.normalizeConfig({ skillDirs: ['/nonexistent-root'], providerName: 'custom-name' })
  check('config overrides the provider name', extra.providerName === 'custom-name')
  check('config keeps the package root first', extra.roots[0] === ROOT, `got ${extra.roots[0]}`)

  // A folder without SKILL.md is not a skill.
  const entries = await readdir(ROOT, { withFileTypes: true })
  const plainDirs = entries.filter((entry) => entry.isDirectory() && !EXPECTED_SKILLS.includes(entry.name))
  check('non-skill folders exist to prove filtering', plainDirs.length > 0, `dirs: ${plainDirs.map((d) => d.name).join(', ')}`)
  check(
    'non-skill folders are not listed',
    plainDirs.every((entry) => !names.includes(entry.name)),
  )
}

/** Report and exit. */
async function main() {
  await checkManifest()
  await checkProvider()
  const total = failures.length
  console.log(total === 0 ? '\nverify-plugin: all checks passed' : `\nverify-plugin: ${total} check(s) failed`)
  process.exit(total === 0 ? 0 : 1)
}

await main()
