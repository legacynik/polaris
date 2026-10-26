"""The two risks #345 names, as tests: a duplicate issue, and a lie about "no crash".

Fixture-only: no browser, no network, no `gh`. What is proved here is the part that can
lie — the verdict a run reports and the identity of the finding it files.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "crash_report.py"
_spec = importlib.util.spec_from_file_location("crash_report", SCRIPT)
if _spec is None or _spec.loader is None:
    raise AssertionError(f"crash_report.py did not resolve at {SCRIPT} — the suite under test "
                         "is missing, which is a failure to report, not an import to crash on")
cr = importlib.util.module_from_spec(_spec)
sys.modules["crash_report"] = cr
_spec.loader.exec_module(cr)


SURFACE = ("/", "/a", "/b")


def run(attempted, findings=(), budget=8):
    return {"target": "https://staging.example.invalid", "budget": budget,
            "surface": list(SURFACE), "attempted": list(attempted),
            "findings": [dict(f) for f in findings]}


HANG = {"route": "/generate", "klass": "gen_hang", "evidence": "transcript.log",
        "domain": "gates", "impact": "2", "cost": "M",
        "symptom": "generate never returned, waited 421s"}
REPRO = "curl -f https://staging.example.invalid/health returns status 200"


class NoCrashMustBeEarned(unittest.TestCase):
    def test_zero_paths_attempted_cannot_report_no_crash(self):
        code, lines = cr.verdict(run([]))
        self.assertEqual(code, 1, lines)
        self.assertIn("attempted", "\n".join(lines).lower())

    def test_no_crash_names_every_path_it_actually_tried(self):
        code, lines = cr.verdict(run(["/", "/a"]))
        self.assertEqual(code, 0, lines)
        text = "\n".join(lines)
        self.assertIn("NO CRASH FOUND", text)
        self.assertIn("/a", text)
        self.assertIn("2/3", text)

    def test_a_run_beyond_its_budget_is_refused(self):
        code, lines = cr.verdict(run(["/", "/a", "/b"], budget=2))
        self.assertEqual(code, 1, lines)
        self.assertIn("budget", "\n".join(lines).lower())

    def test_a_finding_missing_its_route_or_symptom_is_refused(self):
        code, lines = cr.verdict(run(["/"], [{"klass": "gen_hang"}]))
        self.assertEqual(code, 1, lines)

    def test_a_finding_without_a_glossary_domain_is_refused(self):
        nameless = {k: v for k, v in HANG.items() if k != "domain"}
        code, lines = cr.verdict(run(["/"], [nameless]))
        self.assertEqual(code, 1, lines)
        self.assertIn("domain", "\n".join(lines))

    def test_a_run_with_no_surface_cannot_invent_its_coverage(self):
        record = run(["/", "/a"])
        del record["surface"]
        code, lines = cr.verdict(record)
        self.assertEqual(code, 1, lines)
        self.assertIn("surface", "\n".join(lines))

    def test_a_surface_smaller_than_what_was_visited_is_refused(self):
        record = run(["/", "/a", "/b", "/c"])
        code, lines = cr.verdict(record)
        self.assertEqual(code, 1, lines)


class OneCrashIsOneIssue(unittest.TestCase):
    def test_the_same_crash_twice_produces_the_same_title(self):
        again = dict(HANG, symptom="generate never returned, waited 388s",
                     evidence="other.log")
        self.assertEqual(cr.title_of(HANG), cr.title_of(again))

    def test_a_different_route_is_a_different_finding(self):
        self.assertNotEqual(cr.title_of(HANG), cr.title_of(dict(HANG, route="/chat")))

    def test_a_different_failure_class_is_a_different_finding(self):
        self.assertNotEqual(cr.title_of(HANG), cr.title_of(dict(HANG, klass="console")))

    def test_the_title_carries_the_fingerprint_so_the_tracker_can_search_it(self):
        self.assertIn(cr.fingerprint(HANG), cr.title_of(HANG))


class TheRunProposesTheHumanFiles(unittest.TestCase):
    """The crasher proposes; a person picks; issue-contract files. A run that files by itself
    opened a thousand issues, so nothing here may print a filing command."""

    def _main(self, record, *extra, open_issues=None):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.json"
            path.write_text(json.dumps(record))
            argv = ["--run", str(path), *extra]
            if open_issues is not None:
                (Path(td) / "open.json").write_text(json.dumps(open_issues))
                argv += ["--open-issues", str(Path(td) / "open.json")]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cr.main(argv)
            return code, out.getvalue(), json.loads(path.read_text())

    def test_a_run_with_findings_proposes_and_prints_no_filing_command(self):
        code, out, _ = self._main(run(["/"], [HANG, dict(HANG, route="/chat")]))
        self.assertEqual(code, 3, out)
        self.assertIn("PROPOSAL", out)
        self.assertNotIn("gh issue create", out)
        self.assertNotIn("build_issue", out)

    def test_each_proposed_finding_carries_fingerprint_title_and_repro(self):
        finding = dict(HANG, repro=REPRO)
        code, out, _ = self._main(run(["/"], [finding]))
        self.assertEqual(code, 3, out)
        for part in (cr.fingerprint(finding), cr.title_of(finding), REPRO):
            self.assertIn(part, out)

    def test_the_same_crash_twice_in_one_run_is_proposed_once(self):
        again = dict(HANG, symptom="generate never returned, waited 388s")
        code, out, _ = self._main(run(["/"], [HANG, again]))
        self.assertEqual(code, 3, out)
        self.assertEqual(out.count(cr.title_of(HANG)), 1, out)

    def test_an_already_open_twin_is_named_beside_the_finding(self):
        twin = [{"number": 42, "state": "OPEN", "title": cr.title_of(HANG)},
                {"number": 7, "state": "OPEN", "title": "unrelated"}]
        code, out, _ = self._main(run(["/"], [HANG]), open_issues=twin)
        self.assertEqual(code, 3, out)
        self.assertIn("#42", out)
        self.assertNotIn("#7", out)

    def test_an_unattended_run_writes_the_proposal_into_the_record_and_files_nothing(self):
        finding = dict(HANG, repro=REPRO)
        code, out, record = self._main(run(["/"], [finding, finding]), "--unattended")
        self.assertEqual(code, 3, out)
        self.assertNotIn("gh issue", out)
        self.assertEqual([p["fingerprint"] for p in record["proposal"]], [cr.fingerprint(finding)])
        self.assertEqual(record["proposal"][0]["repro"], REPRO)
        self.assertIsNone(record["proposal"][0]["twin"])

    def test_a_finding_without_a_reproducing_command_is_proposed_for_a_person(self):
        _, _, record = self._main(run(["/"], [HANG]), "--unattended")
        self.assertEqual(record["proposal"][0]["afk_human"], "yes")
        _, _, record = self._main(run(["/"], [dict(HANG, repro=REPRO)]), "--unattended")
        self.assertEqual(record["proposal"][0]["afk_human"], "no")

    def test_an_unreadable_open_issue_list_is_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.json"
            path.write_text(json.dumps(run(["/"], [HANG])))
            (Path(td) / "open.json").write_text("{nope")
            self.assertEqual(cr.main(["--run", str(path), "--open-issues",
                                      str(Path(td) / "open.json")]), 2)


class UnusableInputIsNeverGreen(unittest.TestCase):
    def test_an_absent_run_file_is_exit_2(self):
        self.assertEqual(cr.main(["--run", "/nonexistent/run.json"]), 2)

    def test_a_broken_run_file_is_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "run.json"
            p.write_text("{nope")
            self.assertEqual(cr.main(["--run", str(p)]), 2)

    def test_selfcheck_passes(self):
        self.assertEqual(cr.main(["--selfcheck"]), 0)

    def test_a_real_run_file_is_read_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "run.json"
            p.write_text(json.dumps(run(["/", "/a"])))
            self.assertEqual(cr.main(["--run", str(p)]), 0)


if __name__ == "__main__":
    unittest.main()
