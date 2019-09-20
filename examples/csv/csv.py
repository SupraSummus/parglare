from __future__ import unicode_literals
from parglare import Grammar, Parser
from parglare.actions import pass_inner, collect_sep, pass_single

grammar, _ = Grammar.from_struct(
    {
        'CSVFile': [['OptionalNewLines', 'Records', 'OptionalNewLines']],
        'Records': [['Records', 'OptionalNewLines', 'Record'], ['Record']],
        'Record': [['Fields', 'NewLine']],
        'Fields': [['Fields', ',', 'Field'], ['Field']],
        'Field': [['QuotedField'], ['FieldContent']],
        'NewLines': [['NewLine'], ['NewLines', 'NewLine']],
        'OptionalNewLines': [['NewLines'], []],
        'QuotedField': [['"', 'FieldContentQuoted', '"']],
    },
    {
        'FieldContent': ('regexp', r'[^,\n]+'),
        'FieldContentQuoted': ('regexp', r'(("")|([^"]))+'),
        'NewLine': ('string', "\n"),
        ',': ('string', ','),
        '"': ('string', '"'),
    },
    'CSVFile',
)


actions = {
    'CSVFile': pass_inner,
    'Records': collect_sep,
    'Record': pass_single,
    'Fields': collect_sep,
    'QuotedField': pass_inner,
}


def main(debug=False):
    parser = Parser(grammar, actions=actions, ws='\t ', debug=debug, debug_colors=True)

    input_str = """
    First, Second with multiple words, "Third, quoted with comma"


    Next line, Previous line has newlines, 2
    Another Line, 34.45, "Quoted", field


    """

    res = parser.parse(input_str)[0]

    print("Input:\n", input_str)
    print("Result = ", res)


if __name__ == "__main__":
    main(debug=True)
