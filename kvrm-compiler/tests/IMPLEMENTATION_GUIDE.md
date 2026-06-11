# KVRM Compiler Test Suite - Implementation Guide

## Overview

A comprehensive test suite has been created for the KVRM compiler with **288 test cases** covering all compilation stages. The tests currently use mock implementations and serve as **executable specifications** for building the compiler.

## Test Results Summary

```
Total Tests: 288
- Passing: 169 (mock implementations)
- Failing: 119 (awaiting real implementations)

Test Files: 5
- integration.test.ts: 45 tests
- lexer.test.ts: 76 tests
- parser.test.ts: 78 tests
- semantic.test.ts: 61 tests
- tokens.test.ts: 28 tests
```

## Implementation Roadmap

### Phase 1: Lexer Implementation

**File**: `src/lexer/index.ts` or `src/lexer/lexer.ts`

**Required Interface**:
```typescript
interface Lexer {
  nextToken(): Token;
  peek(): Token;
  hasNext(): boolean;
  reset(): void;
}
```

**Test File**: `tests/lexer.test.ts` (76 tests)

**Features to Implement**:
1. Keyword tokenization (fn, let, if, etc.)
2. Operator tokenization (+, -, *, ==, etc.)
3. Number literals (decimal, hex, binary, octal, scientific)
4. String literals with escapes
5. Identifier handling
6. Comment handling (single-line //, multi-line /* */)
7. Whitespace handling and location tracking
8. Error reporting for invalid input

**Steps**:
```bash
# 1. Create lexer implementation
touch src/lexer/index.ts

# 2. Update lexer.test.ts imports
# Replace MockLexer with real Lexer

# 3. Run lexer tests
npm test lexer.test.ts

# 4. Implement features until all 76 tests pass
```

**Expected Outcome**: All 76 lexer tests passing

---

### Phase 2: Parser Implementation

**File**: `src/parser/index.ts` or `src/parser/parser.ts`

**Required Interface**:
```typescript
interface Parser {
  parse(): ASTNode;
  parseExpression(): ASTNode;
  parseStatement(): ASTNode;
  parseDeclaration(): ASTNode;
}
```

**Test File**: `tests/parser.test.ts` (78 tests)

**Features to Implement**:
1. Variable declarations (let, let mut)
2. Function declarations with parameters and return types
3. Expression parsing with correct precedence
4. Control flow (if/else, while, for)
5. Struct and enum definitions
6. Impl blocks
7. Pattern matching
8. Error recovery and reporting

**AST Nodes Required**:
- VariableDeclaration
- FunctionDeclaration
- BinaryExpression
- UnaryExpression
- CallExpression
- MemberExpression
- IfStatement
- WhileStatement
- ForStatement
- StructDeclaration
- EnumDeclaration
- ImplDeclaration

**Steps**:
```bash
# 1. Create parser implementation
touch src/parser/index.ts

# 2. Define AST node types
touch src/parser/ast.ts

# 3. Update parser.test.ts imports
# Replace MockParser with real Parser

# 4. Run parser tests
npm test parser.test.ts

# 5. Implement features until all 78 tests pass
```

**Expected Outcome**: All 78 parser tests passing

---

### Phase 3: Semantic Analyzer Implementation

**File**: `src/semantic/index.ts` or `src/semantic/analyzer.ts`

**Required Interface**:
```typescript
interface SemanticAnalyzer {
  analyze(ast: ASTNode): void;
  checkType(node: ASTNode): Type;
  resolveType(name: string): Type;
  getErrors(): SemanticError[];
}
```

**Test File**: `tests/semantic.test.ts` (61 tests)

**Features to Implement**:
1. Type inference from expressions
2. Type checking for assignments and operations
3. Variable scope tracking
4. Mutability checking
5. Function signature validation
6. Struct field validation
7. Array type checking
8. Type widening rules

**Type System** (already defined in `src/semantic/types.ts`):
- PrimitiveType (i8, i16, i32, i64, u8, u16, u32, u64, f32, f64, bool, char, str)
- ArrayType
- StructType
- EnumType
- FunctionType
- TupleType

**Steps**:
```bash
# 1. Create semantic analyzer
touch src/semantic/index.ts

# 2. Update semantic.test.ts imports
# Replace MockSemanticAnalyzer with real implementation

# 3. Run semantic tests
npm test semantic.test.ts

# 4. Implement features until all 61 tests pass
```

**Expected Outcome**: All 61 semantic tests passing

---

### Phase 4: Integration & Code Generation

**File**: `src/compiler/index.ts` or `src/codegen/index.ts`

**Required Interface**:
```typescript
interface Compiler {
  compile(source: string): CompilationResult;
  compileFile(path: string): CompilationResult;
}

interface CompilationResult {
  success: boolean;
  output?: string;  // Assembly code
  errors?: CompilationError[];
  ast?: ASTNode;
  ir?: any;
}
```

**Test File**: `tests/integration.test.ts` (45 tests)

**Features to Implement**:
1. Complete compilation pipeline
2. Assembly code generation
3. Error propagation across stages
4. File handling
5. Multi-stage compilation

**Steps**:
```bash
# 1. Create compiler orchestrator
touch src/compiler/index.ts

# 2. Create code generator
touch src/codegen/index.ts

# 3. Update integration.test.ts imports
# Replace MockCompiler with real implementation

# 4. Run integration tests
npm test integration.test.ts

# 5. Implement features until all 45 tests pass
```

**Expected Outcome**: All 45 integration tests passing

---

## Quick Start Implementation

### Step 1: Replace Mock Implementations

For each test file, replace the mock class with the real implementation:

**Before** (lexer.test.ts):
```typescript
class MockLexer implements Lexer {
  nextToken() {
    return { type: TokenType.Eof, value: '', line: 1, column: 1 };
  }
  // ...
}

const createLexer = (input: string): Lexer => {
  return new MockLexer();
};
```

**After**:
```typescript
import { Lexer } from '../src/lexer';

const createLexer = (input: string): Lexer => {
  return new Lexer(input);
};
```

### Step 2: Run Tests and Iterate

```bash
# Run specific test file
npm test lexer.test.ts

# Watch mode for rapid iteration
npm run test:watch -- lexer.test.ts

# Check coverage
npm run test:coverage
```

### Step 3: Implement Features

Use Test-Driven Development:
1. Pick a failing test
2. Implement minimum code to pass
3. Refactor
4. Move to next test

---

## Test Fixtures Usage

The test fixtures in `tests/fixtures/` can be used to validate complete compilation:

```typescript
import { readFileSync } from 'fs';
import { Compiler } from '../src/compiler';

const source = readFileSync('tests/fixtures/simple.kv', 'utf-8');
const compiler = new Compiler();
const result = compiler.compile(source);

if (result.success) {
  console.log('Assembly:', result.output);
} else {
  console.error('Errors:', result.errors);
}
```

**Available Fixtures**:
- `simple.kv` - Basic language features
- `functions.kv` - Function declarations and recursion
- `control-flow.kv` - If/else, while, for loops
- `structs.kv` - Struct definitions and methods
- `errors.kv` - Intentional errors for error handling tests

---

## Coverage Goals

Target coverage after full implementation:

```
Lines:      > 90%
Functions:  > 95%
Branches:   > 85%
Statements: > 90%
```

Run coverage report:
```bash
npm run test:coverage
```

---

## Error Handling Guidelines

Based on error tests, the compiler should:

1. **Detect errors at the correct stage**:
   - Lexer: Invalid characters, malformed literals
   - Parser: Syntax errors, missing tokens
   - Semantic: Type errors, undefined variables

2. **Provide helpful error messages**:
   - Clear description of the problem
   - Suggestion for fix when possible
   - Accurate location (line and column)

3. **Support error recovery**:
   - Continue compilation after non-fatal errors
   - Report multiple errors in one pass
   - Synchronize at statement boundaries

4. **Error format**:
   ```typescript
   interface CompilationError {
     message: string;
     location: { line: number; column: number };
     stage: 'lexer' | 'parser' | 'semantic' | 'codegen';
   }
   ```

---

## Validation Checklist

Before considering a stage complete:

### Lexer
- [ ] All 76 tests passing
- [ ] Handles all token types
- [ ] Accurate location tracking
- [ ] Comment handling
- [ ] Error reporting

### Parser
- [ ] All 78 tests passing
- [ ] Correct operator precedence
- [ ] Error recovery works
- [ ] AST structure matches spec
- [ ] All language constructs supported

### Semantic Analyzer
- [ ] All 61 tests passing
- [ ] Type inference working
- [ ] Type checking correct
- [ ] Scope tracking accurate
- [ ] Mutability enforced

### Integration
- [ ] All 45 tests passing
- [ ] Complete pipeline works
- [ ] All fixtures compile (except errors.kv)
- [ ] Assembly output valid
- [ ] Error propagation correct

---

## Debugging Tips

### Test Failures

When tests fail:

1. **Read the test name** - It describes what should work
2. **Check the assertion** - See what's being validated
3. **Look at test input** - Understand the test case
4. **Add debug output** - Log intermediate values
5. **Use debugger** - Set breakpoints in your implementation

### Common Issues

1. **Off-by-one errors** in location tracking
2. **Precedence bugs** in expression parsing
3. **Type widening** rules implementation
4. **Scope tracking** with nested blocks
5. **Error recovery** synchronization

### Test Isolation

Each test should be independent:
```typescript
it('should do something', () => {
  const lexer = createLexer('input');  // Fresh instance
  // Test the feature
});
```

---

## Performance Considerations

Once tests pass, optimize for:

1. **Lexer performance**: Efficient character reading
2. **Parser performance**: Minimal backtracking
3. **Semantic analysis**: Efficient symbol table lookups
4. **Memory usage**: Avoid unnecessary allocations

Add performance benchmarks:
```bash
# Create benchmarks directory
mkdir tests/benchmarks

# Benchmark large files
npm run benchmark
```

---

## Next Steps After Tests Pass

1. **Add more edge cases** discovered during development
2. **Optimize performance** based on benchmarks
3. **Enhance error messages** for better UX
4. **Add language features** (with tests first!)
5. **Create standard library** tests
6. **Build language tools** (formatter, linter)

---

## Getting Help

If stuck on implementation:

1. Review the test file - it shows expected behavior
2. Check existing type definitions in `src/semantic/types.ts`
3. Look at parser error classes in `src/parser/errors.ts`
4. Reference Rust/C syntax for similar constructs
5. Start with simplest case, build up complexity

---

## Summary

You have a complete, professional test suite with 288 tests covering:
- ✅ Lexical analysis (76 tests)
- ✅ Syntax analysis (78 tests)
- ✅ Semantic analysis (61 tests)
- ✅ Integration testing (45 tests)
- ✅ Type system validation (28 tests)

**These tests are your implementation roadmap.** Each test describes a feature that needs to work. Implement features to make tests pass, and you'll have a complete, well-tested KVRM compiler.

Good luck building your compiler!
