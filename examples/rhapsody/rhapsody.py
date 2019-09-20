import os

from parglare import Grammar, Parser


def main(debug=False):

    this_folder = os.path.dirname(__file__)
    grammar, _ = Grammar.from_struct(
        {
            'Model': [['Header', 'Object']],
            'Object': [['{', 'ID', 'Property+', '}']],
            'Property+': [['Property+', 'Property'], ['Property']],
            'Property': [
                ['-', 'ID', '=', 'Values', 'SemiColon?'],
                ['-', 'ID', '=', 'SemiColon'],
            ],
            'Values': [
                ['Value'],
                ['Values', 'SemiColon?', 'Value'],
            ],
            'Value': [['STRING'], ['INT'], ['FLOAT'], ['GUID'], ['Object'], ['ID']],
            'SemiColon?': [[], ['SemiColon']],
        },
        {
            'STRING': ('regexp', r'("(\\"|[^"])*")|(\'(\\\'|[^\'])*\')'),
            'INT': ('regexp', r'[-+]?[0-9]+\b'),
            'FLOAT': ('regexp', r'[-+]?[0-9]*\.[0-9]+([eE][-+]?[0-9]+)?\b'),
            'GUID': ('regexp', r'[a-f0-9]*-[a-f0-9]*-[a-f0-9]*-[a-f0-9]*-[a-f0-9]*'),
            'SemiColon': ('string', ';'),
            'ID': ('regexp', r'[a-zA-Z_][a-zA-Z_0-9]*'),
            'Header': ('regexp', r'[^\n]*'),
            '{': ('string', '{'),
            '}': ('string', '}'),
            '-': ('string', '-'),
            '=': ('string', '='),
        },
        'Model',
    )
    parser = Parser(grammar, build_tree=True, debug=debug, debug_colors=True)

    with open(os.path.join(this_folder, 'LightSwitch.rpy'), 'r') as f:
        result = parser.parse(f.read())
        print(result.tree_str())


if __name__ == '__main__':
    main(debug=True)
