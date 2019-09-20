from parglare import Grammar


grammar, start_production = Grammar.from_struct(
    {
        'ab': [['a', 'ab', 'a'], []],
    },
    {
        'a': ('string', 'a'),
        'b': ('string', 'b'),
    },
    'ab',
)
