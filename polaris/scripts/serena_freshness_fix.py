"""CANONICAL Serena freshness fix for polmem component A — covers BOTH stdio-MCP and HTTP delivery.

HOOK POINT: `Tool.apply_ex()` (serena/tools/tools_base.py:330) — the single choke point BOTH
  delivery paths funnel through: the stdio MCP server dispatches SerenaFastMCPTool.execute_fn ->
  `tool.apply_ex(...)` (serena/mcp.py:100), and the HTTP project-server's `_query_project`
  (project_server.py:98) also calls `tool.apply_ex(...)`. Gate on `Tool.is_symbolic()` so the poll
  fires only before tools whose correctness depends on a live LS index (find_referencing_symbols,
  find_symbol, get_symbols_overview, find_implementations, symbolic edits), never before file tools
  that read disk directly.

  Supersedes an earlier version that hooked `ProjectServer._query_project` (HTTP-only) — that hook
  left the stdio-MCP path STALE (A/B measured 8/23 fresh via the MCP tool call), because MCP dispatch
  never touches `_query_project`. The bundle ships via stdio MCP, so apply_ex is the required hook.
  MCP-path A/B with this hook: 23/23 fresh (rename 11/11, delete 8/8, add 4/4), p50 ~409ms.

MECHANISM (unchanged from canonical): a pre-query mtime poll fires Serena's dormant
  workspace/didChangeWatchedFiles LSP notification (+ an open_file() didOpen/didClose cycle for
  brand-new files) so a warm-resident pyright picks up edits made OUTSIDE Serena's own edit tools.
  Config-driven via Project.gather_source_files() / is_ignored_path(); threading.Lock scoped ONLY
  around the in-memory diff+swap.

COLD-START MITIGATION (new): the documented anomaly — a concurrent first-ever burst of
  never-warmed symbols occasionally returns a WRONG empty caller set (~1/60, cold only) — is closed
  by a per-symbol first-query retry-on-empty, scoped to find_referencing_symbols. On the FIRST time
  a given (name_path, relative_path) is queried, if the reference set comes back empty we re-query
  with short backoff (pyright cold-contention transiently returns []). A symbol is retried at most
  once ever (tracked in _seen), so a genuinely zero-reference symbol pays the retry cost exactly
  once and every steady-state query is untouched. An empty served as valid is a health-honesty bug;
  this makes an empty during the cold window earn its answer instead of being trusted blind.

Still a monkeypatch/wrapper — no vendored edit.

ponytail: gather_source_files() re-walks + pathspec-matches every source file per SYMBOLIC query
  (now find_symbol/get_symbols_overview too, not just references) — O(source files). Measured within
  the warm latency envelope on noemi-backend (~1700 files). Ceiling for >10k-file monorepos: cache
  the file list, os.stat on a TTL, or move to a real fs-watcher (Option B in the upstream proposal).
ponytail: retry-on-empty gated to first-ever query per (name_path, relative_path); global lock on the
  _seen set. Upgrade path if a symbol is legitimately empty AND hot: it already only retries once ever.
"""
from __future__ import annotations

import json
import logging
import pathlib
import threading
import time

# ---- freshness poll state (relative_path -> mtime last seen) -------------------------------------
_last_seen_mtimes: dict[str, float] = {}
_state_lock = threading.Lock()

# ---- cold-start retry state (keys queried at least once) -----------------------------------------
_seen_ref_keys: set[tuple[str, str]] = set()
_seen_lock = threading.Lock()

# retry schedule for the cold window (seconds). 3 attempts, ~1.9s worst case, first-query only.
_COLD_RETRY_BACKOFF = (0.3, 0.6, 1.0)

_log = logging.getLogger("serena_freshness_fix_mcp")


# ==================================================================================================
# Freshness poll (config-driven, lock-safe) — identical mechanism to the canonical fix
# ==================================================================================================
def _diff_and_swap(current: dict[str, float], file_change_type) -> list[tuple[str, int]]:  # noqa: ANN001
    """Atomically diff `current` against shared last-seen state and swap it in. The ONLY function
    allowed to read or mutate _last_seen_mtimes."""
    with _state_lock:
        events: list[tuple[str, int]] = []
        for rel, mtime in current.items():
            prev = _last_seen_mtimes.get(rel)
            if prev is None:
                events.append((rel, file_change_type.Created))
            elif mtime > prev:
                events.append((rel, file_change_type.Changed))
        for rel in _last_seen_mtimes:
            if rel not in current:
                events.append((rel, file_change_type.Deleted))
        _last_seen_mtimes.clear()
        _last_seen_mtimes.update(current)
    return events


def _tracked_files(project) -> dict[str, float]:  # noqa: ANN001
    """{relative_path: mtime} for every source file Serena itself would track, per the project's
    config (languages + .gitignore + ignored_paths). One os.stat per file."""
    root = pathlib.Path(project.project_root)
    current: dict[str, float] = {}
    for rel in project.gather_source_files():
        try:
            current[rel] = (root / rel).stat().st_mtime
        except OSError:
            continue
    return current


def poll_and_notify_changes(project) -> int:  # noqa: ANN001
    """Scan config-driven source files for mtime changes since the last poll and fire
    workspace/didChangeWatchedFiles for each Created/Changed/Deleted file on every language server
    the project manages. Returns number of change events sent."""
    from solidlsp.lsp_protocol_handler.lsp_types import FileChangeType

    root = pathlib.Path(project.project_root)
    current = _tracked_files(project)
    events = _diff_and_swap(current, FileChangeType)  # atomic; also swaps the baseline in.

    if not events:
        return 0

    try:
        manager = project.get_language_server_manager_or_raise()
    except Exception:  # noqa: BLE001
        return 0

    changes = [{"uri": (root / rel).resolve().as_uri(), "type": int(ct)} for rel, ct in events]
    created_rels = [rel for rel, ct in events if ct == FileChangeType.Created]

    for ls in manager.iter_language_servers():
        try:
            ls.server.notify.did_change_watched_files({"changes": changes})
        except Exception as e:  # noqa: BLE001
            _log.warning("did_change_watched_files failed: %s", e)
        # Brand-new files: didChangeWatchedFiles(Created) alone is empirically NOT enough for pyright
        # to include them in cross-file references. An open_file() (didOpen/didClose) cycle -- the
        # same path Serena's own read/edit tools use -- forces a parse+bind into the reference graph.
        for rel in created_rels:
            try:
                with ls.open_file(rel):
                    pass
            except Exception as e:  # noqa: BLE001
                _log.warning("open_file(%s) refresh failed: %s", rel, e)

    return len(events)


def _poll_active_project(tool) -> None:  # noqa: ANN001
    """Poll the tool's active project. Best-effort: a poll failure must never break the tool call."""
    try:
        project = tool.agent.get_active_project()
    except Exception:  # noqa: BLE001
        return
    if project is None:
        return
    t0 = time.monotonic()
    try:
        n = poll_and_notify_changes(project)
    except Exception as e:  # noqa: BLE001
        _log.warning("freshness poll failed: %s", e)
        return
    if n:
        _log.info("freshness poll: %d change event(s) before %s (%.1fms)",
                  n, tool.get_name_from_cls(), (time.monotonic() - t0) * 1000)


# ==================================================================================================
# Cold-start retry-on-empty (scoped to find_referencing_symbols, first-query-per-symbol only)
# ==================================================================================================
def _ref_result_is_empty(result: str) -> bool:
    """find_referencing_symbols serializes grouped references to JSON whose TOP-LEVEL keys are the
    caller relative_paths (empty == no callers). Anything unparseable is treated as non-empty so we
    never retry on an error/shortened payload."""
    try:
        parsed = json.loads(result)
    except (TypeError, json.JSONDecodeError):
        return False
    if isinstance(parsed, dict):
        return len(parsed) == 0
    if isinstance(parsed, list):
        return len(parsed) == 0
    return False


def _first_query_key(kwargs: dict) -> tuple[str, str] | None:
    """Return (name_path, relative_path) if this is the FIRST time we've seen it, marking it seen.
    Returns None for a repeat query (no retry) or if params are absent."""
    name_path = kwargs.get("name_path")
    relative_path = kwargs.get("relative_path")
    if name_path is None or relative_path is None:
        return None
    key = (str(name_path), str(relative_path))
    with _seen_lock:
        if key in _seen_ref_keys:
            return None
        _seen_ref_keys.add(key)
    return key


def _retry_cold_empty(tool, original, kwargs, result):  # noqa: ANN001
    """If a first-ever find_referencing_symbols query returned empty, re-query with backoff — cold
    pyright contention transiently returns []. Returns the first non-empty result, else the last."""
    key = _first_query_key(kwargs)
    if key is None or not _ref_result_is_empty(result):
        return result
    for i, backoff in enumerate(_COLD_RETRY_BACKOFF, 1):
        time.sleep(backoff)
        _poll_active_project(tool)  # cheap; also keeps the just-warmed index fresh
        retried = original(tool, log_call=False, catch_exceptions=True, **kwargs)
        if not _ref_result_is_empty(retried):
            _log.info("cold-start retry %d filled empty ref set for %s", i, key)
            return retried
    _log.info("cold-start retry exhausted, empty stands for %s (assumed genuinely 0 refs)", key)
    return result


# ==================================================================================================
# Install
# ==================================================================================================
_REF_TOOL_NAME = "find_referencing_symbols"


def install_patch() -> None:
    from serena.tools.tools_base import Tool

    original = Tool.apply_ex

    def patched(self, log_call: bool = True, catch_exceptions: bool = True, mcp_ctx=None, **kwargs):  # noqa: ANN001
        if self.is_symbolic():
            _poll_active_project(self)
        result = original(self, log_call=log_call, catch_exceptions=catch_exceptions, mcp_ctx=mcp_ctx, **kwargs)
        if self.get_name_from_cls() == _REF_TOOL_NAME:
            result = _retry_cold_empty(self, original, kwargs, result)
        return result

    Tool.apply_ex = patched
    _log.info("serena freshness fix installed on Tool.apply_ex (covers MCP stdio + HTTP; symbolic-gated)")


# ==================================================================================================
# Self-check — runs without a language server; verifies the pure logic (diff/swap, empty detection,
# first-query gating, retry-fills-then-stops). Real end-to-end validation is mcp_ab_test.py.
# ==================================================================================================
def _selfcheck() -> None:
    class _FCT:
        Created, Changed, Deleted = 1, 2, 3

    # diff/swap: first poll = all Created (baseline), second poll detects one Changed + one Deleted.
    _last_seen_mtimes.clear()
    ev1 = _diff_and_swap({"a.py": 1.0, "b.py": 1.0}, _FCT)
    assert {t for _, t in ev1} == {_FCT.Created}, ev1
    ev2 = _diff_and_swap({"a.py": 2.0}, _FCT)  # a changed, b gone
    kinds = {r: t for r, t in ev2}
    assert kinds == {"a.py": _FCT.Changed, "b.py": _FCT.Deleted}, ev2

    # empty detection
    assert _ref_result_is_empty("{}")
    assert _ref_result_is_empty("[]")
    assert not _ref_result_is_empty('{"src/x.py": {"kind": 1}}')
    assert not _ref_result_is_empty("not json")  # never retry on garbage/error

    # first-query gating: same key seen twice -> only first returns a key
    _seen_ref_keys.clear()
    assert _first_query_key({"name_path": "f", "relative_path": "x.py"}) == ("f", "x.py")
    assert _first_query_key({"name_path": "f", "relative_path": "x.py"}) is None
    assert _first_query_key({"name_path": "f"}) is None  # missing param

    # retry: empty first result, original returns non-empty on 1st retry -> that value; seen key skips
    _seen_ref_keys.clear()
    calls = {"n": 0}

    def fake_original(tool, log_call=True, catch_exceptions=True, mcp_ctx=None, **kw):  # noqa: ANN001
        calls["n"] += 1
        return '{"src/caller.py": {"kind": 12}}'  # non-empty on retry

    got = _retry_cold_empty(None, fake_original, {"name_path": "g", "relative_path": "y.py"}, "{}")
    assert not _ref_result_is_empty(got), got
    assert calls["n"] == 1, "should retry exactly once when the first retry fills it"

    # retry on already-seen key is a no-op (no extra original calls)
    calls["n"] = 0
    got2 = _retry_cold_empty(None, fake_original, {"name_path": "g", "relative_path": "y.py"}, "{}")
    assert got2 == "{}" and calls["n"] == 0, "seen key must not retry"

    print("SELF-CHECK OK: diff/swap, empty-detect, first-query gating, retry-then-remember")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _selfcheck()
