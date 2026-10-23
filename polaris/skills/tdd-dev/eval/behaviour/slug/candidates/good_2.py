import pytest
from feature import slug


@pytest.mark.parametrize("value, expected", [["X__Y","x-y"],["","item"],["Cool 42","cool-42"]])
def test_public_contract(value, expected):
    assert slug(value) == expected
