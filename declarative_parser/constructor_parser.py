import inspect
import re
from collections import defaultdict

from .parser import Parser, Argument


class DocstringAnalyzer:

    def __init__(self, argument_definition, argument_sections, inline=False, indent_sensitive=False, skip=None):
        """Create a docstring analyzer.

        Args:
            argument_definition: regex string matching a single argument
            argument_sections: list or argument section initial strings
            inline: will the argument definition catch value too?
            indent_sensitive: are argument values finished with dedent?
            skip: compiled regex used to skip false positive value matches
        """
        self.argument_definition = re.compile(argument_definition)
        self.argument_sections = argument_sections
        self.indent_sensitive = indent_sensitive
        self.inline_value = inline
        self.skip = skip

    @staticmethod
    def measure_indent(line):
        """Measure indent defined as number of initial whitespace characters"""
        indent = 0
        for c in line:
            if c.isspace():
                indent += 1
            else:
                break
        return indent

    def analyze(self, docstring: str):
        """Analyze docstring and collect arguments with descriptions.

        All arguments have to start with a lowercase letter, be followed
        with a colon (:) and then with the description of the argument.
        """
        help_strings = defaultdict(list)
        collect_help = False
        empty_lines = 0
        base_indent = None
        argument = None

        for raw_line in docstring.split('\n'):
            line = raw_line.strip()

            if not line:
                empty_lines += 1
                collect_help = False
            else:
                empty_lines = 0

            if any(line.startswith(section) for section in self.argument_sections):
                collect_help = True
                base_indent = self.measure_indent(raw_line)

            if collect_help:

                match = self.argument_definition.match(line)

                if self.indent_sensitive:
                    indent = self.measure_indent(raw_line)
                    if indent != base_indent:
                        match = False

                if match:
                    argument = match.group('name')

                    if self.inline_value:
                        value = match.group('value').lstrip()
                        if value:
                            help_strings[argument].append(value)

                elif argument and (not self.skip or not self.skip.match(line)):
                    help_strings[argument].append(line)

        for key, value in help_strings.items():
            help_strings[key] = ' '.join(value)

        return help_strings


google_docstring_analyzer = DocstringAnalyzer(
    argument_definition=r'(?P<name>.+?):(?P<value>.*)',
    argument_sections=['Arguments:', 'Args:'],
    inline=True
)

numpy_docstring_analyzer = DocstringAnalyzer(
    argument_definition=r'(?P<name>[^-]+)',
    argument_sections=['Parameters'],
    indent_sensitive=True,
    skip=re.compile(r'[-]+')
)

rst_docstring_analyzer = DocstringAnalyzer(
    argument_definition=r':param (?P<name>.+?):(?P<value>.*)',
    argument_sections=[':param '],
    inline=True,
    skip=re.compile(r':.*')
)


docstring_analyzers = {
    'numpy': numpy_docstring_analyzer.analyze,
    'google': google_docstring_analyzer.analyze,
    'rst': rst_docstring_analyzer.analyze
}


def is_set(value):
    return not (value == inspect._empty)


def empty_to_none(value):
    if not is_set(value):
        return None
    return value


class ConstructorParser(Parser):
    """Create a parser from an existing class, using arguments from __init__

    as well as arguments and sub-parsers defined as class properties.

    Example usage::

        import argparse

        class MyProgram:

            database = Argument(
                type=argparse.FileType('r'),
                help='Path to file with the database'
            )

            def __init__(self, threshold:float=0.05, database=None):
                # do some magic
                pass

        parser = ConstructorParser(MyProgram)

        options, remaining_unknown_args = parser.parse_known_args(unknown_args)

        program = parser.constructor(**vars(options))
    """

    @property
    def help(self):
        if hasattr(self.constructor, 'help'):
            return self.constructor.help
        if self.constructor.__doc__:
            return self.constructor.__doc__
        return super().help

    @property
    def description(self):
        return self.help

    def __init__(self, constructor, docstring_type='google', **kwargs):
        """Initializes parser analyzing provided class constructor.

        Arguments:
            constructor:
                a class to use for parser auto-generation
            docstring_type:
                docstring convention used in `__init__` method
                of provided class; on of: google, numpy, rst
            kwargs:
                custom keyword arguments to be passed to Parser
        """
        self.constructor = constructor
        restricted_names = ['name']

        # add arguments defined in the class of constructor
        for name, attribute in vars(constructor).items():
            if isinstance(attribute, Parser) or isinstance(attribute, Argument):
                setattr(self, name, attribute)

        # introspect method.__init__
        signature = inspect.signature(constructor)
        docstring = constructor.__init__.__doc__ or ''

        analyze_docstring = docstring_analyzers[docstring_type]
        docstring_help = analyze_docstring(docstring)

        for name, parameter in signature.parameters.items():
            # ignore *args and **kwargs
            if parameter.kind in [parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL]:
                continue
            if name in restricted_names:
                raise ValueError(f'"{name}" cannot be used as a name of argument')
            if not hasattr(self, name):
                argument = Argument(
                    default=empty_to_none(parameter.default),
                    type=empty_to_none(parameter.annotation),
                    optional=is_set(parameter.default),
                    help=docstring_help.get(name, None)

                )
                setattr(self, name, argument)
            else:
                argument = getattr(self, name)
                if not hasattr(argument, 'help') or not argument.help:
                    argument.help = docstring_help.get(name, None)

        super().__init__(**kwargs)
