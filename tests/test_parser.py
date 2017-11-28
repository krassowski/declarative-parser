import pytest

from declarative_parser import Argument, Parser, action
from declarative_parser.types import positive_int

from utilities import parsing_error


class Success(Exception):
    pass


def parse_factory(constructor):
    def parse(commands):
        parser = constructor()
        options = parser.parse_args(commands.split())
        return options
    return parse


def test_action():

    class TestParser(Parser):

        @action
        def version(self):
            raise Success('This is the 2.0 version')

    # test mode which is a required argument
    with pytest.raises(Success, message='This is the 2.0 version'):
        parser = TestParser()
        parser.parse_args(['--version'])


def test_arguments_interplay(capsys):

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

    parse = parse_factory(ShoppingCart)

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


def test_parallel():

    supported_formats = ['png', 'jpeg', 'gif']

    class InputOptions(Parser):
        format = Argument(default='png', choices=supported_formats)

    class OutputOptions(Parser):
        format = Argument(default='jpeg', choices=supported_formats)
        scale = Argument(type=int, default=100, help='Rescale image to % of original size')

    class ImageConverter(Parser):
        description = 'This app converts images'

        verbose = Argument(action='store_true')
        input = InputOptions()
        output = OutputOptions()

    parse = parse_factory(ImageConverter)

    opts = parse('--verbose input --format jpeg output --format gif --scale 50')

    assert opts.input.format == 'jpeg'
    assert opts.output.format == 'gif'
    assert opts.output.scale == 50
    assert opts.verbose is True


def test_parser(capsys):

    class Greetings(Parser):

        name = Argument(
            help='Whom to greet',
            optional=False
        )

        count = Argument(
            default=1,
            type=int,
            short='c',
            help='Number of greetings.'
        )

        def produce(self, unknown_args):
            opts = self.namespace

            opts.greetings = f'Hello {opts.name}!\n' * opts.count

            return opts

    parse = parse_factory(Greetings)

    opts = parse('joe')
    assert opts.greetings == 'Hello joe!\n'
    assert opts.name == 'joe'
    assert opts.count == 1

    for command in ['joe --count 2', 'joe --c 2']:
        assert parse(command).greetings == 'Hello joe!\nHello joe!\n'

    with parsing_error(match='unrecognized arguments: --cont 4'):
        parse('joe --cont 4')

    with parsing_error(match='the following arguments are required: name'):
        parse('')
