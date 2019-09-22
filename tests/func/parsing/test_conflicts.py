import pytest

from parglare import Grammar, Parser
from parglare.exceptions import SRConflicts, RRConflicts


def test_sr_conflict():
    g, _ = Grammar.from_struct(
        {
            'S': [['As', 'A', 'A']],
            'As': [['As', 'A'], ['A']],
        },
        {'A': ('string', 'A')},
        'S',
    )
    with pytest.raises(SRConflicts) as e:
        Parser(g, prefer_shifts=False)

    assert "As = As A" in str(e.value.conflicts[0].message)


def test_rr_empty_conflict():
    g, _ = Grammar.from_struct(
        {
            'S': [['A', 'B', 'C'], ['A', 'D', 'C']],
            'B': [['B1'], []],
            'D': [['D1'], []],
        },
        {s: ('string', s) for s in ['A', 'C', 'B1', 'D1']},
        'S',
    )
    with pytest.raises(RRConflicts) as e:
        Parser(g)

    # For B and D empty reductions both "A B C" and "A D C" can reduce to S
    assert "B = <EMPTY>" in str(e.value.conflicts[0].message)
    assert "D = <EMPTY>" in str(e.value.conflicts[0].message)


def test_rr_nonempty_conflict():
    g, _ = Grammar.from_struct(
        {
            'S': [['A'], ['B']],
            'A': [['A1', 'B1']],
            'B': [['A1', 'B1']],
        },
        {s: ('string', s) for s in ['A1', 'B1']},
        'S',
    )
    with pytest.raises(RRConflicts) as e:
        Parser(g)

    # "A1 B1" can reduce to both A and B
    assert "A = A1 B1" in str(e.value.conflicts[0].message)
    assert "B = A1 B1" in str(e.value.conflicts[0].message)
