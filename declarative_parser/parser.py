import argparse
import textwrap
from collections import defaultdict
from copy import deepcopy
from typing import Sequence

import sys


def group_arguments(args, group_names):
    """Group arguments into given groups + None group for all others"""
    groups = defaultdict(list)
    group = None
    for arg in args:
        if arg in group_names:
            group = arg
        else:
            groups[group].append(arg)
    return groups, groups[None]


class Argument:
    """Defines argument for `Parser`.

    In essence, this is a wrapper for :meth:`argparse.ArgumentParser.add_argument`,
    so most options (type, help) which work in standard Python
    parser will work with Argument too. Additionally, some nice
    features, like automated naming are available.

    Worth to mention that when used with :class:`~.constructor_parser.ConstructorParser`,
    `type` and `help` will be automatically deduced.
    """

    def __init__(
            self, name=None, short=None, optional=True,
            as_many_as: 'Argument'=None, **kwargs
    ):
        """
        Args:
            name:
                overrides deduced argument name
            short:
                a single letter to be used as a short name
                (e.g. "c" will enable using "-c")
            optional:
                by default True, provide False
                to make the argument required
            as_many_as:
                if provided, will check if len() of the produced
                value is equal to len() of the provided argument
            **kwargs:
                other keyword arguments which are
                supported by `argparse.add_argument()`
        """
        self.name = name
        self.short_name = short
        self.optional = optional
        self.as_many_as = as_many_as
        self.kwargs = kwargs
        self.default = kwargs.get('default', None)

        if not optional and short:
            raise ValueError(
                f'Keyword argument `short={short}` is useless '
                f'for an optional argument named "{name}".'
            )

    @property
    def args(self):

        args = []
        if self.optional:
            if self.short_name:
                args.append(f'-{self.short_name}')
            args.append(f'--{self.name}')
        else:
            args.append(self.name)

        return args

    @staticmethod
    def as_numerous_as(myself, partner):
        # if we have callable, we can call it as many times as we want
        if callable(myself):
            return True
        if partner and myself:
            return len(partner) == len(myself)
        return True

    def validate(self, opts):
        myself = getattr(opts, self.name)

        if self.as_many_as:
            partner = getattr(opts, self.as_many_as.name)
            if not self.as_numerous_as(myself, partner):
                raise ValueError(
                    f'{self.name} for {len(myself)} {self.as_many_as.name} '
                    f'provided, expected for {len(partner)}'
                )


def create_action(callback, exit_immediately=True):
    """Factory for :class:`argparse.Action`, for simple callback execution"""

    class Action(argparse.Action):

        def __call__(self, parser, namespace, *args, **kwargs):
            code = callback(namespace)
            if exit_immediately:
                sys.exit(code)

    return Action


def action(method):
    """Decorator for Action.

    Args:
        method: static or class method for use as a callback
    """
    return Argument(
        action=create_action(method),
        nargs=0
    )


def dedent_help(text):
    """Dedent text by four spaces"""
    return textwrap.dedent(' ' * 4 + text)


class Parser:
    """Parser is a wrapper around Python built-in :class:`argparse.ArgumentParser`.

    Subclass the `Parser` to create your own parser.

    Use help, description and epilog properties to adjust the help screen.
    By default help and description will be auto-generated using docstring
    and defined arguments.

    Attach custom arguments and sub-parsers by defining class-variables
    with :class:`Argument` and :class:`Parser` instances.

    Example::

        class TheParser(Parser):
            help = 'This takes only one argument, but it is required'

            arg = Argument(optional=False, help='This is required')

        class MyParser(Parser):
            description = 'This should be a longer text'

            my_argument = Argument(type=int, help='some number')
            my_sub_parser = TheParser()

            epilog = 'You can create a footer with this'

        # To execute the parser use:

        parser = MyParser()

        # The commands will usually be `sys.argv[1:]`
        commands = '--my_argument 4 my_sub_parser value'.split()

        namespace = parser.parse_args(commands)

        # `namespace` is a normal `argparse.Namespace`
        assert namespace.my_argument == 4
        assert namespace.my_sub_parser.arg == 'value'

    Implementation details:

        To enable behaviour not possible with limited, plain `ArgumentParser`
        (e.g. to dynamically attach a sub-parser, or to chain two or more
        sub-parsers together) the stored actions and sub-parsers are:
            - not attached permanently to the parser,
            - attached in a tricky way to enable desired behaviour,
            - executed directly or in hierarchical order.

        Class-variables with parsers will be deep-copied on initialization,
        so you do not have to worry about re-use of parsers.
    """
    # sub-parsers will have dynamically populated name variable
    parser_name = None

    @property
    def help(self):
        """A short message, shown as summary on >parent< parser help screen.

        Help will be displayed for sub-parsers only.
        """
        return (
            ' Accepts: ' + ', '.join(self.arguments.keys())
        )

    @property
    def description(self):
        """Longer description of the parser.

        Description is shown when user narrows down the help
        to the parser with: ``./run.py sub_parser_name -h``.
        """
        return (self.__doc__ or '').format(**vars(self))

    @property
    def epilog(self):
        """Use this to append text after the help message"""
        return ''

    def __init__(self, parser_name=None, **kwargs):
        """Uses kwargs to pre-populate namespace of the `Parser`.

        Args:
            parser_name: a name used for identification of sub-parser
        """
        self.namespace = argparse.Namespace()
        self.parser_name = parser_name
        self.parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        assert self.__parsing_order__ in ['depth-first', 'breadth-first']

        self.arguments = {}
        # children parsers
        self.subparsers = {}

        # parses and arguments pulled up from children parsers
        self.lifted_parsers = {}
        self.lifted_args = {}

        attribute_handlers = {
            Argument: self.bind_argument,
            Parser: self.bind_parser,
        }

        # register class attributes
        for name in dir(self):
            attribute = getattr(self, name)
            for attribute_type, handler in attribute_handlers.items():
                if isinstance(attribute, attribute_type):
                    handler(attribute, name)

        # initialize namespace
        for name, argument in self.all_arguments.items():
            setattr(self.namespace, name, argument.default)

        for name, value in kwargs.items():
            setattr(self.namespace, name, value)

        self.to_builtin_parser()
        self.kwargs = kwargs

    @property
    def all_subparsers(self):
        return {**self.subparsers, **self.lifted_parsers}

    @property
    def all_arguments(self):
        return {**self.arguments, **self.lifted_args}

    def to_builtin_parser(self):
        for argument in self.all_arguments.values():
            self.attach_argument(argument)

    def attach_argument(self, argument: Argument, parser=None):
        """Attach Argument instance to given (or own) argparse.parser."""
        if not parser:
            parser = self.parser

        parser.add_argument(*argument.args, **argument.kwargs)

    def attach_subparsers(self):
        """Only in order to show a nice help, really.

        There are some issues when using subparsers added with the built-in
        add_subparsers for parsing. Instead subparsers are handled in a
        custom implementation of parse_known_args (which really builds upon
        the built-in one, just tweaking some places).
        """
        # regenerate description and epilog: enables use of custom variables
        # (which may be not yet populated at init.) in descriptions epilogues
        self.parser.description = dedent_help(self.description)
        self.parser.epilog = dedent_help(self.epilog)

        native_sub_parser = self.parser.add_subparsers()

        for name, sub_parser in self.all_subparsers.items():

            if sub_parser.__pull_to_namespace_above__:
                continue

            parser = native_sub_parser.add_parser(
                help=sub_parser.help, name=name,
                description=sub_parser.description
            )

            for argument in sub_parser.arguments.values():
                self.attach_argument(argument, parser)

    def bind_parser(self, parser: 'Parser', name):
        """Bind deep-copy of Parser with this instance (as a sub-parser).

        Args:
            parser:
                parser to be bound as a sub-parser
                (must be already initialized)
            name:
                name of the new sub-parser

        This method takes care of 'translucent' sub-parsers (i.e. parsers
        which expose their arguments and sub-parsers to namespace above),
        saving their members to appropriate dicts (lifted_args/parsers).
        """
        # Copy is needed as we do not want to share values of parsers'
        # arguments across separate instances of parsers (which is the
        # default behaviour when using class-properties).
        parser = deepcopy(parser)

        # For easier access, and to make sure that we will not access
        # the "raw" (not deep-copied) instance of parser again.
        setattr(self, name, parser)

        parser.parser_name = name
        self.subparsers[name] = parser

        if parser.__pull_to_namespace_above__:
            self.lifted_args.update(parser.arguments)
            self.lifted_parsers.update(parser.subparsers)

    def bind_argument(self, argument: Argument, name=None):
        """Bind argument to current instance of Parser."""
        if not argument.name and name:
            argument.name = name
        self.arguments[name] = argument

    def parse_single_level(self, ungrouped_args):
        if self.__pull_to_namespace_above__ and self.__skip_if_absent__ and not ungrouped_args:
            # do not run validate/produce and parsing if there is nothing to parse (part B)
            return self.namespace, ungrouped_args

        namespace, unknown_args = self.parser.parse_known_args(
            ungrouped_args,
            namespace=self.namespace
        )
        try:
            self.validate(self.namespace)
            opts = self.produce(unknown_args)
        except (ValueError, TypeError, argparse.ArgumentTypeError) as e:
            self.error(e.args[0])
            raise e

        assert opts is namespace

        return opts, unknown_args

    def parse_known_args(self, args: Sequence[str]):
        """Parse known arguments, like :meth:`argparse.ArgumentParser.parse_known_args`.

        Additional features (when compared to argparse implementation) are:
            - ability to handle multiple sub-parsers
            - validation with `self.validate` (run after parsing)
            - additional post-processing with `self.produce` (after validation)
        """
        grouped_args, ungrouped_args = group_arguments(args, self.all_subparsers)

        if self.__parsing_order__ == 'breadth-first':
            opts, unknown_args = self.parse_single_level(ungrouped_args)

        for name, parser in self.subparsers.items():

            if parser.__pull_to_namespace_above__:

                namespace, not_parsed_args = parser.parse_known_args([
                    arg_str
                    for key in parser.subparsers
                    for arg_str in [key, *grouped_args[key]]
                    # only include the sub-parser if it was explicitly enlisted
                    if key in grouped_args
                ])

                for key, value in vars(namespace).items():
                    setattr(self.namespace, key, value)
            else:
                if parser.__skip_if_absent__ and name not in grouped_args:
                    # do not run validate/produce and parsing if there is nothing to parse (part A)
                    setattr(self.namespace, name, None)
                    not_parsed_args = None
                else:
                    namespace, not_parsed_args = parser.parse_known_args(grouped_args[name])
                    setattr(self.namespace, name, namespace)

            if not_parsed_args:
                parser.error(f'unrecognized arguments: {" ".join(not_parsed_args)}')

        if self.__parsing_order__ == 'depth-first':
            opts, unknown_args = self.parse_single_level(ungrouped_args)

        return self.namespace, unknown_args

    def validate(self, opts):
        """Perform additional validation, using `Argument.validate`.

        As validation is performed after parsing, all arguments should
        be already accessible in `self.namespace`. This enables testing
        if arguments depending one on another have proper values.
        """
        if not opts:
            opts = self.namespace
        for argument in self.all_arguments.values():
            argument.validate(opts)

    @property
    def __pull_to_namespace_above__(self):
        """Makes the parser "translucent" for the end user.

        Though parsing methods (as well as validate & produce)
        are still evaluated, the user won't be able to see this
        sub-parser in command-line interface.

        This is intended to provide additional logic separation
        layer & to keep the parsers nicely organized and nested,
        without forcing the end user to type in prolonged names
        to localise an argument in a sub-parser of a sub-parser
        of some other parser.
        """
        return False

    @property
    def __skip_if_absent__(self):
        """Only invoke sub-parser parsing if it was explicitly enlisted"""
        return True

    @property
    def __parsing_order__(self):
        """What should be parsed first:

            arguments of this parser ('breadth-first') or
            arguments and parsers of sup-parsers ('depth-first')?
        """
        return 'depth-first'

    def produce(self, unknown_args):
        """Post-process already parsed namespace.

        You can override this method to create a custom objects
        in the parsed namespace (e.g. if you cannot specify the
        target class with Argument(type=X), because X depends
        on two or more arguments).

        You can chery-pick the arguments which were not parsed
        by the current parser (e.g. when some step of parsing
        depends on provided arguments), but please remember
        to remove those from `unknown_args` list.

        Remember to operate on the provided list object (do not
        rebind the name with `unknown_args = []`, as doing so
        will have no effect: use `unknown_args.remove()` instead).
        """
        return self.namespace

    def error(self, message):
        """Raises SystemExit with status code 2 and shows usage message."""
        self.attach_subparsers()
        self.parser.error(message)

    def parse_args(self, args: Sequence[str] = None):
        """Same as :meth:`parse_known_args` but all arguments must be parsed.

        This is an equivalent of :meth:`argparse.ArgumentParser.parse_args`
        although it does >not< support `namespace` keyword argument.

        Comparing to :meth:`parse_known_args`, this method handles help
        messages nicely (i.e. passes everything to :mod:`argparse`).

        Args:
            args: strings to parse, default is sys.argv[1:]
        """
        args = args if args is not None else sys.argv[1:]

        # Use the built-in help (just attach sub-parsers before).
        if '-h' in args or '--help' in args or not args:
            self.attach_subparsers()
            self.parser.parse_args(args)

        # Parse wisely, we need to support chaining sub-parsers,
        # validation and so on. Everything in parse_known_args.
        options, unknown_args = self.parse_known_args(args)

        if unknown_args:
            self.error(f'unrecognized arguments: {" ".join(unknown_args)}')

        return options

    def __deepcopy__(self, memodict={}):
        return self.__class__(**self.kwargs)
