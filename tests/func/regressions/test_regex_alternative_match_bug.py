from parglare import Grammar, GLRParser


def test_regex_alternative_match_bug():
    g, _ = Grammar.from_struct(
        {'A': [['Begin', 'Eq', 'End']]},
        {
            'Begin': ('string', 'Begin'),
            'End': ('string', 'End'),
            'Eq': ('regexp', '=|EQ'),
        },
        'A',
    )
    parser = GLRParser(g)
    parser.parse('Begin EQ End')
