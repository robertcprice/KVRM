# KVRM Compiler IR (Intermediate Representation)

A clean, SSA-based intermediate representation for the KVRM compiler, designed to bridge high-level typed AST and low-level KVRM CPU assembly.

## Architecture Overview

The IR module consists of four main components:

### 1. IR Nodes (`ir-nodes.ts`)

Defines the core IR data structures in SSA (Static Single Assignment) form:

- **Types**: `IRType` with support for i32, i64, f32, f64, bool, pointers, structs, and void
- **Values**: `IRValue` representing SSA values with unique IDs
- **Instructions**: Complete instruction set including:
  - `IRConst`: Load constant values
  - `IRLoad/IRStore`: Memory operations
  - `IRBinOp/IRUnaryOp`: Arithmetic and logical operations
  - `IRCall`: Function calls
  - `IRJump/IRCondJump`: Control flow
  - `IRPhi`: SSA phi nodes for value merging
  - `IRAlloc`: Stack allocation
  - `IRGetElementPtr`: Struct field access and array indexing

### 2. IR Generator (`generator.ts`)

Converts typed AST programs to SSA-form IR:

```typescript
const generator = new IRGenerator();
const ir = generator.generate(typedProgram);
```

**Features**:
- SSA value numbering
- Basic block construction
- Control flow graph building
- Symbol table management
- Struct layout calculation

**Supported Constructs**:
- Function definitions with parameters
- Local variables (stack allocation)
- Arithmetic and logical expressions
- Control flow (if/else, while loops)
- Struct field access
- Function calls

### 3. IR Optimizer (`optimizer.ts`)

Implements standard optimization passes:

```typescript
const optimizer = new IROptimizer();
const optimizedIR = optimizer.optimize(ir, iterations = 3);
```

**Optimization Passes**:
- **Constant Folding**: Evaluate constant expressions at compile time
  - `5 + 3` → `8`
  - `10 * 2` → `20`

- **Dead Code Elimination**: Remove instructions computing unused values

- **Common Subexpression Elimination**: Avoid redundant computations
  - `x * x` computed once and reused

- **Copy Propagation**: Replace copied values with originals

### 4. IR Printer (`printer.ts`)

Human-readable IR output for debugging and visualization:

```typescript
const output = printIR(program);
console.log(output);
```

**Utilities**:
- `printIR()`: Format entire program
- `printFunction()`: Format single function
- `generateCFGDot()`: Export control flow graph in DOT format
- `generateStats()`: Compute IR statistics
- `printStats()`: Display instruction counts and metrics

## Design Rationale

### SSA Form

All values are in SSA form with unique IDs. Benefits:
- Simplifies optimization passes
- Makes data flow explicit
- Enables efficient analysis

### Load/Store Architecture

Memory operations are explicit through `load` and `store` instructions, matching the KVRM CPU's load/store architecture.

### Type System

IR preserves type information for:
- Type-safe optimizations
- Efficient code generation
- Better error detection

## Example Usage

### Simple Function

**Source**:
```rust
fn add(a: i32, b: i32) -> i32 {
  return a + b;
}
```

**Generated IR**:
```
fn @add(%param_a: i32, %param_b: i32) -> i32 {
entry_0:
  %0: *i32 = alloc i32
  %1: *i32 = alloc i32
  %2: i32 = load %0
  %3: i32 = load %1
  %4: i32 = add %2, %3
  return %4
}
```

### Loop with Optimization

**Source**:
```rust
fn factorial(n: i32) -> i32 {
  let mut result = 1;
  let mut i = n;
  while i > 0 {
    result = result * i;
    i = i - 1;
  }
  return result;
}
```

**IR Features**:
- Multiple basic blocks (entry, while_header, while_body, while_exit)
- Conditional jumps
- Memory operations for mutable variables
- SSA values throughout

### Constant Folding

**Before Optimization**:
```
%0: i32 = const 5
%1: i32 = const 3
%2: i32 = add %0, %1
```

**After Optimization**:
```
%2: i32 = const 8
```

## KVRM CPU Target

The IR is designed for the KVRM CPU architecture:

**CPU Specifications**:
- 16 general-purpose registers (R0-R15)
- Stack-based calling convention
- Load/Store architecture (no memory operands in arithmetic)
- 32-bit and 64-bit integer operations
- Floating-point support

**Lowering Strategy**:
- SSA values map to virtual registers
- Register allocation assigns virtual registers to physical registers
- Stack used for spills and local variables
- Function parameters passed via stack

## Type Mappings

| IR Type | KVRM Size | Alignment |
|---------|-----------|-----------|
| i32     | 4 bytes   | 4 bytes   |
| i64     | 8 bytes   | 8 bytes   |
| f32     | 4 bytes   | 4 bytes   |
| f64     | 8 bytes   | 8 bytes   |
| bool    | 4 bytes   | 4 bytes   |
| ptr     | 8 bytes   | 8 bytes   |
| struct  | Variable  | 8 bytes   |

## Running Examples

```bash
# Build the compiler
npm run build

# Run IR examples
node dist/ir/example.js
```

This will generate and optimize IR for several example programs, showing:
- Unoptimized IR
- Optimized IR
- Statistics (instruction counts, block sizes)
- Control flow graphs in DOT format

## Control Flow Graph Visualization

Generate CFG in DOT format and visualize with Graphviz:

```bash
node dist/ir/example.js > output.txt
# Extract DOT section
dot -Tpng cfg.dot -o cfg.png
```

## Extension Points

### Adding Custom Optimization Passes

```typescript
class MyOptimization implements OptimizationPass {
  name = 'MyOptimization';

  optimize(program: IRProgram): IRProgram {
    // Your optimization logic
    return program;
  }
}

const optimizer = new IROptimizer();
optimizer.addPass(new MyOptimization());
```

### Adding New Instructions

1. Define instruction interface in `ir-nodes.ts`
2. Add to `IRInstr` union type
3. Update generator in `generator.ts`
4. Update printer in `printer.ts`
5. Handle in relevant optimization passes

## Future Enhancements

- [ ] Advanced optimizations (loop unrolling, inlining)
- [ ] SSA construction with proper phi node placement
- [ ] Live range analysis for register allocation
- [ ] Instruction selection patterns
- [ ] Peephole optimizations
- [ ] Profile-guided optimizations

## Testing

The IR system can be tested with various typed AST programs. See `example.ts` for comprehensive test cases covering:
- Simple arithmetic
- Control flow (if/else, loops)
- Struct operations
- Constant folding opportunities

## References

- **SSA Form**: Cytron et al., "Efficiently Computing Static Single Assignment Form and the Control Dependence Graph"
- **Optimization Passes**: "Engineering a Compiler" by Cooper & Torczon
- **IR Design**: LLVM IR documentation (inspiration for structure)

## Integration

The IR module integrates with the KVRM compiler pipeline:

```
Source Code
    ↓
[Lexer] → Tokens
    ↓
[Parser] → AST
    ↓
[Semantic Analyzer] → Typed AST
    ↓
[IR Generator] → IR (SSA form)  ← This module
    ↓
[IR Optimizer] → Optimized IR   ← This module
    ↓
[Code Generator] → KVRM Assembly
    ↓
Machine Code
```

## License

MIT License - See LICENSE file for details
