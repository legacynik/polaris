import pytest
from feature import round_price


@pytest.mark.parametrize("value, expected", [["1.005","1.01"],["2.675","2.68"],["0","0.00"]])
def test_public_contract(value, expected):
    assert round_price(value) == expected
