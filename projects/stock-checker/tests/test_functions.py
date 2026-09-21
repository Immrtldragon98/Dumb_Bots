import pytest
from src.functions import is_below_minimum_stock


def test_is_below_minimum_stock_valid_cases():
    assert is_below_minimum_stock(5, 10) == True
    assert is_below_minimum_stock(10, 10) == False
    assert is_below_minimum_stock(15, 10) == False

def test_is_below_minimum_stock_invalid_cases():
    with pytest.raises(ValueError, match='Quantity cannot be negative'):
        is_below_minimum_stock(-5, 10)
    with pytest.raises(ValueError, match='Quantity cannot be negative'):
        is_below_minimum_stock(-10, 10)

def test_is_below_minimum_stock_edge_cases():
    assert is_below_minimum_stock(0, 0) == False
    assert is_below_minimum_stock(0, 1) == True
