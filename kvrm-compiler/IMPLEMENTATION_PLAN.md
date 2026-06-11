# KVRM Compiler Implementation Plan

**Project**: KVRM-Lang Compiler
**Target**: Compile high-level language to KVRM-CPU assembly
**Date**: December 11, 2025
**Status**: Ready for implementation

---

## Executive Summary

Build a compiler that transforms a simple high-level language (KVRM-Lang) into KVRM-CPU assembly. This completes the computing stack: **Source Code → Compiler → Assembly → CPU Execution**.

---

## 1. Project Structure

```
/Users/bobbyprice/projects/KVRM/kvrm-compiler/
├── src/
│   ├── __init__.py          # Package exports
│   ├── tokens.py            # Token types and Token class
│   ├── ast.py               # AST node definitions
│   ├── lexer.py             # Tokenizer (source → tokens)
│   ├── parser.py            # Parser (tokens → AST)
│   ├── codegen.py           # Code generator (AST → assembly)
│   └── compiler.py          # Pipeline orchestrator
├── examples/
│   ├── fibonacci.kvrm       # Fibonacci example
│   ├── sum.kvrm             # Sum 1 to N
│   ├── factorial.kvrm       # Factorial
│   └── simple.kvrm          # Basic arithmetic
├── tests/
│   ├── __init__.py
│   ├── test_lexer.py        # Lexer unit tests
│   ├── test_parser.py       # Parser unit tests
│   ├── test_codegen.py      # Codegen unit tests
│   └── test_integration.py  # Full compile+run tests
├── main.py                  # CLI and demos
├── requirements.txt         # Dependencies
├── pyproject.toml           # Package config
└── README.md                # Documentation
```

---

## 2. Language Specification (KVRM-Lang)

### 2.1 Grammar (EBNF)

```ebnf
program     ::= { statement }*

statement   ::= assignment
              | if_stmt
              | while_stmt
              | print_stmt
              | return_stmt
              | fn_def
              | expr_stmt
              | NEWLINE

assignment  ::= "let" IDENT "=" expr
              | IDENT "=" expr

expr        ::= comparison

comparison  ::= arith_expr [ ("<" | ">" | "==" | "!=" | "<=" | ">=") arith_expr ]

arith_expr  ::= term { ("+" | "-") term }*

term        ::= factor { ("*" | "/" | "%") factor }*

factor      ::= NUMBER
              | IDENT
              | "(" expr ")"
              | "-" factor
              | fn_call

fn_call     ::= IDENT "(" [ args ] ")"

args        ::= expr { "," expr }*

if_stmt     ::= "if" expr "{" { statement }* "}" [ "else" "{" { statement }* "}" ]

while_stmt  ::= "while" expr "{" { statement }* "}"

print_stmt  ::= "print" expr

return_stmt ::= "return" [ expr ]

fn_def      ::= "fn" IDENT "(" [ params ] ")" "{" { statement }* "}"

params      ::= IDENT { "," IDENT }*

expr_stmt   ::= expr

IDENT       ::= [a-zA-Z_][a-zA-Z0-9_]*
NUMBER      ::= [0-9]+
NEWLINE     ::= "\n"
```

### 2.2 Example Programs

**fibonacci.kvrm**:
```
fn fib(n) {
    let a = 0
    let b = 1
    let i = 0
    while i < n {
        let temp = b
        b = a + b
        a = temp
        i = i + 1
    }
    return b
}

let result = fib(10)
print result
```

**sum.kvrm**:
```
let n = 10
let sum = 0
let i = 1

while i <= n {
    sum = sum + i
    i = i + 1
}

print sum
```

**simple.kvrm**:
```
let x = 10
let y = 20
let z = x + y * 2
print z
```

---

## 3. Component Specifications

### 3.1 tokens.py

```python
"""Token types and Token dataclass for KVRM-Lang lexer."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    IDENT = auto()

    # Keywords
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FN = auto()
    RETURN = auto()
    PRINT = auto()

    # Operators
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    PERCENT = auto()    # %

    # Comparison
    LT = auto()         # <
    GT = auto()         # >
    EQ = auto()         # ==
    NE = auto()         # !=
    LE = auto()         # <=
    GE = auto()         # >=

    # Assignment
    ASSIGN = auto()     # =

    # Delimiters
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACE = auto()     # {
    RBRACE = auto()     # }
    COMMA = auto()      # ,

    # Special
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


# Keyword mapping
KEYWORDS = {
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "print": TokenType.PRINT,
}
```

### 3.2 ast.py

```python
"""AST node definitions for KVRM-Lang parser."""

from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


@dataclass
class Program(ASTNode):
    """Root node containing all statements."""
    statements: List[ASTNode] = field(default_factory=list)


@dataclass
class NumberLiteral(ASTNode):
    """Integer literal."""
    value: int


@dataclass
class Identifier(ASTNode):
    """Variable or function name."""
    name: str


@dataclass
class BinaryOp(ASTNode):
    """Binary operation: left op right."""
    op: str  # '+', '-', '*', '/', '%', '<', '>', '==', '!=', '<=', '>='
    left: ASTNode
    right: ASTNode


@dataclass
class UnaryOp(ASTNode):
    """Unary operation: op operand."""
    op: str  # '-'
    operand: ASTNode


@dataclass
class Assignment(ASTNode):
    """Variable assignment: target = value."""
    target: str
    value: ASTNode
    is_declaration: bool = False  # True for 'let x = ...'


@dataclass
class IfStatement(ASTNode):
    """If statement with optional else."""
    condition: ASTNode
    then_body: List[ASTNode]
    else_body: Optional[List[ASTNode]] = None


@dataclass
class WhileStatement(ASTNode):
    """While loop."""
    condition: ASTNode
    body: List[ASTNode]


@dataclass
class PrintStatement(ASTNode):
    """Print expression."""
    value: ASTNode


@dataclass
class ReturnStatement(ASTNode):
    """Return from function."""
    value: Optional[ASTNode] = None


@dataclass
class FunctionDef(ASTNode):
    """Function definition."""
    name: str
    params: List[str]
    body: List[ASTNode]


@dataclass
class FunctionCall(ASTNode):
    """Function call."""
    name: str
    args: List[ASTNode]
```

### 3.3 lexer.py

```python
"""Lexer for KVRM-Lang: source code → tokens."""

import re
from typing import List, Optional
from .tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    """Lexer error with position info."""
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Lexer error at {line}:{column}: {message}")
        self.line = line
        self.column = column


class Lexer:
    """Tokenize KVRM-Lang source code."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """Convert source to list of tokens."""
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            char = self.source[self.pos]

            # Skip comments
            if char == '#':
                self._skip_comment()
                continue

            # Newline
            if char == '\n':
                self._add_token(TokenType.NEWLINE, '\n')
                self._advance()
                self.line += 1
                self.column = 1
                continue

            # Number
            if char.isdigit():
                self._read_number()
                continue

            # Identifier or keyword
            if char.isalpha() or char == '_':
                self._read_identifier()
                continue

            # Two-character operators
            if self.pos + 1 < len(self.source):
                two_char = self.source[self.pos:self.pos + 2]
                if two_char == '==':
                    self._add_token(TokenType.EQ, '==')
                    self._advance(2)
                    continue
                if two_char == '!=':
                    self._add_token(TokenType.NE, '!=')
                    self._advance(2)
                    continue
                if two_char == '<=':
                    self._add_token(TokenType.LE, '<=')
                    self._advance(2)
                    continue
                if two_char == '>=':
                    self._add_token(TokenType.GE, '>=')
                    self._advance(2)
                    continue

            # Single-character tokens
            single_char_tokens = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '<': TokenType.LT,
                '>': TokenType.GT,
                '=': TokenType.ASSIGN,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                ',': TokenType.COMMA,
            }

            if char in single_char_tokens:
                self._add_token(single_char_tokens[char], char)
                self._advance()
                continue

            raise LexerError(f"Unexpected character: {char!r}", self.line, self.column)

        self._add_token(TokenType.EOF, None)
        return self.tokens

    def _advance(self, n: int = 1):
        """Advance position by n characters."""
        self.pos += n
        self.column += n

    def _add_token(self, type: TokenType, value):
        """Add a token to the list."""
        self.tokens.append(Token(type, value, self.line, self.column))

    def _skip_whitespace(self):
        """Skip spaces and tabs (not newlines)."""
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r':
            self._advance()

    def _skip_comment(self):
        """Skip from # to end of line."""
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self._advance()

    def _read_number(self):
        """Read an integer literal."""
        start = self.pos
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self._advance()
        value = int(self.source[start:self.pos])
        self.tokens.append(Token(TokenType.NUMBER, value, self.line, start - self.pos + self.column))

    def _read_identifier(self):
        """Read an identifier or keyword."""
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            self._advance()
        name = self.source[start:self.pos]

        # Check if keyword
        if name in KEYWORDS:
            token_type = KEYWORDS[name]
        else:
            token_type = TokenType.IDENT

        self.tokens.append(Token(token_type, name, self.line, start - self.pos + self.column))
```

### 3.4 parser.py

```python
"""Parser for KVRM-Lang: tokens → AST."""

from typing import List, Optional
from .tokens import Token, TokenType
from .ast import *


class ParseError(Exception):
    """Parser error with token info."""
    def __init__(self, message: str, token: Token):
        super().__init__(f"Parse error at {token.line}:{token.column}: {message}")
        self.token = token


class Parser:
    """Recursive descent parser for KVRM-Lang."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Program:
        """Parse tokens into AST."""
        statements = []
        while not self._is_at_end():
            self._skip_newlines()
            if self._is_at_end():
                break
            stmt = self._statement()
            if stmt:
                statements.append(stmt)
        return Program(statements)

    # === Helpers ===

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _is_at_end(self) -> bool:
        return self._current().type == TokenType.EOF

    def _check(self, type: TokenType) -> bool:
        return not self._is_at_end() and self._current().type == type

    def _advance(self) -> Token:
        token = self._current()
        if not self._is_at_end():
            self.pos += 1
        return token

    def _match(self, *types: TokenType) -> Optional[Token]:
        for type in types:
            if self._check(type):
                return self._advance()
        return None

    def _expect(self, type: TokenType, message: str) -> Token:
        if self._check(type):
            return self._advance()
        raise ParseError(message, self._current())

    def _skip_newlines(self):
        while self._check(TokenType.NEWLINE):
            self._advance()

    # === Grammar Rules ===

    def _statement(self) -> Optional[ASTNode]:
        """Parse a statement."""
        if self._check(TokenType.LET):
            return self._let_statement()
        if self._check(TokenType.IF):
            return self._if_statement()
        if self._check(TokenType.WHILE):
            return self._while_statement()
        if self._check(TokenType.FN):
            return self._function_def()
        if self._check(TokenType.RETURN):
            return self._return_statement()
        if self._check(TokenType.PRINT):
            return self._print_statement()

        # Expression statement (could be assignment or function call)
        return self._expression_statement()

    def _let_statement(self) -> Assignment:
        """Parse: let IDENT = expr"""
        self._advance()  # consume 'let'
        name_token = self._expect(TokenType.IDENT, "Expected variable name after 'let'")
        self._expect(TokenType.ASSIGN, "Expected '=' after variable name")
        value = self._expression()
        return Assignment(target=name_token.value, value=value, is_declaration=True)

    def _if_statement(self) -> IfStatement:
        """Parse: if expr { stmts } [else { stmts }]"""
        self._advance()  # consume 'if'
        condition = self._expression()
        self._expect(TokenType.LBRACE, "Expected '{' after if condition")
        self._skip_newlines()

        then_body = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._statement()
            if stmt:
                then_body.append(stmt)
            self._skip_newlines()
        self._expect(TokenType.RBRACE, "Expected '}' after if body")

        else_body = None
        self._skip_newlines()
        if self._match(TokenType.ELSE):
            self._expect(TokenType.LBRACE, "Expected '{' after 'else'")
            self._skip_newlines()
            else_body = []
            while not self._check(TokenType.RBRACE) and not self._is_at_end():
                stmt = self._statement()
                if stmt:
                    else_body.append(stmt)
                self._skip_newlines()
            self._expect(TokenType.RBRACE, "Expected '}' after else body")

        return IfStatement(condition=condition, then_body=then_body, else_body=else_body)

    def _while_statement(self) -> WhileStatement:
        """Parse: while expr { stmts }"""
        self._advance()  # consume 'while'
        condition = self._expression()
        self._expect(TokenType.LBRACE, "Expected '{' after while condition")
        self._skip_newlines()

        body = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._statement()
            if stmt:
                body.append(stmt)
            self._skip_newlines()
        self._expect(TokenType.RBRACE, "Expected '}' after while body")

        return WhileStatement(condition=condition, body=body)

    def _function_def(self) -> FunctionDef:
        """Parse: fn IDENT(params) { stmts }"""
        self._advance()  # consume 'fn'
        name_token = self._expect(TokenType.IDENT, "Expected function name")
        self._expect(TokenType.LPAREN, "Expected '(' after function name")

        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENT, "Expected parameter name").value)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENT, "Expected parameter name").value)
        self._expect(TokenType.RPAREN, "Expected ')' after parameters")

        self._expect(TokenType.LBRACE, "Expected '{' before function body")
        self._skip_newlines()

        body = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._statement()
            if stmt:
                body.append(stmt)
            self._skip_newlines()
        self._expect(TokenType.RBRACE, "Expected '}' after function body")

        return FunctionDef(name=name_token.value, params=params, body=body)

    def _return_statement(self) -> ReturnStatement:
        """Parse: return [expr]"""
        self._advance()  # consume 'return'
        value = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.RBRACE):
            value = self._expression()
        return ReturnStatement(value=value)

    def _print_statement(self) -> PrintStatement:
        """Parse: print expr"""
        self._advance()  # consume 'print'
        value = self._expression()
        return PrintStatement(value=value)

    def _expression_statement(self) -> Optional[ASTNode]:
        """Parse expression or assignment."""
        expr = self._expression()

        # Check for assignment: IDENT = expr
        if isinstance(expr, Identifier) and self._match(TokenType.ASSIGN):
            value = self._expression()
            return Assignment(target=expr.name, value=value, is_declaration=False)

        return expr

    def _expression(self) -> ASTNode:
        """Parse expression (comparison level)."""
        return self._comparison()

    def _comparison(self) -> ASTNode:
        """Parse comparison: arith [comp_op arith]"""
        left = self._arith_expr()

        if self._match(TokenType.LT):
            right = self._arith_expr()
            return BinaryOp(op='<', left=left, right=right)
        if self._match(TokenType.GT):
            right = self._arith_expr()
            return BinaryOp(op='>', left=left, right=right)
        if self._match(TokenType.EQ):
            right = self._arith_expr()
            return BinaryOp(op='==', left=left, right=right)
        if self._match(TokenType.NE):
            right = self._arith_expr()
            return BinaryOp(op='!=', left=left, right=right)
        if self._match(TokenType.LE):
            right = self._arith_expr()
            return BinaryOp(op='<=', left=left, right=right)
        if self._match(TokenType.GE):
            right = self._arith_expr()
            return BinaryOp(op='>=', left=left, right=right)

        return left

    def _arith_expr(self) -> ASTNode:
        """Parse addition/subtraction."""
        left = self._term()

        while True:
            if self._match(TokenType.PLUS):
                right = self._term()
                left = BinaryOp(op='+', left=left, right=right)
            elif self._match(TokenType.MINUS):
                right = self._term()
                left = BinaryOp(op='-', left=left, right=right)
            else:
                break

        return left

    def _term(self) -> ASTNode:
        """Parse multiplication/division."""
        left = self._factor()

        while True:
            if self._match(TokenType.STAR):
                right = self._factor()
                left = BinaryOp(op='*', left=left, right=right)
            elif self._match(TokenType.SLASH):
                right = self._factor()
                left = BinaryOp(op='/', left=left, right=right)
            elif self._match(TokenType.PERCENT):
                right = self._factor()
                left = BinaryOp(op='%', left=left, right=right)
            else:
                break

        return left

    def _factor(self) -> ASTNode:
        """Parse factor: number, ident, call, paren, unary."""
        # Unary minus
        if self._match(TokenType.MINUS):
            operand = self._factor()
            return UnaryOp(op='-', operand=operand)

        # Number literal
        if self._check(TokenType.NUMBER):
            token = self._advance()
            return NumberLiteral(value=token.value)

        # Identifier or function call
        if self._check(TokenType.IDENT):
            token = self._advance()

            # Check for function call
            if self._match(TokenType.LPAREN):
                args = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._expression())
                self._expect(TokenType.RPAREN, "Expected ')' after arguments")
                return FunctionCall(name=token.value, args=args)

            return Identifier(name=token.value)

        # Parenthesized expression
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        raise ParseError(f"Unexpected token: {self._current().type.name}", self._current())
```

### 3.5 codegen.py

```python
"""Code generator for KVRM-Lang: AST → KVRM assembly."""

from typing import List, Dict, Optional, Tuple
from .ast import *


class CodeGenError(Exception):
    """Code generation error."""
    pass


class CodeGenerator:
    """Generate KVRM-CPU assembly from AST."""

    # Available registers: R0-R7
    # R7 is reserved for output/print
    AVAILABLE_REGS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6']
    OUTPUT_REG = 'R7'

    def __init__(self):
        self.code: List[str] = []
        self.variables: Dict[str, str] = {}  # var_name -> register
        self.functions: Dict[str, Tuple[str, List[str]]] = {}  # fn_name -> (label, params)
        self.reg_stack: List[str] = list(reversed(self.AVAILABLE_REGS))
        self.label_counter = 0
        self.current_function: Optional[str] = None

    def generate(self, program: Program) -> List[str]:
        """Generate assembly from program AST."""
        self.code = []
        self.variables = {}
        self.functions = {}
        self.reg_stack = list(reversed(self.AVAILABLE_REGS))
        self.label_counter = 0

        # First pass: collect function definitions
        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                label = f"_fn_{stmt.name}"
                self.functions[stmt.name] = (label, stmt.params)

        # Generate main code (skip function definitions for now)
        self.code.append("; KVRM-Lang compiled output")
        self.code.append("; Main program")

        for stmt in program.statements:
            if not isinstance(stmt, FunctionDef):
                self._gen_statement(stmt)

        self.code.append("HALT")

        # Generate function definitions
        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                self._gen_function(stmt)

        return self.code

    def _new_label(self, prefix: str = "L") -> str:
        """Generate a unique label."""
        label = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def _alloc_reg(self) -> str:
        """Allocate a register."""
        if not self.reg_stack:
            raise CodeGenError("Out of registers")
        return self.reg_stack.pop()

    def _free_reg(self, reg: str):
        """Free a register."""
        if reg != self.OUTPUT_REG and reg not in self.reg_stack:
            self.reg_stack.append(reg)

    def _get_var_reg(self, name: str) -> str:
        """Get register for a variable."""
        if name not in self.variables:
            raise CodeGenError(f"Undefined variable: {name}")
        return self.variables[name]

    def _emit(self, instruction: str):
        """Emit an assembly instruction."""
        self.code.append(f"    {instruction}")

    def _emit_label(self, label: str):
        """Emit a label."""
        self.code.append(f"{label}:")

    # === Statement Generation ===

    def _gen_statement(self, stmt: ASTNode):
        """Generate code for a statement."""
        if isinstance(stmt, Assignment):
            self._gen_assignment(stmt)
        elif isinstance(stmt, IfStatement):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileStatement):
            self._gen_while(stmt)
        elif isinstance(stmt, PrintStatement):
            self._gen_print(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._gen_return(stmt)
        elif isinstance(stmt, FunctionCall):
            reg = self._gen_call(stmt)
            self._free_reg(reg)
        elif isinstance(stmt, BinaryOp) or isinstance(stmt, Identifier) or isinstance(stmt, NumberLiteral):
            # Expression statement - evaluate and discard
            reg = self._gen_expr(stmt)
            self._free_reg(reg)

    def _gen_assignment(self, stmt: Assignment):
        """Generate code for assignment."""
        value_reg = self._gen_expr(stmt.value)

        if stmt.is_declaration or stmt.target not in self.variables:
            # New variable - allocate register
            var_reg = self._alloc_reg()
            self.variables[stmt.target] = var_reg
        else:
            var_reg = self.variables[stmt.target]

        if value_reg != var_reg:
            self._emit(f"MOV {var_reg}, {value_reg}")
            self._free_reg(value_reg)

    def _gen_if(self, stmt: IfStatement):
        """Generate code for if statement."""
        else_label = self._new_label("else")
        end_label = self._new_label("endif")

        # Generate condition
        cond_reg = self._gen_expr(stmt.condition)

        # If it's a comparison, flags are already set
        # Otherwise, compare with 0
        if not isinstance(stmt.condition, BinaryOp) or stmt.condition.op not in ['<', '>', '==', '!=', '<=', '>=']:
            temp_reg = self._alloc_reg()
            self._emit(f"MOV {temp_reg}, 0")
            self._emit(f"CMP {cond_reg}, {temp_reg}")
            self._free_reg(temp_reg)

        self._free_reg(cond_reg)

        # Jump to else if zero (condition false)
        if stmt.else_body:
            self._emit(f"JZ {else_label}")
        else:
            self._emit(f"JZ {end_label}")

        # Then body
        for s in stmt.then_body:
            self._gen_statement(s)

        if stmt.else_body:
            self._emit(f"JMP {end_label}")
            self._emit_label(else_label)
            for s in stmt.else_body:
                self._gen_statement(s)

        self._emit_label(end_label)

    def _gen_while(self, stmt: WhileStatement):
        """Generate code for while loop."""
        loop_label = self._new_label("while")
        end_label = self._new_label("endwhile")

        self._emit_label(loop_label)

        # Generate condition
        cond_reg = self._gen_expr(stmt.condition)

        # Compare handling
        if not isinstance(stmt.condition, BinaryOp) or stmt.condition.op not in ['<', '>', '==', '!=', '<=', '>=']:
            temp_reg = self._alloc_reg()
            self._emit(f"MOV {temp_reg}, 0")
            self._emit(f"CMP {cond_reg}, {temp_reg}")
            self._free_reg(temp_reg)

        self._free_reg(cond_reg)

        # Jump to end if zero (condition false)
        self._emit(f"JZ {end_label}")

        # Body
        for s in stmt.body:
            self._gen_statement(s)

        self._emit(f"JMP {loop_label}")
        self._emit_label(end_label)

    def _gen_print(self, stmt: PrintStatement):
        """Generate code for print statement."""
        value_reg = self._gen_expr(stmt.value)
        self._emit(f"MOV {self.OUTPUT_REG}, {value_reg}")
        self._free_reg(value_reg)

    def _gen_return(self, stmt: ReturnStatement):
        """Generate code for return statement."""
        if stmt.value:
            value_reg = self._gen_expr(stmt.value)
            # Store result in R0 (calling convention)
            if value_reg != 'R0':
                self._emit(f"MOV R0, {value_reg}")
                self._free_reg(value_reg)
        # Jump to function end (simplified - no actual return address)
        if self.current_function:
            self._emit(f"JMP _end_{self.current_function}")

    def _gen_function(self, stmt: FunctionDef):
        """Generate code for function definition."""
        self.current_function = stmt.name
        label, params = self.functions[stmt.name]

        self.code.append(f"; Function: {stmt.name}")
        self._emit_label(label)

        # Save current variable state
        old_vars = self.variables.copy()
        old_stack = self.reg_stack.copy()

        # Set up parameters (simplified: assume args in R0, R1, R2...)
        self.variables = {}
        self.reg_stack = list(reversed(self.AVAILABLE_REGS))

        for i, param in enumerate(params):
            if i < len(self.AVAILABLE_REGS):
                reg = self.AVAILABLE_REGS[i]
                self.variables[param] = reg
                self.reg_stack.remove(reg)

        # Generate body
        for s in stmt.body:
            self._gen_statement(s)

        self._emit_label(f"_end_{stmt.name}")
        self._emit("RET")  # Simplified return

        # Restore state
        self.variables = old_vars
        self.reg_stack = old_stack
        self.current_function = None

    # === Expression Generation ===

    def _gen_expr(self, expr: ASTNode) -> str:
        """Generate code for expression, return register with result."""
        if isinstance(expr, NumberLiteral):
            reg = self._alloc_reg()
            self._emit(f"MOV {reg}, {expr.value}")
            return reg

        if isinstance(expr, Identifier):
            return self._get_var_reg(expr.name)

        if isinstance(expr, UnaryOp):
            return self._gen_unary(expr)

        if isinstance(expr, BinaryOp):
            return self._gen_binary(expr)

        if isinstance(expr, FunctionCall):
            return self._gen_call(expr)

        raise CodeGenError(f"Unknown expression type: {type(expr)}")

    def _gen_unary(self, expr: UnaryOp) -> str:
        """Generate code for unary operation."""
        operand_reg = self._gen_expr(expr.operand)
        result_reg = self._alloc_reg()

        if expr.op == '-':
            # Negate: result = 0 - operand
            self._emit(f"MOV {result_reg}, 0")
            self._emit(f"SUB {result_reg}, {result_reg}, {operand_reg}")

        self._free_reg(operand_reg)
        return result_reg

    def _gen_binary(self, expr: BinaryOp) -> str:
        """Generate code for binary operation."""
        left_reg = self._gen_expr(expr.left)
        right_reg = self._gen_expr(expr.right)
        result_reg = self._alloc_reg()

        op = expr.op

        if op == '+':
            self._emit(f"ADD {result_reg}, {left_reg}, {right_reg}")
        elif op == '-':
            self._emit(f"SUB {result_reg}, {left_reg}, {right_reg}")
        elif op == '*':
            self._emit(f"MUL {result_reg}, {left_reg}, {right_reg}")
        elif op in ['<', '>', '==', '!=', '<=', '>=']:
            # Comparison - use CMP and set result based on flags
            self._emit(f"CMP {left_reg}, {right_reg}")
            # For simplicity, store 1 in result if condition true, 0 otherwise
            # This requires conditional jumps
            true_label = self._new_label("cmp_true")
            end_label = self._new_label("cmp_end")

            if op == '<':
                self._emit(f"JS {true_label}")  # Jump if sign (less than)
            elif op == '>':
                # Greater: not (less or equal)
                self._emit(f"JZ {end_label}")  # If equal, result is 0
                self._emit(f"JNS {true_label}")  # If not sign (not less), it's greater
            elif op == '==':
                self._emit(f"JZ {true_label}")  # Jump if zero (equal)
            elif op == '!=':
                self._emit(f"JNZ {true_label}")  # Jump if not zero (not equal)
            elif op == '<=':
                self._emit(f"JZ {true_label}")  # Equal
                self._emit(f"JS {true_label}")  # Less than
            elif op == '>=':
                self._emit(f"JZ {true_label}")  # Equal
                self._emit(f"JNS {true_label}")  # Greater than

            self._emit(f"MOV {result_reg}, 0")
            self._emit(f"JMP {end_label}")
            self._emit_label(true_label)
            self._emit(f"MOV {result_reg}, 1")
            self._emit_label(end_label)
        else:
            raise CodeGenError(f"Unknown operator: {op}")

        self._free_reg(left_reg)
        self._free_reg(right_reg)
        return result_reg

    def _gen_call(self, expr: FunctionCall) -> str:
        """Generate code for function call."""
        if expr.name not in self.functions:
            raise CodeGenError(f"Undefined function: {expr.name}")

        label, params = self.functions[expr.name]

        # Generate arguments (simplified: store in R0, R1, R2...)
        arg_regs = []
        for i, arg in enumerate(expr.args):
            reg = self._gen_expr(arg)
            arg_regs.append(reg)

        # Move args to parameter registers
        for i, reg in enumerate(arg_regs):
            if i < len(self.AVAILABLE_REGS):
                target = self.AVAILABLE_REGS[i]
                if reg != target:
                    self._emit(f"MOV {target}, {reg}")
                    self._free_reg(reg)

        # Call function (simplified - just jump)
        self._emit(f"JMP {label}")
        # Note: This is a simplification. Real implementation needs call/ret with stack.

        # Result is in R0
        return 'R0'
```

### 3.6 compiler.py

```python
"""KVRM-Lang compiler pipeline."""

from typing import List, Optional
from .tokens import Token
from .lexer import Lexer
from .parser import Parser
from .codegen import CodeGenerator
from .ast import Program


class CompileError(Exception):
    """Compilation error."""
    pass


class Compiler:
    """KVRM-Lang to KVRM-CPU assembly compiler."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.tokens: Optional[List[Token]] = None
        self.ast: Optional[Program] = None
        self.assembly: Optional[List[str]] = None

    def compile(self, source: str) -> str:
        """Compile source code to assembly."""
        # Stage 1: Lexing
        if self.debug:
            print("=== Lexing ===")
        lexer = Lexer(source)
        self.tokens = lexer.tokenize()
        if self.debug:
            for tok in self.tokens:
                print(f"  {tok}")

        # Stage 2: Parsing
        if self.debug:
            print("\n=== Parsing ===")
        parser = Parser(self.tokens)
        self.ast = parser.parse()
        if self.debug:
            self._print_ast(self.ast)

        # Stage 3: Code Generation
        if self.debug:
            print("\n=== Code Generation ===")
        codegen = CodeGenerator()
        self.assembly = codegen.generate(self.ast)

        # Join assembly lines
        result = '\n'.join(self.assembly)
        if self.debug:
            print(result)

        return result

    def compile_file(self, filepath: str) -> str:
        """Compile a source file."""
        with open(filepath, 'r') as f:
            source = f.read()
        return self.compile(source)

    def _print_ast(self, node, indent=0):
        """Pretty print AST for debugging."""
        prefix = "  " * indent
        if hasattr(node, '__dataclass_fields__'):
            print(f"{prefix}{node.__class__.__name__}:")
            for field_name in node.__dataclass_fields__:
                value = getattr(node, field_name)
                if isinstance(value, list):
                    print(f"{prefix}  {field_name}:")
                    for item in value:
                        self._print_ast(item, indent + 2)
                elif hasattr(value, '__dataclass_fields__'):
                    print(f"{prefix}  {field_name}:")
                    self._print_ast(value, indent + 2)
                else:
                    print(f"{prefix}  {field_name}: {value}")
        else:
            print(f"{prefix}{node}")
```

---

## 4. Example Programs

### examples/fibonacci.kvrm
```
# Fibonacci sequence
# Compute F(10) = 55

let n = 10
let a = 0
let b = 1
let i = 0

while i < n {
    let temp = b
    b = a + b
    a = temp
    i = i + 1
}

print b
```

### examples/sum.kvrm
```
# Sum 1 to N
# Sum(10) = 55

let n = 10
let sum = 0
let i = 1

while i <= n {
    sum = sum + i
    i = i + 1
}

print sum
```

### examples/simple.kvrm
```
# Simple arithmetic
let x = 10
let y = 20
let z = x + y * 2
print z
```

---

## 5. Test Cases

### test_lexer.py
```python
def test_simple_assignment():
    lexer = Lexer("let x = 5")
    tokens = lexer.tokenize()
    assert tokens[0].type == TokenType.LET
    assert tokens[1].type == TokenType.IDENT
    assert tokens[1].value == "x"
    assert tokens[2].type == TokenType.ASSIGN
    assert tokens[3].type == TokenType.NUMBER
    assert tokens[3].value == 5

def test_arithmetic():
    lexer = Lexer("x + y * 2 - 3")
    tokens = lexer.tokenize()
    types = [t.type for t in tokens[:-1]]  # exclude EOF
    assert TokenType.PLUS in types
    assert TokenType.STAR in types
    assert TokenType.MINUS in types

def test_comparison():
    lexer = Lexer("x < y == z != w")
    tokens = lexer.tokenize()
    types = [t.type for t in tokens[:-1]]
    assert TokenType.LT in types
    assert TokenType.EQ in types
    assert TokenType.NE in types
```

### test_parser.py
```python
def test_assignment():
    tokens = Lexer("let x = 5").tokenize()
    ast = Parser(tokens).parse()
    assert len(ast.statements) == 1
    assert isinstance(ast.statements[0], Assignment)
    assert ast.statements[0].target == "x"
    assert ast.statements[0].is_declaration == True

def test_while_loop():
    source = "while x < 10 { x = x + 1 }"
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    assert isinstance(ast.statements[0], WhileStatement)

def test_if_else():
    source = "if x > 0 { y = 1 } else { y = 0 }"
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    stmt = ast.statements[0]
    assert isinstance(stmt, IfStatement)
    assert stmt.else_body is not None
```

### test_integration.py
```python
def test_compile_and_run_simple():
    """Compile simple arithmetic and run on CPU."""
    source = """
let x = 10
let y = 20
let z = x + y
print z
"""
    compiler = Compiler()
    assembly = compiler.compile(source)

    # Run on KVRM-CPU
    from kvrm_cpu import KVRMCPU
    cpu = KVRMCPU(mock_mode=True)
    cpu.load_program(assembly)
    cpu.run()

    # R7 should be 30
    assert cpu.get_register('R7') == 30

def test_fibonacci():
    """Compile Fibonacci and verify result."""
    source = """
let n = 10
let a = 0
let b = 1
let i = 0
while i < n {
    let temp = b
    b = a + b
    a = temp
    i = i + 1
}
print b
"""
    compiler = Compiler()
    assembly = compiler.compile(source)

    from kvrm_cpu import KVRMCPU
    cpu = KVRMCPU(mock_mode=True)
    cpu.load_program(assembly)
    cpu.run(max_cycles=500)

    # F(10) = 55
    assert cpu.get_register('R7') == 55
```

---

## 6. Integration with KVRM-CPU

The compiler output is directly compatible with KVRM-CPU:

```python
from kvrm_compiler import Compiler
from kvrm_cpu import KVRMCPU

# Compile
compiler = Compiler()
assembly = compiler.compile_file("examples/fibonacci.kvrm")

# Execute
cpu = KVRMCPU(mock_mode=True)
cpu.load_program(assembly)
cpu.run()

# Get result
result = cpu.get_register('R7')  # Output register
print(f"Result: {result}")  # Should print 55
```

---

## 7. Implementation Order

1. **tokens.py** - Token types and dataclass (10 min)
2. **ast.py** - AST node definitions (15 min)
3. **lexer.py** - Tokenizer (30 min)
4. **parser.py** - Recursive descent parser (45 min)
5. **codegen.py** - Assembly generator (45 min)
6. **compiler.py** - Pipeline orchestrator (15 min)
7. **Tests** - Unit and integration tests (30 min)
8. **Examples** - Sample programs (10 min)

**Total estimated time: 3-4 hours**

---

## 8. Commands for Codex Agents

After restarting Claude Code with Codex MCP, use these prompts:

### Agent 1: Lexer + Tokens
```
Implement tokens.py and lexer.py for KVRM-Lang compiler at /Users/bobbyprice/projects/KVRM/kvrm-compiler/src/
Follow the specification in IMPLEMENTATION_PLAN.md sections 3.1 and 3.3.
Include all token types and the full lexer with error handling.
```

### Agent 2: AST + Parser
```
Implement ast.py and parser.py for KVRM-Lang compiler at /Users/bobbyprice/projects/KVRM/kvrm-compiler/src/
Follow the specification in IMPLEMENTATION_PLAN.md sections 3.2 and 3.4.
Include all AST nodes and recursive descent parser.
```

### Agent 3: CodeGen + Compiler
```
Implement codegen.py and compiler.py for KVRM-Lang compiler at /Users/bobbyprice/projects/KVRM/kvrm-compiler/src/
Follow the specification in IMPLEMENTATION_PLAN.md sections 3.5 and 3.6.
Generate KVRM-CPU compatible assembly.
```

### Agent 4: Tests + Examples
```
Create tests and example programs for KVRM-Lang compiler at /Users/bobbyprice/projects/KVRM/kvrm-compiler/
Follow the specification in IMPLEMENTATION_PLAN.md sections 4 and 5.
Include integration tests with KVRM-CPU.
```

---

## 9. Success Criteria

- [ ] All tokens correctly identified
- [ ] Parser handles all grammar rules
- [ ] Generated assembly is valid KVRM-CPU code
- [ ] Fibonacci compiles and runs correctly (result = 55)
- [ ] Sum 1-10 compiles and runs correctly (result = 55)
- [ ] All tests pass

---

*Document created: December 11, 2025*
*Ready for implementation with Codex agents*
