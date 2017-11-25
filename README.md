# Declarative Parser
[![Build Status](https://travis-ci.org/krassowski/declarative-parser.svg?branch=master)](https://travis-ci.org/krassowski/declarative-parser) [![Code Climate](https://codeclimate.com/github/krassowski/declarative-parser/badges/gpa.svg)](https://codeclimate.com/github/krassowski/declarative-parser) [![Coverage Status](https://coveralls.io/repos/github/krassowski/declarative-parser/badge.svg)](https://coveralls.io/github/krassowski/declarative-parser) [![Documentation Status](https://readthedocs.org/projects/declarative-parser/badge/?version=latest)](http://declarative-parser.readthedocs.io/en/latest/?badge=latest)

Modern, declarative argument parser for Python 3.6+.
Powerful like click, integrated like argparse, declarative as sqlalchemy. MIT licenced.

```bash
pip3 install declarative_parser
```


### As simple as argparse

It's built on top of argparse - everything you already know stays valid!

```python
from declarative_parser import Parser, Argument

class MyParser(Parser):
    square = Argument(help='display a square of a given number')

parser = MyParser()
args = parser.parse_args()
print(args.square**2)
```


### Nested and Parellel

Everyone knows about nested args. What about parallel groups?

```python
supported_formats = ['png', 'jpeg', 'gif']

class InputOptions(Parser):
    path = Argument(type=argparse.FileType('rb'), optional=False)
    format = Argument(default='png', choices=supported_formats)

class OutputOptions(Parser):
    format = Argument(default='jpeg', choices=supported_formats)
    scale = Argument(type: int, default=100, help='Rescale image to % of original size')

class ImageConverter(Parser):
    description = 'This app converts images'

    verbose = Argument(action='store_true')
    input = InputParser()
    output = OutputParser()

parser = MyParser()

commands = '--verbose input image.png output --format gif --scale 50'.split()

namespace = parser.parse_args(commands)

assert namespace.input.format == 'png'
assert namespace.output.format == 'gif'
```


### Inteligent

Make use of Python 3 type hints to reduce tedious task of parsers writing to two or three lines.
Positional, keyword arguments, type hints, docstrings - everything can be meaningfully transformed into a parser.
And if you decide to take control, just overwrite the automatically deduced arguments with an `Argument()` defined as a class variable.

```python
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
```

And it works quite intuitively:

```bash
$ ./my_program.py test --threshold 0.6
test 0.6 None
$ ./my_program.py test --threshold f
usage: my_program.py [-h] [--database DATABASE] [--threshold THRESHOLD] text {} ...
my_program.py: error: argument --threshold: invalid float value: 'f'
$ ./my_program.py --threshold 0.6
usage: my_program.py [-h] [--database DATABASE] [--threshold THRESHOLD] text {} ...
my_program.py: error: the following arguments are required: text
```

### Practical

What if you only want to show licence of your program? or version? Is there a need to write a separate logic?
DeclarativeParser gives you utility decorator: `@action` which utilizes the power of `argparse.Action`,
leaving behind the otherwise necessary boilerplate code.

```python
__version__ = 2.0

import argparse
from declarative_parser import action
from declarative_parser.constructor_parser import ConstructorParser

class MyProgram:

    def __init__(self, threshold:float=0.05):
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
```

The execution of an action will (by default) cause the program to exit immediately when finished.

See following run as example:

```bash
$ ./my_program.py --version
2.0
```
