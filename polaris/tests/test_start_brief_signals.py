"""D1-D3 — `/start` shows what the system already knows (polaris-os#243, #240, polaris#3).

Three signals exist today and nobody reads them: the legacy session-log spool, the drift of
the main worktree, and the sections a state file has lost. Two more surfaces landed with the
four-file donor form and no reader: `state/todos.md` and `## Recent Context`. And the typed
backbone must be used where a repo has one and be invisible where it does not.

Every case runs the shipped `start/scripts/brief_signals.py` in a real host repo.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from host_repo import LOGIN, git, host_repo, run_script, seed_state


def signals(repo, *args: str) -> str:
    root = repo / "_polaris"
    out = run_script("start", "brief_signals.py", "--root", str(root),
                     "--current", str(root / "state" / "current.md"), *args, cwd=str(repo))
    assert out.returncode == 0, f"the brief must never fail a session:\n{out.stderr}"
    return out.stdout


class TodosReachTheBrief(unittest.TestCase):
    """D1 — `/start` reads the host repo's todos file, or says it is not there."""

    def test_active_rows_and_only_overdue_followups_are_named(self):
        repo = host_repo()
        todos = seed_state(repo, "todos.md")
        past = (date.today() - timedelta(days=2)).isoformat()
        soon = (date.today() + timedelta(days=9)).isoformat()
        todos.write_text("## Active\n\n- #11 — primo · Added: W32\n- #12 — secondo · Added: W36\n"
                         f"\n## Completed\n\n## Follow-ups\n\n- riprendi #9 · Review: {past}\n"
                         f"- non ancora · Review: {soon}\n")
        out = signals(repo)
        self.assertIn("TODOS_ACTIVE=2", out)
        self.assertIn("#11 — primo", out)
        self.assertIn("#12 — secondo", out)
        self.assertIn("FOLLOWUP_DUE=", out)
        self.assertIn("riprendi #9", out)
        self.assertNotIn("non ancora", out, "a follow-up not yet due is noise in the brief")

    def test_a_repo_without_todos_says_so_once_and_still_exits_zero(self):
        repo = host_repo()
        out = signals(repo)
        self.assertIn("TODOS=absent", out)
        self.assertNotIn("TODOS_ACTIVE=", out)

    def test_recent_context_entries_are_carried_newest_first(self):
        repo = host_repo()
        current = repo / "_polaris" / "state" / "current.md"
        current.write_text("Updated: 2026-09-03 — @acme-dev\n\n## Recent Context\n\n"
                           "### 2026-09-03 — terza\n\n### 2026-09-02 — seconda\n\n"
                           "### 2026-09-01 — prima\n")
        lines = [ln for ln in signals(repo).splitlines() if ln.startswith("RECENT=")]
        self.assertEqual([ln.split("=", 1)[1] for ln in lines][:2],
                         ["2026-09-03 — terza", "2026-09-02 — seconda"])


class TheThreeSignals(unittest.TestCase):
    """D2 — polaris-os#243: a line that always says zero teaches you to ignore it."""

    def test_a_legacy_spool_is_counted_only_when_it_holds_something(self):
        repo = host_repo()
        self.assertNotIn("SPOOL_LEGACY=", signals(repo))
        spool = repo / ".git" / "polaris-deferred"
        spool.mkdir()
        (spool / "a.md").write_text("x")
        (spool / "b.md").write_text("y")
        self.assertIn("SPOOL_LEGACY=2", signals(repo))

    def test_main_worktree_drift_is_named_off_default_and_silent_on_it(self):
        repo = host_repo()
        self.assertNotIn("DRIFT=", signals(repo), "a clean default branch has no drift to report")
        git(repo, "checkout", "-q", "-b", "reference/other-panel")
        for name in ("a.md", "b.md", "c.md"):
            (repo / name).write_text("foreign work\n")
        git(repo, "add", "-A")
        line = [ln for ln in signals(repo).splitlines() if ln.startswith("DRIFT=")]
        self.assertEqual(len(line), 1, "off the default branch the brief must name the drift")
        self.assertIn("reference/other-panel", line[0])
        self.assertIn("3", line[0])

    def test_missing_state_sections_are_named_and_a_complete_file_is_silent(self):
        repo = host_repo()
        current = repo / "_polaris" / "state" / "current.md"
        self.assertNotIn("SECTIONS_MISSING=", signals(repo), "the template is complete")
        current.write_text("Updated: 2026-09-03 — @acme-dev\n\n## Open\n\n- `a` — x\n")
        self.assertIn("Recent Context", [ln for ln in signals(repo).splitlines()
                                         if ln.startswith("SECTIONS_MISSING=")][0])

    def test_an_absent_state_file_invents_nothing(self):
        repo = host_repo()
        (repo / "_polaris" / "state" / "current.md").unlink()
        out = signals(repo)
        self.assertNotIn("SECTIONS_MISSING=", out)
        self.assertNotIn("RECENT=", out)


class TheBackboneIsFeatureDetected(unittest.TestCase):
    """D3 / polaris-os#405 — with a typed backbone the brief carries the host's two-stage
    readout, as LINES; without one, nothing changes.

    It used to carry `PACK=CTX-<id>`, and polaris-os#326 measured what one opaque id is worth:
    the agent ignored it. What the host answers now is the area index with its counts, the
    area chosen or the one question to ask, and the rows of that area's pack. Nothing the
    package prints starts with `PACK=` any more."""

    @staticmethod
    def _backbone(repo, *, emits=None, blocks=None):
        """A host repo carrying the REAL shapes: a manifest with no `pack_id` key (the live one
        has none) and a resolver that answers the declared CLI contract, not a stub file."""
        root = repo / "_polaris"
        (root / "decisions").mkdir()
        (root / "decisions" / "manifest.json").write_text(json.dumps(
            {"schema_version": 1, "repo": "host", "workspace": "w",
             "manifest_hash": "abc", "decisions": [], "live_documents": []}))
        (root / "scripts").mkdir()
        body = (f"print({emits!r})\n" if emits else
                f"import sys\nsys.stderr.write({blocks!r})\nsys.exit(1)\n")
        (root / "scripts" / "contextpack_dashboard.py").write_text(body)
        return root

    def test_the_brief_carries_the_rows_the_host_resolver_prints(self):
        """Rows, not an id: the agent can act on `layer: … source_id: …` and could not act
        on `PACK=CTX-…`."""
        repo = host_repo()
        self._backbone(repo, emits="AREA: memoria  issues: 3  prs: 1  last_decision: DEC-9\n"
                                   "layer: sealed  source_id: DEC-9  path: decisions/DEC-9.md"
                                   "  freshness: CURRENT")
        out = signals(repo)
        self.assertIn("AREA: memoria  issues: 3", out)
        self.assertIn("PACK: 1 rows held for lane entry", out)  # 2026-09-23: counted, not printed
        self.assertNotIn("PACK=", out)

    def test_a_blocked_pack_is_loud_not_silent(self):
        """DB-FR-05: a blocked emission blocks. A silent empty line is indistinguishable from
        a repo that has no backbone at all."""
        repo = host_repo()
        self._backbone(repo, blocks="DECISION_SCOPE_STALE: docs/x.md\n")
        out = signals(repo)
        self.assertIn("PACK: blocked", out)
        self.assertIn("DECISION_SCOPE_STALE", out)
        self.assertNotIn("PACK=", out)

    def test_a_repo_without_the_backbone_prints_no_pack_line_and_no_error(self):
        """#155 unchanged: a repository with no typed backbone must not even learn that the
        feature exists, so an absent resolver is silence — not `PACK: none`."""
        repo = host_repo()
        out = run_script("start", "brief_signals.py", "--root", str(repo / "_polaris"),
                         "--current", str(repo / "_polaris" / "state" / "current.md"),
                         cwd=str(repo))
        self.assertEqual(out.returncode, 0)
        self.assertNotIn("PACK", out.stdout)
        self.assertEqual(out.stderr.strip(), "", "a missing backbone is not an error")


def clean_env(**extra: str) -> dict:
    """The session's environment minus the vault this machine happens to declare.

    Every case below is about what the REPOSITORY declares. A `$POLARIS_VAULT` inherited from
    the founder's own shell would make the silent cases pass for the wrong reason.
    """
    env = {k: v for k, v in os.environ.items() if k != "POLARIS_VAULT"}
    return {**env, **extra}


def brief_of(repo, **env: str):
    """The shipped signals script on a host repo, with the environment under test."""
    root = repo / "_polaris"
    return run_script("start", "brief_signals.py", "--root", str(root),
                      "--current", str(root / "state" / "current.md"),
                      cwd=str(repo), env=clean_env(**env))


def stub_vault(body: str) -> Path:
    """A throwaway vault carrying `scripts/contextpack_dashboard.py` and nothing else."""
    vault = Path(tempfile.mkdtemp(prefix="pm-vault-"))
    (vault / "scripts").mkdir()
    (vault / "scripts" / "contextpack_dashboard.py").write_text(body)
    return vault


class TheResolverIsFoundThroughTheDeclaredVault(unittest.TestCase):
    """polaris-os L-ctx step 1 — a product repo carries the contract, never the harness.

    Measured before this change: the vault's resolver answers a product repo with a full
    prose pack (29 and 34 `layer: declared` rows in the two host repos), and `/start` never
    showed one of them, because the package looked for the compiler INSIDE the host and for
    a `decisions/manifest.json` no product repo has. The host is asked first — a repo that
    ships its own compiler owns it — then the vault the repo declares, and nothing else.
    """

    ECHO = "import sys\nprint('ROOT_SEEN: ' + sys.argv[sys.argv.index('--root') + 1])\n"

    def test_no_resolver_and_no_declared_vault_stays_silent(self):
        """(a) #155: a repo with neither must not learn the feature exists."""
        out = brief_of(host_repo())
        self.assertEqual(out.returncode, 0)
        self.assertNotIn("PACK", out.stdout)
        self.assertEqual(out.stderr.strip(), "")

    def test_the_declared_vault_resolver_answers_for_the_host(self):
        """(b) `polaris.vault` is the fallback the whole lane hangs on."""
        repo = host_repo()
        vault = stub_vault("print('AREA: memoria  issues: 3  prs: 1  last_decision: DEC-9')\n"
                           "print('layer: declared  source_id: CONTEXT.md  path: CONTEXT.md"
                           "  freshness: UNKNOWN')\nprint('layer: flight  source_id: b  path: -"
                           "  freshness: UNKNOWN')\n")
        git(repo, "config", "polaris.vault", str(vault))
        out = brief_of(repo)
        self.assertIn("AREA: memoria  issues: 3", out.stdout)
        self.assertIn("PACK: 2 rows held for lane entry", out.stdout)  # 2026-09-23: counted, not printed

    def test_the_environment_wins_over_the_declared_vault(self):
        """(c) `$POLARIS_VAULT` is how one session points somewhere else for one run."""
        repo = host_repo()
        git(repo, "config", "polaris.vault", str(stub_vault("print('FROM: config')\n")))
        out = brief_of(repo, POLARIS_VAULT=str(stub_vault("print('FROM: env')\n")))
        self.assertIn("FROM: env", out.stdout)
        self.assertNotIn("FROM: config", out.stdout)

    def test_a_declared_vault_without_the_script_is_silence_not_an_error(self):
        """(d) A stale `polaris.vault` must degrade to the no-backbone case."""
        repo = host_repo()
        git(repo, "config", "polaris.vault", tempfile.mkdtemp(prefix="pm-empty-"))
        out = brief_of(repo)
        self.assertEqual(out.returncode, 0)
        self.assertNotIn("PACK", out.stdout)
        self.assertEqual(out.stderr.strip(), "")

    def test_a_refusing_vault_resolver_is_loud(self):
        """(e) DB-FR-05: a blocked emission blocks, wherever the resolver lives."""
        repo = host_repo()
        git(repo, "config", "polaris.vault", str(stub_vault(
            "import sys\nsys.stderr.write('DECISION_SCOPE_STALE: docs/x.md\\n')\nsys.exit(2)\n")))
        out = brief_of(repo)
        self.assertIn("PACK: blocked", out.stdout)
        self.assertIn("DECISION_SCOPE_STALE", out.stdout)

    def test_a_prose_pack_needs_no_decisions_manifest(self):
        """(f) T4/#403: the `declared` layer IS a valid pack. Requiring `decisions/manifest.json`
        is what kept every product repo silent — none of them has one."""
        repo = host_repo()
        git(repo, "config", "polaris.vault", str(stub_vault(
            "print('layer: declared  source_id: CONTEXT.md  path: CONTEXT.md"
            "  freshness: UNKNOWN')\n")))
        self.assertFalse((repo / "_polaris" / "decisions" / "manifest.json").exists())
        self.assertIn("PACK: 1 rows held for lane entry", brief_of(repo).stdout)

    def test_the_pack_is_compiled_against_the_checkout_not_the_contract_dir(self):
        """(g) The typed documents live at the CHECKOUT root (`CONTEXT.md`, `decisions/`),
        while `/start` passes `$ROOT` = `<repo>/_polaris`. Compiling the pack against the
        contract directory is what made the two host repos answer 0 `declared` rows instead
        of 29 and 34."""
        repo = host_repo()
        git(repo, "config", "polaris.vault", str(stub_vault(self.ECHO)))
        self.assertIn(f"ROOT_SEEN: {repo}", brief_of(repo).stdout.splitlines(),
                      "a substring assertion passes on `<repo>/_polaris` too")

    def test_the_host_resolver_wins_over_a_healthy_vault_even_when_it_refuses(self):
        """(h) Precedence, at the only moment it is observable: a host that ships its own
        compiler OWNS the answer, so its refusal is the answer — the declared vault is a
        fallback for a repo that has none, never a second opinion on a repo that does. The
        doctor's `resolve` holds the same order."""
        repo = host_repo()
        root = repo / "_polaris"
        (root / "scripts").mkdir()
        (root / "scripts" / "contextpack_dashboard.py").write_text(
            "import sys\nsys.stderr.write('HOST_REFUSED: the host said no\\n')\nsys.exit(2)\n")
        git(repo, "config", "polaris.vault", str(stub_vault("print('FROM: the vault')\n")))
        out = brief_of(repo).stdout
        self.assertIn("PACK: blocked", out)
        self.assertIn("HOST_REFUSED", out)
        self.assertNotIn("FROM: the vault", out)

    def test_a_relative_declared_vault_resolves_against_the_repo_not_the_cwd(self):
        """(i) `git config polaris.vault ../vault` answered 0 rows from one directory and the
        whole pack from another, because a relative path was resolved against the PROCESS's
        cwd. A declaration belongs to the repository, so it resolves against the repository."""
        repo = host_repo()
        vault = stub_vault("print('layer: declared  source_id: CONTEXT.md  path: CONTEXT.md"
                           "  freshness: UNKNOWN')\n")
        (repo / "_polaris" / "vault-link").symlink_to(vault, target_is_directory=True)
        git(repo, "config", "polaris.vault", "vault-link")
        self.assertIn("PACK: 1 rows held for lane entry", brief_of(repo).stdout)

    def test_a_tilde_in_the_declared_vault_is_expanded(self):
        """(j) `~/dev/vault` is how a human writes a path. Unexpanded it is a directory that
        does not exist, and the brief went SILENT — the one shape indistinguishable from a
        repository that never declared a vault at all."""
        repo = host_repo()
        vault = stub_vault("print('FROM: the home vault')\n")
        git(repo, "config", "polaris.vault", f"~/{vault.name}")
        self.assertIn("FROM: the home vault", brief_of(repo, HOME=str(vault.parent)).stdout)

    def test_a_resolver_that_prints_bytes_no_decoder_accepts_does_not_kill_the_brief(self):
        """(k) A `UnicodeDecodeError` out of the compiler is not a pack problem: it took the
        WHOLE brief with it — todos, recent, drift, everything — and a brief that fails a
        session is worse than a thin one."""
        repo = host_repo()
        git(repo, "config", "polaris.vault", str(stub_vault(
            "import sys\nsys.stdout.buffer.write(b'layer: declared \\xff\\xfe bad\\n')\n")))
        out = brief_of(repo)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("TODOS=absent", out.stdout, "the rest of the brief must survive")
        self.assertIn("PACK: 1 rows held for lane entry", out.stdout)

    def test_a_blocked_pack_names_the_resolver_that_refused(self):
        """(l) `PACK: blocked — <CODE>` did not say WHICH compiler refused. With two possible
        places, a reader cannot tell a broken host from a broken vault."""
        repo = host_repo()
        vault = stub_vault("import sys\nsys.stderr.write('DECISION_SCOPE_STALE: x\\n')\n"
                           "sys.exit(2)\n")
        git(repo, "config", "polaris.vault", str(vault))
        out = brief_of(repo).stdout
        self.assertIn("PACK: blocked", out)
        self.assertIn(str(vault / "scripts" / "contextpack_dashboard.py"), out)


class TheBriefMustPrintThePackRowsItResolved(unittest.TestCase):
    """A GUARD, declared as one: nothing in this package renders the brief — the model does,
    from the instruction. So no test here can prove the rows reach a reader.

    What it is guarding against was measured end to end on a host repo: `brief_signals.py`
    printed 42 `layer:` rows and 3 `UNKNOWN:` lines, and the rendered brief carried **zero**,
    summarised into one sentence about `DOMAIN.md` being absent. A row is an ADDRESS; a
    sentence about the rows is not the context, it is the loss of it. The instruction has to
    say VERBATIM, state the cap, and say it in both places a reader looks.
    """

    def test_the_skill_and_the_reference_both_prescribe_verbatim_pack_rows(self):
        from host_repo import PKG
        start = PKG / "skills" / "start"
        for path in (start / "SKILL.md", start / "reference" / "two-stage-brief.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("**Pack**", text, path.name)
            self.assertIn("verbatim", text.lower(), path.name)
            self.assertIn("40", text, f"{path.name} must state the cap, not imply it")
            self.assertIn("layer:", text, path.name)


class TheSkillActuallyCallsIt(unittest.TestCase):
    def test_start_resolves_the_shipped_signals_script(self):
        from host_repo import skill_block
        self.assertIn("brief_signals.py", skill_block("start", "brief_signals.py"))

    def test_selfcheck_is_a_real_check(self):
        out = run_script("start", "brief_signals.py", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("OK", out.stdout)


if __name__ == "__main__":
    unittest.main()
