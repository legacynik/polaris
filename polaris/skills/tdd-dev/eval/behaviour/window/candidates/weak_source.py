from pathlib import Path


def test_source_text():
    assert "RULE_READY = True" in Path("feature.py").read_text()
