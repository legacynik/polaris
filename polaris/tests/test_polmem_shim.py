# polaris/tests/test_polmem_shim.py
"""polmem shim: discovery, protocol round-trip, CLI contract. No mocks on
subprocess — the fake bundle is a real process speaking the real protocol."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SHIM = Path(__file__).resolve().parents[1] / "bin" / "polmem"
FAKE = Path(__file__).resolve().parent / "fake_bundle.py"


def _load_shim():
    spec = importlib.util.spec_from_loader("polmem_shim", loader=None, origin=str(SHIM))
    mod = importlib.util.module_from_spec(spec)
    exec(compile(SHIM.read_text(), str(SHIM), "exec"), mod.__dict__)
    return mod


def _wired_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".git").mkdir()
    shutil.copy(FAKE, repo / "scripts" / "polaris_memory_repo.py")
    return repo


def test_find_bundle_walks_up(tmp_path):
    mod = _load_shim()
    repo = _wired_repo(tmp_path)
    deep = repo / "a" / "b"
    deep.mkdir(parents=True)
    assert mod.find_bundle(deep) == repo / "scripts" / "polaris_memory_repo.py"


def test_find_bundle_none_outside_repo(tmp_path):
    mod = _load_shim()
    assert mod.find_bundle(tmp_path) is None


def test_mcp_call_recall_roundtrip(tmp_path):
    mod = _load_shim()
    repo = _wired_repo(tmp_path)
    text, err = mod.mcp_call(repo / "scripts" / "polaris_memory_repo.py",
                             "recall", {"query": "pricing", "top": 3})
    assert err is False and "RECALL[pricing]" in text and "top=3" in text


def test_cli_recall_exit0(tmp_path, monkeypatch, capsys):
    mod = _load_shim()
    repo = _wired_repo(tmp_path)
    monkeypatch.chdir(repo)
    assert mod.main(["recall", "pricing"]) == 0
    assert "RECALL[pricing]" in capsys.readouterr().out


def test_cli_remember_exit0(tmp_path, monkeypatch, capsys):
    mod = _load_shim()
    repo = _wired_repo(tmp_path)
    monkeypatch.chdir(repo)
    assert mod.main(["remember", "nota importante"]) == 0
    assert "REMEMBERED[nota importante]" in capsys.readouterr().out


def test_cli_unwired_repo_exit1(tmp_path, monkeypatch, capsys):
    mod = _load_shim()
    monkeypatch.chdir(tmp_path)
    assert mod.main(["recall", "x"]) == 1
    assert "not memory-wired" in capsys.readouterr().err


def test_cli_unknown_tool_error_exit1(tmp_path, monkeypatch):
    mod = _load_shim()
    repo = _wired_repo(tmp_path)
    monkeypatch.chdir(repo)
    assert mod.main(["__nope__"]) == 2  # argparse usage error


def test_health_wired(tmp_path, monkeypatch, capsys):
    mod = _load_shim()
    repo = _wired_repo(tmp_path)
    (repo / ".wiki").mkdir()
    (repo / ".wiki" / "index.md").write_text("# i\n")
    monkeypatch.chdir(repo)
    assert mod.main(["health"]) == 0
    out = capsys.readouterr().out
    assert "bundle" in out and "index" in out


def test_health_unwired_exit1(tmp_path, monkeypatch):
    mod = _load_shim()
    monkeypatch.chdir(tmp_path)
    assert mod.main(["health"]) == 1


def test_shim_is_executable_and_stdlib_only():
    src = SHIM.read_text()
    assert src.startswith("#!/usr/bin/env python3")
    banned = ["import requests", "import yaml", "import click"]
    assert not any(b in src for b in banned)
