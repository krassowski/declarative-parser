from argparse import Namespace
from contextlib import contextmanager, redirect_stderr
from io import StringIO

import pytest


@contextmanager
def parsing_output(capsys, contains=None, does_not_contain=None):
    text = Namespace()
    capsys.readouterr()     # clean buffers
    with pytest.raises(SystemExit):
        yield text
    text.std, text.err = capsys.readouterr()
    if contains:
        if contains not in text.std:
            raise AssertionError(f'{contains} not in {text.std}')
    if does_not_contain:
        if does_not_contain in text.std:
            raise AssertionError(f'{does_not_contain} in {text.std}')


class ParsingError(Exception):
    pass


@contextmanager
def parsing_error(match=None):
    error_file = StringIO()
    with redirect_stderr(error_file):
        with pytest.raises(ParsingError, match=match):
            try:
                yield
            except SystemExit as exit_exception:
                if exit_exception.code == 2:
                    usage_and_error_msg = error_file.getvalue()
                    raise ParsingError(usage_and_error_msg)
