import pytest  # noqa
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

    grammar = """
    Elements: Elements Element;
    Element: "a" | "b";
    """

    g = Grammar.from_string(grammar)

    with pytest.raises(GrammarError) as e:
        Parser(g)

    assert 'First set empty for grammar symbol "Elements"' in str(e)
    assert 'infinite recursion' in str(e)


def test_terminals_with_different_names():
    """Test that all terminals with same string match have the same name.
    """

    # In this grammar we have 'd' terminal in S production and B terminal with
    # the same 'd' recognizer.
    grammar = """
    S: 'a' A 'd' | 'b' A B;
    A: 'c' A | 'c';
    B: 'd';
    """

    with pytest.raises(GrammarError) as e:
        Grammar.from_string(grammar)

    assert 'B' in str(e)
    assert 'd' in str(e)
    assert 'already exists' in str(e)


def todo_test_unreachable_accept_state():
    """
    TODO: Language of even palindromes without ending empty match will produce
    DPDA with infinite transition between two state without possibility
    to reach ACCEPT state for any input string.
   """
    grammar = """
    S: A | B;
    A: '1' S '1';
    B: '0' S '0';
    """

    g = Grammar.from_string(grammar)
    p = Parser(g)
    p.parse('0101000110001010')
