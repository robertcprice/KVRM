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
