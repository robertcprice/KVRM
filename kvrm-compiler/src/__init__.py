"""Compiler package exports."""

from . import ast as _ast
from .ast import *
from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .codegen import CodeGenerator, CodeGenError
from .compiler import Compiler, CompileError
from .tokens import TokenType, Token, KEYWORDS

__version__ = "0.1.0"

_ast_exports = [
    name
    for name, obj in vars(_ast).items()
    if not name.startswith("_") and getattr(obj, "__module__", None) == _ast.__name__
]

__all__ = [
    "Lexer",
    "LexerError",
    "Parser",
    "ParseError",
    "CodeGenerator",
    "CodeGenError",
    "Compiler",
    "CompileError",
    "TokenType",
    "Token",
    "KEYWORDS",
    *_ast_exports,
]
