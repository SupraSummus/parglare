from os import path
import itertools
import re

from parglare.actions import pass_none
from parglare.common import Location, load_python_module
from parglare.exceptions import GrammarError, ParserInitError
from parglare.termui import prints, s_emph, s_header, a_print, h_print


text = str

# Associativity
ASSOC_NONE = 0
ASSOC_LEFT = 1
ASSOC_RIGHT = 2

# Priority
DEFAULT_PRIORITY = 10

# Multiplicity
MULT_ONE = '1'
MULT_OPTIONAL = '0..1'
MULT_ONE_OR_MORE = '1..*'
MULT_ZERO_OR_MORE = '0..*'

RESERVED_SYMBOL_NAMES = ['EOF', 'STOP', 'EMPTY']
SPECIAL_SYMBOL_NAMES = ['KEYWORD', 'LAYOUT']


def escape(instr):
    return instr.replace('\n', r'\n').replace('\t', r'\t')


class GrammarSymbol(object):
    """
    Represents an abstract grammar symbol.

    Attributes:
    name(str): The name of this grammar symbol.
    location(Location): The location where symbol is defined.
    action_name(string): Name of common/user action given in the grammar.
    action(callable): Resolved action given by the user. Overrides grammar
        action if provided. If not provided by the user defaults to
        grammar_action.
    grammar_action(callable): Resolved action given in the grammar.
    imported_with (PGFileImport): PGFileImport where this symbol is first time
        imported from. Used for FQN calculation.
    user_meta(dict): User meta-data.
    """
    def __init__(self, name, location=None, imported_with=None,
                 user_meta=None):
        self.name = escape(name)
        self.location = location
        self.action_name = None
        self.action = None
        self.grammar_action = None
        self.imported_with = imported_with
        self.user_meta = user_meta
        self._hash = hash(self.fqn)

    @property
    def fqn(self):
        if self.imported_with:
            return "{}.{}".format(self.imported_with.fqn, self.name)
        else:
            return self.name

    @property
    def action_fqn(self):
        if self.action_name:
            if self.imported_with:
                return "{}.{}".format(self.imported_with.fqn, self.action_name)
            else:
                return self.action_name

    def add_user_meta_data(self, name, value):
        if self.user_meta is None:
            self.user_meta = {}
        self.user_meta[name] = value

    def __getattr__(self, name):
        if self.user_meta is not None:
            attr = self.user_meta.get(name)
            if attr:
                return attr
        raise AttributeError

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return self.fqn

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(self))

    def __hash__(self):
        return self._hash


class NonTerminal(GrammarSymbol):
    """Represents a non-termial symbol of the grammar.

    Attributes:
    productions(list of Production): A list of alternative productions for
        this NonTerminal.
    """
    def __init__(self, name, productions=None, location=None,
                 imported_with=None, user_meta=None):
        super(NonTerminal, self).__init__(name, location, imported_with,
                                          user_meta)
        self.productions = productions if productions is not None else []


class Terminal(GrammarSymbol):
    """Represent a terminal symbol of the grammar.

    Attributes:
    prior(int): Priority used for lexical disambiguation.
    dynamic(bool): Should dynamic disambiguation be called to resolve conflict
        involving this terminal.
    finish(bool): Used for scanning optimization. If this terminal is `finish`
        no other recognizers will be checked if this succeeds. If not provided
        in the grammar implicit rules will be used during table construction.
    prefer(bool): Prefer this recognizer in case of multiple recognizers match
        at the same place and implicit disambiguation doesn't resolve.
    keyword(bool): `True` if this Terminal represents keyword. `False` by
        default.

    recognizer(callable): Called with input list of objects and position in the
        stream. Should return a sublist of recognized objects. The sublist
        should be rooted at the given position.
    """
    def __init__(self, name, recognizer=None, location=None,
                 imported_with=None):
        self.prior = DEFAULT_PRIORITY
        self._recognizer = None
        self.recognizer = recognizer if recognizer else StringRecognizer(name)
        self.finish = None
        self.prefer = False
        self.dynamic = False
        self.keyword = False
        super(Terminal, self).__init__(name, location, imported_with,
                                       user_meta=None)

    @property
    def recognizer(self):
        return self._recognizer

    @recognizer.setter
    def recognizer(self, value):
        self._recognizer = value


class Reference(object):
    """
    A name reference to a GrammarSymbol used for cross-resolving during
    grammar construction.
    Attributes:
        name (str): The FQN name of the referred symbol. This is the name of
            the original desuggared symbol without taking into account
            multiplicity and separator.
        location (Location): Location object of this reference.
        multiplicty(str): Multiplicity of the RHS reference (used for regex
            operators ?, *, +). See MULT_* constants above. By default
            multiplicity is MULT_ONE.
        separator (symbol or Reference): A reference to the separator symbol or
            the separator symbol itself if resolved.
    """
    def __init__(self, location, name):
        self.name = name
        self.location = location
        self.multiplicity = MULT_ONE
        self.separator = None

    @property
    def multiplicity_name(self):
        """
        Returns the name of the symbol that should be used if
        multiplicity/separator is used.
        """
        return make_multiplicity_name(
            self.name, self.multiplicity,
            self.separator.name if self.separator else None)

    def clone(self):
        new_ref = Reference(self.location, self.name)
        new_ref.multiplicity = self.multiplicity
        new_ref.separator = self.separator
        return new_ref

    def __repr__(self):
        return self.name


class Recognizer(object):
    """
    Recognizers are callables capable of recognizing low-level patterns
    (a.k.a tokens) in the input.
    """
    def __init__(self, name, location=None):
        self.name = name
        self.location = location


class StringRecognizer(Recognizer):
    def __init__(self, value, ignore_case=False, **kwargs):
        super(StringRecognizer, self).__init__(value, **kwargs)
        self.value = value
        self.ignore_case = ignore_case
        self.value_cmp = value.lower() if ignore_case else value

    def __call__(self, in_str, pos):
        if self.ignore_case:
            if in_str[pos:pos+len(self.value)].lower() == self.value_cmp:
                return self.value
        else:
            if in_str[pos:pos+len(self.value)] == self.value_cmp:
                return self.value


def esc_control_characters(regex):
    """
    Escape control characters in regular expressions.
    """
    unescapes = [('\a', r'\a'), ('\b', r'\b'), ('\f', r'\f'), ('\n', r'\n'),
                 ('\r', r'\r'), ('\t', r'\t'), ('\v', r'\v')]
    for val, text in unescapes:
        regex = regex.replace(val, text)
    return regex


class RegExRecognizer(Recognizer):
    def __init__(self, regex, name=None, re_flags=re.MULTILINE,
                 ignore_case=False, **kwargs):
        if name is None:
            name = regex
        super(RegExRecognizer, self).__init__(name, kwargs)
        self._regex = regex
        self.ignore_case = ignore_case
        if ignore_case:
            re_flags |= re.IGNORECASE
        self.re_flags = re_flags
        try:
            self.regex = re.compile(self._regex, re_flags)
        except re.error as ex:
            regex = esc_control_characters(self._regex)
            message = 'Regex compile error in /{}/ (report: "{}")'
            raise GrammarError(message.format(regex, str(ex)))

    def __call__(self, in_str, pos):
        m = self.regex.match(in_str, pos)
        if m and m.group():
            return m.group()


def EMPTY_recognizer(input, pos):
    pass


def EOF_recognizer(input, pos):
    pass


def STOP_recognizer(input, pos):
    pass


# These two terminals are special terminals used internally.
AUGSYMBOL = NonTerminal("S'")
STOP = Terminal("STOP", STOP_recognizer)

# These two terminals are special terminals used in the grammars.
# EMPTY will match nothing and always succeed.
# EOF will match only at the end of the input string.
EMPTY = Terminal("EMPTY", EMPTY_recognizer)
EMPTY.grammar_action = pass_none
EOF = Terminal("EOF", EOF_recognizer)
EOF.grammar_action = pass_none


class Production(object):
    """Represent production from the grammar.

    Attributes:
    symbol (GrammarSymbol):
    rhs (ProductionRHS):
    assignments(dict): Assignment instances keyed by name.
    assoc (int): Associativity. Used for ambiguity (shift/reduce) resolution.
    prior (int): Priority. Used for ambiguity (shift/reduce) resolution.
    dynamic (bool): Is dynamic disambiguation used for this production.
    nops (bool): Disable prefer_shifts strategy for this production.
        Only makes sense for GLR parser.
    nopse (bool): Disable prefer_shifts_over_empty strategy for this
        production. Only makes sense for GLR parser.
    user_meta(dict): User meta-data.
    prod_id (int): Ordinal number of the production.
    prod_symbol_id (int): A zero-based ordinal of alternative choice for this
        production grammar symbol.
    """

    def __init__(self, symbol, rhs, assignments=None, assoc=ASSOC_NONE,
                 prior=DEFAULT_PRIORITY, dynamic=False, nops=False,
                 nopse=False, user_meta=None):
        """
        Args:
        symbol (GrammarSymbol): A grammar symbol on the LHS of the production.
        rhs (list of GrammarSymbols):
        """
        self.symbol = symbol
        self.rhs = rhs if rhs else ProductionRHS()
        self.assignments = None
        if assignments:
            self.assignments = {}
            for assignment in assignments:
                if assignment.name:
                    self.assignments[assignment.name] = assignment
        self.assoc = assoc
        self.prior = prior
        self.dynamic = dynamic
        self.nops = nops
        self.nopse = nopse
        self.user_meta = user_meta

    def __str__(self):
        if hasattr(self, 'prod_id'):
            return (s_header("%d:") + " %s " + s_emph("=") +
                    " %s") % (self.prod_id, self.symbol, self.rhs)
        else:
            return ("%s " + s_emph("=") + " %s") % (self.symbol, self.rhs)

    def __repr__(self):
        return 'Production({})'.format(str(self.symbol))

    def __getattr__(self, name):
        if self.user_meta is not None:
            attr = self.user_meta.get(name)
            if attr:
                return attr
        raise AttributeError


class ProductionRHS(list):
    def __getitem__(self, idx):
        try:
            while True:
                symbol = super(ProductionRHS, self).__getitem__(idx)
                if symbol is not EMPTY:
                    break
                idx += 1
            return symbol
        except IndexError:
            return None

    def __len__(self):
        return super(ProductionRHS, self).__len__() - self.count(EMPTY)

    def __str__(self):
        if self:
            return " ".join([str(x) for x in self])
        else:
            # empty list
            return "<EMPTY>"

    def __repr__(self):
        return "<ProductionRHS([{}])>".format(
            ", ".join([str(x) for x in self]))


class Assignment(object):
    """
    General assignment (`=` or `?=`, a.k.a. `named matches`) in productions.
    Used also for references as LHS and assignment operator are optional.
    """
    def __init__(self, name, op, symbol):
        """
        Attributes:
            name(str): The name on the LHS of assignment.
            op(str): Either a `=` or `?=`.
            symbol(Reference or GrammarSymbol): A grammar symbol on the RHS.
            symbol_name(str): A de-sugarred grammar symbol name on the
                RHS, i.e. referenced symbol without regex operators.
            multiplicty(str): Multiplicity of the RHS reference (used for regex
                operators ?, *, +). See MULT_* constants above. By default
                multiplicity is MULT_ONE.
            index(int): Index in the production RHS
        """
        self.name = name
        self.op = op
        self.symbol = symbol
        self.symbol_name = symbol.name
        self.multiplicity = symbol.multiplicity \
            if isinstance(symbol, Reference) else MULT_ONE
        self.index = None


class PGAttribute(object):
    """
    PGAttribute definition created by named matches.

    Attributes:
        name(str): The name of the attribute.
        multiplicity(str): Multiplicity of the attribute. See MULT_* constants.
        type_name(str): The type name of the attribute value(s). It is also the
            name of the referring grammar rule.
    """
    def __init__(self, name, multiplicity, type_name):
        self.name = name
        self.multiplicity = multiplicity
        self.type_name = type_name


class PGFile(object):
    """Objects of this class represent parglare grammar files.

    Grammar files can be imported using `import` keyword. Rules referenced from
    the imported grammar must be fully qualified by the grammar module name. By
    default the name of the target .pg file is the name of the module. `as`
    keyword can be used to override the default.

    Example:
    ```
    import `some/path/mygrammar.pg` as target
    ```

    Rules from file `mygrammar.pg` will be available under `target` namespace:

    ```
    MyRule: target.someRule+;
    ```

    Actions are by default loaded from the file named `<grammar>_actions.py`
    where `grammar` is basename of grammar file. Recognizers are loaded from
    `<grammar>_recognizers.py`. Actions and recognizers given this way are both
    optional. Furthermore, both actions and recognizers can be overriden by
    supplying actions and/or recognizers dict during grammar/parser
    instantiation.

    Attributes:

    productions (list of Production): Local productions defined in this file.
    terminals (dict of Terminal):
    classes (dict of ParglareClass): Dynamically created classes. Used by
        obj action.
    imports (dict): Mapping imported module/file local name to PGFile object.
    file_path (str): A full canonic path to the .pg file.
    grammar (PGFile): A root/grammar file.
    recognizers (dict of callables): A dict of Python callables used as a
        terminal recognizers.
    """
    def __init__(self, productions, terminals=None, classes=None, imports=None,
                 file_path=None, grammar=None, recognizers=None,
                 imported_with=None):
        self.productions = productions
        self.terminals = terminals
        self.classes = classes if classes else {}
        self.grammar = self if grammar is None else grammar

        self.file_path = path.realpath(file_path) if file_path else None
        self.imported_with = imported_with
        self.recognizers = recognizers
        self.actions = {}

        # default values (mutable, so shouldnt be provided in function header)
        if self.recognizers is None:
            self.recognizers = {}

        self.collect_and_unify_symbols()

        if self.file_path:
            self.grammar.imported_files[self.file_path] = self

        if imports:
            self.imports = {i.module_name: i for i in imports}
            for i in imports:
                i.grammar = self.grammar
                try:
                    i.load_pgfile()
                except IOError:
                    raise GrammarError(
                        location=Location(file_name=self.file_path),
                        message='Can\'t import file "{}".'.format(
                            i.file_path))
        else:
            self.imports = {}

        self.resolve_references()
        self.load_actions()
        self.load_recognizers()

    def collect_and_unify_symbols(self):
        """Collect non-terminals and terminals (both explicit and implicit/inline)
        defined in this file and make sure there is only one instance for each
        of them.

        """
        nonterminals_by_name = {}
        terminals_by_name = {}
        terminals_by_str_rec = {}

        # Check terminal uniqueness in both name and string recognition
        # and collect all terminals from explicit definitions.
        for terminal in self.terminals:
            if terminal.name in terminals_by_name:
                raise GrammarError(
                    location=terminal.location,
                    message='Multiple definitions of terminal rule "{}"'
                            .format(terminal.name))
            if isinstance(terminal.recognizer, StringRecognizer):
                rec = terminal.recognizer
                if rec.value in terminals_by_str_rec:
                    raise GrammarError(
                        location=terminal.location,
                        message='Terminals "{}" and "{}" match '
                        'the same string.'
                        .format(terminal.name,
                                terminals_by_str_rec[rec.value].name))
                terminals_by_str_rec[rec.value] = terminal
            terminals_by_name[terminal.name] = terminal

        self.terminals = terminals_by_name
        self.terminals_by_str_rec = terminals_by_str_rec

        # Collect non-terminals
        for production in self.productions:
            symbol = production.symbol
            symbol.imported_with = self.imported_with
            # Check that there is no terminal defined by the same name.
            if symbol.name in self.terminals:
                raise GrammarError(
                    location=symbol.location,
                    message='Rule "{}" already defined as terminal'
                    .format(symbol.name))
            # Unify all non-terminal objects
            if symbol.name in nonterminals_by_name:
                old_symbol = symbol
                new_symbol = nonterminals_by_name[symbol.name]
                production.symbol = new_symbol
            else:
                nonterminals_by_name[symbol.name] = symbol
                old_symbol = new_symbol = symbol
            new_symbol.productions.append(production)

            # Check grammar actions for rules/symbols.
            if new_symbol.action_name:
                if new_symbol.action_name != old_symbol.action_name:
                    raise GrammarError(
                        location=new_symbol.location,
                        message='Multiple different grammar actions '
                        'for rule "{}".'.format(new_symbol.name))

        self.nonterminals = nonterminals_by_name
        self.symbols_by_name = dict(nonterminals_by_name)
        self.symbols_by_name.update(self.terminals)

        # Add special terminals
        self.symbols_by_name['EMPTY'] = EMPTY
        self.symbols_by_name['EOF'] = EOF
        self.symbols_by_name['STOP'] = STOP

    def resolve_references(self):
        # Two pass resolving to enable referening symbols created during
        # resolving (e.g. multiplicity symbols).
        for pazz in [True, False]:
            for production in self.productions:
                for idx, ref in enumerate(production.rhs):
                    if isinstance(ref, Reference):
                        production.rhs[idx] = self.resolve_ref(ref, pazz)

    def register_symbol(self, symbol):
        self.symbols_by_name[symbol.name] = symbol

    def load_actions(self):
        """
        Loads actions from <grammar_name>_actions.py if the file exists.
        Actions must be collected with action decorator and the decorator must
        be called `action`.
        """
        actions_file = None
        if self.file_path:
            actions_file = path.join(
                path.dirname(self.file_path),
                "{}_actions.py".format(path.splitext(
                    path.basename(self.file_path))[0]))
            if path.exists(actions_file):
                mod_name = "{}actions".format(
                    self.imported_with.fqn
                    if self.imported_with is not None else "")
                actions_module = load_python_module(mod_name, actions_file)
                if not hasattr(actions_module, 'action'):
                    raise GrammarError(
                        Location(file_name=actions_file),
                        message='Actions file "{}" must have "action" '
                        'decorator defined.'.format(actions_file))
                self.actions = actions_module.action.all

    def load_recognizers(self):
        """Load recognizers from <grammar_name>_recognizers.py. Override
        with provided recognizers.

        """
        if self.file_path:
            recognizers_file = path.join(
                path.dirname(self.file_path),
                "{}_recognizers.py".format(path.splitext(
                    path.basename(self.file_path))[0]))

            if path.exists(recognizers_file):
                mod_name = "{}recognizers".format(
                    self.imported_with.fqn
                    if self.imported_with is not None else "")
                mod_recognizers = load_python_module(mod_name,
                                                     recognizers_file)
                recognizers = mod_recognizers.recognizer.all

                for recognizer_name, recognizer in recognizers.items():
                    symbol = self.resolve_symbol_by_name(
                        recognizer_name,
                        location=Location(file_name=recognizers_file))
                    if symbol is None:
                        raise GrammarError(
                            location=Location(file_name=recognizers_file),
                            message='Recognizer given for unknown '
                            'terminal "{}".'.format(recognizer_name)
                        )
                    if not isinstance(symbol, Terminal):
                        raise GrammarError(
                            location=Location(file_name=recognizers_file),
                            message='Recognizer given for non-terminal "{}".'
                            .format(recognizer_name))
                    symbol.recognizer = recognizer

    def resolve_ref(self, symbol_ref, first_pass=False):
        """Resolves given symbol reference.

        For local name search this file, for FQN use imports and delegate to
        imported file.

        On each resolved symbol productions in the root file are updated.

        If this is first pass do not fail on unexisting reference as there
        might be new symbols created during resolving (e.g. multiplicity
        symbols).

        """
        if isinstance(symbol_ref.separator, Reference):
            symbol_ref.separator = self.resolve_ref(symbol_ref.separator)

        symbol_name = symbol_ref.name
        symbol = self.resolve_symbol_by_name(symbol_name, symbol_ref.location)
        if not symbol:
            if first_pass:
                return symbol_ref
            else:
                raise GrammarError(
                    location=symbol_ref.location,
                    message='Unknown symbol "{}"'.format(symbol_name))

        mult = symbol_ref.multiplicity
        if mult != MULT_ONE:
            # If multiplicity is used than we are referring to
            # suggared symbol

            separator = symbol_ref.separator \
                if symbol_ref.separator else None

            base_symbol = symbol
            symbol_name = symbol_ref.multiplicity_name
            symbol = self.resolve_symbol_by_name(symbol_name,
                                                 symbol_ref.location)
            if not symbol:
                # If there is no multiplicity version of the symbol we
                # will create one at this place
                symbol = self.make_multiplicity_symbol(
                    symbol_ref, base_symbol, separator, self.imported_with)

        return symbol

    def resolve_symbol_by_name(self, symbol_name, location=None):
        """
        Resolves symbol by fqn.
        """
        if '.' in symbol_name:
            import_module_name, name = symbol_name.split('.', 1)
            try:
                imported_pg_file = self.imports[import_module_name]
            except KeyError:
                raise GrammarError(
                    location=location,
                    message='Unexisting module "{}" in reference "{}"'
                    .format(import_module_name, symbol_name))
            return imported_pg_file.resolve_symbol_by_name(name, location)
        else:
            return self.symbols_by_name.get(symbol_name, None)

    def resolve_action_by_name(self, action_name):
        if action_name in self.actions:
            return self.actions[action_name]
        elif '.' in action_name:
            import_module_name, name = action_name.split('.', 1)
            if import_module_name in self.imports:
                imported_pg_file = self.imports[import_module_name]
                return imported_pg_file.resolve_action_by_name(name)

    def make_multiplicity_symbol(self, symbol_ref, base_symbol, separator,
                                 imported_with):
        """
        Creates new NonTerminal for symbol refs using multiplicity and
        separators.
        """
        mult = symbol_ref.multiplicity
        if mult in [MULT_ONE_OR_MORE, MULT_ZERO_OR_MORE]:
            symbol_name = make_multiplicity_name(
                symbol_ref.name, MULT_ONE_OR_MORE,
                separator.name if separator else None)
            symbol = self.resolve_symbol_by_name(symbol_name)
            if not symbol:
                # noqa See: http://www.igordejanovic.net/parglare/grammar_language/#one-or-more_1
                productions = []
                symbol = NonTerminal(symbol_name, productions,
                                     base_symbol.location,
                                     imported_with=imported_with)

                if separator:
                    productions.append(
                        Production(symbol,
                                   ProductionRHS([symbol,
                                                  separator,
                                                  base_symbol])))
                    symbol.action_name = 'collect_sep'
                else:
                    productions.append(
                        Production(symbol,
                                   ProductionRHS([symbol,
                                                  base_symbol])))
                    symbol.action_name = 'collect'

                productions.append(
                    Production(symbol, ProductionRHS([base_symbol])))

                self.register_symbol(symbol)

            if mult == MULT_ZERO_OR_MORE:
                productions = []
                symbol_one = symbol
                symbol_name = make_multiplicity_name(
                    symbol_ref.name, mult,
                    separator.name if separator else None)
                symbol = NonTerminal(symbol_name, productions,
                                     base_symbol.location,
                                     imported_with=imported_with)

                productions.extend([Production(symbol,
                                               ProductionRHS([symbol_one]),
                                               nops=True),
                                    Production(symbol,
                                               ProductionRHS([EMPTY]))])

                def action(_, nodes):
                    if nodes:
                        return nodes[0]
                    else:
                        return []

                symbol.grammar_action = action

                self.register_symbol(symbol)

        else:
            # MULT_OPTIONAL
            if separator:
                raise GrammarError(
                    location=symbol_ref.location,
                    message='Repetition modifier not allowed for '
                    'optional (?) for symbol "{}".'
                    .format(symbol_ref.name))
            productions = []
            symbol_name = make_multiplicity_name(symbol_ref.name, mult)
            symbol = NonTerminal(symbol_name, productions,
                                 base_symbol.location,
                                 imported_with=imported_with)
            productions.extend([Production(symbol,
                                           ProductionRHS([base_symbol])),
                                Production(symbol,
                                           ProductionRHS([EMPTY]))])

            symbol.action_name = 'optional'

            self.register_symbol(symbol)

        return symbol


class Grammar(PGFile):
    """
    Grammar is a collection of production rules, nonterminals and terminals.
    First production is reserved for the augmented production (S' -> S).

    Attributes:
    start_symbol (GrammarSymbol or str): start/root symbol of the grammar or
        its name.
    nonterminals (set of NonTerminal):
    terminals(set of Terminal):
    imported_files(dict): Global registry of all imported files.

    """

    def __init__(self, productions=None, terminals=None,
                 classes=None, imports=None, file_path=None,
                 start_symbol=None,
                 re_flags=re.MULTILINE, ignore_case=False, debug=False,
                 debug_parse=False, debug_colors=False, **kwargs):
        """
        Grammar constructor is not meant to be called directly by the user.
        See `from_str` and `from_file` static methods instead.

        Arguments:
        see Grammar attributes.
        """

        self.imported_files = {}

        super(Grammar, self).__init__(productions=productions,
                                      terminals=terminals,
                                      classes=classes,
                                      imports=imports,
                                      file_path=file_path,
                                      grammar=self,
                                      **kwargs)

        # Determine start symbol. If name is provided search for it. If name is
        # not given use the first production LHS symbol as the start symbol.
        if start_symbol:
            if isinstance(start_symbol, str):
                for p in self.productions:
                    if p.symbol.name == start_symbol:
                        self.start_symbol = p.symbol
            else:
                self.start_symbol = start_symbol
        else:
            # By default, first production symbol is the start symbol.
            self.start_symbol = self.productions[0].symbol

        self._init_grammar()

    def _init_grammar(self):
        """
        Extracts all grammar symbol (nonterminal and terminal) from the
        grammar, resolves and check references in productions, unify all
        grammar symbol objects and enumerate productions.
        """
        # Reserve 0 production. It is used for augmented prod. in LR
        # automata calculation.
        self.productions.insert(
            0,
            Production(AUGSYMBOL, ProductionRHS([self.start_symbol, STOP])))

        self._add_all_symbols_productions()
        self._enumerate_productions()
        self._fix_keyword_terminals()
        self._resolve_actions()

        # Connect recognizers, override grammar provided
        self._connect_override_recognizers()

    def _add_all_symbols_productions(self):

        self.nonterminals = {}
        for prod in self.productions:
            self.nonterminals[prod.symbol.fqn] = prod.symbol
        self.terminals.update([(s.name, s) for s in (EMPTY, EOF, STOP)])

        def add_productions(productions):
            for production in productions:
                symbol = production.symbol
                if symbol.fqn not in self.nonterminals:
                    self.nonterminals[symbol.fqn] = symbol
                for idx, rhs_elem in enumerate(production.rhs):
                    if isinstance(rhs_elem, Terminal):
                        if rhs_elem.fqn not in self.terminals:
                            self.terminals[rhs_elem.fqn] = rhs_elem
                        else:
                            # Unify terminals
                            production.rhs[idx] = self.terminals[rhs_elem.fqn]
                    elif isinstance(rhs_elem, NonTerminal):
                        if rhs_elem.fqn not in self.nonterminals:
                            self.productions.extend(rhs_elem.productions)
                            add_productions(rhs_elem.productions)
                    else:
                        # This should never happen
                        assert False, "Invalid RHS element type '{}'."\
                            .format(type(rhs_elem))
        add_productions(list(self.productions))

    def _enumerate_productions(self):
        """
        Enumerates all productions (prod_id) and production per symbol
        (prod_symbol_id).
        """
        idx_per_symbol = {}
        for idx, prod in enumerate(self.productions):
            prod.prod_id = idx
            prod.prod_symbol_id = idx_per_symbol.get(prod.symbol, 0)
            idx_per_symbol[prod.symbol] = \
                idx_per_symbol.get(prod.symbol, 0) + 1

    def _fix_keyword_terminals(self):
        """
        If KEYWORD terminal with regex match is given fix all matching string
        recognizers to match on a word boundary.
        """
        keyword_term = self.get_terminal('KEYWORD')
        if keyword_term is None:
            return

        # KEYWORD rule must have a regex recognizer
        keyword_rec = keyword_term.recognizer
        if not isinstance(keyword_rec, RegExRecognizer):
            raise GrammarError(
                location=keyword_term.location,
                message='KEYWORD rule must have a regex recognizer defined.')

        # Change each string recognizer corresponding to the KEYWORD
        # regex by the regex recognizer that match on word boundaries.
        for term in self.terminals.values():
            if isinstance(term.recognizer, StringRecognizer):
                match = keyword_rec(term.recognizer.value, 0)
                if match == term.recognizer.value:
                    term.recognizer = RegExRecognizer(
                        r'\b{}\b'.format(match),
                        ignore_case=term.recognizer.ignore_case)
                    term.keyword = True

    def _resolve_actions(self, action_overrides=None,
                         fail_on_no_resolve=False):
        """
        Checks and resolves semantic actions given in the grammar and
        additional `*_actions.py` module.

        Args:
            action_overrides(dict): Dict of actions that take precendence. Used
                for actions supplied during parser construction.
        """
        import parglare.actions as actmodule

        for symbol in self:

            # Resolve trying from most specific to least specific
            action = None

            # 1. Resolve by fully qualified symbol name
            if '.' in symbol.fqn:
                if action_overrides:
                    action = action_overrides.get(symbol.fqn, None)

                if action is None:
                    action = self.resolve_action_by_name(symbol.fqn)

            # 2. Fully qualified action name
            if action is None and symbol.action_fqn is not None \
               and '.' in symbol.action_fqn:
                if action_overrides:
                    action = action_overrides.get(symbol.action_fqn, None)

                if action is None:
                    action = self.resolve_action_by_name(symbol.action_fqn)

            # 3. Symbol name
            if action is None:
                if action_overrides:
                    action = action_overrides.get(symbol.name, None)

                if action is None:
                    action = self.resolve_action_by_name(symbol.name)

            # 4. Action name
            if action is None and symbol.action_name is not None:
                if action_overrides:
                    action = action_overrides.get(symbol.action_name, None)

                if action is None:
                    action = self.resolve_action_by_name(symbol.action_name)

                # 5. Try to find action in built-in actions module.
                if action is None:
                    action_name = symbol.action_name
                    if hasattr(actmodule, action_name):
                        action = getattr(actmodule, action_name)

            if symbol.action_name and action is None \
               and fail_on_no_resolve:
                raise ParserInitError(
                    'Action "{}" given for rule "{}" '
                    'doesn\'t exists in parglare common actions and '
                    'is not provided using "actions" parameter.'
                    .format(symbol.action_name, symbol.name))

            if action is not None:
                symbol.action = action

                # Some sanity checks for actions
                if type(symbol.action) is list:
                    if type(symbol) is Terminal:
                        raise ParserInitError(
                            'Cannot use a list of actions for '
                            'terminal "{}".'.format(symbol.name))
                    else:
                        if len(symbol.action) != len(symbol.productions):
                            raise ParserInitError(
                                'Length of list of actions must match the '
                                'number of productions for non-terminal '
                                '"{}".'.format(symbol.name))
            else:
                symbol.action = symbol.grammar_action

    def _connect_override_recognizers(self):
        for term in self.terminals.values():
            if self.recognizers and term.fqn in self.recognizers:
                term.recognizer = self.recognizers[term.fqn]
            else:
                if term.recognizer is None:
                    if not self.recognizers:
                        raise GrammarError(
                            location=term.location,
                            message='Terminal "{}" has no recognizer defined '
                            'and no recognizers are given during grammar '
                            'construction.'.format(term.fqn))
                    else:
                        if term.fqn not in self.recognizers:
                            raise GrammarError(
                                location=term.location,
                                message='Terminal "{}" has no recognizer '
                                'defined.'.format(term.fqn))

        # checking for unused recognizers
        for recognizer_name in self.recognizers.keys():
            symbol = self.resolve_symbol_by_name(recognizer_name)
            if symbol is None:
                raise GrammarError(
                    message='Recognizer given for unknown '
                    'terminal "{}".'.format(recognizer_name)
                )
            if not isinstance(symbol, Terminal):
                raise GrammarError(
                    message='Recognizer given for non-terminal "{}".'
                    .format(recognizer_name))

    def get_terminal(self, name):
        "Returns terminal with the given fully qualified name or name."
        return self.terminals.get(name)

    def get_nonterminal(self, name):
        "Returns non-terminal with the given fully qualified name or name."
        return self.nonterminals.get(name)

    def get_symbol(self, name):
        "Returns grammar symbol with the given name."
        s = self.get_terminal(name)
        if not s:
            s = self.get_nonterminal(name)
        return s

    def __iter__(self):
        return (s for s in itertools.chain(self.nonterminals.values(),
                                           self.terminals.values())
                if s not in [AUGSYMBOL, STOP])

    def get_production_id(self, name):
        "Returns first production id for the given symbol name"
        for p in self.productions:
            if p.symbol.fqn == name:
                return p.prod_id

    @staticmethod
    def _from_struct_old(productions, start_symbol=None):
        """Used internally to bootstrap grammar file parser."""
        productions, terminals = create_productions_terminals(productions)
        return Grammar(productions,
                       terminals=terminals,
                       start_symbol=start_symbol)

    @staticmethod
    def from_struct(productions_dict, terminals_dict, start, **kwargs):
        """Make parglare Grammar object from plain description dicts.
         * productions_dict is a dictionary mapping nonterminal names into list of alternative productions sequences
         * terminals_dict is a dictionary mapping terminal names into their definition
        Example. A grammar for strings containg a, b and c multiple times:
        Grammar.from_struct(
            {
                'start': [['start', 'a'], ['start', 'b_or_c'], []],
            },
            {
                'a': ('string', 'a'),
                'b_or_c': ('regexp', 'b|c'),
            },
            'start',
        )
        """
        def make_terminal(name, t):
            check_symbol_name(name)
            if not isinstance(t, (tuple, list)) or len(t) != 2:
                raise GrammarError(f"{name} terminal specification has to"
                                   f"be a list or a tuple of two elements")

            typ = t[0]
            if typ == 'external':
                return Terminal(name=name)

            val = t[1]
            if typ == 'string':
                recognizer_class = StringRecognizer
            elif typ == 'regexp':
                recognizer_class = RegExRecognizer
            else:
                raise GrammarError(f"terminal {name}: unknown recognizer type {typ}")
            return Terminal(recognizer=recognizer_class(val), name=name)

        if not isinstance(terminals_dict, dict):
            raise GrammarError("terminals_dict has to be a dict")

        terminals = {
            name: make_terminal(name, value)
            for name, value in terminals_dict.items()
        }

        if not isinstance(productions_dict, dict):
            raise GrammarError("productions_dict has to be a dict")

        for name in productions_dict.keys():
            if name in terminals:
                raise GrammarError(f"production {name} is already defined (as a terminal)")

        non_terminals = {
            name: NonTerminal(name)
            for name in productions_dict.keys()
        }

        def get_symbol(name):
            if name in terminals:
                assert name not in non_terminals
                return terminals[name]
            else:
                return non_terminals.get(name)

        productions = []
        for name, alternatives in productions_dict.items():
            check_symbol_name(name)
            for i, alternative in enumerate(alternatives):
                lhs_symbol = non_terminals[name]
                rhs_symbols = []
                for symbol_name in alternative:
                    symbol = get_symbol(symbol_name)
                    if symbol is None:
                        raise GrammarError(f"production {name}, alternative {i}: "
                                           f"reference to undefined symbol {symbol_name}")
                    rhs_symbols.append(symbol)
                rhs = ProductionRHS(rhs_symbols)
                productions.append(Production(
                    lhs_symbol,
                    rhs,
                ))

        if get_symbol(start) is None:
            raise GrammarError(f"Undefined start symbol {start}")

        meta_start_production_name = '__start'

        if meta_start_production_name in non_terminals or \
           meta_start_production_name in terminals:
            raise GrammarError(f"{meta_start_production_name} symbol name is reserved"
                               f"and you can't use it - sorry")

        start_non_terminal = NonTerminal(meta_start_production_name)
        productions.insert(0, Production(
            start_non_terminal,
            ProductionRHS([get_symbol(start), EOF]),
        ))

        return Grammar(
            productions=productions,
            terminals=terminals.values(),
            start_symbol=start_non_terminal,
            **kwargs,
        ), meta_start_production_name

    def print_debug(self):
        a_print("*** GRAMMAR ***", new_line=True)
        h_print("Terminals:")
        prints(" ".join([text(t) for t in self.terminals]))
        h_print("NonTerminals:")
        prints(" ".join([text(n) for n in self.nonterminals]))

        h_print("Productions:")
        for p in self.productions:
            prints(text(p))


class PGFileImport(object):
    """
    Represents import of a grammar file.

    Attributes:
    module_name (str): Name of this import. By default is the name of grammar
        file without .pg extension.
    file_path (str): A canonical full path of the imported .pg file.
    context (Context): The parsing context.
    imported_with (PGFileImport): First import this import is imported from.
        Used for FQN calculation.
    grammar (Grammar): Grammar object under construction.
    pgfile (PGFile instance or None):

    """
    def __init__(self, module_name, file_path, context):
        self.module_name = module_name
        self.file_path = file_path
        self.context = context
        self.imported_with = context.extra.imported_with
        self.grammar = None
        self.pgfile = None

    @property
    def fqn(self):
        "A fully qualified name of the import following the first import path."
        if self.imported_with:
            return "{}.{}".format(self.imported_with.fqn, self.module_name)
        else:
            return self.module_name

    def resolve_symbol_by_name(self, symbol_name, location=None):
        "Resolves symbol from the imported file."

        return self.pgfile.resolve_symbol_by_name(symbol_name, location)

    def resolve_action_by_name(self, action_name):
        "Resolves action from the imported file."

        return self.pgfile.resolve_action_by_name(action_name)


def create_productions_terminals(productions):
    """Creates Production instances from the list of productions given in
    the form:
    [LHS, RHS, optional ASSOC, optional PRIOR].
    Where LHS is grammar symbol and RHS is a list or tuple of grammar
    symbols from the right-hand side of the production.
    """
    gp = []
    inline_terminals = {}
    for p in productions:
        assoc = ASSOC_NONE
        prior = DEFAULT_PRIORITY
        symbol = p[0]
        if not isinstance(symbol, NonTerminal):
            raise GrammarError(
                location=None,
                message="Invalid production symbol '{}' "
                "for production '{}'".format(symbol, text(p)))
        rhs = ProductionRHS(p[1])
        if len(p) > 2:
            assoc = p[2]
        if len(p) > 3:
            prior = p[3]

        # Convert strings to string recognizers
        for idx, t in enumerate(rhs):
            if isinstance(t, text):
                if t not in inline_terminals:
                    inline_terminals[t] = \
                        Terminal(recognizer=StringRecognizer(t), name=t)
                rhs[idx] = Reference(location=None, name=t)
            elif isinstance(t, Terminal):
                if t.name not in inline_terminals:
                    inline_terminals[t.name] = t
                rhs[idx] = Reference(location=None, name=t.name)

        gp.append(Production(symbol, rhs, assoc=assoc, prior=prior))

    return gp, list(inline_terminals.values())


def make_multiplicity_name(symbol_name, multiplicity=None,
                           separator_name=None):
    if multiplicity is None or multiplicity == MULT_ONE:
        return symbol_name
    name_by_mult = {
        MULT_ZERO_OR_MORE: "0",
        MULT_ONE_OR_MORE: "1",
        MULT_OPTIONAL: "opt"
    }
    if multiplicity:
        return "{}_{}{}".format(
            symbol_name, name_by_mult[multiplicity],
            "_{}".format(separator_name) if separator_name else "")


def check_symbol_name(name):
    """
    Used in actions to check for reserved names usage.
    """

    if name in RESERVED_SYMBOL_NAMES:
        raise GrammarError(
            message='Rule name "{}" is reserved.'.format(name))
    if '.' in name:
        raise GrammarError(
            message='Using dot in names is not allowed.'.format(name))
