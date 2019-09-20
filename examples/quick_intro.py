from parglare import Parser, Grammar

grammar, _ = Grammar.from_struct(
    productions_dict={
        'E1': [
            ['E1', '+', 'E2'],
            ['E1', '-', 'E2'],
            ['E2'],
        ],
        'E2': [
            ['E2', '*', 'E3'],
            ['E2', '/', 'E3'],
            ['E3'],
        ],
        'E3': [
            ['E4', '^', 'E3'],
            ['E4'],
        ],
        'E4': [
            ['(', 'E1', ')'],
            ['number'],
        ],
    },
    terminals_dict={
        'number': ('regexp', r'\d+(\.\d+)?'),
        '+': ('string', '+'),
        '-': ('string', '-'),
        '*': ('string', '*'),
        '/': ('string', '/'),
        '^': ('string', '^'),
        '(': ('string', '('),
        ')': ('string', ')'),
    },
    start='E1',
)

actions = {
    "E1": [
        lambda _, nodes: nodes[0] + nodes[2],
        lambda _, nodes: nodes[0] - nodes[2],
        lambda _, nodes: nodes[0],
    ],
    "E2": [
        lambda _, nodes: nodes[0] * nodes[2],
        lambda _, nodes: nodes[0] / nodes[2],
        lambda _, nodes: nodes[0],
    ],
    "E3": [
        lambda _, nodes: nodes[0] ** nodes[2],
        lambda _, nodes: nodes[0],
    ],
    "E4": [
        lambda _, nodes: nodes[1],
        lambda _, nodes: float(nodes[0]),
    ],
}

parser = Parser(grammar, debug=True, actions=actions)

result = parser.parse("34 + 4.6 / 2 * 4^2^2 + 78")

print("Result = ", result)

# Output
# -- Debugging/tracing output with detailed info about grammar, productions,
# -- terminals and nonterminals, DFA states, parsing progress,
# -- and at the end of the output:
# Result = 700.8
