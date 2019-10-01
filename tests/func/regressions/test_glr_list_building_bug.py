from parglare import Grammar, GLRParser
from parglare.actions import collect


def test_glr_list_building_bug():
    """Test regression for a bug in building lists from default `collect` actions."""

    g, _ = Grammar.from_struct(
        {
            'B+': [['B+', 'B'], ['B']],
            'B': [['A+'], ['b', 'A+']],
            'A+': [['A+', 'A'], ['A']],
        },
        {
            'A': ('string', 'a'),
            'b': ('string', 'b'),
        },
        'B+',
    )
    parser = GLRParser(
        g,
        actions={
            'B+': collect,
            'A+': collect,
        },
    )
    result = parser.parse('b a b a a a')

    # possible parses:
    #  * (b a) (b a a a)
    #  * (b a) (b a a) (a)
    #  * (b a) (b a) (a) (a)
    #  * (b a) (b a) (a a)
    assert len(result) == 4
    assert [
        [['b', ['a']], ['b', ['a', 'a', 'a']]],
        None,
    ] in result
