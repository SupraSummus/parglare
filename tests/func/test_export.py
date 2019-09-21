import os
import tempfile
from parglare import Grammar
from parglare.tables import create_table
from parglare.export import grammar_pda_export


def test_dot_export():
    grammar, _ = Grammar.from_struct(
        {'S': [['S', 'S'], ['S', 'S', 'S'], ['b']]},
        {'b': ('string', 'b')},
        'S',
    )

    table = create_table(grammar)

    tmp_dir = tempfile.mkdtemp()
    file_name = os.path.join(tmp_dir, 'testexport.dot')

    grammar_pda_export(table, file_name)

    with open(file_name) as f:
        assert 'label' in f.read()

    os.remove(file_name)
    os.rmdir(tmp_dir)
