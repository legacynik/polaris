import pytest
from feature import round_price


@pytest.mark.parametrize("value, expected", [["-1.005","-1.01"],["0.005","0.01"],["4","4.00"]])
def test_public_contract(value, expected):
    assert round_price(value) == expected
