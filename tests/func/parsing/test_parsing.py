from os.path import join, dirname

from parglare import Parser
from ..grammar.expression_grammar import get_grammar


def test_parsing():
    grammar = get_grammar()
    p = Parser(grammar)
    assert p.parse("id+id+id")


def test_parsing_from_file():
    grammar = get_grammar()
    p = Parser(grammar)
    assert p.parse_file(join(dirname(__file__), 'parsing_from_file.txt'))
