/**
 * Lexer demonstration
 * Shows basic usage of the KVRM lexer
 */

import { Lexer, formatToken } from '../src/lexer';

const sampleCode = `
// Simple function with Rust-like syntax
fn add<'a, T>(x: &'a T, y: T) -> T {
    let mut sum = x + y;
    sum += 10;
    return sum;
}

// Numeric literals
let hex = 0xFF;
let bin = 0b1010;
let float = 3.14;
let sci = 1.5e-10;

// Strings and chars
let str = "Hello, World!\\n";
let emoji = "\\u{1F680}";
let ch = 'x';

// Lifetime annotation
'static 'a 'lifetime123
`;

console.log('KVRM Lexer Demonstration\n========================\n');

const lexer = new Lexer(sampleCode, 'lexer-demo.kvrm');
const tokens = lexer.tokenize();

console.log(`Total tokens: ${tokens.length}\n`);

// Display first 30 tokens
tokens.slice(0, 30).forEach((token, index) => {
  console.log(`${(index + 1).toString().padStart(2)}. ${formatToken(token)}`);
});

if (tokens.length > 30) {
  console.log(`\n... and ${tokens.length - 30} more tokens`);
}

console.log('\n\nTesting error handling:\n----------------------\n');

try {
  const badLexer = new Lexer('"unterminated string');
  badLexer.tokenize();
} catch (e) {
  console.log('Error caught:', e.message);
}

try {
  const badLexer2 = new Lexer('0xGGG');
  badLexer2.tokenize();
} catch (e) {
  console.log('Error caught:', e.message);
}

console.log('\n\nDone!');
