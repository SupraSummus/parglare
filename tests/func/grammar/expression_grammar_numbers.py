from parglare import Grammar


def get_grammar():
    # Expression grammar with float numbers
    return Grammar.from_struct(
        {
            'E': [
                ['E', 'PLUS', 'T'],
                ['T'],
            ],
            'T': [
                ['T', 'MULT', 'F'],
                ['F'],
            ],
            'F': [
                ['OPEN', 'E', 'CLOSE'],
                ['number'],
            ],
        },
        {
            'PLUS': ('string', '+'),
            'MULT': ('string', '*'),
            'OPEN': ('string', '('),
            'CLOSE': ('string', ')'),
            'number': ('regexp', r'\d+(\.\d+)?'),
        },
        'E',
    )[0]
