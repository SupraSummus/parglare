"""Test lexical disambiguation strategy.

Longest-match strategy is first used. If more tokens has the same length
priority is given to the more specific match (i.e. str match over regex).
If ambiguity is still unresolved priority is checked as the last resort.
At the end disambiguation error is reported.

"""
import pytest
import difflib
import re

from parglare import Parser, Grammar, Token, ParseError, DisambiguationError


called = [False, False, False]


def act_called(which_called):
    def _called(_, __):
        called[which_called] = True
    return _called


actions = {
    "a": act_called(0),
    "b": act_called(1),
    "c": act_called(2),
}


@pytest.fixture()
def cf():
    global called
    called = [False, False, False]


def test_most_specific(cf):
    g, _ = Grammar.from_struct(
        {'s': [['a'], ['b']]},
        {
            'a': ('string', '14'),
            'b': ('regexp', r'\d+'),
        },
        's',
    )
    parser = Parser(g, actions=actions)

    # String match in string rule is more specific than regexp rule.
    parser.parse('14')
    assert called[0]
    assert not called[1]


def test_most_specific_longest_match(cf):
    g, _ = Grammar.from_struct(
        {'s': [['a', '7'], ['b'], ['c']]},
        {
            'a': ('string', '14'),
            'b': ('regexp', r'\d+'),
            'c': ('string', '147'),
            '7': ('string', '7'),
        },
        's',
    )
    parser = Parser(g, actions=actions)

    # All three rules could match. 'c' is tried first because it is
    # more specific (str match) and longest. It succeeds so other two
    # are not tried at all.
    parser.parse('147')
    assert called == [False, False, True]


def test_longest_match(cf):
    g, _ = Grammar.from_struct(
        {'s': [['a', 'dot', 'a'], ['b']]},
        {
            'a': ('regexp', r'\d+'),
            'b': ('regexp', r'\d+.\d+'),
            'dot': ('string', '.'),
        },
        's',
    )
    parser = Parser(g, actions=actions)

    # If all matches are regexes of the same priority use longest match
    # disambiguation.
    parser.parse('14.17')
    assert called == [False, True, False]


def test_failed_disambiguation(cf):
    g, _ = Grammar.from_struct(
        {'s': [['a'], ['b']]},
        {
            'a': ('regexp', r'\d+.\d+'),
            'b': ('regexp', r'\d+.75'),
        },
        's',
    )
    parser = Parser(g, actions=actions, debug=True)

    # Both are regexes so longest match will be used.
    # Both have the same length.

    with pytest.raises(DisambiguationError) as e:
        parser.parse('14.75')

    assert 'disambiguate' in str(e)
    assert 'a(' in str(e)
    assert 'b(' in str(e)


def test_dynamic_lexical_disambiguation():
    """
    Dynamic disambiguation enables us to choose right token from the
    tokens posible to appear at given place in the input.
    """
    g, _ = Grammar.from_struct(
        {
            'Element+': [['Element'], ['Element+', 'Element']],
            'Element': [['Bar'], ['Baz'], ['Number']],
        },
        {
            'Bar': ('regexp', r'Bar. \d+'),
            'Baz': ('regexp', r'Baz. \d+'),
            'Number': ('regexp', r'\d+'),
        },
        'Element+',
    )

    def custom_token_recognition(context, get_tokens):
        """
        Custom token recognition should return a single token that is
        recognized at the given place in the input string.
        """
        # Call default token recognition.
        tokens = get_tokens()

        if tokens:
            # If default recognition succeeds use the result.
            return tokens
        else:
            # If no tokens are found do the fuzzy match.
            matchers = [
                lambda x: difflib.SequenceMatcher(None, 'bar.', x.lower()),
                lambda x: difflib.SequenceMatcher(None, 'baz.', x.lower())
            ]
            symbols = [
                g.get_terminal('Bar'),
                g.get_terminal('Baz'),
            ]
            # Try to do fuzzy match at the position
            elem = context.input_str[context.position:context.position+4]
            elem_num = context.input_str[context.position:]
            number_matcher = re.compile(r'[^\d]*(\d+)')
            number_match = number_matcher.match(elem_num)
            ratios = []
            for matcher in matchers:
                ratios.append(matcher(elem).ratio())

            max_ratio_index = ratios.index(max(ratios))
            if ratios[max_ratio_index] > 0.7 and number_match.group(1):
                return [Token(symbols[max_ratio_index], number_match.group())]

    parser = Parser(
        g, custom_token_recognition=custom_token_recognition)

    # Bar and Baz will be recognized by a fuzzy match
    result = parser.parse('bar. 56 Baz 12')
    assert result == [['bar. 56', 'Baz 12'], None]

    result = parser.parse('Buz. 34 bar 56')
    assert result == [['Buz. 34', 'bar 56'], None]

    result = parser.parse('Ba. 34 baz 56')
    assert result == [['Ba. 34', 'baz 56'], None]

    # But if Bar/Baz are too different from the correct pattern
    # we get ParseError. In this case `bza` score is below 0.7
    # for both Bar and Baz symbols.
    with pytest.raises(ParseError):
        parser.parse('Bar. 34 bza 56')
