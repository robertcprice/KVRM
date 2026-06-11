import pytest
import sys

sys.path.insert(0, '/Users/bobbyprice/projects/KVRM/kvrm-compiler')
from src.compiler import Compiler


def test_simple_compile():
    source = "let x = 10\nprint x"
    compiler = Compiler()
    asm = compiler.compile(source)
    assert "MOV" in asm
    assert "HALT" in asm
