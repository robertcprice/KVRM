# KVRM Execution Engine: Source-to-Execution Pipeline

**Document Version**: 1.0.0
**Last Updated**: 2024-12-14
**Author**: Bobby Price (blackWeb Research)

---

## Executive Summary

This document describes the KVRM Execution Engine, a complete source-to-execution pipeline that connects the KVRM LLM Compiler to the KVRM-CPU. This integration represents a **major milestone**: the first fully operational system where Large Language Models handle every stage of code compilation AND execution.

**Key Achievement**: On 2024-12-14, we successfully executed a KVRM-Lang program through five distinct LLM stages, from source code to computed output, with zero traditional hardcoded logic in the critical path.

---

## 1. Architecture Overview

### 1.1 Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KVRM EXECUTION ENGINE                                 │
│                    Source-to-Execution via LLMs                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SOURCE CODE (KVRM-Lang)                                                    │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              STAGE 1: LEXER LLM (lexer_lora)                    │       │
│   │   Input:  Raw source text                                        │       │
│   │   Output: Token stream (JSON array)                              │       │
│   │   Model:  Qwen3-1.7B + LoRA (r=16, α=32)                        │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              STAGE 2: PARSER LLM (parser_lora)                  │       │
│   │   Input:  Token stream                                           │       │
│   │   Output: Abstract Syntax Tree (JSON)                            │       │
│   │   Model:  Qwen3-1.7B + LoRA (r=16, α=32)                        │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              STAGE 3: CODEGEN LLM (codegen_lora)                │       │
│   │   Input:  Abstract Syntax Tree                                   │       │
│   │   Output: Assembly instructions (list)                           │       │
│   │   Model:  Qwen3-1.7B + LoRA (r=32, α=32)                        │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              ASSEMBLY FORMATTER                                  │       │
│   │   Input:  Assembly list from CodeGen                             │       │
│   │   Output: CPU-compatible assembly string                         │       │
│   │   Type:   Pure function (format conversion only)                 │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              STAGE 4: CPU DECODE LLM (decode_llm)               │       │
│   │   Input:  Assembly instruction text                              │       │
│   │   Output: Instruction key for registry lookup                    │       │
│   │   Model:  Qwen2.5-Coder-1.5B + LoRA (r=16, α=32)                │       │
│   │   Accuracy: 100% on full ISA                                     │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              EXECUTION (Registry + State Machine)               │       │
│   │   Input:  Instruction key                                        │       │
│   │   Output: State changes (registers, flags, memory)               │       │
│   │   Type:   Pre-verified primitives from immutable registry        │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        │                                                                     │
│        ▼                                                                     │
│   EXECUTION RESULT                                                           │
│   - Output value (R7 register by convention)                                 │
│   - Final register state                                                     │
│   - CPU flags (ZF, SF)                                                       │
│   - Cycle count                                                              │
│   - Execution trace                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 LLM Stages Summary

| Stage | Model | LoRA | Purpose | Input → Output |
|-------|-------|------|---------|----------------|
| **Lexer** | Qwen3-1.7B | r=16 | Tokenization | Source → Tokens |
| **Parser** | Qwen3-1.7B | r=16 | Syntax Analysis | Tokens → AST |
| **CodeGen** | Qwen3-1.7B | r=32 | Code Generation | AST → Assembly |
| **Decode** | Qwen2.5-1.5B | r=16 | Instruction Decode | Asm → Key |

**Total LLM Invocations per Program**: 3 (compile) + N (execute, where N = instruction count)

---

## 2. Implementation Details

### 2.1 KVRMExecutionEngine Class

The `KVRMExecutionEngine` class orchestrates the complete pipeline:

```python
class KVRMExecutionEngine:
    """Unified compile-and-execute engine for KVRM programs."""

    def __init__(
        self,
        model_path: str = "Qwen/Qwen3-1.7B",
        models_dir: Optional[str] = None,
        cpu_model_path: Optional[str] = None,
        mock_mode: bool = False,
        generation_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """Initialize all LLM stages and CPU."""

    def compile(self, source: str) -> CompilationResult:
        """Compile source code to assembly through Lexer → Parser → CodeGen."""

    def execute_assembly(self, assembly: str) -> ExecutionResult:
        """Execute pre-compiled assembly on the KVRM-CPU."""

    def run(self, source: str) -> ExecutionResult:
        """Full compile-and-execute in one call."""

    def run_and_print(self, source: str) -> Any:
        """Compile, execute, and print detailed trace."""
```

### 2.2 Assembly Format Bridge

The CodeGen LLM outputs assembly as a Python list. The CPU expects a newline-separated string. The `format_assembly()` function bridges this gap:

```python
def format_assembly(assembly_list: List[str], variables: Optional[Dict] = None) -> str:
    """Convert assembly list to CPU-compatible string format.

    Features:
    - Adds header comment with variable mapping
    - Proper indentation for instructions
    - Labels kept at column 0 (no indent)
    - HALT instruction formatting

    Example Output:
        ; KVRM-Lang compiled output
        ; Variables: {'x': 'R1', 'y': 'R2'}

            MOV R0, 42
            MOV R1, R0
        loop_start:
            CMP R1, R2
            JZ loop_end
            ...
        HALT
    """
```

### 2.3 Data Structures

**CompilationResult**:
```python
@dataclass
class CompilationResult:
    success: bool
    assembly: str = ""           # Final assembly string
    tokens: List[Dict] = []      # Lexer output
    ast: Dict = {}               # Parser output
    variables: Dict[str, int] = {}  # Variable-to-register mapping
    error: Optional[str] = None
    stage_failed: Optional[str] = None  # 'lexer', 'parser', or 'codegen'
```

**ExecutionResult**:
```python
@dataclass
class ExecutionResult:
    success: bool
    output: Any = None           # Value from R7 (print convention)
    registers: Dict[str, int] = {}  # Final register state
    flags: Dict[str, bool] = {}  # CPU flags (ZF, SF)
    cycles: int = 0              # Total execution cycles
    compilation: Optional[CompilationResult] = None
    error: Optional[str] = None
    trace: List[Dict] = []       # Instruction-by-instruction trace
```

---

## 3. Test Results

### 3.1 Simple Program Execution

**Source Code**:
```
let x = 42
print x
```

**Lexer Output** (8 tokens):
```json
[
  {"type": "LET", "value": "let"},
  {"type": "IDENT", "value": "x"},
  {"type": "ASSIGN", "value": "="},
  {"type": "NUMBER", "value": 42},
  {"type": "NEWLINE", "value": "\\n"},
  {"type": "PRINT", "value": "print"},
  {"type": "IDENT", "value": "x"},
  {"type": "EOF", "value": ""}
]
```

**Parser Output** (AST):
```json
{
  "type": "Program",
  "statements": [
    {
      "type": "Assignment",
      "target": "x",
      "value": {"type": "NumberLiteral", "value": 42}
    },
    {
      "type": "PrintStatement",
      "expression": {"type": "Identifier", "name": "x"}
    }
  ]
}
```

**CodeGen Output** (Assembly):
```asm
; KVRM-Lang compiled output
; Variables: {'x': 'R1'}

    MOV R0, 42
    MOV R1, R0
    MOV R7, R1
HALT
```

**Execution Result**:
```
Output (R7): 42
Cycles: 4
Registers: {'R0': 42, 'R1': 42, 'R2': 0, ..., 'R7': 42}
```

### 3.2 Conditional Program Execution

**Source Code**:
```
let a = 10
let b = 20
if a < b {
    print a
} else {
    print b
}
```

**Execution Trace**:
```
PC=0:  MOV R0, 10     → R0=10
PC=1:  MOV R1, R0     → R1=10 (a=10)
PC=2:  MOV R0, 20     → R0=20
PC=3:  MOV R2, R0     → R2=20 (b=20)
PC=4:  CMP R1, R2     → FLAGS.SF=1 (10 < 20)
PC=5:  JS cmp_true2   → Jump taken (SF=1)
PC=7:  MOV R0, 1      → R0=1 (condition true)
PC=9:  JZ else0       → Not taken (R0≠0)
PC=10: MOV R7, R1     → R7=10 (print a)
PC=11: JMP endif1     → Jump to end
PC=13: HALT           → Execution complete
```

**Execution Result**:
```
Output (R7): 10     ← Correct! (10 < 20, so print a)
Cycles: 11
Registers: {'R0': 1, 'R1': 10, 'R2': 20, ..., 'R7': 10}
Flags: {'ZF': False, 'SF': False}
```

### 3.3 Performance Metrics

| Metric | Simple Program | Conditional Program |
|--------|----------------|---------------------|
| **Source Lines** | 2 | 7 |
| **Tokens** | 8 | 29 |
| **AST Statements** | 2 | 3 |
| **Assembly Instructions** | 4 | 14 |
| **CPU Cycles** | 4 | 11 |
| **Compile Time (MPS)** | ~15s | ~20s |
| **Execute Time** | <0.1s | <0.1s |

---

## 4. Instruction Set Architecture

### 4.1 Supported Instructions

| Instruction | Format | Description |
|-------------|--------|-------------|
| `MOV Rd, imm` | Data Movement | Load immediate value into register |
| `MOV Rd, Rs` | Data Movement | Copy register to register |
| `ADD Rd, Rs` | Arithmetic | Rd = Rd + Rs |
| `SUB Rd, Rs` | Arithmetic | Rd = Rd - Rs |
| `MUL Rd, Rs` | Arithmetic | Rd = Rd * Rs |
| `CMP Ra, Rb` | Comparison | Set flags based on Ra - Rb |
| `JMP label` | Control Flow | Unconditional jump |
| `JZ label` | Control Flow | Jump if Zero Flag set |
| `JNZ label` | Control Flow | Jump if Zero Flag clear |
| `JS label` | Control Flow | Jump if Sign Flag set |
| `JNS label` | Control Flow | Jump if Sign Flag clear |
| `INC Rd` | Arithmetic | Rd = Rd + 1 |
| `DEC Rd` | Arithmetic | Rd = Rd - 1 |
| `HALT` | Control | Terminate execution |
| `NOP` | No Operation | Do nothing |

### 4.2 Register Conventions

| Register | Purpose |
|----------|---------|
| R0 | Accumulator / Temporary |
| R1-R6 | General Purpose / Variables |
| R7 | **Output Register** (print convention) |

### 4.3 Flags

| Flag | Set When |
|------|----------|
| ZF (Zero) | Result of last operation is zero |
| SF (Sign) | Result of last operation is negative |

---

## 5. Code Listing

### 5.1 execution_engine.py (Key Sections)

```python
"""KVRM Execution Engine: Source-to-Execution Pipeline.

Pipeline:
    Source Code
        ↓
    Lexer LLM → Tokens
        ↓
    Parser LLM → AST
        ↓
    CodeGen LLM → Assembly
        ↓
    KVRM-CPU (Decode LLM) → Execution
        ↓
    Result
"""

class KVRMExecutionEngine:
    def compile(self, source: str) -> CompilationResult:
        """Compile source code to assembly."""
        try:
            # Stage 1: Lexer
            lexer_result = self.lexer.process({
                "task": "tokenize",
                "source": source
            })
            tokens = lexer_result.get("tokens", [])

            if not tokens:
                return CompilationResult(
                    success=False,
                    error="Lexer produced no tokens",
                    stage_failed="lexer",
                )

            # Stage 2: Parser
            self.lexer.unload()  # Free memory
            parser_result = self.parser.process({
                "task": "parse",
                "tokens": tokens
            })
            ast = parser_result.get("ast", {})

            if not ast:
                return CompilationResult(
                    success=False,
                    tokens=tokens,
                    error="Parser produced no AST",
                    stage_failed="parser",
                )

            # Stage 3: CodeGen
            self.parser.unload()  # Free memory
            codegen_result = self.codegen.process({
                "task": "codegen",
                "ast": ast
            })

            assembly_raw = codegen_result.get("assembly", [])
            variables = codegen_result.get("variables", {})

            if not assembly_raw:
                return CompilationResult(
                    success=False,
                    tokens=tokens,
                    ast=ast,
                    error="CodeGen produced no assembly",
                    stage_failed="codegen",
                )

            # Convert assembly to string format
            if isinstance(assembly_raw, list):
                assembly = format_assembly(assembly_raw, variables)
            else:
                assembly = assembly_raw

            self.codegen.unload()  # Free memory

            return CompilationResult(
                success=True,
                assembly=assembly,
                tokens=tokens,
                ast=ast,
                variables=variables,
            )

        except Exception as e:
            return CompilationResult(success=False, error=str(e))

    def execute_assembly(self, assembly: str) -> ExecutionResult:
        """Execute pre-compiled assembly on the CPU."""
        try:
            self.cpu.load_program(assembly)
            self.cpu.run()

            # Get output from R7 (print convention)
            registers = self.cpu.dump_registers()
            output = registers.get("R7", 0)

            return ExecutionResult(
                success=True,
                output=output,
                registers=registers,
                flags=self.cpu.get_flags(),
                cycles=self.cpu.get_cycle_count(),
                trace=[{
                    "cycle": e.cycle,
                    "instruction": e.instruction,
                    "key": e.decode_result.key,
                } for e in self.cpu.trace],
            )

        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

    def run(self, source: str) -> ExecutionResult:
        """Compile and execute source code."""
        compilation = self.compile(source)

        if not compilation.success:
            return ExecutionResult(
                success=False,
                compilation=compilation,
                error=f"Compilation failed at {compilation.stage_failed}: {compilation.error}",
            )

        execution = self.execute_assembly(compilation.assembly)
        execution.compilation = compilation

        return execution
```

---

## 6. Integration Notes

### 6.1 Memory Management

Each LLM stage is unloaded after use to manage GPU memory:

```python
# Stage 1: Lexer
lexer_result = self.lexer.process(...)
self.lexer.unload()  # Free ~3GB VRAM

# Stage 2: Parser
parser_result = self.parser.process(...)
self.parser.unload()  # Free ~3GB VRAM

# Stage 3: CodeGen
codegen_result = self.codegen.process(...)
self.codegen.unload()  # Free ~3GB VRAM

# Stage 4: CPU (kept loaded for execution)
self.cpu.run()
```

### 6.2 Error Handling

The pipeline provides detailed error information at each stage:

```python
if not result.success:
    print(f"Stage: {result.compilation.stage_failed}")
    print(f"Error: {result.error}")
    print(f"Tokens collected: {len(result.compilation.tokens)}")
    print(f"AST generated: {bool(result.compilation.ast)}")
```

### 6.3 Mock Mode

For development and testing without GPU:

```python
# Mock mode uses hardcoded responses
engine = KVRMExecutionEngine(mock_mode=True)
result = engine.run("let x = 42\nprint x")
# Works instantly without model loading
```

---

## 7. Future Enhancements

### 7.1 Planned Features

1. **Validator Integration**: Add semantic validation stage before CodeGen
2. **Caching**: Cache compiled assembly for repeated executions
3. **Streaming**: Stream execution trace in real-time
4. **Debugging**: Step-through execution with breakpoints

### 7.2 Performance Optimization

1. **Model Quantization**: INT8/INT4 for faster inference
2. **Batch Compilation**: Compile multiple programs together
3. **Persistent Models**: Keep models loaded across compilations
4. **Speculative Decoding**: Faster token generation

---

## 8. Usage Examples

### 8.1 Basic Usage

```python
from kvrm_llm_compiler import KVRMExecutionEngine

# Initialize engine
engine = KVRMExecutionEngine()

# Compile and execute
result = engine.run("let x = 42\nprint x")

if result.success:
    print(f"Output: {result.output}")  # 42
else:
    print(f"Error: {result.error}")
```

### 8.2 Step-by-Step Compilation

```python
# Compile only
compilation = engine.compile("let x = 42\nprint x")
print(f"Tokens: {len(compilation.tokens)}")
print(f"AST: {compilation.ast['type']}")
print(f"Assembly:\n{compilation.assembly}")

# Execute separately
result = engine.execute_assembly(compilation.assembly)
print(f"Output: {result.output}")
```

### 8.3 Detailed Trace

```python
result = engine.run_and_print("let x = 42\nprint x")
# Prints complete execution trace with:
# - Source code
# - Assembly output
# - Cycle-by-cycle execution
# - Final register state
# - Output value
```

---

## References

- `kvrm-llm-compiler/src/kvrm_llm_compiler/execution_engine.py` - Implementation
- `kvrm-cpu/src/kvrm_cpu/cpu.py` - CPU implementation
- `COMPILER_TO_CPU_INTEGRATION.md` - Integration planning document
- `RESEARCH_ISSUES.md` - Technical issues resolved

---

*Document part of KVRM Research - blackWeb Research*
