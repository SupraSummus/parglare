import pytest

from parglare import Parser, Grammar
from parglare.exceptions import RRConflicts


def test_repeatable_one_zero_rr_conflicts():
    """
    Check that translations of B+ and B* don't produce R/R conflict.
    """

    g, _ = Grammar.from_struct(
        {
            's': [
                ['a', 'b+', 'c'],
                ['a', 'b*', 'd'],
            ],
            'b+': [['b+', 'b'], ['b']],
            'b*': [['b*', 'b'], []],
        },
        {
            s: ('string', s)
            for s in ['a', 'b', 'c', 'd']
        },
        's',
    )

    # Check if parser construction raises exception
    try:
        Parser(g)
    except RRConflicts:
        pytest.fail("R/R conflicts not expected here.")
