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
