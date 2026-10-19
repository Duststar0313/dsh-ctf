"""Regression tests for scripts/install_ctf_tools.sh.

The installer had three latent bugs that no test caught, because the script is
only exercised by hand:

1. `resolve_pip` printed its diagnostics to stdout, which the caller captured
   via `$(resolve_pip)`. The captured "pip command" became the log banner text
   instead of a command, so every install failed with `pip3: not found`.
2. `DRY_RUN=1 bash ...` (as documented in README.md) was silently ignored —
   the global was hard-reset to false — so a "preview" performed a real install.
3. `verify()` activated the venv, which is created WITHOUT
   `--system-site-packages`, so it reported every system-installed module as
   missing (0 found).

These tests are static/behavioural checks that need no network access.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = REPO_ROOT / "scripts" / "install_ctf_tools.sh"


def _run(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 60):
    """Run the installer, returning (exit_code, stdout, stderr)."""
    import os

    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        ["bash", str(INSTALLER), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=full_env,
        cwd=str(REPO_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestInstallerScript(unittest.TestCase):
    def setUp(self):
        if not INSTALLER.exists():
            self.skipTest("installer script not present")
        if not shutil.which("bash"):
            self.skipTest("bash not available")

    def test_script_parses(self):
        proc = subprocess.run(
            ["bash", "-n", str(INSTALLER)], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, f"bash -n failed: {proc.stderr}")

    def test_resolve_pip_stdout_is_only_a_command(self):
        """resolve_pip's stdout is captured, so it must emit just the command.

        Regression: a log_info banner was captured here, producing
        "==> Using virtualenv: ..." as the command to execute.
        """
        # Source the functions by extracting everything before the argument
        # dispatch, then call resolve_pip and assert its stdout is only a
        # command. Cut before the no-argument usage block, which also lives in
        # the dispatch section and would otherwise print on source.
        text = INSTALLER.read_text(encoding="utf-8")
        cut = text.index('if [ "${#MODES[@]}" -eq 0 ]; then')
        preamble = text[:cut]
        driver = preamble + "\nresolve_pip\n"
        proc = subprocess.run(
            ["bash", "-c", driver], capture_output=True, text=True, timeout=60,
            cwd=str(REPO_ROOT),
        )
        out = proc.stdout
        self.assertNotIn(
            "\033[",
            out,
            "resolve_pip leaked ANSI-formatted log output to stdout: "
            f"{out!r}",
        )
        self.assertNotIn(
            "==>",
            out,
            f"resolve_pip leaked a log banner to stdout: {out!r}",
        )
        # Whatever it printed must be a single bare token (a path or name).
        self.assertEqual(
            out.count("\n"),
            0,
            f"resolve_pip must print exactly one line, got {out!r}",
        )

    def test_dry_run_env_var_is_honoured(self):
        """README documents `DRY_RUN=1 bash ...`; it must not install anything."""
        code, out, _ = _run(["python"], env={"DRY_RUN": "1"}, timeout=120)
        self.assertEqual(code, 0, f"env dry run exited {code}; out={out!r}")
        self.assertIn(
            "would install",
            out,
            "DRY_RUN=1 did not take the preview path (it likely attempted a real "
            f"install): {out!r}",
        )

    def test_dry_run_flag_is_honoured(self):
        code, out, _ = _run(["--dry-run", "python"], timeout=120)
        self.assertEqual(code, 0, f"--dry-run exited {code}; out={out!r}")
        self.assertIn("would install", out, f"--dry-run output: {out!r}")

    def test_no_arguments_prints_usage_and_installs_nothing(self):
        """A bare invocation must not silently perform a full system install.

        Regression: MODES defaulted to ("all"), so running the script with no
        arguments started installing every apt/pip/gem package on the machine.
        """
        code, out, _ = _run([], timeout=120)
        self.assertNotEqual(
            code,
            0,
            "no-argument invocation exited 0, so it likely went ahead and "
            f"installed something instead of printing usage: {out!r}",
        )
        self.assertIn("usage", out.lower(), f"no usage text printed: {out!r}")
        # The usage text itself may contain the words "install/installing", so
        # assert on the banner the installer prints when it actually starts work.
        self.assertNotIn(
            "==>",
            out,
            f"no-argument invocation proceeded past usage into real work: {out!r}",
        )
        self.assertNotIn(
            "Summary",
            out,
            f"no-argument invocation reached the install summary: {out!r}",
        )

    def test_python_mode_installs_packages_individually(self):
        """One unsatisfiable pin must not abort the whole batch.

        Regression: `pip install "${todo[@]}"` is a single transaction, so a bad
        pin (segno==1.6.2 did not exist upstream) made all packages in the batch
        fail, including ones that would have installed fine.
        """
        text = INSTALLER.read_text(encoding="utf-8")
        m = re.search(r"^install_python\(\)\s*\{(.*?)^\}", text, re.S | re.M)
        self.assertIsNotNone(m, "could not locate install_python()")
        body = m.group(1)
        self.assertNotIn(
            'install "${todo[@]}"',
            body,
            "install_python still installs the whole batch in one transaction; "
            "a single bad pin would abort every package",
        )
        self.assertIn(
            "for pkg in",
            body,
            "install_python should iterate packages individually",
        )

    def test_all_pipspecs_are_wellformed(self):
        """Every PIP_PACKAGES entry must be `spec:importname` with a sane spec."""
        text = INSTALLER.read_text(encoding="utf-8")
        m = re.search(r"PIP_PACKAGES=\((.*?)\n\)", text, re.S)
        self.assertIsNotNone(m, "could not locate PIP_PACKAGES")
        entries = [
            ln.strip().strip('"\'')
            for ln in m.group(1).splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        self.assertTrue(entries, "PIP_PACKAGES is empty")
        for entry in entries:
            with self.subTest(entry=entry):
                self.assertIn(
                    ":",
                    entry,
                    f"{entry!r} lacks the `spec:importname` separator",
                )
                spec, _, mod = entry.partition(":")
                self.assertTrue(spec, f"{entry!r} has an empty package spec")
                self.assertTrue(mod, f"{entry!r} has an empty import name")
                # A version pin must look like ==1.2.3, not a typo'd operator.
                if "==" in spec:
                    _, _, ver = spec.partition("==")
                    self.assertRegex(
                        ver,
                        r"^\d",
                        f"{entry!r} has a suspicious version pin {ver!r}",
                    )

    def test_verify_does_not_activate_the_venv(self):
        """verify() must observe the real interpreter, not the empty venv.

        Regression: activating the venv made verify report 0 modules found even
        though pwntools/pycryptodome/etc. are installed system-wide.
        """
        text = INSTALLER.read_text(encoding="utf-8")
        m = re.search(r"^verify\(\)\s*\{(.*?)^\}", text, re.S | re.M)
        self.assertIsNotNone(m, "could not locate verify() in the installer")
        body = m.group(1)
        self.assertNotIn(
            "activate_venv",
            body,
            "verify() must not activate the venv: it lacks --system-site-packages, "
            "so system packages would be reported missing",
        )

    def test_verify_reports_installed_modules_as_found(self):
        """End-to-end: modules that are importable must be reported found.

        Uses the real interpreter, so skip when nothing is installed at all.
        """
        probe = subprocess.run(
            ["python3", "-c", "import pwn, Crypto"],
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            self.skipTest("pwntools/pycryptodome not installed in this environment")

        code, out, _ = _run(["--verify"], timeout=180)
        # A non-zero exit only signals "something is missing", which is expected
        # in this environment; the assertion is about the found-count.
        m = re.search(r"Py\s+found\s+\(\s*(\d+)\)", out)
        self.assertIsNotNone(m, f"could not parse verify output: {out!r}")
        found = int(m.group(1))
        self.assertGreater(
            found,
            0,
            "verify reported zero Python modules found although pwntools and "
            "pycryptodome are importable — it is probably inspecting the venv "
            f"instead of the system interpreter:\n{out}",
        )


class TestBarePipTargetsPython3(unittest.TestCase):
    """A bare `pip` must resolve to the Python 3 interpreter CTF scripts use.

    This image shipped a Python 2.7 pip at /usr/local/bin/pip, which sorts
    before /usr/bin on PATH. `pip install X` therefore installed into an
    interpreter nothing else used. The fix is a symlink to the py3 pip; this
    test fails loudly if that regresses.
    """

    def setUp(self):
        # Only meaningful where the trap existed: a py2 pip shadowing py3.
        self.pip = shutil.which("pip")
        if self.pip is None:
            self.skipTest("no bare `pip` on PATH")

    def test_bare_pip_is_python3(self):
        proc = subprocess.run(
            [self.pip, "--version"], capture_output=True, text=True, timeout=60
        )
        out = (proc.stdout + proc.stderr).strip()
        self.assertNotIn(
            "python 2",
            out.lower(),
            f"bare `pip` ({self.pip}) targets Python 2: {out!r}. Re-point it at the "
            "Python 3 pip (the original is kept as /usr/local/bin/pip.py2.orig).",
        )
        self.assertRegex(
            out,
            r"python 3\.\d+",
            f"bare `pip` does not report a Python 3 target: {out!r}",
        )

    def test_legacy_pip_is_still_available(self):
        """pip2/pip2.7 must keep working, so the py2 environment stays reachable."""
        which = shutil.which("pip2") or shutil.which("pip2.7")
        if which is None:
            self.skipTest("pip2/pip2.7 not present; nothing to preserve")
        proc = subprocess.run(
            [which, "--version"], capture_output=True, text=True, timeout=60
        )
        out = (proc.stdout + proc.stderr).strip()
        self.assertTrue(out, f"{which} --version produced no output")
        # It may legitimately be py2 here; the point is only that it still runs.
        self.assertIn("pip ", out.lower(), f"unexpected pip2 output: {out!r}")


if __name__ == "__main__":
    unittest.main()
