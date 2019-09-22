"""
Test special KEYWORD rule.
"""
import pytest
from parglare import Parser, Grammar, RegExRecognizer, StringRecognizer
from parglare.exceptions import GrammarError, ParseError


common_terminals = {
    'ID': ('regexp', r'\w+'),
    'INT': ('regexp', r'\d+'),
    'for': ('string', 'for'),
    '=': ('string', '='),
    'to': ('string', 'to'),
}


def test_keyword_must_be_regex():
    with pytest.raises(GrammarError) as e:
        Grammar.from_struct(
            {'S': [['for', 'ID', '=', 'INT', 'to', 'INT']]},
            {
                'KEYWORD': ('string', 'id'),
                **common_terminals,
            },
            'S',
        )

    assert 'must have a regex recognizer defined' in str(e)


def test_keyword_grammar_init():
    g, _ = Grammar.from_struct(
        {'S': [['for', 'ID', '=', 'INT', 'to', 'INT']]},
        {
            'KEYWORD': ('regexp', r'\w+'),
            **common_terminals,
        },
        'S',
    )

    # 'for' term matches KEYWORD rule so it'll be replaced by
    # RegExRecognizer instance.
    for_term = g.get_terminal('for')
    assert type(for_term.recognizer) is RegExRecognizer
    assert for_term.recognizer._regex == r'\bfor\b'

    # '=' term doesn't match KEYWORD rule so it will not change
    eq_term = g.get_terminal('=')
    assert type(eq_term.recognizer) is StringRecognizer


def test_keyword_matches_on_word_boundary():
    g, _ = Grammar.from_struct(
        {'S': [['for', 'ID', '=', 'INT', 'to', 'INT']]},
        {
            'KEYWORD': ('regexp', r'\w+'),
            **common_terminals,
        },
        'S',
    )

    parser = Parser(g)
    with pytest.raises(ParseError) as e:
        # This *will* raise an error
        parser.parse('forid=10 to20')
    assert '"*forid=10 t" => Expected: for' in str(e)
    with pytest.raises(ParseError) as e:
        # This *will* also raise an error
        parser.parse('for id=10 to20')
    assert 'Expected: to' in str(e)

    # But this is OK
    parser.parse('for id=10 to 20')
    parser.parse('for for=10 to 20')


def test_keyword_preferred_over_regexes():
    """
    Test that keyword matches (internally converted to regex matches) are
    preferred over ordinary regex matches of the same length.
    """

    g, _ = Grammar.from_struct(
        {
            'S': [['for?', 'ID?', '=', 'INT', 'to', 'INT']],
            'for?': [[], ['for']],
            'ID?': [[], ['ID']],
        },
        {
            'KEYWORD': ('regexp', r'\w+'),
            **common_terminals,
        },
        'S',
    )

    parser = Parser(g)

    # 'for' is ambiguous as it can be keyword or ID(name)
    # ParseError could be thrown but parglare will prefer
    # StringRecognizer and keywords over RegExRecognizer for
    # the match of the same length (i.e. "more specific match")
    parser.parse("for = 10 to 100")


@pytest.mark.skip
def test_keword_rule():
    """
    Test terminal layout definition.
    """

    with pytest.raises(GrammarError):
        Grammar.from_struct(
            {
                'KEYWORD': [['s']],
            },
            {
                's': ('string', 'a'),
            },
            's',
        )
