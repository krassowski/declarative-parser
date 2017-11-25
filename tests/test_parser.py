import pytest

from declarative_parser import Argument, Parser, action
from declarative_parser.types import positive_int

from utilities import parsing_error


class Success(Exception):
    pass


def test_action():

    class TestParser(Parser):

        @action
        def version(self):
            raise Success('This is the 2.0 version')

    # test mode which is a required argument
    with pytest.raises(Success, message='This is the 2.0 version'):
        parser = TestParser()
        parser.parse_args(['--version'])


def test_parser(capsys):

    class ShoppingCart(Parser):

        products = Argument(
            type=str,
            nargs='*'
        )

        counts = Argument(
            type=positive_int,
            help='How many products of each type there are in your trolley?',
            nargs='*',
            as_many_as=products
        )

    def parse(commands):
        parser = ShoppingCart()
        options = parser.parse_args(commands.split())
        return options

    # does it fail properly?
    with parsing_error(match='counts for 2 products provided, expected for 1'):
        parse('--products milk --counts 3 1')

    with parsing_error(match='counts for 1 products provided, expected for 2'):
        parse('--products milk coffee --counts 3')

    with parsing_error(match='argument --counts: invalid positive_int value: \'-1\''):
        parse('--products milk coffee --counts 3 -1')

    # does it work at all?
    opts = parse('--products milk coffee --counts 3 1')

    assert opts.products == ['milk', 'coffee']
    assert opts.counts == [3, 1]

