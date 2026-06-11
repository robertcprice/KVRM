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
