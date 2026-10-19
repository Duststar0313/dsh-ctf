"""Validate the ctf-routing decision layer against the content libraries it indexes.

`ctf-routing/routing/<direction>.md` is the sole entry point for CTF work: it holds a
"File Index" table naming every content file in the matching `<direction>/` skill. If a
row is missing (or names a file that does not exist), the routing layer silently stops
pointing at that content — the file becomes unreachable without anyone noticing.

The upstream test suite does not cover this, because the upstream project has no routing
layer. These checks are specific to this fork's architecture.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTING_DIR = REPO_ROOT / "ctf-routing" / "routing"

# The nine content-library directions, each of which must have a routing decision file.
DIRECTIONS = [
    "ctf-web",
    "ctf-pwn",
    "ctf-reverse",
    "ctf-crypto",
    "ctf-forensics",
    "ctf-misc",
    "ctf-malware",
    "ctf-osint",
    "ctf-ai-ml",
]

# Matches a File Index table row: | `some-file.md` | contents | when to read |
INDEX_ROW_RE = re.compile(r"^\|\s*`([A-Za-z0-9._-]+\.md)`\s*\|", re.M)


def _content_files(direction: str) -> set[str]:
    """Every .md under <direction>/, excluding its own SKILL.md."""
    d = REPO_ROOT / direction
    if not d.is_dir():
        return set()
    return {p.name for p in d.glob("*.md") if p.name != "SKILL.md"}


def _index_rows(direction: str) -> list[str]:
    """Filenames listed in the routing file's File Index table, in order."""
    f = ROUTING_DIR / f"{direction}.md"
    if not f.exists():
        return []
    return INDEX_ROW_RE.findall(f.read_text(encoding="utf-8"))


class TestRoutingLayer(unittest.TestCase):
    """The routing decision layer must stay in sync with the content libraries."""

    def test_every_direction_has_a_routing_file(self):
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                self.assertTrue(
                    (ROUTING_DIR / f"{direction}.md").exists(),
                    f"missing routing file {direction}.md",
                )

    def test_index_lists_every_content_file(self):
        """No content file may be orphaned from the routing index."""
        for direction in DIRECTIONS:
            index = set(_index_rows(direction))
            actual = _content_files(direction)
            with self.subTest(direction=direction):
                self.assertEqual(
                    actual - index,
                    set(),
                    f"{direction}: content files missing from the routing File Index: "
                    f"{sorted(actual - index)}",
                )

    def test_index_references_no_missing_files(self):
        """No index row may point at a file that does not exist."""
        for direction in DIRECTIONS:
            index = set(_index_rows(direction))
            actual = _content_files(direction)
            with self.subTest(direction=direction):
                self.assertEqual(
                    index - actual,
                    set(),
                    f"{direction}: routing File Index names non-existent files: "
                    f"{sorted(index - actual)}",
                )

    def test_index_has_no_duplicate_rows(self):
        for direction in DIRECTIONS:
            rows = _index_rows(direction)
            dupes = {r for r in rows if rows.count(r) > 1}
            with self.subTest(direction=direction):
                self.assertEqual(dupes, set(), f"{direction}: duplicate index rows: {sorted(dupes)}")

    def test_skill_md_resource_list_matches_index(self):
        """The routing index and the skill's own resource list must agree."""
        for direction in DIRECTIONS:
            index = set(_index_rows(direction))
            skill = REPO_ROOT / direction / "SKILL.md"
            listed = set(
                re.findall(r"^- \[([A-Za-z0-9._-]+\.md)\]", skill.read_text(encoding="utf-8"), re.M)
            )
            with self.subTest(direction=direction):
                self.assertEqual(
                    index,
                    listed,
                    f"{direction}: routing index and SKILL.md resource list disagree "
                    f"(index-only={sorted(index - listed)}, skill-only={sorted(listed - index)})",
                )

    def test_routing_files_have_a_decision_tree(self):
        """A routing file without a decision tree cannot route."""
        for direction in DIRECTIONS:
            text = (ROUTING_DIR / f"{direction}.md").read_text(encoding="utf-8")
            with self.subTest(direction=direction):
                self.assertIn("## File Index", text)
                self.assertIn("## Decision Tree", text)


class TestNoOrphanRouting(unittest.TestCase):
    """Every routing file should correspond to an actual skill directory."""

    def test_no_routing_file_without_a_skill(self):
        routing = {
            p.stem for p in ROUTING_DIR.glob("ctf-*.md") if p.stem.startswith("ctf-")
        }
        self.assertEqual(
            routing - set(DIRECTIONS),
            set(),
            "routing files exist with no matching content directory",
        )


# Matches a Directions-table row count, e.g. "HTTP apps, clients (22 files)".
COUNT_RE = re.compile(r"\((\d+)\s+files?\)")


class TestDirectionsTableCounts(unittest.TestCase):
    """The Directions table's per-direction file counts must match reality.

    These counts are prose metadata that no other test reads; they silently went
    stale when content files were added. A wrong count is a routing hazard: it
    tells the agent how much of a direction it may need to consider.
    """

    def _claimed_counts(self) -> dict[str, int]:
        text = (REPO_ROOT / "ctf-routing" / "SKILL.md").read_text(encoding="utf-8")
        row_re = re.compile(r"^\|\s*`(ctf-[a-z-]+)`\s*\|([^|]*)\|", re.M)
        out: dict[str, int] = {}
        for direction, cell in row_re.findall(text):
            m = COUNT_RE.search(cell)
            if m:
                out[direction] = int(m.group(1))
        return out

    def test_directions_table_counts_match_content_files(self):
        claimed = self._claimed_counts()
        self.assertTrue(claimed, "no per-direction counts found in the Directions table")
        for direction, count in claimed.items():
            with self.subTest(direction=direction):
                self.assertEqual(
                    count,
                    len(_content_files(direction)),
                    f"{direction}: Directions table claims {count} files, "
                    f"actual is {len(_content_files(direction))}",
                )

    def test_skill_count_statement_matches_reality(self):
        """The routing entry point must not misstate how many skills it indexes."""
        text = (REPO_ROOT / "ctf-routing" / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"indexes (\d+) skill directories", text)
        self.assertIsNotNone(m, "routing SKILL.md no longer states a skill count")
        claimed = int(m.group(1))
        # 9 routable directions + ctf-match-ops + ctf-writeup + ctf-routing.
        self.assertEqual(
            claimed,
            len(DIRECTIONS) + 3,
            f"routing SKILL.md claims {claimed} indexed skill directories, expected "
            f"{len(DIRECTIONS) + 3} (solve-challenge is intentionally excluded)",
        )


class TestTriageDispatcherCoverage(unittest.TestCase):
    """triage.md must be able to dispatch to every direction, including AI/ML.

    triage.md is what gets read when the direction is NOT yet obvious. Its
    "by file type" table is the dispatcher: if an artifact extension is absent
    there, the challenge cannot be routed at all even though the destination
    decision layer (`routing/ctf-ai-ml.md`) would have recognised it.

    Regression: `.pt` / `.pth` / `.safetensors` / `.onnx` were listed only in
    the AI/ML destination and in solve-challenge, so a model-weights challenge
    with an unknown direction fell through the dispatcher.
    """

    TRIAGE = ROUTING_DIR / "triage.md"

    # Extensions the AI/ML destination commits to handling.
    AIML_EXTENSIONS = [".pt", ".pth", ".safetensors", ".onnx"]

    def setUp(self):
        if not self.TRIAGE.exists():
            self.skipTest("triage.md not present")

    def test_triage_dispatch_table_covers_ai_ml_artifacts(self):
        text = self.TRIAGE.read_text(encoding="utf-8")
        for ext in self.AIML_EXTENSIONS:
            with self.subTest(extension=ext):
                self.assertIn(
                    f"`{ext}`",
                    text,
                    f"triage.md does not mention `{ext}`: a model-weights challenge "
                    "with an unknown direction cannot be dispatched to ctf-ai-ml",
                )

    def test_every_direction_is_reachable_from_triage(self):
        """Each routable direction must be named in triage's Step 3 table."""
        text = self.TRIAGE.read_text(encoding="utf-8")
        referenced = set(re.findall(r"`routing/(ctf-[a-z-]+)\.md`", text))
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                self.assertIn(
                    direction,
                    referenced,
                    f"triage.md never points at routing/{direction}.md",
                )

    def test_triage_and_skill_md_direction_tables_agree(self):
        """triage's Step 3 table and SKILL.md's Directions table must not diverge."""
        skill_text = (REPO_ROOT / "ctf-routing" / "SKILL.md").read_text(encoding="utf-8")
        triage_text = self.TRIAGE.read_text(encoding="utf-8")
        skill_dirs = set(re.findall(r"^\|\s*`(ctf-[a-z-]+)`\s*\|", skill_text, re.M))
        triage_refs = set(re.findall(r"`routing/(ctf-[a-z-]+)\.md`", triage_text))
        content_dirs = set(DIRECTIONS)
        # Only the routable content directions are expected on both sides.
        self.assertEqual(
            (skill_dirs & content_dirs) - triage_refs,
            set(),
            "directions in SKILL.md's table are missing from triage's Step 3 table",
        )
        self.assertEqual(
            triage_refs - skill_dirs,
            set(),
            "triage's Step 3 table references directions absent from SKILL.md",
        )


class TestFlagSearchPattern(unittest.TestCase):
    """The documented flag-search command must actually find common flag formats.

    triage.md lists `flag{}`, `FLAG{}`, `CTF{}` and `TEAM{}` as common formats,
    but the `grep` command it ships used a five-word whitelist
    (`flag|ctf|eno|htb|pico`). `TEAM{...}` was therefore documented yet NOT
    matched — a missed flag is an unsolved challenge. These tests pin the
    pattern to the formats the docs promise.
    """

    # Prefixes the documentation names, plus widely used event prefixes.
    MUST_MATCH = [
        "flag{abc_def_123}",
        "FLAG{abc_def_123}",
        "CTF{abc_def_123}",
        "TEAM{abc_def_123}",
        "ENO{abc_def_123}",
        "HTB{abc_def_123}",
        "picoCTF{abc_def_123}",
        "SEKAI{abc_def_123}",
        "buckeye{abc_def_123}",
        "DUCTF{abc_def_123}",
    ]

    def _patterns_from(self, path: Path) -> list[str]:
        """Extract `grep ... -E '<pattern>'` patterns from a markdown file."""
        text = path.read_text(encoding="utf-8")
        return re.findall(r"grep\s+-[a-zA-Z]*E\s+'([^']+)'", text)

    def _sources(self) -> list[Path]:
        return [
            p
            for p in (
                ROUTING_DIR / "triage.md",
                REPO_ROOT / "ctf-writeup" / "SKILL.md",
                REPO_ROOT / "solve-challenge" / "SKILL.md",
            )
            if p.exists()
        ]

    def test_flag_patterns_match_documented_formats(self):
        for src in self._sources():
            patterns = self._patterns_from(src)
            # The flag-search pattern is the one mentioning brace matching.
            flag_pats = [p for p in patterns if "{" in p or "\\{" in p]
            self.assertTrue(
                flag_pats, f"{src.name}: no flag-search grep pattern found"
            )
            for pat in flag_pats:
                for sample in self.MUST_MATCH:
                    with self.subTest(source=src.name, pattern=pat, sample=sample):
                        self.assertIsNotNone(
                            re.search(pat, sample),
                            f"{src.name} pattern {pat!r} does not match {sample!r}",
                        )

    def test_triage_documents_only_formats_its_search_finds(self):
        """Formats named in triage's flag section must be found by its grep."""
        triage = ROUTING_DIR / "triage.md"
        text = triage.read_text(encoding="utf-8")
        # Collect `PREFIX{...}` formats mentioned in the flag-format section.
        section = re.search(r"^## Flag formats(.*?)(?=^## )", text, re.S | re.M)
        self.assertIsNotNone(section, "triage.md has no '## Flag formats' section")
        named = set(re.findall(r"`([A-Za-z0-9_]+)\{", section.group(1)))
        named |= {n.lower() for n in named}
        flag_pats = [
            p for p in self._patterns_from(triage) if "{" in p or "\\{" in p
        ]
        self.assertTrue(flag_pats, "no flag grep pattern in triage.md")
        for prefix in named:
            sample = f"{prefix}{{abc_def_123}}"
            for pat in flag_pats:
                with self.subTest(prefix=prefix, pattern=pat):
                    self.assertIsNotNone(
                        re.search(pat, sample),
                        f"triage.md documents `{prefix}{{...}}` but its own grep "
                        f"pattern {pat!r} does not match it",
                    )


if __name__ == "__main__":
    unittest.main()
