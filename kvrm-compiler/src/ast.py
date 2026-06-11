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
