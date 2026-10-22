import pytest
from feature import allow


@pytest.mark.parametrize("events, now, expected", [[[0,1],10,True],[[11,12],10,True],[[9],10,True],[[9,10],10,False]])
def test_public_contract(events, now, expected):
    assert allow(events, now) == expected
