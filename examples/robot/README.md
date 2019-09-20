# Robot example

In this example we have a simple language for moving a robot on a discrete grid.
There are two type of commands: (1) setting initial position (2) moving in a
given direction for given steps. If no steps are given 1 is assumed.

- `robot.pg.json` - is the grammar of the language. Language supports C-like comments.
- `program.rbt` - is the "program" executed in this example
- `robot.py` - is a script that defines semantic actions, constructs and
  executes parser.
