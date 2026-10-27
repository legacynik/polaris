import feature


def test_private_helper():
    assert feature._legacy(" A!!B ") == "a-b"
