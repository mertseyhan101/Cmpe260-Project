# Mert Yilmaz, 2024XXXXXX
# Metehan Yilmaz, 2024XXXXXX

# Melang Interpreter
# CmpE 260 - Spring 2026, Project 1
#
# We built this from scratch - no parser libraries, no magic.
# The language is called Melang (Me(rt) + Me(tehan) + lang).
# It supports lexical scoping, closures, first-class functions,
# and a bunch of other stuff we had to figure out the hard way.

import sys
import math

# ─────────────────────────────────────────────
#  TOKEN TYPES
# ─────────────────────────────────────────────

# Literals
INT     = 'INT'
BOOL    = 'BOOL'
STRING  = 'STRING'

# Identifiers & keywords
IDENT   = 'IDENT'
LET     = 'LET'
FUN     = 'FUN'
IF      = 'IF'
THEN    = 'THEN'
ELSE    = 'ELSE'
END     = 'END'
AND     = 'AND'
OR      = 'OR'
NOT     = 'NOT'
TRUE    = 'TRUE'
FALSE   = 'FALSE'
PRINT   = 'PRINT'

# Bonus keywords (reserved even if bonus not active)
WHILE   = 'WHILE'
DO      = 'DO'
LENGTH  = 'LENGTH'
APPEND  = 'APPEND'

# Operators
PLUS    = 'PLUS'       # +
MINUS   = 'MINUS'      # -
STAR    = 'STAR'       # *
SLASH   = 'SLASH'      # /
EQ      = 'EQ'         # ==
NEQ     = 'NEQ'        # !=
LT      = 'LT'         # <
GT      = 'GT'         # >
LTE     = 'LTE'        # <=
GTE     = 'GTE'        # >=
ASSIGN  = 'ASSIGN'     # =
ARROW   = 'ARROW'      # ->

# Delimiters
LPAREN  = 'LPAREN'     # (
RPAREN  = 'RPAREN'     # )
LBRACE  = 'LBRACE'     # [
RBRACE  = 'RBRACE'     # ]
COMMA   = 'COMMA'      # ,
SEMI    = 'SEMI'       # ;

EOF     = 'EOF'

# keyword table — one place to maintain all reserved words
KEYWORDS = {
    'let':    LET,
    'fun':    FUN,
    'if':     IF,
    'then':   THEN,
    'else':   ELSE,
    'end':    END,
    'and':    AND,
    'or':     OR,
    'not':    NOT,
    'true':   TRUE,
    'false':  FALSE,
    'print':  PRINT,
    'while':  WHILE,
    'do':     DO,
    'length': LENGTH,
    'append': APPEND,
}


class Token:
    """A single token with a type, value, and position for error messages."""
    def __init__(self, type_, value, line=0, col=0):
        self.type  = type_
        self.value = value
        self.line  = line
        self.col   = col

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, {self.line}:{self.col})'


# ─────────────────────────────────────────────
#  LEXER
# ─────────────────────────────────────────────

class LexError(Exception):
    pass


class Lexer:
    """
    Hand-written character-by-character lexer for Melang.

    We keep a position pointer (pos) and walk through the source string
    one character at a time. When we recognise a pattern we emit a Token.
    Line/column tracking is just for decent error messages.
    """

    def __init__(self, source):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1

    # ── helpers ──────────────────────────────

    def current(self):
        """Character under the cursor, or empty string at end-of-file."""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return ''

    def peek(self, offset=1):
        """Look ahead without advancing."""
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return ''

    def advance(self):
        """Move the cursor one step forward, tracking line/col."""
        ch = self.current()
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col   = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace(self):
        while self.current() in (' ', '\t', '\n', '\r'):
            self.advance()

    def skip_block_comment(self):
        """
        Block comments: (* ... *)
        Nesting is NOT supported per the spec, so we just scan
        for the first '*)'  we find.
        """
        # consume the opening '(*'
        self.advance()  # *
        self.advance()  # (  — wait, we already consumed '(' before calling this
        # actually we consumed '(' in tokenize(); here we need to eat '*'
        self.advance()  # consume '*'
        while self.pos < len(self.source):
            if self.current() == '*' and self.peek() == ')':
                self.advance()  # *
                self.advance()  # )
                return
            self.advance()
        raise LexError(f"Unterminated block comment starting around line {self.line}")

    # ── number ───────────────────────────────

    def read_number(self):
        start_line, start_col = self.line, self.col
        digits = []
        while self.current().isdigit():
            digits.append(self.advance())
        value = int(''.join(digits))
        return Token(INT, value, start_line, start_col)

    # ── string ───────────────────────────────

    def read_string(self):
        """
        String literals: "hello\nworld"
        Supported escapes: \n  \t  \\  \"
        """
        start_line, start_col = self.line, self.col
        self.advance()  # opening "
        chars = []
        while self.current() and self.current() != '"':
            ch = self.advance()
            if ch == '\\':
                esc = self.advance()
                if   esc == 'n':  chars.append('\n')
                elif esc == 't':  chars.append('\t')
                elif esc == '\\': chars.append('\\')
                elif esc == '"':  chars.append('"')
                else:
                    raise LexError(f"Unknown escape sequence \\{esc} at {self.line}:{self.col}")
            else:
                chars.append(ch)
        if self.current() != '"':
            raise LexError(f"Unterminated string literal at {start_line}:{start_col}")
        self.advance()  # closing "
        return Token(STRING, ''.join(chars), start_line, start_col)

    # ── identifier / keyword ─────────────────

    def read_ident_or_keyword(self):
        start_line, start_col = self.line, self.col
        chars = []
        while self.current().isalnum() or self.current() == '_':
            chars.append(self.advance())
        word = ''.join(chars)
        tok_type = KEYWORDS.get(word, IDENT)
        # true/false get their Python boolean value baked in
        if tok_type == TRUE:
            return Token(BOOL, True, start_line, start_col)
        if tok_type == FALSE:
            return Token(BOOL, False, start_line, start_col)
        return Token(tok_type, word, start_line, start_col)

    # ── main tokenize loop ───────────────────

    def tokenize(self):
        tokens = []

        while True:
            self.skip_whitespace()

            if not self.current():
                tokens.append(Token(EOF, None, self.line, self.col))
                break

            ch = self.current()
            ln, cl = self.line, self.col

            # ── block comment ──
            if ch == '(' and self.peek() == '*':
                self.advance()  # consume '('
                self.skip_block_comment()
                continue

            # ── string literal ──
            if ch == '"':
                tokens.append(self.read_string())
                continue

            # ── number ──
            if ch.isdigit():
                tokens.append(self.read_number())
                continue

            # ── identifier / keyword ──
            if ch.isalpha() or ch == '_':
                tokens.append(self.read_ident_or_keyword())
                continue

            # ── two-character operators ──
            two = ch + self.peek()
            if two == '==':
                self.advance(); self.advance()
                tokens.append(Token(EQ,     '==', ln, cl)); continue
            if two == '!=':
                self.advance(); self.advance()
                tokens.append(Token(NEQ,    '!=', ln, cl)); continue
            if two == '<=':
                self.advance(); self.advance()
                tokens.append(Token(LTE,    '<=', ln, cl)); continue
            if two == '>=':
                self.advance(); self.advance()
                tokens.append(Token(GTE,    '>=', ln, cl)); continue
            if two == '->':
                self.advance(); self.advance()
                tokens.append(Token(ARROW,  '->', ln, cl)); continue

            # ── single-character operators & delimiters ──
            single = {
                '+': PLUS,   '-': MINUS,  '*': STAR,   '/': SLASH,
                '<': LT,     '>': GT,     '=': ASSIGN,
                '(': LPAREN, ')': RPAREN, ',': COMMA,   ';': SEMI,
                '[': LBRACE, ']': RBRACE,
            }
            if ch in single:
                self.advance()
                tokens.append(Token(single[ch], ch, ln, cl))
                continue

            raise LexError(f"Unexpected character {ch!r} at line {ln}, col {cl}")

        return tokens


# ─────────────────────────────────────────────
#  AST NODES
# ─────────────────────────────────────────────
#
# We use plain Python classes with __repr__ so printing an AST
# during debugging actually tells you something useful.
# Each node stores only what it needs — no fat base class.

class NumberLit:
    def __init__(self, value):          self.value = value
    def __repr__(self):                 return f'NumberLit({self.value})'

class BoolLit:
    def __init__(self, value):          self.value = value
    def __repr__(self):                 return f'BoolLit({self.value})'

class StringLit:
    def __init__(self, value):          self.value = value
    def __repr__(self):                 return f'StringLit({self.value!r})'

class ListLit:
    """[e1, e2, ...]"""
    def __init__(self, elements):       self.elements = elements
    def __repr__(self):                 return f'ListLit({self.elements})'

class Identifier:
    def __init__(self, name):           self.name = name
    def __repr__(self):                 return f'Identifier({self.name!r})'

class BinOp:
    def __init__(self, op, left, right):
        self.op    = op
        self.left  = left
        self.right = right
    def __repr__(self):
        return f'BinOp({self.op!r}, {self.left}, {self.right})'

class UnaryOp:
    def __init__(self, op, operand):
        self.op      = op
        self.operand = operand
    def __repr__(self):
        return f'UnaryOp({self.op!r}, {self.operand})'

class IfExpr:
    def __init__(self, cond, then_block, else_block):
        self.cond       = cond
        self.then_block = then_block
        self.else_block = else_block
    def __repr__(self):
        return f'IfExpr({self.cond}, then={self.then_block}, else={self.else_block})'

class FunExpr:
    def __init__(self, params, body):
        self.params = params   # list of strings
        self.body   = body     # Block node
    def __repr__(self):
        return f'FunExpr(params={self.params}, body={self.body})'

class CallExpr:
    def __init__(self, func, args):
        self.func = func   # expression that evaluates to a function
        self.args = args   # list of expressions
    def __repr__(self):
        return f'CallExpr({self.func}, args={self.args})'

class IndexExpr:
    """lst[i]"""
    def __init__(self, lst, index):
        self.lst   = lst
        self.index = index
    def __repr__(self):
        return f'IndexExpr({self.lst}, {self.index})'

class LetStmt:
    def __init__(self, name, value):
        self.name  = name
        self.value = value
    def __repr__(self):
        return f'LetStmt({self.name!r}, {self.value})'

class AssignStmt:
    def __init__(self, name, value):
        self.name  = name
        self.value = value
    def __repr__(self):
        return f'AssignStmt({self.name!r}, {self.value})'

class PrintStmt:
    def __init__(self, expr):           self.expr = expr
    def __repr__(self):                 return f'PrintStmt({self.expr})'

class WhileStmt:
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body
    def __repr__(self):
        return f'WhileStmt({self.cond}, {self.body})'

class Block:
    """
    A sequence of statements followed by an optional final expression.
    The value of a block is the value of that trailing expression,
    or None if there is none.
    """
    def __init__(self, stmts, expr=None):
        self.stmts = stmts   # list of statement nodes
        self.expr  = expr    # final expression node, may be None
    def __repr__(self):
        return f'Block(stmts={self.stmts}, expr={self.expr})'


# ─────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────

class ParseError(Exception):
    pass


class Parser:
    """
    Recursive descent parser for Melang.

    The precedence table from the spec (lowest → highest):
      1. or
      2. and
      3. == != < > <= >=   (non-associative)
      4. + -               (left)
      5. * /               (left)
      6. not, unary -      (prefix / right)
      7. function call     (left, highest)

    We implement this with one method per precedence level,
    each calling the next level — textbook recursive descent.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    # ── navigation ───────────────────────────

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise ParseError(
                f"Expected {type_!r} but got {tok.type!r} ({tok.value!r}) "
                f"at line {tok.line}, col {tok.col}"
            )
        return self.advance()

    def match(self, *types):
        """Consume and return the current token if its type is in types."""
        if self.current().type in types:
            return self.advance()
        return None

    # ── block ────────────────────────────────

    def parse_block(self, terminators):
        """
        Parse a block until we hit one of the terminator token types.
        A block is: (stmt ';')* expr?

        The tricky part: we need to decide whether something is a
        statement (has a trailing ';') or the final expression (no ';').
        We do one lookahead after parsing each item.
        """
        stmts = []
        final_expr = None

        while self.current().type not in terminators and self.current().type != EOF:
            # Try to parse a statement-or-expression.
            node = self.parse_stmt_or_expr()

            if self.current().type == SEMI:
                # It's a statement — consume the semicolon and keep going.
                self.advance()
                stmts.append(node)
            else:
                # No semicolon — this must be the final expression.
                final_expr = node
                break

        return Block(stmts, final_expr)

    def parse_stmt_or_expr(self):
        """
        Decide what kind of thing we're looking at.
        Statements: let, assignment (ident =), print, while.
        Everything else is an expression.
        """
        tok = self.current()

        if tok.type == LET:
            return self.parse_let()

        if tok.type == PRINT:
            return self.parse_print()

        if tok.type == WHILE:
            return self.parse_while()

        # assignment: IDENT '=' expr  — but NOT IDENT '==' ...
        # We distinguish by peeking at the second token.
        if tok.type == IDENT and self.peek().type == ASSIGN:
            return self.parse_assign()

        # everything else falls through to expression parsing
        return self.parse_expr()

    # ── statements ───────────────────────────

    def parse_let(self):
        self.expect(LET)
        name = self.expect(IDENT).value
        self.expect(ASSIGN)
        value = self.parse_expr()
        return LetStmt(name, value)

    def parse_assign(self):
        name = self.expect(IDENT).value
        self.expect(ASSIGN)
        value = self.parse_expr()
        return AssignStmt(name, value)

    def parse_print(self):
        self.expect(PRINT)
        self.expect(LPAREN)
        expr = self.parse_expr()
        self.expect(RPAREN)
        return PrintStmt(expr)

    def parse_while(self):
        self.expect(WHILE)
        cond = self.parse_expr()
        self.expect(DO)
        body = self.parse_block([END])
        self.expect(END)
        return WhileStmt(cond, body)

    # ── expressions (precedence climbing) ────

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == OR:
            op = self.advance().value
            right = self.parse_and()
            left = BinOp(op, left, right)
        return left

    def parse_and(self):
        left = self.parse_comparison()
        while self.current().type == AND:
            op = self.advance().value
            right = self.parse_comparison()
            left = BinOp(op, left, right)
        return left

    def parse_comparison(self):
        left = self.parse_additive()
        op_types = (EQ, NEQ, LT, GT, LTE, GTE)
        if self.current().type in op_types:
            op = self.advance().value
            right = self.parse_additive()
            return BinOp(op, left, right)
        # non-associative: a == b == c is a parse error
        if self.current().type in op_types:
            tok = self.current()
            raise ParseError(
                f"Comparison operators are non-associative. "
                f"Use parentheses at line {tok.line}, col {tok.col}"
            )
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current().type in (PLUS, MINUS):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinOp(op, left, right)
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current().type in (STAR, SLASH):
            op = self.advance().value
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self):
        if self.current().type == NOT:
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('not', operand)
        if self.current().type == MINUS:
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('-', operand)
        return self.parse_call()

    def parse_call(self):
        """
        Function call is left-associative at the highest precedence:
        f(x)(y) means (f(x))(y)
        Also handles list indexing: lst[i]
        """
        expr = self.parse_primary()

        while True:
            if self.current().type == LPAREN:
                self.advance()
                args = []
                if self.current().type != RPAREN:
                    args.append(self.parse_expr())
                    while self.current().type == COMMA:
                        self.advance()
                        args.append(self.parse_expr())
                self.expect(RPAREN)
                expr = CallExpr(expr, args)

            elif self.current().type == LBRACE:  # [ for list index
                self.advance()
                index = self.parse_expr()
                self.expect(RBRACE)
                expr = IndexExpr(expr, index)

            else:
                break

        return expr

    def parse_primary(self):
        tok = self.current()

        # integer literal
        if tok.type == INT:
            self.advance()
            return NumberLit(tok.value)

        # boolean literal
        if tok.type == BOOL:
            self.advance()
            return BoolLit(tok.value)

        # string literal
        if tok.type == STRING:
            self.advance()
            return StringLit(tok.value)

        # list literal [e1, e2, ...]
        if tok.type == LBRACE:
            return self.parse_list_literal()

        # identifier
        if tok.type == IDENT:
            self.advance()
            return Identifier(tok.name if hasattr(tok, 'name') else tok.value)

        # length(...) — built-in, parsed like a function call syntactically
        if tok.type == LENGTH:
            self.advance()
            self.expect(LPAREN)
            arg = self.parse_expr()
            self.expect(RPAREN)
            return CallExpr(Identifier('__length__'), [arg])

        # append(lst, x)
        if tok.type == APPEND:
            self.advance()
            self.expect(LPAREN)
            lst  = self.parse_expr()
            self.expect(COMMA)
            item = self.parse_expr()
            self.expect(RPAREN)
            return CallExpr(Identifier('__append__'), [lst, item])

        # grouped expression
        if tok.type == LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(RPAREN)
            return expr

        # if expression
        if tok.type == IF:
            return self.parse_if()

        # fun expression
        if tok.type == FUN:
            return self.parse_fun()

        raise ParseError(
            f"Unexpected token {tok.type!r} ({tok.value!r}) "
            f"at line {tok.line}, col {tok.col}"
        )

    def parse_list_literal(self):
        self.expect(LBRACE)   # [
        elements = []
        if self.current().type != RBRACE:
            elements.append(self.parse_expr())
            while self.current().type == COMMA:
                self.advance()
                elements.append(self.parse_expr())
        self.expect(RBRACE)   # ]
        return ListLit(elements)

    def parse_if(self):
        self.expect(IF)
        cond = self.parse_expr()
        self.expect(THEN)
        then_block = self.parse_block([ELSE])
        self.expect(ELSE)
        else_block = self.parse_block([END])
        self.expect(END)
        return IfExpr(cond, then_block, else_block)

    def parse_fun(self):
        self.expect(FUN)
        self.expect(LPAREN)
        params = []
        if self.current().type != RPAREN:
            params.append(self.expect(IDENT).value)
            while self.current().type == COMMA:
                self.advance()
                params.append(self.expect(IDENT).value)
        self.expect(RPAREN)
        self.expect(ARROW)
        body = self.parse_block([END])
        self.expect(END)
        return FunExpr(params, body)

    # ── entry point ──────────────────────────

    def parse(self):
        block = self.parse_block([EOF])
        self.expect(EOF)
        return block


# ─────────────────────────────────────────────
#  ENVIRONMENT
# ─────────────────────────────────────────────
#
# An environment is just a dict with a parent pointer.
# Nothing fancy — but we need it explicit so closures can
# capture it and we can implement both scoping rules.

def make_env(parent=None):
    return {'bindings': {}, 'parent': parent}


def env_lookup(name, env):
    if name in env['bindings']:
        return env['bindings'][name]
    if env['parent'] is not None:
        return env_lookup(name, env['parent'])
    raise RuntimeError(f"Undefined variable: '{name}'")


def env_extend(name, value, env):
    """Create a new binding in the current frame (for let)."""
    env['bindings'][name] = value


def env_update(name, value, env):
    """
    Walk up the chain and update an existing binding (for assignment).
    Raises if name isn't bound anywhere — that's a runtime error.
    """
    if name in env['bindings']:
        env['bindings'][name] = value
        return
    if env['parent'] is not None:
        env_update(name, value, env['parent'])
        return
    raise RuntimeError(f"Assignment to undefined variable: '{name}'")


# ─────────────────────────────────────────────
#  CLOSURE VALUE
# ─────────────────────────────────────────────

class Closure:
    """
    A first-class function value.
    Stores the parameter list, the body AST, and the environment
    that was active when the function was *defined* (for lexical scoping).
    For dynamic scoping we ignore the captured env at call time.
    """
    def __init__(self, params, body, env):
        self.params = params
        self.body   = body
        self.env    = env   # defining environment (used for static scoping)

    def __repr__(self):
        return f'<function({", ".join(self.params)})>'


# ─────────────────────────────────────────────
#  EVALUATOR
# ─────────────────────────────────────────────

class RuntimeError_(Exception):
    """Our own runtime error so we don't accidentally catch Python's."""
    pass


# Sentinel for "this block had no trailing expression"
_VOID = object()


class Interpreter:
    """
    Tree-walking interpreter for Melang.

    Supports both static (lexical) and dynamic scoping,
    selectable via the `scope` parameter.
    """

    def __init__(self, scope='static'):
        if scope not in ('static', 'dynamic'):
            raise ValueError(f"Unknown scope mode: {scope!r}. Use 'static' or 'dynamic'.")
        self.scope = scope

        # Global environment — built-ins live here
        self.global_env = make_env()

        # Register built-in sentinels so lookup doesn't crash
        env_extend('__length__', '__builtin_length__', self.global_env)
        env_extend('__append__', '__builtin_append__', self.global_env)

    # ── public entry point ────────────────────

    def run(self, source):
        try:
            lexer  = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast    = parser.parse()
            result = self.eval_block(ast, self.global_env)
            return result
        except LexError as e:
            print(f"Lex error: {e}", file=sys.stderr)
            sys.exit(1)
        except ParseError as e:
            print(f"Parse error: {e}", file=sys.stderr)
            sys.exit(1)
        except RuntimeError_ as e:
            print(f"Runtime error: {e}", file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(f"Runtime error: {e}", file=sys.stderr)
            sys.exit(1)

    # ── block evaluation ──────────────────────

    def eval_block(self, block, env):
        for stmt in block.stmts:
            self.eval_node(stmt, env)
        if block.expr is not None:
            return self.eval_node(block.expr, env)
        return _VOID

    # ── dispatch ──────────────────────────────

    def eval_node(self, node, env):
        method = 'eval_' + type(node).__name__
        handler = getattr(self, method, None)
        if handler is None:
            raise RuntimeError_(f"Don't know how to evaluate {type(node).__name__}")
        return handler(node, env)

    # ── literals ──────────────────────────────

    def eval_NumberLit(self, node, env):
        return node.value

    def eval_BoolLit(self, node, env):
        return node.value

    def eval_StringLit(self, node, env):
        return node.value

    def eval_ListLit(self, node, env):
        return [self.eval_node(e, env) for e in node.elements]

    # ── identifier ────────────────────────────

    def eval_Identifier(self, node, env):
        return env_lookup(node.name, env)

    # ── statements ────────────────────────────

    def eval_LetStmt(self, node, env):
        """
        Let bindings are implicitly recursive for function values.
        We bind a placeholder first, evaluate the expression (so closures
        can capture a reference to this frame), then overwrite with
        the real value. This lets factorial refer to itself.
        """
        env_extend(node.name, None, env)          # placeholder
        value = self.eval_node(node.value, env)
        env['bindings'][node.name] = value        # overwrite in place
        return _VOID

    def eval_AssignStmt(self, node, env):
        value = self.eval_node(node.value, env)
        env_update(node.name, value, env)
        return _VOID

    def eval_PrintStmt(self, node, env):
        value = self.eval_node(node.expr, env)
        print(self.format_value(value))
        return _VOID

    def eval_WhileStmt(self, node, env):
        # while is a statement — no return value
        while True:
            cond = self.eval_node(node.cond, env)
            if not isinstance(cond, bool):
                raise RuntimeError_(f"While condition must be a boolean, got {type(cond).__name__}")
            if not cond:
                break
            self.eval_block(node.body, env)
        return _VOID

    # ── expressions ───────────────────────────

    def eval_IfExpr(self, node, env):
        cond = self.eval_node(node.cond, env)
        if not isinstance(cond, bool):
            raise RuntimeError_(
                f"Type error: if condition must be boolean, got {self.type_name(cond)}"
            )
        if cond:
            return self.eval_block(node.then_block, env)
        else:
            return self.eval_block(node.else_block, env)

    def eval_FunExpr(self, node, env):
        # Capture the current environment for lexical scoping.
        return Closure(node.params, node.body, env)

    def eval_CallExpr(self, node, env):
        func = self.eval_node(node.func, env)

        # ── built-ins ──
        if func == '__builtin_length__':
            if len(node.args) != 1:
                raise RuntimeError_("length() takes exactly one argument")
            arg = self.eval_node(node.args[0], env)
            if isinstance(arg, str):
                return len(arg)
            if isinstance(arg, list):
                return len(arg)
            raise RuntimeError_(
                f"Type error: length() expects string or list, got {self.type_name(arg)}"
            )

        if func == '__builtin_append__':
            if len(node.args) != 2:
                raise RuntimeError_("append() takes exactly two arguments")
            lst  = self.eval_node(node.args[0], env)
            item = self.eval_node(node.args[1], env)
            if not isinstance(lst, list):
                raise RuntimeError_(
                    f"Type error: append() expects a list, got {self.type_name(lst)}"
                )
            lst.append(item)
            return lst

        if not isinstance(func, Closure):
            raise RuntimeError_(
                f"Type error: tried to call a non-function value: {self.format_value(func)!r}"
            )

        # ── call-by-value: evaluate all arguments first ──
        arg_values = [self.eval_node(a, env) for a in node.args]

        if len(arg_values) != len(func.params):
            raise RuntimeError_(
                f"Arity mismatch: function expects {len(func.params)} argument(s), "
                f"got {len(arg_values)}"
            )

        # ── create new frame ──
        # Static scoping: parent is the closure's defining environment.
        # Dynamic scoping: parent is the *current* call-site environment.
        if self.scope == 'static':
            call_env = make_env(parent=func.env)
        else:
            call_env = make_env(parent=env)

        for param, val in zip(func.params, arg_values):
            env_extend(param, val, call_env)

        return self.eval_block(func.body, call_env)

    def eval_IndexExpr(self, node, env):
        lst = self.eval_node(node.lst, env)
        idx = self.eval_node(node.index, env)
        if not isinstance(lst, list):
            raise RuntimeError_(
                f"Type error: indexing requires a list, got {self.type_name(lst)}"
            )
        if not isinstance(idx, int):
            raise RuntimeError_(
                f"Type error: list index must be an integer, got {self.type_name(idx)}"
            )
        if idx < 0 or idx >= len(lst):
            raise RuntimeError_(
                f"Index out of range: index {idx} for list of length {len(lst)}"
            )
        return lst[idx]

    def eval_UnaryOp(self, node, env):
        val = self.eval_node(node.operand, env)
        if node.op == '-':
            if not isinstance(val, int):
                raise RuntimeError_(
                    f"Type error: unary '-' requires integer, got {self.type_name(val)}"
                )
            return -val
        if node.op == 'not':
            if not isinstance(val, bool):
                raise RuntimeError_(
                    f"Type error: 'not' requires boolean, got {self.type_name(val)}"
                )
            return not val
        raise RuntimeError_(f"Unknown unary operator: {node.op!r}")

    def eval_BinOp(self, node, env):
        op = node.op

        # Short-circuit evaluation for logical operators
        if op == 'or':
            left = self.eval_node(node.left, env)
            self._check_bool(left, 'or')
            return left or self.eval_node(node.right, env)

        if op == 'and':
            left = self.eval_node(node.left, env)
            self._check_bool(left, 'and')
            return left and self.eval_node(node.right, env)

        left  = self.eval_node(node.left, env)
        right = self.eval_node(node.right, env)

        # arithmetic
        if op == '+':
            if isinstance(left, int) and isinstance(right, int):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise RuntimeError_(
                f"Type error: '+' requires two integers or two strings, "
                f"got {self.type_name(left)} and {self.type_name(right)}"
            )
        if op == '-':
            self._check_int2(left, right, '-')
            return left - right
        if op == '*':
            self._check_int2(left, right, '*')
            return left * right
        if op == '/':
            self._check_int2(left, right, '/')
            if right == 0:
                raise RuntimeError_("Runtime error: division by zero")
            # truncate toward zero, like C/Java (NOT Python's //)
            return math.trunc(left / right)

        # comparison
        if op in ('==', '!='):
            result = (left == right)
            return result if op == '==' else not result

        if op in ('<', '>', '<=', '>='):
            if type(left) != type(right):
                raise RuntimeError_(
                    f"Type error: cannot compare {self.type_name(left)} "
                    f"and {self.type_name(right)}"
                )
            if op == '<':  return left < right
            if op == '>':  return left > right
            if op == '<=': return left <= right
            if op == '>=': return left >= right

        raise RuntimeError_(f"Unknown binary operator: {op!r}")

    # ── helpers ───────────────────────────────

    def _check_bool(self, val, op):
        if not isinstance(val, bool):
            raise RuntimeError_(
                f"Type error: '{op}' requires boolean, got {self.type_name(val)}"
            )

    def _check_int2(self, left, right, op):
        if not isinstance(left, int) or not isinstance(right, int):
            raise RuntimeError_(
                f"Type error: '{op}' requires two integers, "
                f"got {self.type_name(left)} and {self.type_name(right)}"
            )

    def type_name(self, val):
        if isinstance(val, bool):  return 'boolean'   # bool before int — Python subclass!
        if isinstance(val, int):   return 'integer'
        if isinstance(val, str):   return 'string'
        if isinstance(val, list):  return 'list'
        if isinstance(val, Closure): return 'function'
        return type(val).__name__

    def format_value(self, val):
        """How values look when printed."""
        if isinstance(val, bool):   return 'true' if val else 'false'
        if isinstance(val, int):    return str(val)
        if isinstance(val, str):    return val
        if isinstance(val, list):   return '[' + ', '.join(self.format_list_elem(e) for e in val) + ']'
        if isinstance(val, Closure): return '<function>'
        return str(val)

    def format_list_elem(self, val):
        """Inside a list, strings are shown with surrounding quotes."""
        if isinstance(val, str):    return f'"{val}"'
        return self.format_value(val)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    # Parse CLI arguments manually — no argparse so we keep dependencies minimal.
    args   = sys.argv[1:]
    scope  = 'static'   # default

    # pull out --scope flag if present
    if '--scope' in args:
        idx = args.index('--scope')
        if idx + 1 >= len(args):
            print("Error: --scope requires an argument (static or dynamic)", file=sys.stderr)
            sys.exit(1)
        scope = args[idx + 1]
        args  = args[:idx] + args[idx + 2:]

    if not args:
        print("Usage: python interpreter.py [--scope static|dynamic] <program.txt>", file=sys.stderr)
        sys.exit(1)

    filename = args[0]
    try:
        with open(filename, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {filename!r}", file=sys.stderr)
        sys.exit(1)

    interpreter = Interpreter(scope=scope)
    interpreter.run(source)


if __name__ == '__main__':
    main()
