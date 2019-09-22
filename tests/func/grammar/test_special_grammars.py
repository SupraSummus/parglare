import pytest

from parglare import Parser, GLRParser, Grammar, SLR, LALR
from parglare.exceptions import ParseError, SRConflicts, RRConflicts


def test_lr_1_grammar():
    """From the Knuth's 1965 paper: On the Translation of Languages from Left to
    Right

    """
    g, _ = Grammar.from_struct(
        {
            'S': [['a', 'A', 'd'], ['b', 'A', 'd']],
            'A': [['c', 'A'], 'c'],
        },
        {s: ('string', s) for s in ['a', 'b', 'c', 'd']},
        'S',
    )

    parser = Parser(g)
    parser.parse("acccccccccd")
    parser.parse("bcccccccccd")

    parser = GLRParser(g)
    assert len(parser.parse("accccccccd")) == 1
    assert len(parser.parse("bccccccccd")) == 1


def test_slr_conflict():
    """
    Unambiguous grammar which is not SLR(1).
    From the Dragon Book.
    This grammar has a S/R conflict if SLR tables are used.
    """
    grammar, _ = Grammar.from_struct(
        {
            'S': [['L', '=', 'R'], ['R']],
            'L': [['*', 'R'], ['id']],
            'R': [['L']],
        },
        {s: ('string', s) for s in ['=', '*', 'id']},
        'S',
    )

    with pytest.raises(SRConflicts):
        Parser(grammar, tables=SLR, prefer_shifts=False)

    Parser(grammar, tables=LALR, prefer_shifts=False)


def test_lalr_reduce_reduce_conflict():
    """
    Naive merging of states can lead to R/R conflict as shown in this grammar
    from the Dragon Book.
    But the extended LALR state compression algorithm used in parglare doesn't
    exibit this problem.
    """
    grammar, _ = Grammar.from_struct(
        {
            'S': [['a', 'A', 'd'], ['b', 'B', 'd'], ['a', 'B', 'e'], ['b', 'A', 'e']],
            'A': [['C']],
            'B': [['C']],
            'C': [['c']],
        },
        {s: ('string', s) for s in ['a', 'b', 'c', 'd', 'e']},
        'S',
    )
    Parser(grammar)


def test_nondeterministic_LR_raise_error():
    """Language of even length palindromes.

    This is a non-deterministic grammar and the language is non-ambiguous.

    If the string is a even length palindrome parser should reduce EMPTY at he
    middle of the string and start to reduce by A and B.

    LR parsing is deterministic so this grammar can't parse the input as the
    EMPTY reduction will be tried only after consuming all the input by
    implicit disambiguation strategy of favouring shifts over empty reductions.

    OTOH, GLR parser can handle this by forking parser at each step and trying
    both empty reductions and shifts. Only the parser that has reduced empty at
    the middle of the input will succeed.

    """
    g, _ = Grammar.from_struct(
        {
            'S': [['A'], ['B'], []],
            'A': [['1', 'S', '1']],
            'B': [['0', 'S', '0']],
        },
        {s: ('string', s) for s in ['0', '1']},
        'S',
    )

    in_str = '0101000110001010'

    p = Parser(g)
    with pytest.raises(ParseError):
        p.parse(in_str)

    p = GLRParser(g)
    results = p.parse(in_str)
    assert len(results) == 1


@pytest.mark.skip
def test_cyclic_grammar_1():
    """
    From the paper: "GLR Parsing for e-Grammers" by Rahman Nozohoor-Farshi
    """
    g, _ = Grammar.from_struct(
        {
            'S': [['A']],
            'A': [['S'], ['x']],
        },
        {'x': ('string', 'x')},
        'S',
    )

    with pytest.raises(SRConflicts):
        Parser(g, prefer_shifts=False)

    p = GLRParser(g)
    results = p.parse('x')
    # x -> A -> S
    assert len(results) == 1


@pytest.mark.skip
def test_cyclic_grammar_2():
    """
    From the paper: "GLR Parsing for e-Grammers" by Rahman Nozohoor-Farshi

    """
    g, _ = Grammar.from_struct(
        {'S': [['S', 'S'], ['x'], []]},
        {'x': ('string', 'x')},
        'S',
    )

    with pytest.raises(SRConflicts):
        Parser(g, prefer_shifts=False)

    p = GLRParser(g, debug=True)
    results = p.parse('xx')
    # This grammar has infinite ambiguity but by minimizing empty reductions
    # we shall get only one result xx -> xS -> SS -> S
    assert len(results) == 1


def test_cyclic_grammar_3():
    g, _ = Grammar.from_struct(
        {
            'S': [['S', 'A'], ['A']],
            'A': [['a'], []],
        },
        {'a': ('string', 'a')},
        'S',
    )

    p = Parser(g)
    p.parse('aa')

    p = GLRParser(g, debug=True)
    results = p.parse('aa')
    assert len(results) == 1


def test_highly_ambiguous_grammar():
    """
    This grammar has both Shift/Reduce and Reduce/Reduce conflicts and
    thus can't be parsed by a deterministic LR parsing.
    Shift/Reduce can be resolved by prefer_shifts strategy.
    """
    g, _ = Grammar.from_struct(
        {'S': [['b'], ['S', 'S'], ['S', 'S', 'S']]},
        {'b': ('string', 'b')},
        'S',
    )

    with pytest.raises(SRConflicts):
        Parser(g, prefer_shifts=False)

    # S/R are resolved by selecting prefer_shifts strategy.
    # But R/R conflicts remain.
    with pytest.raises(RRConflicts):
        Parser(g, prefer_shifts=True)

    # GLR parser handles this fine.
    p = GLRParser(g)

    # For three tokens we have 3 valid derivations/trees.
    results = p.parse("bbb")
    assert len(results) == 3

    # For 4 tokens we have 10 valid derivations.
    results = p.parse("bbbb")
    assert len(results) == 10


def test_indirect_left_recursive():
    """Grammar with indirect/hidden left recursion.

    parglare LR parser will handle this using implicit disambiguation by
    prefering shifts over empty reductions. It will greadily match "b" tokens
    and than reduce EMPTY before "a" and start to reduce by 'B="b" B'
    production.

    """
    g, _ = Grammar.from_struct(
        {
            'S': [['B', 'a']],
            'B': [['b', 'B'], []],
        },
        {
            'b': ('string', 'b'),
            'a': ('string', 'a'),
        },
        'S',
    )

    p = Parser(g)
    p.parse("bbbbbbbbbbbba")

    p = GLRParser(g, debug=True)
    results = p.parse("bbbbbbbbbbbba")
    assert len(results) == 1


def test_reduce_enough_empty():
    """In this unambiguous grammar parser must reduce as many empty A productions
    as there are "b" tokens ahead to be able to finish successfully, thus it
    needs unlimited lookahead

    Language is: xb^n, n>=0

    References:

    Nozohoor-Farshi, Rahman: "GLR Parsing for ε-Grammers", Generalized LR
    parsing, Springer, 1991.

    Rekers, Joan Gerard: "Parser generation for interactive environments",
    phD thesis, Universiteit van Amsterdam, 1992.

    """
    g, _ = Grammar.from_struct(
        {
            'S': [['A', 'S', 'b'], ['x']],
            'A': [[]],
        },
        {
            'b': ('string', 'b'),
            'x': ('string', 'x'),
        },
        'S',
    )

    p = GLRParser(g, debug=True)
    results = p.parse("xbbb")

    assert len(results) == 1
