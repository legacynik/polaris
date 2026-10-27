import pytest
from feature import allow


@pytest.mark.parametrize("events, now, expected", [[[-10,-9],0,True],[[1,2],0,True],[[-1],0,True],[[-1,0],0,False]])
def test_public_contract(events, now, expected):
    assert allow(events, now) == expected
