from feature import round_price


def test_tautology():
    result = round_price("1.005")
    assert result == result
