from __future__ import unicode_literals
from parglare import Grammar, Parser
from parglare.actions import pass_inner, pass_single

grammar, _ = Grammar.from_struct(
    {
        'Calc': [['Assignments', 'E1']],
        'Assignments': [['Assignment'], ['Assignments', 'Assignment'], []],
        'Assignment': [['VariableName', "=", 'Number']],
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
            ['(', 'E1', ')'],
            ['Number'],
            ['VariableName'],
        ],
    },
    {
        'VariableName': ('regexp', r'[a-zA-Z_][_a-zA-Z0-9]*'),
        'Number': ('regexp', r'\d+(\.\d+)?'),
        '+': ('string', '+'),
        '-': ('string', '-'),
        '*': ('string', '*'),
        '/': ('string', '/'),
        '(': ('string', '('),
        ')': ('string', ')'),
        '=': ('string', '='),
    },
    'Calc',
)


# Semantic Actions
def act_assignment(context, nodes):
    """Semantic action for variable assignment."""

    name = nodes[0]
    number = float(nodes[2])

    if context.extra is None:
        context.extra = {}

    context.extra[name] = number


actions = {
    "Calc": pass_inner,
    "Assignment": act_assignment,
    "E1": [
        lambda _, nodes: nodes[0] + nodes[2],
        lambda _, nodes: nodes[0] - nodes[2],
        pass_single,
    ],
    "E2": [
        lambda _, nodes: nodes[0] * nodes[2],
        lambda _, nodes: nodes[0] / nodes[2],
        pass_single,
    ],
    "E3": [
        pass_inner,
        lambda _, nodes: float(nodes[0]),
        lambda context, nodes: context.extra[nodes[0]],
    ],
}


def main(debug=False):
    parser = Parser(grammar, actions=actions, debug=debug, debug_colors=True)

    input_str = """
    a = 5
    b = 10

    a + 56.4 / 3 * 5 - b + 8 * 3
    """

    res = parser.parse(input_str)[0]
    print(res)

    assert res == 5. + 56.4 / 3 * 5 - 10 + 8 * 3
    print("Input:\n", input_str)
    print("Result = ", res)


if __name__ == "__main__":
    main(debug=True)
