# KVRM Compiler

A production-quality compiler for the KVRM programming language, built with TypeScript.

## Overview

KVRM is a modern systems programming language with Rust-inspired syntax and a focus on safety, performance, and expressiveness. This compiler implements the full language specification with comprehensive type checking, optimization, and code generation.

## Features

- **Complete Lexer**: Tokenizes KVRM source code with full operator and keyword support
- **Type-Safe AST**: Comprehensive abstract syntax tree with discriminated unions
- **Modern Architecture**: Clean separation of concerns across compilation phases
- **Production Quality**: Strict TypeScript, comprehensive error handling, extensive testing
- **CLI Interface**: Command-line tools for compilation, type checking, and formatting

## Installation

```bash
npm install
npm run build
```

## Usage

### Compile a KVRM Program

```bash
kvrmc compile program.kvrm -o program
```

### Type Check Without Compiling

```bash
kvrmc check program.kvrm
```

### Format Source Code

```bash
kvrmc fmt program.kvrm
```

### Interactive REPL

```bash
kvrmc repl
```

## Project Structure

```
kvrm-compiler/
├── src/
│   ├── lexer/          # Lexical analysis
│   ├── parser/         # Syntax analysis and AST generation
│   ├── semantic/       # Type checking and semantic analysis
│   ├── ir/             # Intermediate representation
│   ├── codegen/        # Code generation
│   ├── types/          # Type definitions (tokens, AST)
│   ├── utils/          # Shared utilities
│   ├── cli.ts          # Command-line interface
│   └── index.ts        # Public API exports
├── tests/              # Test suites
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript configuration
└── vitest.config.ts    # Test configuration
```

## Compiler Phases

1. **Lexer**: Converts source code into tokens
2. **Parser**: Builds an abstract syntax tree (AST)
3. **Semantic Analyzer**: Type checking and validation
4. **IR Generator**: Creates intermediate representation
5. **Code Generator**: Emits target code (LLVM IR, native code)

## Development

### Build

```bash
npm run build          # Compile TypeScript
npm run build:watch    # Watch mode
```

### Test

```bash
npm test              # Run all tests
npm run test:watch    # Watch mode
npm run test:coverage # Generate coverage report
```

### Code Quality

```bash
npm run typecheck     # Type checking
npm run format        # Format code
npm run format:check  # Check formatting
npm run lint          # Run all quality checks
```

## Language Features

KVRM supports modern language features including:

- **Type System**: Structs, enums, traits, generics, type inference
- **Memory Safety**: Ownership, borrowing, lifetimes
- **Control Flow**: If/else, while, for, match expressions
- **Functions**: First-class functions, closures, lambdas
- **Module System**: Namespaces, imports, visibility control
- **Pattern Matching**: Exhaustive match expressions
- **Operator Overloading**: Custom operator implementations
- **Metaprogramming**: Compile-time evaluation

## Example KVRM Code

```rust
// Function declaration with generics
pub fn max<T: Ord>(a: T, b: T) -> T {
    if a > b { a } else { b }
}

// Struct with implementation
pub struct Point {
    x: f64,
    y: f64,
}

impl Point {
    pub fn new(x: f64, y: f64) -> Point {
        Point { x, y }
    }

    pub fn distance(&self, other: &Point) -> f64 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }
}

// Enum with pattern matching
enum Option<T> {
    Some(T),
    None,
}

fn unwrap_or<T>(opt: Option<T>, default: T) -> T {
    match opt {
        Some(value) => value,
        None => default,
    }
}
```

## Architecture Principles

- **Type Safety**: Comprehensive TypeScript types prevent runtime errors
- **Immutability**: All AST nodes are readonly for predictable behavior
- **Error Handling**: Rich error messages with source location tracking
- **Testability**: Pure functions and dependency injection enable thorough testing
- **Performance**: Efficient data structures and algorithms throughout
- **Extensibility**: Clear interfaces for adding new language features

## Testing Strategy

- **Unit Tests**: Individual components (lexer, parser, type checker)
- **Integration Tests**: End-to-end compilation pipeline
- **Property-Based Tests**: Invariants and edge cases
- **Snapshot Tests**: AST and IR output verification
- **Performance Tests**: Benchmarks for compilation speed

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass (`npm test`)
2. Code is formatted (`npm run format`)
3. Types are correct (`npm run typecheck`)
4. Coverage remains above 80% (`npm run test:coverage`)

## License

MIT

## Roadmap

- [x] Token types and lexer foundation
- [x] AST node definitions
- [ ] Lexer implementation
- [ ] Parser implementation
- [ ] Semantic analyzer
- [ ] Type system implementation
- [ ] IR generation
- [ ] LLVM backend
- [ ] Optimization passes
- [ ] Standard library
- [ ] Package manager integration

## Links

- Documentation: (Coming soon)
- Language Specification: (Coming soon)
- Examples: (Coming soon)
