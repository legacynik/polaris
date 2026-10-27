from feature import allow


def test_tautology():
    result = allow([0, 1], 10)
    assert result == result
