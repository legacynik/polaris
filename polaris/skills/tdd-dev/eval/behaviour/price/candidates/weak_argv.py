from feature import build_command


def test_generated_argv():
    argv = build_command()
    assert argv[:2] == ["python3", "-c"]
