# Protocol — file layout, JSON schemas, checklist detail

## Layout (gitignore all of it — local working state, not source)

```
.review-gate/
  findings/<hash>-standards.json   written by the Standards pass
  findings/<hash>-spec.json        written by the Spec pass
  approvals/<hash>.json            written ONLY by finalize_review.py
```
`<hash>` = `git write-tree` of the currently staged index. Recomputed fresh every time —
never cached, never passed by the caller and trusted.

## Findings file schema (one per axis, never merged)

```json
{
  "axis": "standards",
  "scope": {"files": ["a.py", "b.py"], "diff_lines": 42},
  "findings": [
    {
      "file": "path/relative/to/repo/root.py",
      "line": 42,
      "severity": "CRITICAL",
      "summary": "one sentence, what's wrong",
      "evidence": "the exact source line quoted — required, no exceptions"
    }
  ]
}
```
`severity` is `CRITICAL` or `INFORMATIONAL` only. A finding without `evidence` fails
`finalize_review.py`'s structural validation — the whole run aborts, nothing is written.
This is deliberate: "quote the line or the finding doesn't count" is what stops a reviewer
pass from hand-waving a verdict (G2.7 — the reviewer itself is the piece that can be broken).

`scope` is **required on every findings file, even an empty one**. Run
`finalize_review.py --print-scope --cwd .` before dispatching Standards/Spec and embed its
output verbatim as `scope` in both files. `finalize_review.py` recomputes the real staged
file list + diff line count itself and rejects a `scope` that doesn't cover it — this is what
stops "two empty JSON files, written in two seconds with zero relation to the diff" from
passing as "reviewed, nothing found" (the literal reproduced bypass, bypass-test case
3a). It does **not** prove the pass reasoned about the diff's meaning — only that whoever
wrote the findings file knew what was actually staged. Genuine-reasoning authenticity stays
undecidable by a stdlib script; that gap is declared, not hidden.

## Approval file schema (written by `finalize_review.py` only)

```json
{
  "tree_hash": "...", "verdict": "PASS | PASS-WITH-WAIVER | FAIL",
  "reasons": ["..."], "standards_findings": 0, "spec_findings": 0,
  "waivers": ["MONEY-PATH", "app.py:12"],
  "findings_digest": "sha256 of standards+spec file bytes, concatenated",
  "standards_path": "...", "spec_path": "...", "created_at": "ISO8601"
}
```
`gate_hook.py` trusts `verdict` only after recomputing `findings_digest` from the two named
files and confirming it still matches — an approval that doesn't name real, matching findings
files is treated as forged, not as a pass (see `bypass-test.md` case 2/3).

## Standards axis — baseline checklist (CRITICAL unless noted)

Money-path, mock-only-test, and untracked-secret items below are **scripted**
(`scan_blockers.py`) — the reviewer's job is to confirm/dispute the scan's flag, not to
re-discover it by eye. Everything else here is human/LLM judgment, cited with evidence:

- SQL/query built by string concatenation instead of parameterized calls or an ORM builder
- output from an LLM/tool call trusted downstream without validation (trust-boundary)
- a shell/subprocess call assembled from unsanitized input
- a secret or credential literal anywhere in the diff
- a race condition on shared/mutable state with no lock or transaction
- a new enum/union case not handled at every existing switch/match over that type
- a money/pricing/margin/tax path changed with no test-file companion **correlated to that
  file** (stem or content) and no `MONEY-PATH` waiver (scripted block — G3.7; an unrelated
  test elsewhere in the same changeset does not satisfy this — that was the literal
  reproduced bypass: `pricing.py`'s margin bug riding past next to `test_unrelated.py`)
- a test file that only mocks the exact surface it claims to exercise, no STRUCTURED real-IO
  marker (`@real_test`, `@pytest.mark.integration`, a `# real-test`/`# integration-test`
  comment — scripted flag, G2.1/G2.6; a bare word like "real" in an unrelated comment no
  longer clears it, that was the reproduced bypass; does not auto-block, must be addressed
  in a finding)
- an untracked file matching a secret or shell-injection pattern in the same changeset
  (scripted block — G9.1)

INFORMATIONAL: async/sync mixing, an obvious N+1 on a hot path, an internal error/stack
trace reaching a client-facing boundary, naming/format drifting from the repo's documented
convention.

## Spec axis — baseline checklist

- does the diff implement what the linked issue/plan asked, no more and no less (scope
  drift is a finding, not silently accepted or silently blocked)
- does it close the item it claims to close (traceability — cite the issue/plan reference)
- are stated acceptance criteria addressed one-to-one
- did the diff make a decision the plan explicitly left open — must surface as a finding,
  never resolved silently by whoever wrote the code

## Why Standards and Spec never merge into one ranking

A Standards CRITICAL is not a substitute verdict for a Spec gap, and vice versa — merging
them into one ranking lets whichever axis found more issues mask the other. `critical_reasons`
runs identically over both, `decide_verdict` concatenates the reason lists but the two
findings files stay on disk as two separate artifacts, readable and citable independently.
