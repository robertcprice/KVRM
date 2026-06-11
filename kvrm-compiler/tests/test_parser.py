import pytest
import sys

sys.path.insert(0, '/Users/bobbyprice/projects/KVRM/kvrm-compiler')
from src.lexer import Lexer
from src.parser import Parser
from src.ast import Assignment, WhileStatement, IfStatement


def test_assignment():
    tokens = Lexer("let x = 5").tokenize()
    ast = Parser(tokens).parse()
    assert len(ast.statements) == 1
    assert isinstance(ast.statements[0], Assignment)


def test_while_loop():
    tokens = Lexer("while x < 10 { x = x + 1 }").tokenize()
    ast = Parser(tokens).parse()
    assert isinstance(ast.statements[0], WhileStatement)
