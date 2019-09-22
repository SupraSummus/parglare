from copy import deepcopy

from parglare.actions import (
    collect, collect_optional,
    collect_sep, collect_sep_optional, collect_right,
    collect_right_optional, collect_right_sep,
    collect_right_sep_optional, pass_single,
)
from parglare import Grammar, Parser


grammar_common = {
    'productions_dict': {
        'Elements': None,
        'Element': [['a'], ['b']],
    },
    'terminals_dict': {
        'a': ('string', 'a'),
        'b': ('string', 'b'),
        ',': ('string', ','),
    },
    'start': 'Elements',
}


def test_collect_left():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Elements', 'Element'], ['Element']]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a b a a b')

    assert result == ['a', 'b', 'a', 'a', 'b']


def test_collect_left_optional():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Elements', 'Element'], []]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_optional,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a b a a b')
    assert result == ['a', 'b', 'a', 'a', 'b']

    # Empty parse returns None
    result = parser.parse('')
    assert result == []


def test_collect_left_sep():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Elements', ',', 'Element'], ['Element']]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_sep,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a, b, a ,a, b')

    assert result == ['a', 'b', 'a', 'a', 'b']


def test_collect_left_sep_optional():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Elements', ',', 'Element'], ['Element'], []]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_sep_optional,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a ,b, a, a, b')
    assert result == ['a', 'b', 'a', 'a', 'b']

    # Empty parse returns None
    result = parser.parse('')
    assert result == []


def test_collect_right():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Element', 'Elements'], ['Element']]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_right,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a b a a b')

    assert result == ['a', 'b', 'a', 'a', 'b']


def test_collect_right_optional():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Element', 'Elements'], []]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_right_optional,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a b a a b')
    assert result == ['a', 'b', 'a', 'a', 'b']

    # Empty parse returns None
    result = parser.parse('')
    assert result == []


def test_collect_right_sep():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Element', ',', 'Elements'], ['Element']]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_right_sep,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a, b, a ,a, b')

    assert result == ['a', 'b', 'a', 'a', 'b']


def test_collect_right_sep_optional():
    grammar = deepcopy(grammar_common)
    grammar['productions_dict']['Elements'] = [['Element', ',', 'Elements'], ['Element'], []]
    g, start_symbol = Grammar.from_struct(**grammar)

    actions = {
        "Elements": collect_right_sep_optional,
        "Element": pass_single,
        start_symbol: pass_single,
    }

    parser = Parser(g, actions=actions, debug=True)

    result = parser.parse('a ,b, a, a, b')
    assert result == ['a', 'b', 'a', 'a', 'b']

    # Empty parse returns None
    result = parser.parse('')
    assert result == []
