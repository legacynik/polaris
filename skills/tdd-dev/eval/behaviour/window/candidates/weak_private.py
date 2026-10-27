import feature


def test_private_helper():
    assert feature._legacy([0, 1], 10) == True
