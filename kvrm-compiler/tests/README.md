# KVRM Compiler Tests

Comprehensive test suite for the KVRM compiler covering all compilation stages.

## Test Structure

### Unit Tests

#### `lexer.test.ts`
Tests for the lexical analysis phase:
- **Keywords**: All language keywords (fn, let, if, struct, etc.)
- **Operators**: Arithmetic, comparison, logical, assignment operators
- **Numbers**: Integers, floats, hex, binary, octal, scientific notation
- **Strings**: String literals with escape sequences and Unicode
- **Identifiers**: Variable and function names
- **Comments**: Single-line and multi-line comments
- **Delimiters**: Parentheses, braces, brackets
- **Whitespace**: Proper handling and line/column tracking
- **Error Cases**: Invalid characters, unterminated strings, malformed numbers

**Coverage**: 200+ test cases covering happy paths and edge cases

#### `parser.test.ts`
Tests for the syntax analysis phase:
- **Variable Declarations**: let, mut, type annotations
- **Function Declarations**: Parameters, return types, generics
- **Expressions**: Literals, binary/unary operations, function calls
- **Precedence**: Correct operator precedence and associativity
- **Control Flow**: if/else, while, for loops
- **Type Definitions**: Structs, enums, impl blocks
- **Complex Programs**: Multi-declaration programs
- **Error Recovery**: Graceful handling of syntax errors

**Coverage**: 100+ test cases for all AST node types

#### `semantic.test.ts`
Tests for semantic analysis and type checking:
- **Type System**: Primitive types, arrays, structs, functions, tuples
- **Type Inference**: Automatic type deduction from expressions
- **Type Checking**: Assignment compatibility, function calls, operations
- **Type Widening**: Integer promotion, float conversions
- **Variable Scope**: Declaration, usage, shadowing, redefinition
- **Mutability**: Immutable vs mutable variable checking
- **Function Validation**: Return types, parameter types, argument counts
- **Struct Validation**: Field access, construction, method calls
- **Array Validation**: Element types, indexing, bounds

**Coverage**: 80+ test cases for type system correctness

### Integration Tests

#### `integration.test.ts`
End-to-end compilation tests:
- **Simple Programs**: Variable declarations, arithmetic
- **Functions**: Declarations, calls, recursion
- **Control Flow**: Complete if/else/while/for programs
- **Structs**: Definitions, implementations, usage
- **Enums**: Variants, pattern matching
- **Arrays**: Literals, indexing, iteration
- **Assembly Output**: Generated code validation
- **Error Handling**: Error detection across all stages
- **Complete Programs**: Real-world examples (fibonacci, calculator)

**Coverage**: 50+ end-to-end scenarios

## Test Fixtures

Located in `tests/fixtures/`, these are complete KVRM programs for integration testing:

### `simple.kv`
Basic language features:
- Variable declarations (immutable and mutable)
- Arithmetic expressions
- Boolean expressions
- Different number formats (hex, binary, octal)
- String literals

### `functions.kv`
Function-related features:
- Simple and complex function declarations
- Recursive functions (factorial, fibonacci)
- Multiple parameters and return types
- Generic functions
- Function calls and composition

### `control-flow.kv`
Control structures:
- If/else statements and chains
- While loops with various conditions
- For loops with ranges (inclusive and exclusive)
- Nested control structures
- Early returns and guard clauses

### `structs.kv`
Struct and implementation features:
- Struct definitions with various field types
- Nested structs
- Implementation blocks with methods
- Static methods and constructors
- Generic structs
- Struct usage examples

### `errors.kv`
**Intentional errors for testing error detection:**
- Lexer errors (invalid characters, malformed literals)
- Parser errors (missing semicolons, syntax errors)
- Semantic errors (type mismatches, undefined variables)
- Scope errors (out-of-scope access, redefinitions)
- Function errors (wrong argument counts/types)
- Struct errors (missing fields, invalid access)

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run specific test file
npm test lexer.test.ts

# Run tests matching pattern
npm test -- --grep "Parser - Variable"
```

## Test Organization

Tests follow the AAA (Arrange-Act-Assert) pattern:

```typescript
it('should tokenize keywords', () => {
  // Arrange
  const lexer = new Lexer('fn let if');

  // Act
  const token1 = lexer.nextToken();

  // Assert
  expect(token1.type).toBe(TokenType.Fn);
});
```

## Mock Implementation

Current tests use mock implementations with placeholder interfaces. Replace with actual implementations:

```typescript
// Replace:
import { MockLexer } from './mocks';
const lexer = new MockLexer(input);

// With:
import { Lexer } from '../src/lexer';
const lexer = new Lexer(input);
```

## Coverage Goals

- **Line Coverage**: > 90%
- **Branch Coverage**: > 85%
- **Function Coverage**: > 95%
- **Statement Coverage**: > 90%

## Test-Driven Development

These tests serve as specifications for implementing the compiler:

1. **Lexer Implementation**: Use `lexer.test.ts` as specification
2. **Parser Implementation**: Use `parser.test.ts` as specification
3. **Semantic Analyzer**: Use `semantic.test.ts` as specification
4. **Integration**: Use `integration.test.ts` to validate pipeline

## Edge Cases Tested

- Empty input
- Whitespace-only input
- Maximum/minimum numeric values
- Very long identifiers
- Deeply nested structures
- Large programs
- Unicode characters
- Comments in various positions
- Error recovery scenarios

## Error Testing Strategy

Tests validate:
1. **Error Detection**: Errors are caught at the correct stage
2. **Error Messages**: Clear, helpful error messages
3. **Error Location**: Accurate line/column information
4. **Error Recovery**: Compilation continues when possible
5. **Multiple Errors**: All errors reported, not just first

## Continuous Integration

Tests run automatically on:
- Every commit (pre-commit hook)
- Pull requests
- Scheduled nightly builds
- Before package publishing

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests cover happy path and edge cases
3. Add error case tests
4. Update fixtures if needed
5. Run full test suite before committing
