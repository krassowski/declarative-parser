from abc import ABC, abstractmethod
from argparse import ArgumentTypeError
from typing import Iterable, Any


def abstract_property(method):
    return property(abstractmethod(method))


class StringHandlingMixin(ABC):
    """Turn string provided on initialization into `data_type`."""

    @abstract_property
    def separator(self):
        """Separator for split operation"""
        pass

    @abstract_property
    def item_type(self):
        pass

    @abstract_property
    def data_type(self):
        pass

    @property
    def require_separator(self):
        """If True and the string has no separator ArgumentTypeError will be raised."""
        return False

    def __init__(self, string):
        if self.require_separator and self.separator not in string:
            name = self.__class__.__name__
            raise ArgumentTypeError(
                f'Given string {string} does not look like a '
                f'{name} (no {self.separator}, which is required)'
            )
        try:
            self.data = self.data_type(
                [
                    self.item_type(value) if value != '' else None
                    for value in string.split(self.separator)
                ]
                if self.separator else
                self.item_type(string)
            )
        except (TypeError, ValueError) as e:
            raise ArgumentTypeError(*e.args)


class Subset(ABC):

    @abstractmethod
    def get_iterator(self, iterable: Iterable[Any]) -> Iterable:
        return iterable

    def get(self, iterable: Iterable[Any]):
        return list(self.get_iterator(iterable))


def positive_int(value):
    value = int(value)
    if value < 0:
        raise ValueError('Indices need to be positive integers')
    return value


def n_tuple(n):
    """Factory for n-tuples."""

    def custom_tuple(data):
        if len(data) != n:
            raise TypeError(
                f'{n}-tuple requires exactly {n} items '
                f'({len(data)} received).'
            )
        return tuple(data)

    return custom_tuple


def dsv(value_type, delimiter=','):
    """Delimiter Separated Values"""
    def closure(value):
        return [
            value_type(y)
            for y in value.split(delimiter)
        ]
    return closure


def one_of(*types):
    """Create a function which attempts to cast input to any of provided types.

    The order of provided `types` is meaningful - if two types accept given
    input value, the first one on list will be used. Types should be able
    to accept a string (if correct) as input value for their constructors.
    """

    def one_of_types(string):
        exceptions = []
        for type_constructor in types:
            try:
                return type_constructor(string)
            except (ArgumentTypeError, TypeError, ValueError) as e:
                exceptions.append(f'{type_constructor.__name__}: {e}')

        names = ', '.join(t.__name__ for t in types)
        exceptions = ''.join('\n\t' + e for e in exceptions)

        raise ArgumentTypeError(
            f'Argument {string} does not match any of allowed types: {names}.\n' +
            f'Following exceptions has been raised: {exceptions}'
        )

    return one_of_types


static = staticmethod


class Indices(Subset, StringHandlingMixin):

    separator = ','

    # negative indices may be ambiguous
    item_type = static(positive_int)

    # each column should be used once
    data_type = set

    def get_iterator(self, iterable):
        for i, value in enumerate(iterable):
            if i in self.data:
                yield value


class Slice(Subset, StringHandlingMixin):

    require_separator = True
    separator = ':'
    item_type = int

    data_type = static(one_of(n_tuple(2), n_tuple(3)))

    def get_iterator(self, iterable):
        return iterable[slice(*self.data)]


class Range(Subset, StringHandlingMixin):
    """Simplified slice with '-' as separator.

    Handles only start and end, does not support negative numbers.
    """

    require_separator = True
    separator = '-'
    item_type = int

    # if user provides '1-3-5' or '1--3' we will not handle that
    # (such values are ambiguous, possibly typos)
    data_type = static(n_tuple(2))

    def get_iterator(self, iterable):
        return iterable[slice(*self.data)]
