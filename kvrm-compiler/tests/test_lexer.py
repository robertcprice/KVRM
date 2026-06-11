import pytest
import sys

sys.path.insert(0, '/Users/bobbyprice/projects/KVRM/kvrm-compiler')
from src.lexer import Lexer
from src.tokens import TokenType


def test_simple_assignment():
    lexer = Lexer("let x = 5")
    tokens = lexer.tokenize()
    assert tokens[0].type == TokenType.LET
    assert tokens[1].type == TokenType.IDENT
    assert tokens[1].value == "x"


def test_arithmetic():
    lexer = Lexer("x + y * 2")
    tokens = lexer.tokenize()
    types = [t.type for t in tokens[:-1]]
    assert TokenType.PLUS in types
    assert TokenType.STAR in types


def test_comparison():
    lexer = Lexer("x < y == z")
    tokens = lexer.tokenize()
    types = [t.type for t in tokens[:-1]]
    assert TokenType.LT in types
    assert TokenType.EQ in types
