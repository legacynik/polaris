import pytest
from feature import slug


@pytest.mark.parametrize("value, expected", [[" A!!B ","a-b"],["---","item"],["9","9"]])
def test_public_contract(value, expected):
    assert slug(value) == expected
