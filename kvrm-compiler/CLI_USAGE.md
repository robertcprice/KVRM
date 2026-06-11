# KVRM Compiler CLI

Professional command-line interface for the KVRM language compiler.

## Installation

```bash
npm install -g @kvrm/compiler
```

Or run locally:

```bash
npm install
npm run build
node dist/cli.js --help
```

## Commands

### `kvrmc compile <file>`

Compile KVRM source code to assembly.

```bash
kvrmc compile program.kv
kvrmc compile program.kv -o output.asm
kvrmc compile program.kv -O --emit-ir --emit-ast -v
```

**Options:**
- `-o, --output <file>` - Output file path (default: `<input>.asm`)
- `-O, --optimize` - Enable optimizations
- `--emit-ir` - Also emit IR to `<output>.ir`
- `--emit-ast` - Also emit AST to `<output>.ast.json`
- `-v, --verbose` - Verbose output with compilation stages
- `--no-color` - Disable colored output

**Example output:**
```
Compiling program.kv...
  Lexing: ✓ 342 tokens
  Parsing: ✓
  Type checking: ✓
  IR generation: ✓
  Code generation: ✓
Written to program.asm (1.2KB)
```

### `kvrmc check <file>`

Type check KVRM source code without generating output.

```bash
kvrmc check program.kv
kvrmc check program.kv -v
```

**Options:**
- `-v, --verbose` - Verbose output
- `--no-color` - Disable colored output

**Example output:**
```
Checking program.kv...
  Lexing: ✓ 342 tokens
  Parsing: ✓
  Type checking: ✓
✓ No errors found
```

### `kvrmc parse <file>`

Parse KVRM source code and display AST.

```bash
kvrmc parse program.kv
kvrmc parse program.kv -o ast.json
```

**Options:**
- `-o, --output <file>` - Output AST to file
- `-v, --verbose` - Verbose output
- `--no-color` - Disable colored output

### `kvrmc lex <file>`

Tokenize KVRM source code and display tokens.

```bash
kvrmc lex program.kv
kvrmc lex program.kv -o tokens.txt
```

**Options:**
- `-o, --output <file>` - Output tokens to file
- `-v, --verbose` - Verbose output
- `--no-color` - Disable colored output

**Example output:**
```
Tokenizing program.kv...
Total tokens: 34

Line  Col   Type                Value
------------------------------------------------------------
   1      0 FN                   fn
   1      3 IDENTIFIER           main
   1      7 LPAREN               (
   1      8 RPAREN               )
   1     10 LBRACE               {
...
✓ 34 tokens
```

### `kvrmc ir <file>`

Generate and display intermediate representation.

```bash
kvrmc ir program.kv
kvrmc ir program.kv -o program.ir
kvrmc ir program.kv -O
```

**Options:**
- `-o, --output <file>` - Output IR to file
- `-O, --optimize` - Enable optimizations
- `-v, --verbose` - Verbose output
- `--no-color` - Disable colored output

## Error Reporting

The compiler provides rich, colorized error messages with source context:

```
error[E0001]: type mismatch
  --> program.kv:10:5
   |
10 |     let x: i32 = "hello";
   |                  ^^^^^^^ expected `i32`, found `str`
   |
   help: try converting the string to a number

1 error
```

## Diagnostic Codes

### Lexer Errors (L000-L999)
- `L001` - Unterminated string literal
- `L002` - Invalid number format
- `L003` - Unexpected character
- `L004` - Invalid escape sequence

### Parser Errors (P000-P999)
- `P001` - Unexpected token
- `P002` - Expected token
- `P003` - Invalid syntax
- `P004` - Unclosed delimiter

### Semantic Errors (S000-S999)
- `S001` - Type mismatch
- `S002` - Undefined variable
- `S003` - Duplicate declaration
- `S004` - Invalid operation
- `S005` - Immutable assignment
- `S006` - Return type mismatch

### Codegen Errors (C000-C999)
- `C001` - Unsupported feature
- `C002` - Code generation failed

## Programmatic Usage

```typescript
import { compile, check, Compiler } from '@kvrm/compiler';

// Quick compilation
const result = compile('fn main() { return 42; }');
if (result.success) {
  console.log(result.output);
}

// Type checking
const checkResult = check('fn main() { return 42; }');
console.log(checkResult.success); // true

// Advanced usage
const compiler = new Compiler({
  filename: 'program.kv',
  optimize: true,
  emitIR: true,
  verbose: true,
  color: true,
});

const result = compiler.compile(source);
console.log(result.diagnostics.format());
console.log(result.stats);
```

## Library API

```typescript
// Compiler
class Compiler {
  constructor(options?: CompileOptions);
  compile(source: string): CompileResult;
  check(source: string): CompileResult;
  parseOnly(source: string): CompileResult;
  lexOnly(source: string): CompileResult;
}

// Convenience functions
function compile(source: string, options?: CompileOptions): CompileResult;
function check(source: string, options?: CompileOptions): CompileResult;

// Diagnostics
class DiagnosticReporter {
  error(code: DiagnosticCode, message: string, span?: SourceSpan, hint?: string): void;
  warning(code: DiagnosticCode, message: string, span?: SourceSpan, hint?: string): void;
  hasErrors(): boolean;
  format(): string;
}

// Lexer
class Lexer {
  constructor(source: string, file?: string);
  tokenize(): Token[];
}
```

## Exit Codes

- `0` - Success
- `1` - Compilation/check failed with errors

## Environment

- Node.js ≥18.0.0
- TypeScript support with full type definitions

## Examples

### Basic Compilation
```bash
# Compile a simple program
echo 'fn main() { return 42; }' > hello.kv
kvrmc compile hello.kv
```

### Optimized Build
```bash
# Compile with optimizations and full output
kvrmc compile program.kv -O -v --emit-ir --emit-ast -o release.asm
```

### CI/CD Integration
```bash
# Type check in CI
kvrmc check src/**/*.kv || exit 1

# Compile with strict error checking
kvrmc compile main.kv --no-color || exit 1
```

### Watch Mode (with external tool)
```bash
# Use with nodemon for auto-recompilation
nodemon --watch src --ext kv --exec "kvrmc compile src/main.kv"
```

## Performance

The compiler is designed for production use:

- **Fast lexing**: ~1M tokens/sec
- **Efficient parsing**: Single-pass with error recovery
- **Incremental compilation**: Planned for future releases
- **Parallel processing**: Multi-file compilation support

## Support

- Issues: https://github.com/your-org/kvrm-compiler/issues
- Docs: https://kvrm-lang.org/docs
- Discord: https://discord.gg/kvrm-lang
