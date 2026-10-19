/**
 * dsh-ctf — ship the CTF skill library to DeepSeek Harness as a skill provider.
 *
 * This module is the whole runtime: a dependency-free Cordis plugin that
 * registers one `skills` provider reading `SKILL.md` folders inside this
 * package. It imports nothing outside `node:` builtins on purpose — a plugin
 * installed into a profile's `node_modules` must not depend on host packages
 * being resolvable, and the provider contract in
 * `@deepseek-ai/dsh-skill` is small enough (list + get) to implement directly.
 *
 * Contract notes (see `@deepseek-ai/dsh-skill/lib/types/index.d.ts`):
 *  - `list()` returns candidates; `rank` resolves duplicate names across
 *    providers (lower wins), and `resourceBase` is what the host renders to the
 *    model as "Base directory for this skill: …" so relative links inside a
 *    SKILL.md keep working.
 *  - `get()` re-reads the file, so edits on disk need no re-registration.
 *  - provider names are unique per registry layer; this one is `ctf-bundle`.
 *
 * @module dsh-ctf
 */

import { readdir, readFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Package root — the directory holding `lib/`, the skill folders and README. */
const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')

/** Instruction file every skill folder must carry. */
const SKILL_FILE = 'SKILL.md'

/** Default provider name; unique per registry layer. */
const DEFAULT_PROVIDER_NAME = 'ctf-bundle'

/** Prompt-visible origin bucket. Lower ranks win duplicate names. */
const SOURCE = 'bundled'

/** Rank 600 matches `BUNDLED_SKILL_RANK`: a user copy under ~/.dsh/skills (400) still wins. */
const RANK = 600

/**
 * The skill-name grammar the host validates candidates against, mirrored here so
 * a malformed folder is skipped instead of crashing discovery.
 */
const SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export const name = 'dsh-ctf'

/** The plugin contributes a skill provider, so it needs the registry. */
export const inject = ['skills']

/**
 * Register the bundled skill provider.
 * @param ctx - Cordis context carrying the `skills` service.
 * @param config - optional plugin config: `skillDirs` (extra roots) and `providerName`.
 */
export function apply(ctx, config = {}) {
  const provider = createSkillProvider(normalizeConfig(config))
  ctx.skills.registerProvider(() => provider)
}

/**
 * Normalize plugin config into provider options.
 * @param config - raw `config:` block from the patch row.
 * @returns roots in scan order plus the provider name.
 */
export function normalizeConfig(config = {}) {
  const extra = Array.isArray(config?.skillDirs) ? config.skillDirs : []
  const roots = [PACKAGE_ROOT, ...extra].filter((value) => typeof value === 'string' && value !== '')
  const providerName =
    typeof config?.providerName === 'string' && config.providerName !== ''
      ? config.providerName
      : DEFAULT_PROVIDER_NAME
  return { roots: [...new Set(roots)], providerName }
}

/**
 * Build the provider object handed to `ctx.skills.registerProvider()`.
 *
 * Discovery is a shallow scan: every direct child folder of a root that carries
 * a readable `SKILL.md` is a skill, everything else is ignored. That keeps
 * `lib/`, `tests/`, `scripts/` and `node_modules/` out without a blocklist.
 *
 * @param options - `{ roots, providerName }` from {@link normalizeConfig}.
 * @returns a provider with `name`, `list` and `get`.
 */
export function createSkillProvider({ roots, providerName }) {
  /**
   * Read and parse one skill folder.
   * @param directory - absolute skill folder.
   * @returns the parsed record, or `undefined` when this folder is not a skill.
   */
  async function loadFolder(directory) {
    let text
    try {
      text = await readFile(join(directory, SKILL_FILE), 'utf8')
    } catch {
      return undefined
    }
    const parsed = parseSkillFile(text)
    if (parsed === undefined) return undefined
    const { data, content } = parsed
    if (typeof data.name !== 'string' || !SKILL_NAME.test(data.name)) return undefined
    if (typeof data.description !== 'string' || data.description === '') return undefined
    return { directory, data, content }
  }

  /**
   * Summarize one parsed record for the catalog.
   * @param record - output of {@link loadFolder}.
   * @returns a `SkillCandidate`-shaped object.
   */
  function toCandidate({ directory, data }) {
    return {
      name: data.name,
      description: data.description,
      ...(typeof data.whenToUse === 'string' && data.whenToUse !== '' ? { whenToUse: data.whenToUse } : {}),
      invocation: invocationPolicy(data),
      source: SOURCE,
      provider: providerName,
      rank: RANK,
      path: join(directory, SKILL_FILE),
      resourceBase: { kind: 'directory', path: directory },
      locator: { directory },
      ...(isRecord(data.metadata) ? { metadata: data.metadata } : {}),
    }
  }

  return {
    name: providerName,

    /**
     * Discover every skill folder under the configured roots.
     * @param options - lookup options; `signal` aborts discovery.
     * @returns candidates sorted by name, first root wins a duplicate name.
     */
    async list(options = {}) {
      const seen = new Set()
      const candidates = []
      for (const root of roots) {
        let entries
        try {
          entries = await readdir(root, { withFileTypes: true })
        } catch {
          continue
        }
        for (const entry of entries) {
          if (!entry.isDirectory() && !entry.isSymbolicLink()) continue
          throwIfAborted(options.signal)
          const record = await loadFolder(join(root, entry.name))
          if (record === undefined) continue
          if (seen.has(record.data.name)) continue
          seen.add(record.data.name)
          candidates.push(toCandidate(record))
        }
      }
      return candidates.sort((left, right) => left.name.localeCompare(right.name))
    },

    /**
     * Load one skill body for a previously listed candidate.
     * @param candidate - a candidate produced by {@link list}.
     * @param options - lookup options; `signal` aborts the read.
     * @returns the full definition, or `undefined` when the folder disappeared.
     */
    async get(candidate, options = {}) {
      throwIfAborted(options.signal)
      const directory = candidate?.locator?.directory
      if (typeof directory !== 'string') return undefined
      const record = await loadFolder(directory)
      if (record === undefined) return undefined
      const summary = toCandidate(record)
      return {
        name: summary.name,
        description: summary.description,
        ...(summary.whenToUse === undefined ? {} : { whenToUse: summary.whenToUse }),
        invocation: summary.invocation,
        source: summary.source,
        provider: summary.provider,
        path: summary.path,
        resourceBase: summary.resourceBase,
        ...(summary.metadata === undefined ? {} : { metadata: summary.metadata }),
        content: record.content,
      }
    },
  }
}

/**
 * Split a SKILL.md into frontmatter data and body.
 *
 * The corpus uses a deliberately small YAML subset — `name`, `description`,
 * `whenToUse`, `license` — with single-quoted or plain scalars. Supporting that
 * subset keeps the plugin dependency-free; `tests/test_plugin_provider.py`
 * cross-checks every parse against a real YAML parser.
 *
 * @param text - full file contents.
 * @returns `{ data, content }`, or `undefined` without a closed frontmatter block.
 */
export function parseSkillFile(text) {
  const lines = text.split('\n')
  if (lines[0]?.trim() !== '---') return undefined
  const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---')
  if (end < 0) return undefined
  const data = parseFrontmatter(lines.slice(1, end))
  const content = lines.slice(end + 1).join('\n').replace(/^\n+/, '')
  return { data, content }
}

/**
 * Parse the YAML subset used by SKILL.md frontmatter.
 * @param lines - frontmatter lines without the `---` fences.
 * @returns the parsed key/value map.
 */
export function parseFrontmatter(lines) {
  /** @type {Record<string, unknown>} */
  const data = {}
  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    index += 1
    if (line.trim() === '' || line.trimStart().startsWith('#')) continue
    const match = /^([A-Za-z0-9_-]+):[ \t]*(.*)$/.exec(line)
    if (match === null) continue
    const [, key, rawValue] = match
    const trimmed = rawValue.trim()
    if (trimmed.startsWith("'")) {
      // Quoted scalar: `''` escapes a quote and the value may run over lines.
      let value = trimmed.slice(1)
      let closed = false
      while (true) {
        const closing = findClosingQuote(value)
        if (closing >= 0) {
          data[key] = value.slice(0, closing).replaceAll("''", "'")
          closed = true
          break
        }
        if (index >= lines.length) break
        value += `\n${lines[index]}`
        index += 1
      }
      if (closed) continue
      data[key] = value.replaceAll("''", "'")
      continue
    }
    if (trimmed.startsWith('"')) {
      let value = trimmed.slice(1)
      while (!/^([^"\\]|\\.)*"$/.test(value) && index < lines.length) {
        value += `\n${lines[index]}`
        index += 1
      }
      data[key] = value.replace(/^"|"$/g, '').replaceAll('\\"', '"')
      continue
    }
    if (trimmed === '') {
      // Nested block (e.g. `metadata:`): collect indented children as a map.
      const children = []
      while (index < lines.length && /^\s+\S/.test(lines[index])) {
        children.push(lines[index])
        index += 1
      }
      const nested = parseFrontmatter(children.map((child) => child.replace(/^\s+/, '')))
      data[key] = nested
      continue
    }
    // Plain scalar: fold continuation lines with a space, per YAML folding rules.
    let value = trimmed
    while (index < lines.length && /^\s+\S/.test(lines[index]) && !/^\s+[A-Za-z0-9_-]+:/.test(lines[index])) {
      value += ` ${lines[index].trim()}`
      index += 1
    }
    data[key] = stripComment(value)
  }
  return data
}

/**
 * Find the index of the quote that closes a single-quoted scalar.
 * @param value - text after the opening quote.
 * @returns closing quote index, or -1 when the scalar is unterminated.
 */
function findClosingQuote(value) {
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== "'") continue
    if (value[index + 1] === "'") {
      index += 1
      continue
    }
    return index
  }
  return -1
}

/**
 * Drop a trailing `# comment` from a plain scalar.
 * @param value - plain scalar text.
 * @returns the scalar without a comment.
 */
function stripComment(value) {
  const index = value.search(/\s#/)
  return (index < 0 ? value : value.slice(0, index)).trim()
}

/**
 * Resolve model/user invocation controls.
 * @param data - parsed frontmatter.
 * @returns the invocation policy; boolean frontmatter fields override the default.
 */
function invocationPolicy(data) {
  return {
    modelInvocable: readBoolean(data['model-invocable'], true),
    userInvocable: readBoolean(data['user-invocable'], true),
  }
}

/**
 * Read a boolean frontmatter field.
 * @param value - raw field value.
 * @param fallback - value to use when the field is absent or unparsable.
 * @returns the parsed boolean.
 */
function readBoolean(value, fallback) {
  if (typeof value === 'boolean') return value
  if (typeof value !== 'string') return fallback
  switch (value.trim().toLowerCase()) {
    case 'true':
    case 'yes':
    case 'on':
      return true
    case 'false':
    case 'no':
    case 'off':
      return false
    default:
      return fallback
  }
}

/**
 * Test for a non-array object.
 * @param value - candidate value.
 * @returns whether the value is a plain record.
 */
function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Throw the standard abort error when a lookup was cancelled.
 * @param signal - caller abort signal.
 */
function throwIfAborted(signal) {
  if (signal?.aborted === true) throw signal.reason ?? new Error('skill lookup aborted')
}
