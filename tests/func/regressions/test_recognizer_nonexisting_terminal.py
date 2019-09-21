import pytest
from parglare import Grammar, GrammarError, get_collector


recognizer = get_collector()


@recognizer
def A(input, pos):
    return [input[pos]]


# This should raise an exception as there is no `B` terminal in the grammar
@recognizer
def B(input, pos):
    return [input[pos]]


def test_recognizer_for_unexisting_terminal_raises_exception():
    """
    If a recognizer is given for a terminal that can't be found in the grammar
    raise an exception.
    """

    with pytest.raises(GrammarError,
                       match=r'.*given for unknown terminal "B".'):
        Grammar.from_struct(
            {'S': [['A']]},
            {'A': ('string', 'a')},
            'S',
            recognizers=recognizer.all,
        )
