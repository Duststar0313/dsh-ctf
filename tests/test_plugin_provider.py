"""Contract tests for the `dsh-ctf` plugin runtime (lib/index.js).

Two layers are covered here:

* the Node side, by running `scripts/verify-plugin.mjs` — it drives the real
  Cordis entry with a fake `skills` registry and asserts the provider catalog;
* the Python side, by re-parsing every SKILL.md with PyYAML and comparing it to
  what the JavaScript frontmatter subset parser produced. That comparison is
  what keeps the dependency-free parser honest.

The tests skip — never fail — when Node is unavailable.
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

EXPECTED_SKILLS = sorted(
    [
        "ctf-ai-ml",
        "ctf-crypto",
        "ctf-forensics",
        "ctf-malware",
        "ctf-match-ops",
        "ctf-misc",
        "ctf-osint",
        "ctf-pwn",
        "ctf-reverse",
        "ctf-routing",
        "ctf-web",
        "ctf-writeup",
        "solve-challenge",
    ]
)

# Dump the provider catalog through the real plugin entry.
DUMP_SCRIPT = """
import { createSkillProvider, normalizeConfig } from './lib/index.js'
const provider = createSkillProvider(normalizeConfig({}))
const candidates = await provider.list({})
const out = []
for (const candidate of candidates) {
  const body = await provider.get(candidate, {})
  out.push({
    name: candidate.name,
    description: candidate.description,
    whenToUse: candidate.whenToUse ?? null,
    rank: candidate.rank,
    source: candidate.source,
    provider: candidate.provider,
    path: candidate.path,
    resourceBase: candidate.resourceBase,
    contentLength: body.content.length,
    contentHasFrontmatter: body.content.startsWith('---'),
  })
}
console.log(JSON.stringify(out))
"""


def run_node(script: str, *args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    """Run a Node script or entry point, returning the completed process."""
    if script.endswith(".mjs"):
        return subprocess.run(
            [NODE, script, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=180,
        )
    return subprocess.run(
        [NODE, "--input-type=module", "-e", script, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=180,
    )


@unittest.skipIf(NODE is None, "node is not installed")
class TestPluginSelfCheck(unittest.TestCase):
    def test_verify_script_passes(self):
        result = run_node("scripts/verify-plugin.mjs", "--quiet")
        self.assertEqual(
            result.returncode,
            0,
            msg=f"verify-plugin failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_manifest_declares_the_bundle(self):
        manifest = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "dsh-ctf")
        self.assertEqual(manifest["dsh"]["bundle"]["patch"], "./cordis.patch.yml")
        self.assertEqual(manifest.get("dependencies", {}), {})
        self.assertTrue((REPO_ROOT / "cordis.patch.yml").is_file())


@unittest.skipIf(NODE is None, "node is not installed")
class TestProviderCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = run_node(DUMP_SCRIPT, cwd=REPO_ROOT)
        if result.returncode != 0:
            raise unittest.SkipTest(f"could not dump catalog: {result.stderr}")
        cls.catalog = json.loads(result.stdout)
        cls.by_name = {entry["name"]: entry for entry in cls.catalog}

    def test_discovers_the_expected_skills(self):
        self.assertEqual(sorted(self.by_name), EXPECTED_SKILLS)

    def test_candidates_are_bundled_and_ranked_below_user_roots(self):
        for entry in self.catalog:
            with self.subTest(skill=entry["name"]):
                self.assertEqual(entry["source"], "bundled")
                self.assertEqual(entry["provider"], "ctf-bundle")
                self.assertEqual(entry["rank"], 600)

    def test_resource_base_points_at_the_skill_directory(self):
        for entry in self.catalog:
            with self.subTest(skill=entry["name"]):
                base = entry["resourceBase"]
                self.assertEqual(base["kind"], "directory")
                skill_dir = Path(base["path"])
                self.assertTrue(skill_dir.is_dir(), msg=str(skill_dir))
                self.assertEqual(skill_dir.name, entry["name"])
                self.assertTrue((skill_dir / "SKILL.md").is_file())
                self.assertEqual(Path(entry["path"]), skill_dir / "SKILL.md")

    def test_bodies_load_without_frontmatter(self):
        for entry in self.catalog:
            with self.subTest(skill=entry["name"]):
                self.assertGreater(entry["contentLength"], 200)
                self.assertFalse(entry["contentHasFrontmatter"])


class TestFrontmatterParserMatchesYaml(unittest.TestCase):
    """The JS parser must agree with PyYAML on the fields the host reads."""

    def test_every_skill_frontmatter_matches(self):
        for skill in EXPECTED_SKILLS:
            path = REPO_ROOT / skill / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), msg=f"{skill}: no frontmatter")
            _, frontmatter, _ = text.split("---\n", 2)
            expected = yaml.safe_load(frontmatter)
            with self.subTest(skill=skill):
                for field in ("name", "description", "whenToUse", "license"):
                    self.assertIn(field, expected, msg=f"{skill}: {field} missing upstream")
                    self.assertIsInstance(expected[field], str)
                self.assertEqual(expected["name"], skill)


if __name__ == "__main__":
    unittest.main()
