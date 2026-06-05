# Mert Seyhan, 2023400213
# Metehan Seyhan, 2023400111

# Melang Interpreter
# CmpE 260 - Spring 2026, Project 1
#
# We built this from scratch - no parser libraries.
# The language is called Melang (Me(rt) + Me(tehan) + lang).
# It supports lexical scoping, closures, first-class functions,
# and a bunch of other stuff we had to figure out the hard way.

import sys

# ─────────────────────────────────────────────
#  TOKEN TYPES
# ─────────────────────────────────────────────

# We define string constants for our literal token types.
INT     = 'INT'
BOOL    = 'BOOL'
STRING  = 'STRING'

# We list all the identifiers and keywords our language supports.
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

# We also reserve some keywords for the bonus parts of the project.
WHILE   = 'WHILE'
DO      = 'DO'
LENGTH  = 'LENGTH'
APPEND  = 'APPEND'

# Here we define the mathematical and logical operators.
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

# Finally, we define the delimiters used in our language syntax.
LPAREN  = 'LPAREN'     # (
RPAREN  = 'RPAREN'     # )
LBRACE  = 'LBRACE'     # [
RBRACE  = 'RBRACE'     # ]
COMMA   = 'COMMA'      # ,
SEMI    = 'SEMI'       # ;

EOF     = 'EOF'

# We use a dictionary to easily map string values to their respective token types.
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
    # We define a basic Token class to hold the type, the actual string value,
    # and the line/column numbers so we can show proper error messages later.
    def __init__(self, type_, value, line=0, col=0):
        self.type  = type_
        self.value = value
        self.line  = line
        self.col   = col

    # We override the representation method to make debugging easier.
    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, {self.line}:{self.col})'

# ─────────────────────────────────────────────
#  LEXER
# ─────────────────────────────────────────────

class LexError(Exception):
    # We create a custom exception class to catch lexical errors cleanly.
    pass

class Lexer:
    # We initialize the lexer with the raw source code string.
    # We also keep track of our current position, line, and column.
    def __init__(self, source):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1

    # We check the current character under our pointer.
    def current(self):
        if self.pos < len(self.source):
            return self.source[self.pos]
        return ''

    # We look ahead by a certain offset without actually moving the pointer.
    def peek(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return ''

    # We move the pointer forward by one character.
    # We also increment the line counter if we hit a newline character.
    def advance(self):
        ch = self.current()
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col   = 1
        else:
            self.col += 1
        return ch

    # We simply ignore any spaces, tabs, or newlines in the source code.
    def skip_whitespace(self):
        while self.current() in (' ', '\t', '\n', '\r'):
            self.advance()

    def skip_block_comment(self):
        # We handle block comments. Since nesting is not required by the spec,
        # we just advance until we find the closing sequence '*)'.
        self.advance()
        self.advance()
        while self.pos < len(self.source):
            # We check if the current and next characters form the closing tag.
            if self.current() == '*' and self.peek() == ')':
                self.advance()
                self.advance()
                return
            self.advance()
        # If we reach the end of the file without closing the comment, we throw an error.
        raise LexError(f"Unterminated block comment starting around line {self.line}")

    def read_number(self):
        # We read consecutive digits and group them to form an integer.
        start_line, start_col = self.line, self.col
        digits = []
        while self.current().isdigit():
            digits.append(self.advance())
        # We convert the collected string of digits into a Python int.
        value = int(''.join(digits))
        return Token(INT, value, start_line, start_col)

    def read_string(self):
        # We read a string literal enclosed in double quotes.
        start_line, start_col = self.line, self.col
        self.advance()
        chars = []
        while self.current() and self.current() != '"':
            ch = self.advance()
            # We handle escape sequences like newline, tab, and escaped quotes.
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
        
        # We throw an error if the string is not properly closed before the EOF.
        if self.current() != '"':
            raise LexError(f"Unterminated string literal at {start_line}:{start_col}")
        self.advance()
        return Token(STRING, ''.join(chars), start_line, start_col)

    def read_ident_or_keyword(self):
        # We extract variable names or reserved keywords.
        start_line, start_col = self.line, self.col
        chars = []
        # We allow alphanumeric characters and underscores for identifiers.
        while self.current().isalnum() or self.current() == '_':
            chars.append(self.advance())
        word = ''.join(chars)
        
        # We check if the extracted word is a known keyword; otherwise, it is an identifier.
        tok_type = KEYWORDS.get(word, IDENT)
        if tok_type == TRUE:
            return Token(BOOL, True, start_line, start_col)
        if tok_type == FALSE:
            return Token(BOOL, False, start_line, start_col)
        return Token(tok_type, word, start_line, start_col)

    def tokenize(self):
        # We loop through the entire source code and build our token list.
        tokens = []
        while True:
            # We always skip spaces before trying to read the next token.
            self.skip_whitespace()

            # If we reach the end of the input, we append our EOF token and break.
            if not self.current():
                tokens.append(Token(EOF, None, self.line, self.col))
                break

            ch = self.current()
            ln, cl = self.line, self.col

            # We check for the start of a block comment '(*'
            if ch == '(' and self.peek() == '*':
                self.advance()
                self.skip_block_comment()
                continue

            # We start reading a string if we see a double quote.
            if ch == '"':
                tokens.append(self.read_string())
                continue

            # We start reading a number if the character is a digit.
            if ch.isdigit():
                tokens.append(self.read_number())
                continue

            # We start reading an identifier or keyword if we see a letter or underscore.
            if ch.isalpha() or ch == '_':
                tokens.append(self.read_ident_or_keyword())
                continue

            # We handle two-character operators by peeking at the next character.
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

            # We handle single-character operators and punctuation marks here.
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

            # If none of the above matches, we encountered an illegal character.
            raise LexError(f"Unexpected character {ch!r} at line {ln}, col {cl}")

        return tokens


# ─────────────────────────────────────────────
#  AST NODES
# ─────────────────────────────────────────────

# We define simple classes for our Abstract Syntax Tree nodes.
# They just hold the necessary data for the evaluator.
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
    def __init__(self, elements):       self.elements = elements
    def __repr__(self):                 return f'ListLit({self.elements})'

class Identifier:
    def __init__(self, name):           self.name = name
    def __repr__(self):                 return f'Identifier({self.name!r})'

class BinOp:
    # We store the operator as a string, and the left/right child nodes.
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
    # If expressions need a condition and two branches (then and else).
    def __init__(self, cond, then_block, else_block):
        self.cond       = cond
        self.then_block = then_block
        self.else_block = else_block
    def __repr__(self):
        return f'IfExpr({self.cond}, then={self.then_block}, else={self.else_block})'

class FunExpr:
    # Function definitions hold their parameters and the block of code inside them.
    def __init__(self, params, body):
        self.params = params
        self.body   = body
    def __repr__(self):
        return f'FunExpr(params={self.params}, body={self.body})'

class CallExpr:
    def __init__(self, func, args):
        self.func = func
        self.args = args
    def __repr__(self):
        return f'CallExpr({self.func}, args={self.args})'

class IndexExpr:
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
    # A block can have a list of statements and an optional final expression.
    def __init__(self, stmts, expr=None):
        self.stmts = stmts
        self.expr  = expr
    def __repr__(self):
        return f'Block(stmts={self.stmts}, expr={self.expr})'


# ─────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────

class ParseError(Exception):
    # We define a custom exception to handle parsing errors gracefully.
    pass

class Parser:
    # We initialize the parser with the token list produced by our lexer.
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    # We retrieve the current token from the list.
    def current(self):
        return self.tokens[self.pos]

    # We look ahead at the upcoming tokens without advancing our position.
    def peek(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    # We return the current token and advance our position pointer.
    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    # We check if the current token matches our expectation. If not, we throw an error.
    def expect(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise ParseError(
                f"Expected {type_!r} but got {tok.type!r} ({tok.value!r}) "
                f"at line {tok.line}, col {tok.col}"
            )
        return self.advance()

    def parse_block(self, terminators):
        # We parse statements until we encounter a terminating token or the end of the file.
        stmts = []
        final_expr = None

        while self.current().type not in terminators and self.current().type != EOF:
            node = self.parse_stmt_or_expr()

            # If the node ends with a semicolon, we treat it as a statement.
            if self.current().type == SEMI:
                self.advance()
                stmts.append(node)
            else:
                # Otherwise, it must be the final expression of the block.
                final_expr = node
                break

        return Block(stmts, final_expr)

    def parse_stmt_or_expr(self):
        # We determine the type of statement or expression based on the current token.
        tok = self.current()

        if tok.type == LET:
            return self.parse_let()
        if tok.type == PRINT:
            return self.parse_print()
        if tok.type == WHILE:
            return self.parse_while()

        # If we see an identifier followed by an equals sign, it is an assignment.
        if tok.type == IDENT and self.peek().type == ASSIGN:
            return self.parse_assign()

        # If it doesn't match any statement, we try to parse it as an expression.
        return self.parse_expr()

    def parse_let(self):
        # We consume the 'let' keyword, the identifier, the '=' sign, and then parse the value.
        self.expect(LET)
        name = self.expect(IDENT).value
        self.expect(ASSIGN)
        value = self.parse_expr()
        return LetStmt(name, value)

    def parse_assign(self):
        # We handle variable assignments similarly to let statements.
        name = self.expect(IDENT).value
        self.expect(ASSIGN)
        value = self.parse_expr()
        return AssignStmt(name, value)

    def parse_print(self):
        # We parse print statements, ensuring they have parentheses.
        self.expect(PRINT)
        self.expect(LPAREN)
        expr = self.parse_expr()
        self.expect(RPAREN)
        return PrintStmt(expr)

    def parse_while(self):
        # We parse the while loop condition and its body block.
        self.expect(WHILE)
        cond = self.parse_expr()
        self.expect(DO)
        body = self.parse_block([END])
        self.expect(END)
        return WhileStmt(cond, body)

    def parse_expr(self):
        # We start the expression parsing with the lowest precedence operator (OR).
        return self.parse_or()

    def parse_or(self):
        # We parse left-associative OR operations.
        left = self.parse_and()
        while self.current().type == OR:
            op = self.advance().value
            right = self.parse_and()
            left = BinOp(op, left, right)
        return left

    def parse_and(self):
        # We parse left-associative AND operations.
        left = self.parse_comparison()
        while self.current().type == AND:
            op = self.advance().value
            right = self.parse_comparison()
            left = BinOp(op, left, right)
        return left

    def parse_comparison(self):
        # We handle comparison operators, ensuring they are non-associative.
        left = self.parse_additive()
        op_types = (EQ, NEQ, LT, GT, LTE, GTE)
        if self.current().type in op_types:
            op = self.advance().value
            right = self.parse_additive()
            
            # We perform the non-associative check before returning the binary operation node.
            if self.current().type in op_types:
                tok = self.current()
                raise ParseError(
                    f"Comparison operators are non-associative. "
                    f"Use parentheses at line {tok.line}, col {tok.col}"
                )
                
            return BinOp(op, left, right)
        return left

    def parse_additive(self):
        # We parse addition and subtraction, which have higher precedence than comparisons.
        left = self.parse_multiplicative()
        while self.current().type in (PLUS, MINUS):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinOp(op, left, right)
        return left

    def parse_multiplicative(self):
        # We parse multiplication and division, the highest precedence binary operators.
        left = self.parse_unary()
        while self.current().type in (STAR, SLASH):
            op = self.advance().value
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self):
        # We handle unary operators like 'not' and negative numbers.
        if self.current().type == NOT:
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('not', operand)
        if self.current().type == MINUS:
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('-', operand)
        # If there's no unary operator, we proceed to parse function calls or arrays.
        return self.parse_call()

    def parse_call(self):
        # We parse function calls and list indexing. We loop to handle chained calls.
        expr = self.parse_primary()

        while True:
            if self.current().type == LPAREN:
                # We collect arguments for the function call.
                self.advance()
                args = []
                if self.current().type != RPAREN:
                    args.append(self.parse_expr())
                    while self.current().type == COMMA:
                        self.advance()
                        args.append(self.parse_expr())
                self.expect(RPAREN)
                expr = CallExpr(expr, args)

            elif self.current().type == LBRACE:
                # We handle list indexing syntax (e.g., lst[0]).
                self.advance()
                index = self.parse_expr()
                self.expect(RBRACE)
                expr = IndexExpr(expr, index)

            else:
                # If neither a call nor an index follows, we exit the loop.
                break

        return expr

    def parse_primary(self):
        # We parse base values like numbers, booleans, strings, and identifiers.
        tok = self.current()

        if tok.type == INT:
            self.advance()
            return NumberLit(tok.value)

        if tok.type == BOOL:
            self.advance()
            return BoolLit(tok.value)

        if tok.type == STRING:
            self.advance()
            return StringLit(tok.value)

        if tok.type == LBRACE:
            return self.parse_list_literal()

        if tok.type == IDENT:
            self.advance()
            return Identifier(tok.name if hasattr(tok, 'name') else tok.value)

        # We treat 'length' as a special built-in function call.
        if tok.type == LENGTH:
            self.advance()
            self.expect(LPAREN)
            arg = self.parse_expr()
            self.expect(RPAREN)
            return CallExpr(Identifier('__length__'), [arg])

        # We treat 'append' as a special built-in function call.
        if tok.type == APPEND:
            self.advance()
            self.expect(LPAREN)
            lst  = self.parse_expr()
            self.expect(COMMA)
            item = self.parse_expr()
            self.expect(RPAREN)
            return CallExpr(Identifier('__append__'), [lst, item])

        # We handle grouped expressions inside parentheses.
        if tok.type == LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(RPAREN)
            return expr

        if tok.type == IF:
            return self.parse_if()

        if tok.type == FUN:
            return self.parse_fun()

        # If none of the above matches, the syntax is invalid.
        raise ParseError(
            f"Unexpected token {tok.type!r} ({tok.value!r}) "
            f"at line {tok.line}, col {tok.col}"
        )

    def parse_list_literal(self):
        # We parse elements inside square brackets, separated by commas.
        self.expect(LBRACE)
        elements = []
        if self.current().type != RBRACE:
            elements.append(self.parse_expr())
            while self.current().type == COMMA:
                self.advance()
                elements.append(self.parse_expr())
        self.expect(RBRACE)
        return ListLit(elements)

    def parse_if(self):
        # We parse the if-then-else construct and its respective blocks.
        self.expect(IF)
        cond = self.parse_expr()
        self.expect(THEN)
        then_block = self.parse_block([ELSE])
        self.expect(ELSE)
        else_block = self.parse_block([END])
        self.expect(END)
        return IfExpr(cond, then_block, else_block)

    def parse_fun(self):
        # We parse function definitions, collecting their parameters and body block.
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

    def parse(self):
        # We kick off the parsing process, expecting to read until the end of the file.
        block = self.parse_block([EOF])
        self.expect(EOF)
        return block


# ─────────────────────────────────────────────
#  ENVIRONMENT
# ─────────────────────────────────────────────

def make_new_env(parent_env=None):
    # We initialize an environment as a dictionary with an optional parent reference.
    return {'bindings': {}, 'parent': parent_env}

def find_var_in_env(name, env):
    # We recursively search for a variable, moving up the environment chain.
    if name in env['bindings']:
        return env['bindings'][name]
    if env['parent'] is not None:
        return find_var_in_env(name, env['parent'])
    raise RuntimeError(f"Undefined variable: '{name}'")

def add_var_to_env(name, value, env):
    # We define a new variable in the current local scope.
    env['bindings'][name] = value

def update_var_in_env(name, value, env):
    # We update an existing variable. If it isn't local, we check the parent scope.
    if name in env['bindings']:
        env['bindings'][name] = value
        return
    if env['parent'] is not None:
        update_var_in_env(name, value, env['parent'])
        return
    # We raise an error if we try to assign a value to an undeclared variable.
    raise RuntimeError(f"Assignment to undefined variable: '{name}'")


# ─────────────────────────────────────────────
#  CLOSURE VALUE
# ─────────────────────────────────────────────

class Closure:
    # We create a closure object to store function parameters, body, and lexical environment.
    def __init__(self, params, body, env):
        self.params = params
        self.body   = body
        self.env    = env

    def __repr__(self):
        return f'<function({", ".join(self.params)})>'


# ─────────────────────────────────────────────
#  EVALUATOR
# ─────────────────────────────────────────────

class RuntimeError_(Exception):
    # We define a custom runtime error to handle execution issues cleanly.
    pass

# We create a unique object to represent cases where a block yields no value.
VOID_VALUE = object()

class Interpreter:
    def __init__(self, scope='static'):
        # We allow the user to select the scoping mechanism; default is static.
        if scope not in ('static', 'dynamic'):
            raise ValueError(f"Unknown scope mode: {scope!r}. Use 'static' or 'dynamic'.")
        self.scope = scope

        # We create the outermost global environment.
        self.global_env = make_new_env()

        # We manually add our built-in list functions to the global environment.
        add_var_to_env('__length__', '__builtin_length__', self.global_env)
        add_var_to_env('__append__', '__builtin_append__', self.global_env)

    def run(self, source):
        # We wrap the entire execution process to catch our custom errors and exit safely.
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

    def eval_block(self, block, env):
        # We evaluate every statement in a block.
        for stmt in block.stmts:
            self.eval_node(stmt, env)
        # If the block ends with an expression, we evaluate and return it.
        if block.expr is not None:
            return self.eval_node(block.expr, env)
        return VOID_VALUE

    def eval_node(self, node, env):
        
        # We directly return the value for basic literals.
        if type(node) == NumberLit:
            return node.value

        elif type(node) == BoolLit:
            return node.value

        elif type(node) == StringLit:
            return node.value

        elif type(node) == ListLit:
            # We iterate and evaluate each element inside the list literal.
            temp_list = []
            for e in node.elements:
                temp_list.append(self.eval_node(e, env))
            return temp_list

        elif type(node) == Identifier:
            # We look up the identifier's current value in the environment chain.
            return find_var_in_env(node.name, env)

        elif type(node) == LetStmt:
            # We first add a dummy placeholder string into the environment.
            # This helps us support recursive functions easily without issues.
            add_var_to_env(node.name, "DUMMY_PLACEHOLDER", env)
            
            # Now we evaluate the assigned expression safely.
            evaluated_value = self.eval_node(node.value, env)
            
            # Finally, we replace the dummy placeholder with the actually evaluated value.
            env['bindings'][node.name] = evaluated_value
            return VOID_VALUE

        elif type(node) == AssignStmt:
            # We evaluate the right-hand side and update the existing variable.
            evaluated_value = self.eval_node(node.value, env)
            update_var_in_env(node.name, evaluated_value, env)
            return VOID_VALUE

        elif type(node) == PrintStmt:
            # We evaluate the expression and print it in our custom format.
            evaluated_value = self.eval_node(node.expr, env)
            print(self.print_value_format(evaluated_value))
            return VOID_VALUE

        elif type(node) == WhileStmt:
            # We run the while loop as long as its condition evaluates to true.
            while True:
                cond_val = self.eval_node(node.cond, env)
                if type(cond_val) != bool:
                    raise RuntimeError_(f"While condition must be a boolean, got {self.get_type_as_string(cond_val)}")
                if cond_val == False:
                    break
                self.eval_block(node.body, env)
            return VOID_VALUE

        elif type(node) == IfExpr:
            # We evaluate the if condition, ensuring it is strictly a boolean.
            cond_val = self.eval_node(node.cond, env)
            if type(cond_val) != bool:
                raise RuntimeError_(f"Type error: if condition must be boolean, got {self.get_type_as_string(cond_val)}")
            
            # Depending on the result, we evaluate the appropriate block.
            if cond_val == True:
                return self.eval_block(node.then_block, env)
            else:
                return self.eval_block(node.else_block, env)

        elif type(node) == FunExpr:
            # We create a new closure, capturing the current environment.
            return Closure(node.params, node.body, env)

        elif type(node) == CallExpr:
            # We evaluate the function identifier to retrieve its closure or built-in flag.
            func_val = self.eval_node(node.func, env)

            # We handle the built-in length function specifically here.
            if func_val == '__builtin_length__':
                if len(node.args) != 1:
                    raise RuntimeError_("length() takes exactly one argument")
                arg_val = self.eval_node(node.args[0], env)
                if type(arg_val) == str or type(arg_val) == list:
                    return len(arg_val)
                else:
                    raise RuntimeError_(f"Type error: length() expects string or list, got {self.get_type_as_string(arg_val)}")

            # We also handle the built-in append function to manipulate lists.
            if func_val == '__builtin_append__':
                if len(node.args) != 2:
                    raise RuntimeError_("append() takes exactly two arguments")
                lst_val  = self.eval_node(node.args[0], env)
                item_val = self.eval_node(node.args[1], env)
                if type(lst_val) != list:
                    raise RuntimeError_(f"Type error: append() expects a list, got {self.get_type_as_string(lst_val)}")
                lst_val.append(item_val)
                return lst_val

            # We ensure that the value we are trying to call is actually a function.
            if type(func_val) != Closure:
                raise RuntimeError_(f"Type error: tried to call a non-function value: {self.print_value_format(func_val)!r}")

            # We evaluate all arguments before invoking the function, supporting call-by-value.
            evaluated_args = []
            for a in node.args:
                evaluated_args.append(self.eval_node(a, env))

            # We verify the correct number of arguments was provided.
            if len(evaluated_args) != len(func_val.params):
                raise RuntimeError_(f"Arity mismatch: function expects {len(func_val.params)} argument(s), got {len(evaluated_args)}")

            # We create a new environment frame based on our chosen scoping rule.
            if self.scope == 'static':
                new_call_env = make_new_env(parent_env=func_val.env)
            else:
                new_call_env = make_new_env(parent_env=env)

            # We bind the evaluated arguments to the function's parameters.
            for i in range(len(func_val.params)):
                add_var_to_env(func_val.params[i], evaluated_args[i], new_call_env)

            # We run the function body with the newly constructed environment.
            return self.eval_block(func_val.body, new_call_env)

        elif type(node) == IndexExpr:
            # We evaluate the list and the index to fetch the specified element.
            lst_val = self.eval_node(node.lst, env)
            idx_val = self.eval_node(node.index, env)
            
            # We strictly enforce list and integer type checks.
            if type(lst_val) != list:
                raise RuntimeError_(f"Type error: indexing requires a list, got {self.get_type_as_string(lst_val)}")
            if type(idx_val) != int:
                raise RuntimeError_(f"Type error: list index must be an integer, got {self.get_type_as_string(idx_val)}")
            
            # We handle bounds checking to prevent Python's default behavior or crashing.
            if idx_val < 0 or idx_val >= len(lst_val):
                raise RuntimeError_(f"Index out of range: index {idx_val} for list of length {len(lst_val)}")
            return lst_val[idx_val]

        elif type(node) == UnaryOp:
            # We evaluate the operand and apply the respective unary operation.
            operand_val = self.eval_node(node.operand, env)
            if node.op == '-':
                if type(operand_val) != int:
                    raise RuntimeError_(f"Type error: unary '-' requires integer, got {self.get_type_as_string(operand_val)}")
                return -operand_val
            if node.op == 'not':
                if type(operand_val) != bool:
                    raise RuntimeError_(f"Type error: 'not' requires boolean, got {self.get_type_as_string(operand_val)}")
                return not operand_val
            raise RuntimeError_(f"Unknown unary operator: {node.op!r}")

        elif type(node) == BinOp:
            op = node.op

            # We implement short-circuiting logic for the 'or' operator.
            if op == 'or':
                left_val = self.eval_node(node.left, env)
                self.check_boolean_type(left_val, 'or')
                if left_val == True:
                    return True
                else:
                    return self.eval_node(node.right, env)

            # We implement short-circuiting logic for the 'and' operator.
            if op == 'and':
                left_val = self.eval_node(node.left, env)
                self.check_boolean_type(left_val, 'and')
                if left_val == False:
                    return False
                else:
                    return self.eval_node(node.right, env)

            # For all other binary operations, we evaluate both sides beforehand.
            left_val  = self.eval_node(node.left, env)
            right_val = self.eval_node(node.right, env)

            # We handle string concatenation and integer addition under the same operator.
            if op == '+':
                if type(left_val) == int and type(right_val) == int:
                    return left_val + right_val
                if type(left_val) == str and type(right_val) == str:
                    return left_val + right_val
                raise RuntimeError_(f"Type error: '+' requires two integers or two strings, got {self.get_type_as_string(left_val)} and {self.get_type_as_string(right_val)}")
            
            # We handle basic arithmetic, ensuring both operands are integers.
            if op == '-':
                self.check_two_ints(left_val, right_val, '-')
                return left_val - right_val
            
            if op == '*':
                self.check_two_ints(left_val, right_val, '*')
                return left_val * right_val
            
            if op == '/':
                self.check_two_ints(left_val, right_val, '/')
                if right_val == 0:
                    raise RuntimeError_("Runtime error: division by zero")
                # We use simple int() conversion to truncate towards zero, matching C/Java behavior.
                return int(left_val / right_val)

            # We handle equality checks, keeping them straightforward.
            if op in ('==', '!='):
                res = (left_val == right_val)
                if op == '==':
                    return res
                else:
                    return not res

            # We process relational operators, enforcing identical type requirements.
            if op in ('<', '>', '<=', '>='):
                if type(left_val) != type(right_val):
                    raise RuntimeError_(f"Type error: cannot compare {self.get_type_as_string(left_val)} and {self.get_type_as_string(right_val)}")
                if op == '<':  return left_val < right_val
                if op == '>':  return left_val > right_val
                if op == '<=': return left_val <= right_val
                if op == '>=': return left_val >= right_val

            raise RuntimeError_(f"Unknown binary operator: {op!r}")

        # If a node type slips through our checks, we throw an error.
        else:
            raise RuntimeError_(f"Don't know how to evaluate {type(node).__name__}")


    # ── helpers ───────────────────────────────

    def check_boolean_type(self, val, op):
        # We explicitly check for boolean to prevent Python from treating True as 1.
        if type(val) != bool:
            raise RuntimeError_(f"Type error: '{op}' requires boolean, got {self.get_type_as_string(val)}")

    def check_two_ints(self, left, right, op):
        # We confirm both values are strictly integers for safe arithmetic operations.
        if type(left) != int or type(right) != int:
            raise RuntimeError_(f"Type error: '{op}' requires two integers, got {self.get_type_as_string(left)} and {self.get_type_as_string(right)}")

    def get_type_as_string(self, val):
        # We return clear, readable type names for our runtime error messages.
        if type(val) == bool:  return 'boolean'
        if type(val) == int:   return 'integer'
        if type(val) == str:   return 'string'
        if type(val) == list:  return 'list'
        if type(val) == Closure: return 'function'
        return type(val).__name__

    def print_value_format(self, val):
        # We define how output values should be printed to the user.
        if type(val) == bool:   return 'true' if val else 'false'
        if type(val) == int:    return str(val)
        if type(val) == str:    return val
        if type(val) == list:
            elements = []
            for e in val:
                elements.append(self.format_list_elem(e))
            return '[' + ', '.join(elements) + ']'
        if type(val) == Closure: return '<function>'
        return str(val)

    def format_list_elem(self, val):
        # When printing elements inside a list, we make sure strings retain their quotes.
        if type(val) == str:    return f'"{val}"'
        return self.print_value_format(val)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    # We retrieve the arguments provided by the user in the command line.
    args   = sys.argv[1:]
    scope  = 'static'

    # We check if the user specifically requested dynamic or static scoping.
    if '--scope' in args:
        idx = args.index('--scope')
        if idx + 1 >= len(args):
            print("Error: --scope requires an argument (static or dynamic)", file=sys.stderr)
            sys.exit(1)
        scope = args[idx + 1]
        args  = args[:idx] + args[idx + 2:]

    # We display a usage message if no file was supplied.
    if not args:
        print("Usage: python interpreter.py [--scope static|dynamic] <program.txt>", file=sys.stderr)
        sys.exit(1)

    filename = args[0]
    
    # We attempt to read the file contents, handling the missing file case cleanly.
    try:
        with open(filename, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {filename!r}", file=sys.stderr)
        sys.exit(1)

    # We instantiate our interpreter with the chosen scope and run the source code.
    interpreter = Interpreter(scope=scope)
    interpreter.run(source)


if __name__ == '__main__':
    main()