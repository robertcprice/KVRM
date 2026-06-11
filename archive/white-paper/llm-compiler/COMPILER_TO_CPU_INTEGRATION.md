# KVRM Compiler-to-CPU Integration Plan

**Document Version**: 1.0.0
**Last Updated**: 2024-12-14
**Author**: Bobby Price (blackWeb Research)

---

## Executive Summary

This document outlines the integration plan for connecting the KVRM LLM Compiler to the KVRM-CPU, creating a complete **source-to-execution pipeline** powered by fine-tuned micro-LLMs at every stage.

---

## Architecture Overview

### Current State

```
┌─────────────────────────────────────────────────────────────────┐
│              KVRM-LLM-Compiler (OPERATIONAL)                    │
│                                                                  │
│   Source → [Lexer LLM] → [Parser LLM] → [CodeGen LLM] → Assembly │
│              ↓              ↓               ↓                    │
│           Tokens          AST          Assembly                  │
│                                        (ready)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                       INTEGRATION GAP
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              KVRM-CPU (OPERATIONAL)                              │
│                                                                  │
│   Assembly → [Decode LLM] → Instruction Key → Execute → State    │
│                  ↓                                               │
│            decode_llm                                            │
│       (100% accuracy on ISA)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Target State

```
┌─────────────────────────────────────────────────────────────────┐
│                    KVRM EXECUTION ENGINE                         │
│                                                                  │
│   Source Code                                                    │
│        ↓                                                         │
│   ┌─────────────────────────────────────────────┐               │
│   │         KVRM-LLM-Compiler Pipeline          │               │
│   │   [Lexer] → [Parser] → [CodeGen] → [Valid]  │               │
│   └─────────────────────────────────────────────┘               │
│        ↓                                                         │
│   Assembly Text                                                  │
│        ↓                                                         │
│   ┌─────────────────────────────────────────────┐               │
│   │              Assembly Loader                 │               │
│   │   Parse assembly → Load to CPU memory        │               │
│   └─────────────────────────────────────────────┘               │
│        ↓                                                         │
│   ┌─────────────────────────────────────────────┐               │
│   │              KVRM-CPU Execution              │               │
│   │   [Fetch] → [Decode LLM] → [Execute]        │               │
│   └─────────────────────────────────────────────┘               │
│        ↓                                                         │
│   Execution Result                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Tasks

### Task 1: Assembly Format Standardization

**Current Issue**: CodeGen outputs assembly as a list, CPU expects text.

**Required Format** (CPU-compatible):
```asm
; KVRM-Lang compiled output
    MOV R0, 10
    MOV R1, R0
    CMP R1, R2
    JS label1
label1:
    MOV R7, R1
HALT
```

**Changes Needed**:
1. Modify `codegen_llm.py` to output string format
2. Or create assembly list-to-string converter
3. Ensure label syntax matches CPU parser expectations

### Task 2: Assembly Loader Creation

**Purpose**: Bridge between compiler output and CPU memory.

**Components**:
1. **Assembly Parser**: Parse text assembly into instruction list
2. **Memory Loader**: Load instructions into CPU memory array
3. **Label Resolver**: Convert labels to memory addresses

**Interface**:
```python
class AssemblyLoader:
    def load(self, assembly_text: str) -> List[Instruction]:
        """Parse assembly and return CPU-ready instructions."""
        pass

    def load_to_cpu(self, cpu: KVRMCPU, assembly: str) -> None:
        """Load assembly directly into CPU memory."""
        pass
```

### Task 3: CPU ISA Alignment

**Verify ISA Compatibility**:

| Compiler Generates | CPU Supports | Status |
|-------------------|--------------|--------|
| MOV Rd, Imm | MOV | ✓ |
| MOV Rd, Rs | MOV | ✓ |
| ADD Rd, Rs | ADD | ✓ |
| SUB Rd, Rs | SUB | ✓ |
| MUL Rd, Rs | MUL | ✓ |
| CMP Ra, Rb | CMP | ✓ |
| JMP label | JMP | ✓ |
| JZ label | JZ | ✓ |
| JNZ label | JNZ | ✓ |
| JS label | JS | ✓ |
| JNS label | JNS | ✓ |
| HALT | HALT | ✓ |
| Labels (name:) | Labels | ? Verify |

**Potential Gaps**:
- Print semantics (R7 convention vs explicit PRINT)
- Function call/return (CALL, RET)
- Stack operations (PUSH, POP)

### Task 4: End-to-End Pipeline

**Create Unified Interface**:

```python
class KVRMExecutionEngine:
    def __init__(self):
        self.compiler = KVRMLLMCompiler()
        self.loader = AssemblyLoader()
        self.cpu = KVRMCPU()

    def compile(self, source: str) -> str:
        """Compile source to assembly."""
        tokens = self.compiler.lexer.process({"task": "tokenize", "source": source})
        ast = self.compiler.parser.process({"task": "parse", "tokens": tokens["tokens"]})
        asm = self.compiler.codegen.process({"task": "codegen", "ast": ast["ast"]})
        return self._format_assembly(asm["assembly"])

    def execute(self, source: str) -> ExecutionResult:
        """Compile and execute source code."""
        assembly = self.compile(source)
        self.loader.load_to_cpu(self.cpu, assembly)
        return self.cpu.run()

    def run(self, source: str) -> Any:
        """Full compile-and-execute in one call."""
        result = self.execute(source)
        return result.output
```

### Task 5: Validation Integration

**Purpose**: Add semantic validation before execution.

**Validation Checks**:
1. Variable declaration before use
2. Type consistency
3. Branch target validity
4. Stack balance (if applicable)
5. Register allocation sanity

**Integration Point**:
```python
def compile_validated(self, source: str) -> str:
    tokens = self.lexer.process(...)
    ast = self.parser.process(...)

    # Validation step
    validation = self.validator.process({
        "task": "validate",
        "ast": ast["ast"]
    })

    if not validation["valid"]:
        raise CompilationError(validation["errors"])

    assembly = self.codegen.process(...)
    return assembly
```

---

## Implementation Phases

### Phase 1: Assembly Format Bridge (1-2 days)

1. Create `assembly_formatter.py`
2. Convert list output to text format
3. Add label formatting
4. Test with simple programs

### Phase 2: Assembly Loader (2-3 days)

1. Create `assembly_loader.py`
2. Implement assembly parser
3. Implement label resolution
4. Implement memory loading
5. Unit tests for loader

### Phase 3: CPU Integration (2-3 days)

1. Verify ISA compatibility
2. Update CPU if needed for missing instructions
3. Create `execution_engine.py`
4. Integration tests

### Phase 4: Validation Pipeline (3-4 days)

1. Train validator on compiler-specific data (if needed)
2. Integrate validator into pipeline
3. Create error reporting
4. End-to-end validation tests

### Phase 5: Testing & Polish (2-3 days)

1. Comprehensive test suite
2. Performance benchmarking
3. Error handling improvements
4. Documentation

**Total Estimated Time**: 10-15 days

---

## Testing Strategy

### Unit Tests

```python
# Test individual components
def test_assembly_formatter():
    asm_list = ["MOV R0, 5", "HALT"]
    result = format_assembly(asm_list)
    assert "MOV R0, 5" in result
    assert "HALT" in result

def test_assembly_loader():
    asm = "; test\nMOV R0, 5\nHALT"
    instructions = loader.load(asm)
    assert len(instructions) == 2
```

### Integration Tests

```python
def test_compile_and_execute_simple():
    engine = KVRMExecutionEngine()
    result = engine.run("let x = 42\nprint x")
    assert result == 42

def test_compile_and_execute_conditional():
    engine = KVRMExecutionEngine()
    result = engine.run("""
        let a = 10
        let b = 20
        if a < b {
            print a
        } else {
            print b
        }
    """)
    assert result == 10
```

### End-to-End Tests

```python
def test_full_pipeline_all_features():
    programs = load_test_programs("programs/")
    for program in programs:
        result = engine.run(program.source)
        assert result == program.expected_output
```

---

## Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| ISA mismatch | Execution fails | Audit ISA before implementation |
| Label resolution bugs | Wrong jumps | Comprehensive label tests |
| Memory layout issues | Crashes | Careful memory model alignment |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance overhead | Slow execution | Profile and optimize |
| Error messages unclear | Poor debugging | Invest in error reporting |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation gaps | Maintenance cost | Document during implementation |

---

## Success Criteria

### Minimum Viable Integration

- [ ] Simple programs compile and execute correctly
- [ ] Variable assignment works
- [ ] Print outputs correct values
- [ ] HALT terminates execution

### Full Integration

- [ ] All language features work
- [ ] Conditional execution (if/else)
- [ ] Loops (while)
- [ ] Functions (if supported)
- [ ] Error handling and reporting
- [ ] Performance acceptable (<5s for simple programs)

---

## Resources Required

### Code Assets

- `kvrm-llm-compiler/` - Compiler pipeline
- `kvrm-cpu/` - CPU emulator
- `kvrm-compiler/` - Reference compiler (TypeScript)

### Documentation

- CPU ISA specification
- Compiler output format specification
- Test program suite

### Hardware

- Local Mac for development/testing
- Vast.ai for any additional training

---

## Appendix: Example Flow

### Input Program

```
let x = 10
let y = 20
if x < y {
    print x
}
```

### After Lexer

```json
{"tokens": [
  {"type": "LET", "value": "let"},
  {"type": "IDENT", "value": "x"},
  {"type": "ASSIGN", "value": "="},
  {"type": "NUMBER", "value": 10},
  ...
]}
```

### After Parser

```json
{"ast": {
  "type": "Program",
  "statements": [
    {"type": "Assignment", "target": "x", "value": {"type": "NumberLiteral", "value": 10}},
    {"type": "Assignment", "target": "y", "value": {"type": "NumberLiteral", "value": 20}},
    {"type": "IfStatement", "condition": {...}, "then_body": [...]}
  ]
}}
```

### After CodeGen

```asm
; KVRM-Lang compiled output
    MOV R0, 10
    MOV R1, R0    ; x = 10
    MOV R0, 20
    MOV R2, R0    ; y = 20
    CMP R1, R2    ; x < y
    JS cmp_true
    MOV R0, 0
    JMP cmp_end
cmp_true:
    MOV R0, 1
cmp_end:
    JZ endif
    MOV R7, R1    ; print x
endif:
HALT
```

### CPU Execution

```
PC=0: MOV R0, 10    → R0=10
PC=1: MOV R1, R0    → R1=10
PC=2: MOV R0, 20    → R0=20
PC=3: MOV R2, R0    → R2=20
PC=4: CMP R1, R2    → FLAGS.SIGN=1 (10<20)
PC=5: JS cmp_true   → Jump taken
PC=7: MOV R0, 1     → R0=1
PC=9: JZ endif      → Not taken (R0≠0)
PC=10: MOV R7, R1   → OUTPUT: 10
PC=11: HALT         → Execution complete
```

### Final Output

```
10
```

---

*Document part of KVRM Research - blackWeb Research*
