import pytest

from utils.helper import calculate_total


def test_calculate_total_integers():
    assert calculate_total([1, 2, 3]) == 6


def test_calculate_total_floats():
    assert calculate_total([1.5, 2.5]) == 4.0


def test_calculate_total_empty_list():
    assert calculate_total([]) == 0


def test_calculate_total_rejects_strings():
    with pytest.raises(TypeError):
        calculate_total([1, "two", 3])


def test_calculate_total_rejects_non_iterable():
    with pytest.raises(TypeError):
        calculate_total(123)