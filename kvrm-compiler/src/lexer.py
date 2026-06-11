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
