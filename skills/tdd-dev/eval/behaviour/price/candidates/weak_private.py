import feature


def test_private_helper():
    assert feature._legacy("1.005") == "1.01"
