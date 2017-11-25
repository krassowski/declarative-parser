from argparse import ArgumentTypeError

import pytest

from declarative_parser.types import Slice, Range
from declarative_parser.types import Indices
from declarative_parser.types import positive_int


def check_type_cases(type_callable, cases, items):

    for constructor, result in cases.items():
        tested = type_callable(constructor)
        assert tested.get(items) == result


def check_wrong_cases(type_callable, incorrect_cases):
    for constructor in incorrect_cases:
        with pytest.raises(ArgumentTypeError):
            type_callable(constructor)


def test_slice():
    items = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    cases = {
        '2:3': [2],
        '2:5': [2, 3, 4],
        '5:2:-1': [5, 4, 3],
        '2:5:2': [2, 4],
        ':5': [0, 1, 2, 3, 4],
        '::-1': list(reversed(items)),
        ':': items,
        ':-2': items[:-2]
    }

    check_type_cases(Slice, cases, items)

    incorrect_slices = [
        '1',
        '1:2:3:4'
    ]

    check_wrong_cases(Slice, incorrect_slices)


def test_indices():
    items = ['a', 'b', 'c', 'd', 'e']

    cases = {
        '0': ['a'],
        '0,1': ['a', 'b'],
        '1,3': ['b', 'd']
    }

    check_type_cases(Indices, cases, items)


def test_range():
    items = [0, 1, 2, 3, 4]

    cases = {
        '2-3': [2],
        '2-5': [2, 3, 4]
    }

    check_type_cases(Range, cases, items)

    incorrect_ranges = [
        '2',
        '1--2',
        '1-2-3'
    ]

    check_wrong_cases(Range, incorrect_ranges)


def test_positive_int():

    with pytest.raises(ValueError):
        positive_int('-5')

    assert positive_int('5') == 5
