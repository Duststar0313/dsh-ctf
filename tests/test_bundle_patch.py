"""Structural tests for the bundle patch layer (`cordis.patch.yml`).

The patch is YAML with one loader-specific tag (`!!js`). Parsing it here catches
syntax errors and shape regressions that the Node self-check can only grep for:
the row ids the preset depends on, the package names it mounts, and the absence
of machine-specific absolute paths.
"""

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCH = REPO_ROOT / "cordis.patch.yml"


class JsTagLoader(yaml.SafeLoader):
    """SafeLoader that keeps `!!js` expression text verbatim."""


def _construct_js(loader, node):
    return {"__js__": loader.construct_scalar(node)}


JsTagLoader.add_constructor("tag:yaml.org,2002:js", _construct_js)


class TestBundlePatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = yaml.load(PATCH.read_text(encoding="utf-8"), Loader=JsTagLoader)

    def test_patch_is_a_single_insert_list(self):
        self.assertIsInstance(self.rows, list)
        self.assertEqual(len(self.rows), 1)
        self.assertIn("insert", self.rows[0])
        self.assertIsInstance(self.rows[0]["insert"], list)

    def test_preset_row_shape(self):
        presets = [row for row in self.rows[0]["insert"] if row.get("id") == "preset-ctf"]
        self.assertEqual(len(presets), 1, msg="expected exactly one preset-ctf row")
        preset = presets[0]
        self.assertEqual(preset["name"], "@deepseek-ai/dsh-agent-preset")
        config = preset["config"]
        self.assertEqual(config["id"], "ctf")
        self.assertEqual(config["name"], "CTF 解题")
        self.assertIsInstance(config["order"], int)
        self.assertTrue(config["plugins"], msg="preset mounts no plugins")

    def test_preset_mounts_the_skill_provider_and_the_persona(self):
        preset = next(row for row in self.rows[0]["insert"] if row.get("id") == "preset-ctf")
        plugins = preset["config"]["plugins"]
        ids = [row.get("id") for row in plugins]
        names = [row.get("name") for row in plugins]

        self.assertEqual(ids[0], "persona", msg="persona must lead the plugin list")
        self.assertIn("ctf-skills", ids)
        self.assertIn("dsh-ctf", names, msg="the ctf-skills row must mount this package")
        self.assertIn("tool-skill", ids)

        provider_row = next(row for row in plugins if row.get("id") == "ctf-skills")
        self.assertEqual(provider_row["config"]["providerName"], "ctf-bundle")

    def test_persona_pins_the_routing_entry_point(self):
        preset = next(row for row in self.rows[0]["insert"] if row.get("id") == "preset-ctf")
        persona = next(row for row in preset["config"]["plugins"] if row.get("id") == "persona")
        prefix = persona["config"]["prefix"]
        self.assertIn("ctf-routing", prefix)
        self.assertIn("ctf-match-ops", prefix)
        self.assertIn("ctf-writeup", prefix)

    def test_no_machine_specific_paths(self):
        text = PATCH.read_text(encoding="utf-8")
        for needle in ("/root/", "/home/", "C:\\\\", ".dsh/skills"):
            with self.subTest(needle=needle):
                self.assertNotIn(needle, text)

    def test_host_rows_target_public_packages(self):
        preset = next(row for row in self.rows[0]["insert"] if row.get("id") == "preset-ctf")
        for row in preset["config"]["plugins"]:
            name = row.get("name", "")
            with self.subTest(row=row.get("id")):
                self.assertTrue(
                    name.startswith("@deepseek-ai/") or name.startswith("cordis:") or name == "dsh-ctf",
                    msg=f"unexpected package name {name!r}",
                )


if __name__ == "__main__":
    unittest.main()
