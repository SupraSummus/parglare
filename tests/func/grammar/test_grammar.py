import pytest

from parglare import Parser, Grammar
from parglare.exceptions import GrammarError


def test_single_string_terminal():
    """
    Test that grammar may be just a single terminal.
    """
    g, _ = Grammar.from_struct(
        {},
        {'t': ('string', 'a')},
        't',
    )
    parser = Parser(g)
    result = parser.parse('a')
    assert result == ['a', None]


def test_single_regexp_terminal():
    g, _ = Grammar.from_struct(
        {},
        {'t': ('regexp', r'\d+')},
        't',
    )
    parser = Parser(g)
    result = parser.parse('23')
    assert result == ['23', None]


def test_undefined_grammar_symbol():
    "Tests that undefined grammar symbols raises errors."
    with pytest.raises(GrammarError) as e:
        Grammar.from_struct(
            {'s': [['id']]},
            {},
            's',
        )

    assert 'undefined symbol' in str(e)
    assert 'id' in str(e)


def test_undefined_start_symbol():
    with pytest.raises(GrammarError) as e:
        Grammar.from_struct(
            {},
            {},
            'sss',
        )

    assert 'Undefined start symbol' in str(e)
    assert 'sss' in str(e)


def test_reserved_symbol_names():
    """
    Test that reserved symbol names can't be used.
    """
    for reserved_name in ['__start', 'EOF', 'STOP', 'EMPTY']:
        with pytest.raises(GrammarError) as e:
            Grammar.from_struct(
                {'s': [[reserved_name]]},
                {reserved_name: ('string', 'a')},
                's',
            )
        assert reserved_name in str(e)
        assert 'is reserved' in str(e)

        with pytest.raises(GrammarError) as e:
            Grammar.from_struct(
                {reserved_name: [['a']]},
                {'a': ('string', 'a')},
                reserved_name,
            )
        assert reserved_name in str(e)
        assert 'is reserved' in str(e)
