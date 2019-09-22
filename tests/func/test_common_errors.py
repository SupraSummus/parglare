import pytest
from parglare import Grammar, Parser
from parglare.exceptions import GrammarError


def test_infinite_recursions():
    """
    If rule have no recursion termination alternative as for example:

    Elements: Elements Element;

    instead of:
    Elements: Elements Element | Element;

    first set of "Elements" will be empty. GrammarError will be produced during
    parser construction.
    """

    grammar, start_symbol = Grammar.from_struct(
        {'Elements': [['Elements', 'Element']]},
        {'Element': ('string', 'a')},
        start='Elements',
    )

    with pytest.raises(GrammarError) as e:
        Parser(grammar)

    assert f'First set empty for grammar symbol "{start_symbol}"' in str(e)
    assert 'infinite recursion' in str(e)


def test_terminals_with_different_names():
    """Test that all terminals with same string match have the same name.
    """

    with pytest.raises(GrammarError) as e:
        Grammar.from_struct(
            # In this grammar we have 'd' terminal in S production and B terminal with
            # the same 'd' recognizer.
            {
                'S': [['a', 'A', 'd'], ['b', 'A', 'B']],
                'A': [['c', 'A'], ['c']],
            },
            {
                'B': ('string', 'd'),
                'a': ('string', 'a'),
                'b': ('string', 'b'),
                'c': ('string', 'c'),
                'd': ('string', 'd'),
            },
            'S',
        )

    assert 'B' in str(e)
    assert 'd' in str(e)
    assert 'match the same string' in str(e)


def todo_test_grammar_without_valid_inputs():
    """
    TODO: There is no valid input for this grammar. This should be detected by
    the parser.
   """
    grammar = """
    S: A | B;
    A: '1' S '1';
    B: '0' S '0';
    """

    g = Grammar.from_string(grammar)
    p = Parser(g)
    p.parse('0101000110001010')
