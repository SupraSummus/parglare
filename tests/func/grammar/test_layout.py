import pytest

from parglare import Parser, GLRParser, Grammar, GrammarError

parsers = pytest.mark.parametrize("parser_class", [Parser, GLRParser])


@parsers
def test_layout_whitespaces(parser_class):
    g, _ = Grammar.from_struct(
        {
            'K': [['K', 'a'], ['s']],
            'LAYOUT': [['WS'], []],
        },
        {
            'a': ('string', 'a'),
            's': ('string', 's'),
            'WS': ('regexp', r'\s+'),
        },
        'K',
    )

    in_str = """saa a    aaaa
    aa    aa a aaa

    aaa
    """

    parser = parser_class(g, debug=True)
    result = parser.parse(in_str)
    assert result

    parser.parse(' s')


@parsers
def test_layout_simple_comments(parser_class):
    g, _ = Grammar.from_struct(
        {
            'K': [['K', 'a'], ['s']],
            'LAYOUT': [[], ['LAYOUT', 'LayoutItem']],
            'LayoutItem': [['WS'], ['Comment']],
        },
        {
            'a': ('string', 'a'),
            's': ('string', 's'),
            'WS': ('regexp', r'\s+'),
            'Comment': ('regexp', r'\/\/.*'),
        },
        'K',
    )

    in_str = """saaa a    aaaa
    aa    aa a aaa // This is a comment

    aaa
    """

    parser = parser_class(g)
    parser.parse(in_str)

    parser.parse("""
        // comment
        sa
    """)


@parsers
def test_layout_nested_comments(parser_class):
    g, _ = Grammar.from_struct(
        {
            'K': [['K', 'a'], ['s']],
            'LAYOUT': [[], ['LAYOUT', 'LayoutItem']],
            'LayoutItem': [['WS'], ['Comment']],
            'Comment': [['LineComment'], ['/*', 'BlockCommentChunks', '*/']],
            'BlockCommentChunks': [[], ['BlockCommentChunks', 'BlockCommentChunk']],
            'BlockCommentChunk': [['Comment'], ['NotComment'], ['WS']],
        },
        {
            'a': ('string', 'a'),
            's': ('string', 's'),
            'WS': ('regexp', r'\s+'),
            'LineComment': ('regexp', r'\/\/.*'),
            'NotComment': ('regexp', r'((\*[^\/])|[^\s*\/]|\/[^\*])+'),
            '/*': ('string', '/*'),
            '*/': ('string', '*/'),
        },
        'K',
    )

    in_str = """//Line comment at beginning
    s  a a a   a // This is line comment
    a a a a a a  /* This is block
    comment */

    aaaa  a a a a a
    /* Another block comment
       // With nested line comment
       /* And nested block
    comment */
    */

    aaaa a a a
    """

    parser = parser_class(g)
    parser.parse(in_str)

    parser.parse('/* /* // \n */ comment body */ s')


@parsers
def test_layout_context(parser_class):
    """
    Test that layout is passed in the action context.
    """
    g, _ = Grammar.from_struct(
        {
            'K': [['K', 'a'], ['s']],
            'LAYOUT': [[], ['LAYOUT', 'LayoutItem']],
            'LayoutItem': [['WS'], ['Comment']],
        },
        {
            'a': ('string', 'a'),
            's': ('string', 's'),
            'WS': ('regexp', r'\s+'),
            'Comment': ('regexp', r'\/\/.*'),
        },
        'K',
    )

    in_str = """ saa a    aaaa
    aa    aa a aaa // This is a comment

    aaa
    """

    def layout_action(context, _):
        layout_called[0] = True
        if 'This is a comment' in context.layout_content:
            layout_passed[0] = True

    actions = {
        "a": layout_action
    }

    layout_called = [False]
    layout_passed = [False]

    parser = parser_class(g, actions=actions)

    parser.parse(in_str)

    assert layout_called[0]
    assert layout_passed[0]


@parsers
def test_layout_actions(parser_class):
    """
    Test that user provided actions for layout rules are called if given.
    """

    g, _ = Grammar.from_struct(
        {
            'K': [['K', 'a'], ['s']],
            'LAYOUT': [[], ['LAYOUT', 'LayoutItem']],
            'LayoutItem': [['WS'], ['Comment']],
        },
        {
            'a': ('string', 'a'),
            's': ('string', 's'),
            'WS': ('regexp', r'\s+'),
            'Comment': ('regexp', r'\/\/.*'),
        },
        'K',
    )

    in_str = """ saa a    aaaa
    aa    aa a aaa // This is a comment

    aaa
    """

    def comment_action(_, nodes):
        layout_called[0] = True

    def layout_action(_, nodes):
        ret = ''
        for n in nodes:
            if n:
                ret += n
        return ret

    def a_action(context, _):
        called[0] = True

    actions = {
        'Comment': comment_action,
        'LAYOUT': layout_action,
        'a': a_action
    }

    called = [False]
    layout_called = [False]

    parser = parser_class(g, actions=actions, layout_actions=actions)
    parser.parse(in_str)

    assert called[0]
    assert layout_called[0]


@pytest.mark.skip
def test_layout_terminal():
    """
    Test terminal layout definition.
    """

    with pytest.raises(GrammarError):
        Grammar.from_struct(
            {},
            {
                's': ('string', 'a'),
                'LAYOUT': ('string', 'b'),
            },
            's',
        )
