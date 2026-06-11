# KVRM Code Generator

Production-quality code generator for the KVRM CPU architecture. Generates optimized assembly code from intermediate representation (IR).

## Architecture Overview

The code generator consists of several modular components:

```
codegen/
├── codegen.ts              # Main code generator (works with existing SSA IR)
├── generator.ts            # Advanced generator with full optimization pipeline
├── register-allocator.ts   # Linear scan register allocation
├── instruction-selector.ts # IR to assembly instruction mapping
├── asm-emitter.ts          # Assembly formatting and output
├── ir-adapter.ts           # IR format adapter (if needed)
└── example.ts              # Usage examples and demos
```

## KVRM CPU Specifications

### Registers
- **R0-R15**: 16 general-purpose 32-bit registers
- **R0-R3**: Argument passing and scratch registers (caller-saved)
- **R4-R12**: General-purpose registers (R4-R11 are callee-saved)
- **R13 (LR)**: Link Register - stores return address
- **R14 (SP)**: Stack Pointer - points to top of stack
- **R15 (PC)**: Program Counter - points to current instruction

### Instruction Set

#### Arithmetic Operations
- `ADD dest, src1, src2` - Add
- `SUB dest, src1, src2` - Subtract
- `MUL dest, src1, src2` - Multiply
- `DIV dest, src1, src2` - Divide
- `MOD dest, src1, src2` - Modulo

#### Bitwise Operations
- `AND dest, src1, src2` - Bitwise AND
- `OR dest, src1, src2` - Bitwise OR
- `XOR dest, src1, src2` - Bitwise XOR
- `NOT dest, src` - Bitwise NOT
- `SHL dest, src1, src2` - Shift left
- `SHR dest, src1, src2` - Shift right

#### Memory Operations
- `LDR dest, [addr]` - Load from memory
- `STR src, [addr]` - Store to memory
- `LDR dest, [base, #offset]` - Load with offset
- `STR src, [base, #offset]` - Store with offset
- `PUSH reg` - Push register to stack
- `POP reg` - Pop from stack to register

#### Control Flow
- `JMP label` - Unconditional jump
- `JZ label` - Jump if zero
- `JNZ label` - Jump if not zero
- `JEQ label` - Jump if equal
- `JNE label` - Jump if not equal
- `JLT label` - Jump if less than
- `JGT label` - Jump if greater than
- `JLE label` - Jump if less or equal
- `JGE label` - Jump if greater or equal
- `CALL func` - Function call
- `RET` - Return from function

#### Data Movement
- `MOV dest, src` - Move data
- `MOVH dest, #imm` - Move to high 16 bits
- `LEA dest, addr` - Load effective address

#### System
- `NOP` - No operation
- `HLT` - Halt execution
- `CMP src1, src2` - Compare (sets flags)

### Calling Convention

1. **Argument Passing**:
   - First 4 arguments: R0-R3
   - Additional arguments: pushed onto stack (right-to-left)

2. **Return Value**:
   - 32-bit values: R0
   - 64-bit values: R0 (low), R1 (high)

3. **Register Preservation**:
   - Caller-saved: R0-R3, R12
   - Callee-saved: R4-R11, LR, SP
   - Callee must save/restore R4-R11 if used

4. **Stack Frame**:
   ```
   High Address
   ┌─────────────────┐
   │  Previous Frame │
   ├─────────────────┤
   │  Return Address │ <- Saved LR
   ├─────────────────┤
   │  Frame Pointer  │ <- Saved R14
   ├─────────────────┤
   │  Saved Regs     │ <- Callee-saved registers
   ├─────────────────┤
   │  Local Vars     │
   ├─────────────────┤
   │  Spilled Values │
   ├─────────────────┤ <- SP (Stack Pointer)
   Low Address
   ```

## Usage

### Basic Usage

```typescript
import { KVRMCodeGenerator } from './codegen/codegen.js';
import type { IRProgram } from './ir/ir-nodes.js';

// Assuming you have an IR program from the parser/semantic analyzer
const irProgram: IRProgram = /* ... */;

const generator = new KVRMCodeGenerator();
const assembly = generator.generate(irProgram);

console.log(assembly);
```

### Advanced Usage with Full Pipeline

```typescript
import { CodeGenerator, generateWithStats } from './codegen/generator.js';
import type { IRProgram } from './ir/types.js';

const irProgram: IRProgram = /* ... */;

const { assembly, stats } = generateWithStats(irProgram, {
  optimize: true,
  debugInfo: true,
  commentLevel: 'detailed',
  formatOptions: {
    uppercase: true,
    commentColumn: 40,
  },
});

console.log('Generated Assembly:');
console.log(assembly);

console.log('\nStatistics:');
console.log(`Functions: ${stats.functionsGenerated}`);
console.log(`Instructions: ${stats.instructionsGenerated}`);
console.log(`Spilled registers: ${stats.registersSpilled}`);
console.log(`Max stack frame: ${stats.maxStackFrameSize} bytes`);
```

## Example Output

For a simple `add` function:

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

The generator produces:

```assembly
; ========================================
; Function: add
; ========================================
add:
    PUSH LR                              ; Save return address
    PUSH R14                             ; Save frame pointer
    MOV R14, SP                          ; Setup frame pointer
    MOV R4, R0                           ; Move arg a to working register
    ADD R4, R4, R1                       ; Add parameters a and b
    MOV R0, R4                           ; Move result to return register
    POP R14                              ; Restore frame pointer
    POP LR                               ; Restore return address
    RET                                  ; Return
```

## Register Allocation

The code generator implements **linear scan register allocation** with the following features:

### Algorithm
1. **Live Range Computation**: Calculate when each value is live (used)
2. **Interval Sorting**: Sort live intervals by start position
3. **Greedy Allocation**: Assign registers in order, spilling if needed
4. **Spill Selection**: Choose values with lowest spill cost

### Optimization Strategies
- **Callee-saved preference**: Long-lived values prefer R4-R11
- **Argument registers**: R0-R3 for function arguments
- **Spill cost computation**: Based on usage frequency and context
- **Register coalescing**: Eliminate unnecessary moves

### Example

```typescript
import { RegisterAllocator } from './codegen/register-allocator.js';
import type { IRFunction } from './ir/types.js';

const allocator = new RegisterAllocator();
const allocation = allocator.allocate(func);

console.log('Spilled values:', allocation.spilledValues);
console.log('Stack frame size:', allocation.stackFrameSize);
console.log('Callee-saved used:', allocation.calleeSavedUsed);
```

## Instruction Selection

Maps high-level IR operations to KVRM assembly instructions with optimizations:

### Features
- **Immediate folding**: Use immediate operands when possible
- **Addressing modes**: Optimize memory access patterns
- **Instruction combining**: Merge multiple operations
- **Comparison optimization**: Efficient conditional code

### Example

```typescript
import { InstructionSelector } from './codegen/instruction-selector.js';

const selector = new InstructionSelector(registerMap);
const asmInstructions = selector.select(irInstruction);
```

## Assembly Emission

Formats and outputs assembly code with professional quality:

### Features
- **Configurable formatting**: Indentation, case, column alignment
- **Comment generation**: Optional detailed/minimal/none
- **Section management**: .text, .data, .rodata, .bss
- **Label generation**: Automatic unique labels
- **Directive support**: .global, .word, .string, etc.

### Example

```typescript
import { AssemblyEmitter } from './codegen/asm-emitter.js';

const emitter = new AssemblyEmitter({
  indent: '    ',
  commentColumn: 40,
  uppercase: true,
});

emitter.emitPreamble('main');
emitter.emitSection(AsmSection.Text);
emitter.emitFunctionPrologue('main', 16, new Set([4, 5]), true);
// ... emit instructions ...
emitter.emitFunctionEpilogue(16, new Set([4, 5]));

const assembly = emitter.toString();
```

## Code Generation Options

```typescript
interface CodeGenOptions {
  optimize: boolean;           // Enable optimizations
  debugInfo: boolean;          // Include debug information
  commentLevel: 'none' | 'minimal' | 'detailed';
  formatOptions?: {
    indent?: string;           // Default: '    '
    commentColumn?: number;    // Default: 40
    uppercase?: boolean;       // Default: true
  };
}
```

## Testing

Run the example to see the code generator in action:

```bash
cd /Users/bobbyprice/projects/KVRM/kvrm-compiler
npm run build
node dist/codegen/example.js
```

## Architecture Decisions

### Why Linear Scan?
- **Performance**: O(n log n) complexity vs O(n²) for graph coloring
- **Simplicity**: Easier to implement and debug
- **Quality**: 90-95% of graph coloring quality in practice
- **Predictability**: Deterministic allocation behavior

### Why Load/Store Architecture?
- **Simplicity**: Clear separation of memory and register operations
- **RISC philosophy**: Simple, regular instruction format
- **Optimization**: Easier to optimize register allocation

### Why Callee-saved R4-R11?
- **Call overhead**: Reduces register saves across function calls
- **Common pattern**: Matches ARM and other RISC architectures
- **Flexibility**: Caller-saved R0-R3 for scratch work

## Performance Characteristics

- **Register Allocation**: O(n log n) where n = number of values
- **Instruction Selection**: O(n) where n = number of IR instructions
- **Assembly Emission**: O(n) where n = number of assembly instructions
- **Total Compilation**: O(n log n) for most programs

## Security Considerations

- **Stack protection**: Proper frame setup prevents buffer overflows
- **Bounds checking**: Array access validation (when enabled)
- **No executable data**: Separate code and data sections
- **Return address protection**: LR saved to stack

## Future Enhancements

1. **Graph Coloring Allocator**: For better register utilization
2. **Instruction Scheduling**: Reorder for better performance
3. **Peephole Optimization**: Local instruction patterns
4. **Dead Code Elimination**: Remove unused instructions
5. **Constant Propagation**: Fold constants at codegen time
6. **SIMD Support**: Vector instructions if architecture supports

## References

- [Engineering a Compiler (Cooper & Torczon)](https://www.elsevier.com/books/engineering-a-compiler/cooper/978-0-12-088478-0)
- [Linear Scan Register Allocation (Poletto & Sarkar)](http://web.cs.ucla.edu/~palsberg/course/cs132/linearscan.pdf)
- [ARM Architecture Reference Manual](https://developer.arm.com/documentation/)

## License

MIT License - See LICENSE file for details
