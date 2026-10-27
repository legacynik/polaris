from pathlib import Path


def test_prose():
    assert "public interface" in Path("guide.md").read_text()
