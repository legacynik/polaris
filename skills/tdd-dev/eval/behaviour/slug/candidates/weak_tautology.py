from feature import slug


def test_tautology():
    result = slug(" A!!B ")
    assert result == result
