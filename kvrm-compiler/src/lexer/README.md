# KVRM Compiler Lexer

Production-quality lexical analyzer for the KVRM programming language with Rust-like syntax.

## Features

### Language Support
- **Rust-like syntax**: Keywords (`fn`, `let`, `mut`, `struct`, `enum`, `impl`, `trait`)
- **Lifetime annotations**: `'a`, `'static`, `'lifetime123`
- **Modern operators**: Arithmetic, comparison, logical, bitwise, and assignment operators
- **Type annotations**: Colon syntax (`let x: i32 = 5`)
- **Generics**: Angle bracket syntax (`Vec<T>`, `Option<'a, T>`)

### Literals
- **Integers**: Decimal (`42`), hex (`0xFF`), binary (`0b1010`)
- **Floats**: Standard (`3.14`), scientific notation (`1.5e-10`)
- **Strings**: Double-quoted with escape sequences (`"\n"`, `"\u{1F680}"`)
- **Characters**: Single-quoted with escapes (`'a'`, `'\n'`)
- **Booleans**: `true`, `false`
- **Null**: `null`

### Comments
- **Line comments**: `// comment`
- **Block comments**: `/* comment */` with nesting support

### Error Handling
- **Detailed errors**: Line, column, and offset information
- **Descriptive messages**: Clear error descriptions with Unicode code points
- **Unterminated literals**: Catches unclosed strings, chars, and comments

## Usage

### Basic Example

```typescript
import { Lexer } from './lexer';

const source = `
fn add(x: i32, y: i32) -> i32 {
    return x + y;
}
`;

const lexer = new Lexer(source, 'example.kvrm');
const tokens = lexer.tokenize();

tokens.forEach(token => {
    console.log(`${token.type}: ${token.value} at ${token.location.line}:${token.location.column}`);
});
```

### Peek Operations

```typescript
const lexer = new Lexer('let x = 5');

// Peek at next token without consuming
const next = lexer.peek();
console.log(next?.type); // TokenType.LET

// Peek ahead 3 tokens
const third = lexer.peekAhead(3);
console.log(third?.type); // TokenType.ASSIGN
```

### Error Handling

```typescript
import { Lexer, LexerError } from './lexer';

const lexer = new Lexer('"unterminated string');

try {
    const tokens = lexer.tokenize();
} catch (e) {
    if (e instanceof LexerError) {
        console.error(`Error at ${e.line}:${e.column}: ${e.message}`);
    }
}
```

## Architecture

### Main Components

1. **Lexer** (`lexer.ts`): Main tokenization engine
   - Character scanning with lookahead
   - Multi-character operator recognition
   - Comment skipping (line and block with nesting)
   - Position tracking (line, column, offset)

2. **Token** (`../types/tokens.ts`): Token representation
   - Immutable token objects
   - Source location metadata
   - Type and value information

3. **TokenType** (`../types/tokens.ts`): Comprehensive token enumeration
   - Keywords (25+ language keywords)
   - Operators (50+ operators)
   - Delimiters and punctuation
   - Special tokens (EOF, NEWLINE, LIFETIME)

### Scan Methods

- `scanToken()`: Main dispatch method
- `scanNumber()`: Integer and float literals with special bases
- `scanHexNumber()`: Hexadecimal literals (0x...)
- `scanBinaryNumber()`: Binary literals (0b...)
- `scanString()`: String literals with escape sequences
- `scanIdentifier()`: Identifiers and keywords
- `scanLifetimeOrChar()`: Lifetime annotations and character literals

### Character Classification

- `isDigit()`: Decimal digits
- `isHexDigit()`: Hexadecimal digits
- `isBinaryDigit()`: Binary digits
- `isAlpha()`: Alphabetic characters and underscore
- `isAlphaNumeric()`: Alphanumeric characters

## Token Types

### Keywords
```typescript
FN, LET, MUT, IF, ELSE, WHILE, FOR, IN, RETURN, BREAK, CONTINUE,
MATCH, STRUCT, ENUM, IMPL, TRAIT, TYPE, AS, USE, MOD, PUB,
SELF, SUPER, CONST, STATIC, TRUE, FALSE, NULL
```

### Operators
```typescript
// Arithmetic
PLUS, MINUS, STAR, SLASH, PERCENT, POWER

// Comparison
EQ, NE, LT, GT, LE, GE

// Logical
AND, OR, NOT

// Bitwise
BIT_AND, BIT_OR, BIT_XOR, BIT_NOT, LEFT_SHIFT, RIGHT_SHIFT

// Assignment
ASSIGN, PLUS_ASSIGN, MINUS_ASSIGN, STAR_ASSIGN, SLASH_ASSIGN,
PERCENT_ASSIGN, BIT_AND_ASSIGN, BIT_OR_ASSIGN, BIT_XOR_ASSIGN,
LEFT_SHIFT_ASSIGN, RIGHT_SHIFT_ASSIGN
```

### Punctuation
```typescript
COMMA, SEMICOLON, COLON, DOUBLE_COLON, ARROW, FAT_ARROW,
DOT, DOUBLE_DOT, TRIPLE_DOT, QUESTION, AT, HASH, DOLLAR, UNDERSCORE
```

## Performance

- **Efficient scanning**: Single-pass tokenization
- **Lookahead caching**: State-based peek operations
- **Zero-copy where possible**: String slicing instead of copying
- **Minimal allocations**: Reuse of internal buffers

## Testing

Run the test suite:

```bash
npm test tests/lexer.test.ts
```

Run the demonstration:

```bash
npx tsx examples/lexer-demo.ts
```

## Design Decisions

### Why Rust-like Syntax?
- Strong type system with explicit annotations
- Modern language features (generics, lifetimes)
- Clear ownership semantics
- Industry-proven syntax

### Character Literal vs Lifetime Disambiguation
The lexer distinguishes between character literals and lifetime annotations:
- `'a` → Lifetime (followed by identifier characters)
- `'x'` → Character literal (single char in quotes)

### Comment Nesting
Block comments support nesting for better documentation:
```rust
/* outer /* nested */ still in comment */
```

### Error Recovery
The lexer uses precise error recovery:
- Restores line/column on unterminated constructs
- Provides Unicode code points for invalid characters
- Preserves context for error messages

## Future Enhancements

- [ ] Raw string literals (`r"..."`, `r#"..."#`)
- [ ] Byte literals (`b'x'`, `b"..."`)
- [ ] Doc comment support (`///`, `//!`, `/**`, `/*! */`)
- [ ] Macro support (`macro_rules!`)
- [ ] Attribute syntax (`#[...]`, `#![...]`)
- [ ] Unicode identifier support (XID_Start, XID_Continue)

## License

Part of the KVRM Compiler project.
