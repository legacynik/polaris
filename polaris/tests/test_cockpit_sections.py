"""polaris#11 and #14 — the section names a host cockpit may use, and paths with spaces in them.

#11: the vault's cockpit heads its open threads `## Open — thread vivi` and closes them with an
`Owner:` line. `/update` appended the thread AFTER that line — inside the section by the letter,
orphaned by the eye — and `/start` reported `SECTIONS_MISSING`. The names the package expects are
declared once, in `state_sections`, and a heading that QUALIFIES an expected name after a
dash, a colon or a parenthesis is that section. `# Priorità attive` is not `## Active Priorities`
and is still reported missing: a translated heading is a different contract, not an alias.

#14: `resume_paths.sh` is consumed with `eval`, and printed its values unquoted, so a checkout under
a directory with a space in it split into words («command not found: Vibe») and `/start` died at
Step 1b on the founder's own vault.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

from host_repo import LOGIN, PKG, env_for, host_repo, run_script, seed_state, skill_block

sys.path.insert(0, str(PKG / "skills" / "end" / "scripts"))
sys.path.insert(0, str(PKG / "skills" / "start" / "scripts"))
THREAD = "- `feat/lane` (acme-api) — la lane vive · since 2026-09-04"


def vault_shaped(repo: Path) -> Path:
    """The SHIPPED template, re-headed the way the live cockpit heads it: an H1 in the host's own
    language, a qualified `## Open`, and the trailing `Owner:` line under the threads."""
    path = seed_state(repo, "current.md")
    body = (path.read_text().replace("## Active Priorities", "# Priorità attive")
            .replace("## Open\n", "## Open — thread vivi\n")
            .replace("## Recent Context", "Owner: @acme-dev\n\n## Recent Context"))
    path.write_text(body)
    return path


def upsert(path: Path, row: str = THREAD) -> subprocess.CompletedProcess:
    return run_script("end", "state_upsert.py", "thread", str(path),
                      "--owner", LOGIN, "--now", "2026-09-04", input=row + "\n")


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def between(path: Path, first: str, last: str) -> list[str]:
    lines = path.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(first))
    stop = next(i for i, ln in enumerate(lines) if i > start and ln.startswith(last))
    return [ln for ln in lines[start + 1:stop] if ln.strip()]


class QualifiedOpenSection(unittest.TestCase):
    """AC1 — the vault's own heading is that section, and the row lands among the threads."""

    def test_the_row_lands_above_the_owner_line_not_after_it(self):
        repo = host_repo()
        cockpit = vault_shaped(repo)
        out = upsert(cockpit)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = cockpit.read_text()
        self.assertIn(THREAD, body)
        self.assertLess(body.index(THREAD), body.index("Owner:"), body)
        self.assertEqual(between(cockpit, "Owner:", "## Recent Context"), [], body)

    def test_an_absent_open_section_refuses_and_writes_nothing(self):
        repo = host_repo()
        cockpit = vault_shaped(repo)
        cockpit.write_text(cockpit.read_text().replace("## Open — thread vivi", "## Threads"))
        before = md5(cockpit)
        out = upsert(cockpit)
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("## Open", out.stderr, out.stderr)
        self.assertEqual(md5(cockpit), before, "a refusal rewrote the file")


class SectionRegistry(unittest.TestCase):
    """AC2 — one registry, read by the three scripts; no reader compiles its own heading."""

    def test_the_three_readers_share_one_declaration(self):
        import _brief_parts
        import recent_context
        import state_sections
        import state_upsert
        self.assertIs(_brief_parts.REGISTRY, state_sections.SECTIONS)
        self.assertIs(state_upsert.SECTIONS["thread"], state_sections.heading("## Open"))
        self.assertIs(recent_context.HEADING, state_sections.heading("## Recent Context"))
        self.assertEqual(state_sections.SECTIONS["current.md"],
                         ("## Active Priorities", "## Open", "## Recent Context"))

    def test_a_qualified_name_is_the_section_and_a_longer_name_is_not(self):
        import state_sections as reg
        self.assertTrue(reg.heading("## Open").match("## Open — thread vivi"))
        self.assertTrue(reg.heading("## Open").match("# Open (repo)"))
        self.assertIsNone(reg.heading("## Active").match("## Active Priorities"))
        self.assertIsNone(reg.heading("## Open").match("## Opening moves"))
        self.assertIsNone(reg.heading("## Active Priorities").match("# Priorità attive"))

    def test_the_brief_reports_only_the_heading_the_host_really_lost(self):
        repo = host_repo()
        cockpit = vault_shaped(repo)
        out = run_script("start", "brief_signals.py", "--root", str(repo / "_polaris"),
                         "--current", str(cockpit), "--login", LOGIN, "--main-wt", str(repo))
        missing = [ln for ln in out.stdout.splitlines() if ln.startswith("SECTIONS_MISSING")]
        self.assertEqual(missing, ["SECTIONS_MISSING=current.md: ## Active Priorities"], out.stdout)


class ResumePathsQuoting(unittest.TestCase):
    """#14 — `eval` of the shipped Step 1b survives a space, an apostrophe and a `$`."""

    def step1b(self, repo: Path) -> subprocess.CompletedProcess:
        block = skill_block("start", "resume_paths.sh") + '\nprintf "%s\\n%s\\n" "$ROOT" "$MAIN_WT"'
        env = {k: v for k, v in env_for(repo).items()
               if k not in ("ROOT", "MAIN_WT", "CURRENT", "LOGIN")}
        return subprocess.run(["bash", "-c", block], cwd=str(repo), env=env,
                              capture_output=True, text=True)

    def assert_round_trip(self, name: str) -> None:
        repo = host_repo(name=name)
        out = self.step1b(repo)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("command not found", out.stderr, out.stderr)
        self.assertEqual(out.stdout.splitlines()[-2:],
                         [str(repo / "_polaris"), str(repo)], out.stdout)

    def test_a_directory_with_spaces(self):
        self.assert_round_trip("Dir With Spaces")

    def test_a_directory_with_an_apostrophe_and_a_dollar(self):
        self.assert_round_trip("it's $HOME repo")


if __name__ == "__main__":
    unittest.main()
