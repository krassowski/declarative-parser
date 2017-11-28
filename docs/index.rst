Declarative Parser - showcase
============================================

Powerful like click, integrated like argparse, declarative as sqlalchemy. MIT licenced.

.. currentmodule:: declarative_parser

Features:

* :ref:`argparse`
* :ref:`nested`
* :ref:`parallel`
* :ref:`production`
* :ref:`batteries`
* :ref:`deduction`
* :ref:`actions`


.. toctree::
   :caption: Jump into the docs:

   parser
   constructor_parser
   types

.. _argparse:

Built on top of argparse
------------------------
The basic API of the DeclarativeParser is compatible with argparse, so you do not need to learn from start.

This is the arparse way:

.. highlight:: python
.. code-block:: python

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("square", help="display a square of a given number")
    args = parser.parse_args()
    print(args.square**2)


This is the declarative way:

.. code-block:: python

    from declarative_parser import Parser, Argument

    class MyParser(Parser):
        square = Argument(help='display a square of a given number')

    parser = MyParser()
    args = parser.parse_args()
    print(args.square**2)



.. _nested:

Nested parsers
--------------

DeclarativeParser allows you to nest parsers one in another, just like 'git commit' or 'git push':

.. highlight:: python
.. code-block:: python

    class TheParser(Parser):
        help = 'This takes only one argument, but it is required'

        arg = Argument(optional=False, help='This is required')

    class MyParser(Parser):
        description = 'This should be a longer text'

        my_argument = Argument(type=int, help='some number')
        my_sub_parser = TheParser()

        epilog = 'You can create a footer with this'


To execute the parser use:

.. code-block:: python

    parser = MyParser()

    # The commands will usually be `sys.argv[1:]`
    commands = '--my_argument 4 my_sub_parser value'.split()

    namespace = parser.parse_args(commands)

Resultant `namespace` is a normal :class:`argparse.Namespace`

.. code-block:: python

    assert namespace.my_argument == 4
    assert namespace.my_sub_parser.arg == 'value'

.. _parallel:

Parallel parsers
----------------

You can have multiple sub-parsers on the same level, like:

.. code-block:: python

    supported_formats = ['png', 'jpeg', 'gif']

    class InputOptions(Parser):
        path = Argument(type=argparse.FileType('rb'), optional=False)
        format = Argument(default='png', choices=supported_formats)

    class OutputOptions(Parser):
        format = Argument(default='jpeg', choices=supported_formats)
        scale = Argument(type=int, default=100, help='Rescale image to % of original size')

    class ImageConverter(Parser):
        description = 'This app converts images'

        verbose = Argument(action='store_true')
        input = InputOptions()
        output = OutputOptions()

    parser = ImageConverter()

    commands = '--verbose input image.png output --format gif --scale 50'.split()

    namespace = parser.parse_args(commands)

    assert namespace.input.format == 'png'
    assert namespace.output.format == 'gif'

As simple as it looks!

.. _production:

Production pattern
------------------
Do you want to introduce sophisticated behaviour to your parser, but keep the logic away from the core of your app?
DeclarativeParser enables you to add "produce" method to each parser, which will transform the arguments namespace in a way you wish it to be done!

Have a look on this example of advanced file parsing:

.. code-block:: python

    from declarative_parser import Parser, Argument
    from declarative_parser.types import Slice, Indices, Range, one_of


    def slice_file(file, columns_selector=None, delimiter=None):
        pass

    class FileSubsetFactory(Parser):
        """Parse user options and load desired part of given file.

         The files should come in Delimiter Separated Values format
         (like .csv or .tsv). The default delimiter is a tab character.

         To use only a subset of columns from given file,
         specify column numbers with --columns.
         """

        file = Argument(
            type=argparse.FileType('r'),
            optional=False
        )

        columns = Argument(
            # we want to handle either ":4", "5:" or even "1,2,3"
            type=one_of(Slice, Indices, Range),
            # user may (but do not have to) specify columns
            # to be extracted from given file(s).
            help='Columns to be extracted from files: '
                 'either a comma delimited list of 0-based numbers (e.g. 0,2,3) '
                 'or a range defined using Python slice notation (e.g. 3:10). '
                 'Columns for each of files should be separated by space.'
        )

        delimiter = Argument(
            default='\t',
            help='Delimiter of the provided file(s). Default: tabulation mark.'
        )

        def produce(self, unknown_args=None):
            opts = self.namespace

            opts.file_subset = slice_file(
                opts.file,
                columns_selector=opts.columns.get_iterator if opts.columns else None,
                delimiter=opts.delimiter,
            )

            return opts

After parsing `file_subset` will become a part of your resultant namespace.

.. _batteries:

Batteries included
------------------

Powerful validation, additional types and more.

Do you want to allow user to provide distinct options for each of provided files, but not to validate the number of arguments every single time?
No problem, just use `as_many_as=files`.

.. code-block:: python

    class AdvancedFileFactory(Parser):
        """Parse user options and load given file(s).

         To use only a subset of columns from files(s) specify column numbers
         (--columns) or column names (--names) of desired columns.
         """

        files = Argument(
            type=argparse.FileType('r'),
            # at least one file is always required
            nargs='+',
            optional=False
        )

        names = Argument(
            type=dsv(str),
            nargs='*',
            as_many_as=files,
            help='Names of columns to be extracted from the file. '
                 'Names are determined from the first non-empty row. '
                 'Use a comma to separate column names. '
                 'Column names for each of files should be separated by space.'
        )

        columns = Argument(
            # we want to handle either ":4", "5:" or even "1,2,3"
            type=one_of(Slice, Indices, Range),
            # user may (but do not have to) specify columns
            # to be extracted from given file(s).
            nargs='*',
            as_many_as=files,
            help='Columns to be extracted from files: '
                 'either a comma delimited list of 0-based numbers (e.g. 0,2,3) '
                 'or a range defined using Python slice notation (e.g. 3:10). '
                 'Columns for each of files should be separated by space.'
        )


        def produce(self, unknown_args=None):
            opts = self.namespace

            file_chunks = []

            for i, file_obj in enumerate(opts.files):

                file_chunks.append(slice_file(
                    opts.file,
                    names=opts.names[i] if opts.names else None,
                    columns_selector=opts.columns[i].get_iterator if opts.columns else None,
                ))

            opts.file_subset = merge_chunks(file_chunks)

            return opts

To further explore additional types, see: :doc:`types`.

.. _deduction:

Arguments deduction (typing, docstrings, kwargs)
------------------------------------------------

What about automatic parser creation?

Just feed :class:`declarative_parser.constructor_parser.ConstructorParser` with your main class and it will take care of it.
Arguments defined in your `__init__` and in body of your class (i.e. class variables) will be used to create a parser;
Type annotations (as long as based on real types, not typing module) will be used to define types of your arguments;
Default: from keyword arguments. Positional arguments will be always required.
Docstring descriptions will be used to provide help for your arguments.

Following docstring formats are supported: Google, NumPy and reStructuredText, with the default being Google.
To change the format, pass `docstring_type='numpy'` or `docstring_type='rst'` respectively.

When an argument is defined in both: `__init__` and :class:`declarative_parser.Argument()` variable, the class variable overwrites the values from `__init__` .

.. code-block:: python

    import argparse
    from declarative_parser import Argument
    from declarative_parser.constructor_parser import ConstructorParser

    class MyProgram:

        database = Argument(
            type=argparse.FileType('r'),
            help='Path to file with the database'
        )

        def __init__(self, text: str, threshold: float=0.05, database=None):
            """My program does XYZ.

            Arguments:
              threshold: a floating-point value defining threshold, default 0.05
              database: file object to the database if any
            """
            print(text, threshold, None)

    parser = ConstructorParser(MyProgram)

    options = parser.parse_args()
    program = parser.constructor(**vars(options))

And it works quite intuitively:

.. code-block:: bash

    $ ./my_program.py test --threshold 0.6
    test 0.6 None
    $ ./my_program.py test --threshold f
    usage: my_program.py [-h] [--database DATABASE] [--threshold THRESHOLD] text {} ...
    my_program.py: error: argument --threshold: invalid float value: 'f'
    $ ./my_program.py --threshold 0.6
    usage: my_program.py [-h] [--database DATABASE] [--threshold THRESHOLD] text {} ...
    my_program.py: error: the following arguments are required: text


You could then implement `run` method and call `program.run()` to start you application.


.. _actions:

Actions
-------

What if you only want to show licence of your program? or version? It there a need to write a separate logic?
DeclarativeParser gives you utility decorator: `@action` which utilizes the power of :class:`argparse.Action`,
leaving behind the otherwise necessary boilerplate code.

.. code-block:: python

    __version__ = 2.0

    import argparse
    from declarative_parser import action
    from declarative_parser.constructor_parser import ConstructorParser

    class MyProgram:

        def __init__(self, threshold: float=0.05):
            """My program does XYZ.

            Arguments:
              threshold: a floating-point value, default 0.05
            """
            pass

        @action
        def version(options):
           print(__version__)

    parser = ConstructorParser(MyProgram)

    options = parser.parse_args()
    program = parser.constructor(**vars(options))

The execution of an action will (by default) cause the program to exit immediately when finished.
See following run as example:

.. code-block:: bash

    $ ./my_program.py --version
    2.0
    $



Acknowledgements
----------------

This module was originally developed for https://github.com/kn-bibs/pathways-analysis project.
Big thanks go to @hansiu, @sienkie and @pjanek for early feedback, inspiration and some valuable insights.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
