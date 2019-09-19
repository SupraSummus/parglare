# Tracing and debugging

Printing detailed debug information on grammar can be achieved by putting
the grammar in the debug mode:

```python
grammar = Grammar.from_file(file_name, debug=True)
```

For example, `calc` grammar from the quick intro would give the following
output:

```nohighlight
*** GRAMMAR ***
Terminals:
EMPTY - * ^ + STOP ( \d+(\.\d+)? number / EOF )
NonTerminals:
E S'
Productions:
0: S' = E STOP
1: E = E + E
2: E = E - E
3: E = E * E
4: E = E / E
5: E = E ^ E
6: E = ( E )
7: E = number
```

During grammar object construction, grammar file is parsed using the parglare
itself and the grammar object for the new language is constructed. If you want
to see the debug output of this process set the `parse_debug` parameter to
`True`:

```python
grammar = Grammar.from_file(file_name, parse_debug=True)
```


If you are using [custom recognizers](./recognizers.md) or would like to see the
result of each [action](./actions.md) in debug output then you should put the
parser in the debug mode from the code.

To put the parser in the debug mode do:

```python
parser = Parser(grammar, debug=True)
```


To debug [layout
grammar](./grammar_language.md#handling-whitespaces-and-comments) do:

```python
parser = Parser(grammar, debug_layout=True)
```


`GLRParser` can produce visual trace. To enable
visual tracing set `debug` and `debug_trace` to `True`:

```python
parser = GLRParser(grammar, debug=True, debug_trace=True)
```
