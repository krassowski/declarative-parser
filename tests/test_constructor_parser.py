import pytest

from declarative_parser.parser import Argument
from declarative_parser.constructor_parser import ConstructorParser, FunctionParser

from utilities import parsing_output


class Success(Exception):
    pass


def test_parser(capsys):

    class MyProgram:

        name = 'some_method'
        help = 'Some important text help'

        other_argument = Argument(
            type=int,
            help='Only integer numbers!',
            default=0,
        )

        def __init__(self, mode, my_argument: float=None, other_argument=None):
            """

            Args:
                mode: This argument has to be passed!
                my_argument: Help and documentation for my_argument
                other_argument: Documentation for the other_argument
            """

            if mode == 'active':
                raise Success('In active mode!')
            if my_argument == 1.4:
                raise Success('Correct Argument provided +1')
            if type(other_argument) is int:
                raise Success(f'Parsed +{other_argument}')

        def run(self, experiment):
            raise Success('Run +10')

    def parse(commands):
        parser = ConstructorParser(MyProgram)
        options = parser.parse_args(commands.split())
        return parser.constructor(**vars(options))

    # test mode which is a required argument
    with pytest.raises(Success, message='In active mode!'):
        parse('active')

    # test my_argument
    with pytest.raises(Success, message='Correct Argument provided +1'):
        parse('a --my_argument 1.4')

    # test run
    with pytest.raises(Success, message='Run +10'):
        program = parse('a --my_argument 2.1')
        program.run()

    # test other_argument
    with pytest.raises(Success, message='Parsed +5'):
        parse('a --other_argument 5')

    with parsing_output(capsys, contains='Some important text help'):
        parse('--help')

    # test arguments help
    arguments_help = {
        'This argument has to be passed!': True,
        'Help and documentation for my_argument': True,
        'Only integer numbers!': True,
        # Following should not be shown, as it is overwritten by
        # "integers-only" text above from Argument definition:
        'Documentation for the other_argument': False
    }

    for text, is_expected in arguments_help.items():
        contains, does_not_contain = None, None
        if is_expected:
            contains = text
        else:
            does_not_contain = text

        with parsing_output(capsys, contains=contains, does_not_contain=does_not_contain):
            parse('-h')


def test_function_parser():

    def calc_exponent(base: float, exponent: int=2):
        return base ** exponent

    def get_result(command_line):
        parser = FunctionParser(calc_exponent)
        commands = command_line.split()
        options = parser.parse_args(commands)
        return parser.constructor(**vars(options))

    assert get_result('2 --exponent 3') == 2 * 2 * 2
    assert get_result('2') == 2 * 2

    calc_exponent.exponent = Argument(short='n', type=int, default=1)

    assert get_result('2 -n 4') == 2 * 2 * 2 * 2
    assert get_result('2') == 2


def test_analyze_docstring():

    google_docstring = """Some docstring.
    
    Some details.
    
    Arguments:
        my_arg: is an important argument
        active: should some feature be active
                or maybe it should be not?
        spread:
            should be big or small?
            how big or how small?
            
    Example:
        examples should not be interpreted as an argument
    
    Returns:
        A list of results
    """

    numpy_docstring = """Some docstring,
    
    Some details.

    Parameters
    ----------
    my_arg
        is an important argument
    active
        should some feature be active
        or maybe it should be not?
    spread
        should be big or small?
        how big or how small?
        
    Returns
    -------
    list
        A list of results
    """

    rst_docstring = """Some docstring.
    
    Some details.
    
    :param my_arg: is an important argument
    :param active: should some feature be active
            or maybe it should be not?
    :param spread:
        should be big or small?
        how big or how small?
    :returns: A list of results
            
    :Example:
    
    examples should not be interpreted as an argument
    """

    from declarative_parser.constructor_parser import docstring_analyzers

    test_data = {
        'google': google_docstring,
        'numpy': numpy_docstring,
        'rst': rst_docstring
    }

    for convention, docstring in test_data.items():
        print(convention)

        analyze_docstring = docstring_analyzers[convention]

        args = analyze_docstring(docstring)

        expected_args = {
            'my_arg': 'is an important argument',
            'active': 'should some feature be active or maybe it should be not?',
            'spread': 'should be big or small? how big or how small?'
        }

        for name, value in expected_args.items():
            assert args[name] == value

        assert 'Example' not in args

