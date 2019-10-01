from parglare import Grammar, GLRParser


def test_issue31_glr_drop_parses_on_lexical_ambiguity():
    # this input should yield 4 parse trees.
    input = "title table title table"

    g, _ = Grammar.from_struct(
        {
            'element+': [['element+', 'element'], ['element']],
            'element': [['title'], ['table_with_title'], ['table_with_title']],
            'table_with_title': [['table_title', 'table_with_note']],
            'table_with_note': [['table', 'note*']],
            'note*': [[], ['note*', 'note']],
        },
        {
            'title': ('regexp', 'title'),
            'table_title': ('regexp', 'title'),
            'table': ('string', 'table'),
            'note': ('string', 'note'),
        },
        'element+',
    )

    parser = GLRParser(g, debug=True, debug_colors=True)
    results = parser.parse(input)

    # We should have 4 solutions for the input.
    assert len(results) == 4
