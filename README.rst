This is a work-in-progress-fork of igordejanovic/parglare intended to be more minimalistic.

TODO:
 * remove grammar language - replace with native python's structures
 * remove implicit table caching
 * sort out strange metaclass `ParglareMetaClass`
 * remove `Grammar._parse`
 * remove `Grammar._from_struct_old`
 * remove `parser.parse_file`
 * remove magic LAYOUT rule (maybe replace with something less magic)
 * remove `prefer` option on terminals
 * remove context usable by parsing actions. propose something more robust

.. image:: https://raw.githubusercontent.com/igordejanovic/parglare/master/docs/images/parglare-logo.png

|build-status| |coverage| |docs| |status| |license| |python-versions|


A pure Python scannerless LR/GLR parser.


For more information see `the docs <http://www.igordejanovic.net/parglare/>`_.


Quick intro
-----------

This is just a small example to get the general idea. This example shows how to
parse and evaluate expressions with 5 operations with different priority and
associativity. Evaluation is done using semantic/reduction actions.

.. code:: python

    from parglare import Parser, Grammar

    grammar, _ = Grammar.from_struct(
        productions_dict={
            'E1': [
                ['E1', '+', 'E2'],
                ['E1', '-', 'E2'],
                ['E2'],
            ],
            'E2': [
                ['E2', '*', 'E3'],
                ['E2', '/', 'E3'],
                ['E3'],
            ],
            'E3': [
                ['E4', '^', 'E3'],
                ['E4'],
            ],
            'E4': [
                ['(', 'E1', ')'],
                ['number'],
            ],
        },
        terminals_dict={
            'number': ('regexp', r'\d+(\.\d+)?'),
            '+': ('string', '+'),
            '-': ('string', '-'),
            '*': ('string', '*'),
            '/': ('string', '/'),
            '^': ('string', '^'),
            '(': ('string', '('),
            ')': ('string', ')'),
        },
        start='E1',
    )

    actions = {
        "E1": [
            lambda _, nodes: nodes[0] + nodes[2],
            lambda _, nodes: nodes[0] - nodes[2],
            lambda _, nodes: nodes[0],
        ],
        "E2": [
            lambda _, nodes: nodes[0] * nodes[2],
            lambda _, nodes: nodes[0] / nodes[2],
            lambda _, nodes: nodes[0],
        ],
        "E3": [
            lambda _, nodes: nodes[0] ** nodes[2],
            lambda _, nodes: nodes[0],
        ],
        "E4": [
            lambda _, nodes: nodes[1],
            lambda _, nodes: float(nodes[0]),
        ],
    }

    parser = Parser(grammar, debug=True, actions=actions)

    result = parser.parse("34 + 4.6 / 2 * 4^2^2 + 78")

    print("Result = ", result)

    # Output
    # -- Debugging/tracing output with detailed info about grammar, productions,
    # -- terminals and nonterminals, DFA states, parsing progress,
    # -- and at the end of the output:
    # Result = 700.8


Installation
------------

- Development version:

.. code:: shell

    $ git clone https://github.com/SupraSummus/parglare-slim.git
    $ pip install -e parglare


License
-------

MIT

Python versions
---------------

Tested with 3.5-3.7

Credits
-------

Initial layout/content of this package was created with `Cookiecutter
<https://github.com/audreyr/cookiecutter>`_ and the
`audreyr/cookiecutter-pypackage <https://github.com/audreyr/cookiecutter-pypackage>`_ project template.


.. |build-status| image:: https://travis-ci.com/SupraSummus/parglare-slim.svg?branch=master
   :target: https://travis-ci.com/SupraSummus/parglare-slim

.. |coverage| image:: https://codecov.io/gh/SupraSummus/parglare-slim/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/SupraSummus/parglare-slim

.. |docs| image:: https://img.shields.io/badge/docs-latest-green.svg
   :target: http://igordejanovic.net/parglare/latest/

.. |status| image:: https://img.shields.io/pypi/status/parglare-slim.svg

.. |license| image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://opensource.org/licenses/MIT

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/parglare-slim.svg
