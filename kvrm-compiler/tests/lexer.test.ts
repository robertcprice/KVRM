/**
 * Lexer Tests for KVRM Compiler
 *
 * Comprehensive test suite covering:
 * - Keyword tokenization
 * - Operator tokenization
 * - Literal tokenization (numbers, strings, booleans)
 * - Comment handling
 * - Error cases
 * - Edge cases and boundary conditions
 */

import { describe, it, expect } from 'vitest';
import { TokenType } from '../src/types/tokens';

// Mock Lexer interface - replace with actual import when implemented
interface Lexer {
  nextToken(): { type: TokenType; value: string; line: number; column: number };
  peek(): { type: TokenType; value: string };
  hasNext(): boolean;
  reset(): void;
}

// Placeholder - replace with actual Lexer import
// import { Lexer } from '../src/lexer';
class MockLexer implements Lexer {
  nextToken() {
    return { type: TokenType.Eof, value: '', line: 1, column: 1 };
  }
  peek() {
    return { type: TokenType.Eof, value: '' };
  }
  hasNext() {
    return false;
  }
  reset() {}
}

const createLexer = (input: string): Lexer => {
  // Replace with: return new Lexer(input);
  return new MockLexer();
};

describe('Lexer - Keywords', () => {
  it('should tokenize function keyword', () => {
    const lexer = createLexer('fn');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.Fn);
    expect(token.value).toBe('fn');
  });

  it('should tokenize variable declaration keywords', () => {
    const lexer = createLexer('let mut');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    expect(lexer.nextToken().type).toBe(TokenType.Mut);
  });

  it('should tokenize control flow keywords', () => {
    const lexer = createLexer('if else while for return');
    expect(lexer.nextToken().type).toBe(TokenType.If);
    expect(lexer.nextToken().type).toBe(TokenType.Else);
    expect(lexer.nextToken().type).toBe(TokenType.While);
    expect(lexer.nextToken().type).toBe(TokenType.For);
    expect(lexer.nextToken().type).toBe(TokenType.Return);
  });

  it('should tokenize type definition keywords', () => {
    const lexer = createLexer('struct enum impl trait');
    expect(lexer.nextToken().type).toBe(TokenType.Struct);
    expect(lexer.nextToken().type).toBe(TokenType.Enum);
    expect(lexer.nextToken().type).toBe(TokenType.Impl);
    expect(lexer.nextToken().type).toBe(TokenType.Trait);
  });

  it('should tokenize module system keywords', () => {
    const lexer = createLexer('use mod pub');
    expect(lexer.nextToken().type).toBe(TokenType.Use);
    expect(lexer.nextToken().type).toBe(TokenType.Mod);
    expect(lexer.nextToken().type).toBe(TokenType.Pub);
  });

  it('should tokenize self keyword', () => {
    const lexer = createLexer('self');
    expect(lexer.nextToken().type).toBe(TokenType.Self);
  });

  it('should tokenize boolean literals', () => {
    const lexer = createLexer('true false');
    expect(lexer.nextToken().type).toBe(TokenType.True);
    expect(lexer.nextToken().type).toBe(TokenType.False);
  });

  it('should tokenize null keyword', () => {
    const lexer = createLexer('null');
    expect(lexer.nextToken().type).toBe(TokenType.Null);
  });

  it('should distinguish keywords from identifiers', () => {
    const lexer = createLexer('fn function lets if_stmt');
    expect(lexer.nextToken().type).toBe(TokenType.Fn);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
  });
});

describe('Lexer - Operators', () => {
  it('should tokenize arithmetic operators', () => {
    const lexer = createLexer('+ - * / %');
    expect(lexer.nextToken().type).toBe(TokenType.Plus);
    expect(lexer.nextToken().type).toBe(TokenType.Minus);
    expect(lexer.nextToken().type).toBe(TokenType.Star);
    expect(lexer.nextToken().type).toBe(TokenType.Slash);
    expect(lexer.nextToken().type).toBe(TokenType.Percent);
  });

  it('should tokenize comparison operators', () => {
    const lexer = createLexer('== != < <= > >=');
    expect(lexer.nextToken().type).toBe(TokenType.Eq);
    expect(lexer.nextToken().type).toBe(TokenType.Ne);
    expect(lexer.nextToken().type).toBe(TokenType.Lt);
    expect(lexer.nextToken().type).toBe(TokenType.Le);
    expect(lexer.nextToken().type).toBe(TokenType.Gt);
    expect(lexer.nextToken().type).toBe(TokenType.Ge);
  });

  it('should tokenize logical operators', () => {
    const lexer = createLexer('&& || !');
    expect(lexer.nextToken().type).toBe(TokenType.And);
    expect(lexer.nextToken().type).toBe(TokenType.Or);
    expect(lexer.nextToken().type).toBe(TokenType.Not);
  });

  it('should tokenize assignment operators', () => {
    const lexer = createLexer('= += -=');
    expect(lexer.nextToken().type).toBe(TokenType.Assign);
    expect(lexer.nextToken().type).toBe(TokenType.PlusAssign);
    expect(lexer.nextToken().type).toBe(TokenType.MinusAssign);
  });

  it('should tokenize arrow operators', () => {
    const lexer = createLexer('-> =>');
    expect(lexer.nextToken().type).toBe(TokenType.Arrow);
    expect(lexer.nextToken().type).toBe(TokenType.FatArrow);
  });

  it('should distinguish single vs double character operators', () => {
    const lexer = createLexer('= == ! != < <= > >=');
    expect(lexer.nextToken().type).toBe(TokenType.Assign);
    expect(lexer.nextToken().type).toBe(TokenType.Eq);
    expect(lexer.nextToken().type).toBe(TokenType.Not);
    expect(lexer.nextToken().type).toBe(TokenType.Ne);
    expect(lexer.nextToken().type).toBe(TokenType.Lt);
    expect(lexer.nextToken().type).toBe(TokenType.Le);
    expect(lexer.nextToken().type).toBe(TokenType.Gt);
    expect(lexer.nextToken().type).toBe(TokenType.Ge);
  });
});

describe('Lexer - Numbers', () => {
  it('should tokenize decimal integers', () => {
    const lexer = createLexer('0 42 123 999');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toBe('0');

    const token2 = lexer.nextToken();
    expect(token2.type).toBe(TokenType.Number);
    expect(token2.value).toBe('42');
  });

  it('should tokenize floating point numbers', () => {
    const lexer = createLexer('3.14 0.5 42.0');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toBe('3.14');

    const token2 = lexer.nextToken();
    expect(token2.type).toBe(TokenType.Number);
    expect(token2.value).toBe('0.5');
  });

  it('should tokenize hexadecimal numbers', () => {
    const lexer = createLexer('0x1A 0xFF 0x00');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toBe('0x1A');
  });

  it('should tokenize binary numbers', () => {
    const lexer = createLexer('0b1010 0b0 0b11111111');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toBe('0b1010');
  });

  it('should tokenize octal numbers', () => {
    const lexer = createLexer('0o777 0o644 0o0');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toBe('0o777');
  });

  it('should handle underscores in numbers', () => {
    const lexer = createLexer('1_000_000 3.14_159 0xFF_FF');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toMatch(/1[_0]*/);
  });

  it('should tokenize scientific notation', () => {
    const lexer = createLexer('1e10 3.14e-5 2.5E+3');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
    expect(token1.value).toMatch(/1e10/i);
  });
});

describe('Lexer - Strings', () => {
  it('should tokenize simple strings', () => {
    const lexer = createLexer('"hello" "world"');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.String);
    expect(token1.value).toBe('hello');
  });

  it('should tokenize empty strings', () => {
    const lexer = createLexer('""');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.String);
    expect(token.value).toBe('');
  });

  it('should handle escape sequences', () => {
    const lexer = createLexer('"hello\\nworld"');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.String);
    expect(token.value).toContain('\\n');
  });

  it('should handle common escape sequences', () => {
    const lexer = createLexer('"\\t\\r\\n\\\\ \\""');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.String);
    expect(token.value).toMatch(/\\[trn\\"]/);
  });

  it('should handle unicode escape sequences', () => {
    const lexer = createLexer('"\\u{1F600}"');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.String);
  });

  it('should handle multiline strings with escape', () => {
    const lexer = createLexer('"line1\\\nline2"');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.String);
  });
});

describe('Lexer - Identifiers', () => {
  it('should tokenize simple identifiers', () => {
    const lexer = createLexer('foo bar baz');
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
  });

  it('should tokenize identifiers with underscores', () => {
    const lexer = createLexer('_private my_var __internal');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Identifier);
    expect(token1.value).toBe('_private');
  });

  it('should tokenize identifiers with numbers', () => {
    const lexer = createLexer('var1 var2test value123');
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
  });

  it('should not allow identifiers starting with numbers', () => {
    const lexer = createLexer('123var');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Number);
  });

  it('should handle camelCase and snake_case', () => {
    const lexer = createLexer('camelCase snake_case PascalCase');
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
  });
});

describe('Lexer - Delimiters', () => {
  it('should tokenize parentheses', () => {
    const lexer = createLexer('( )');
    expect(lexer.nextToken().type).toBe(TokenType.LParen);
    expect(lexer.nextToken().type).toBe(TokenType.RParen);
  });

  it('should tokenize braces', () => {
    const lexer = createLexer('{ }');
    expect(lexer.nextToken().type).toBe(TokenType.LBrace);
    expect(lexer.nextToken().type).toBe(TokenType.RBrace);
  });

  it('should tokenize brackets', () => {
    const lexer = createLexer('[ ]');
    expect(lexer.nextToken().type).toBe(TokenType.LBracket);
    expect(lexer.nextToken().type).toBe(TokenType.RBracket);
  });

  it('should tokenize angle brackets', () => {
    const lexer = createLexer('< >');
    expect(lexer.nextToken().type).toBe(TokenType.Lt);
    expect(lexer.nextToken().type).toBe(TokenType.Gt);
  });
});

describe('Lexer - Punctuation', () => {
  it('should tokenize comma', () => {
    const lexer = createLexer(',');
    expect(lexer.nextToken().type).toBe(TokenType.Comma);
  });

  it('should tokenize semicolon', () => {
    const lexer = createLexer(';');
    expect(lexer.nextToken().type).toBe(TokenType.Semicolon);
  });

  it('should tokenize colon', () => {
    const lexer = createLexer(':');
    expect(lexer.nextToken().type).toBe(TokenType.Colon);
  });

  it('should tokenize double colon', () => {
    const lexer = createLexer('::');
    expect(lexer.nextToken().type).toBe(TokenType.DoubleColon);
  });

  it('should tokenize dot', () => {
    const lexer = createLexer('.');
    expect(lexer.nextToken().type).toBe(TokenType.Dot);
  });

  it('should tokenize ampersand', () => {
    const lexer = createLexer('&');
    expect(lexer.nextToken().type).toBe(TokenType.Ampersand);
  });

  it('should tokenize question mark', () => {
    const lexer = createLexer('?');
    expect(lexer.nextToken().type).toBe(TokenType.Question);
  });
});

describe('Lexer - Comments', () => {
  it('should skip single-line comments', () => {
    const lexer = createLexer('let // this is a comment\nx');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    const next = lexer.nextToken();
    expect(next.type).toBe(TokenType.Identifier);
    expect(next.value).toBe('x');
  });

  it('should skip multi-line comments', () => {
    const lexer = createLexer('let /* comment */ x');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    const next = lexer.nextToken();
    expect(next.type).toBe(TokenType.Identifier);
    expect(next.value).toBe('x');
  });

  it('should handle nested multi-line comments', () => {
    const lexer = createLexer('let /* outer /* inner */ outer */ x');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    const next = lexer.nextToken();
    expect(next.type).toBe(TokenType.Identifier);
    expect(next.value).toBe('x');
  });

  it('should handle comment at end of file', () => {
    const lexer = createLexer('let x // comment');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Eof);
  });

  it('should preserve line numbers across comments', () => {
    const lexer = createLexer('let\n// comment\nx');
    const token1 = lexer.nextToken();
    expect(token1.line).toBe(1);
    const token2 = lexer.nextToken();
    expect(token2.line).toBe(3);
  });
});

describe('Lexer - Lifetimes', () => {
  it('should tokenize lifetime annotations', () => {
    const lexer = createLexer("'a 'static 'lifetime");
    expect(lexer.nextToken().type).toBe(TokenType.Lifetime);
    expect(lexer.nextToken().type).toBe(TokenType.Lifetime);
    expect(lexer.nextToken().type).toBe(TokenType.Lifetime);
  });

  it('should distinguish lifetimes from character literals', () => {
    const lexer = createLexer("'a' 'b");
    const token1 = lexer.nextToken();
    // First should be char literal (if supported) or lifetime
    expect([TokenType.String, TokenType.Lifetime]).toContain(token1.type);
  });
});

describe('Lexer - Whitespace', () => {
  it('should skip spaces', () => {
    const lexer = createLexer('let   x   =   5');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Assign);
    expect(lexer.nextToken().type).toBe(TokenType.Number);
  });

  it('should skip tabs', () => {
    const lexer = createLexer('let\tx\t=\t5');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Assign);
    expect(lexer.nextToken().type).toBe(TokenType.Number);
  });

  it('should track line numbers with newlines', () => {
    const lexer = createLexer('let\nx\n=\n5');
    const token1 = lexer.nextToken();
    expect(token1.line).toBe(1);
    const token2 = lexer.nextToken();
    expect(token2.line).toBe(2);
    const token3 = lexer.nextToken();
    expect(token3.line).toBe(3);
    const token4 = lexer.nextToken();
    expect(token4.line).toBe(4);
  });

  it('should handle mixed whitespace', () => {
    const lexer = createLexer('  \t\n  let\n\t  x');
    const token1 = lexer.nextToken();
    expect(token1.type).toBe(TokenType.Let);
    const token2 = lexer.nextToken();
    expect(token2.type).toBe(TokenType.Identifier);
  });
});

describe('Lexer - Source Location', () => {
  it('should track column numbers', () => {
    const lexer = createLexer('let x = 5');
    const token1 = lexer.nextToken();
    expect(token1.column).toBe(1);
    const token2 = lexer.nextToken();
    expect(token2.column).toBe(5);
    const token3 = lexer.nextToken();
    expect(token3.column).toBe(7);
  });

  it('should reset column on newline', () => {
    const lexer = createLexer('let\nx');
    const token1 = lexer.nextToken();
    expect(token1.line).toBe(1);
    expect(token1.column).toBe(1);
    const token2 = lexer.nextToken();
    expect(token2.line).toBe(2);
    expect(token2.column).toBe(1);
  });

  it('should provide accurate location for multi-character tokens', () => {
    const lexer = createLexer('==');
    const token = lexer.nextToken();
    expect(token.column).toBe(1);
  });
});

describe('Lexer - Error Handling', () => {
  it('should handle invalid characters', () => {
    const lexer = createLexer('let @x');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    // Next token should be an error or skip the invalid char
    const token = lexer.nextToken();
    expect(token).toBeDefined();
  });

  it('should handle unterminated strings', () => {
    const lexer = createLexer('"unterminated');
    const token = lexer.nextToken();
    // Should either be error token or EOF
    expect(token).toBeDefined();
  });

  it('should handle unterminated multi-line comment', () => {
    const lexer = createLexer('/* unterminated');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.Eof);
  });

  it('should handle invalid number formats', () => {
    const lexer = createLexer('0x 0b 0o');
    // Each should handle error gracefully
    expect(() => lexer.nextToken()).not.toThrow();
  });

  it('should handle invalid escape sequences', () => {
    const lexer = createLexer('"\\z"');
    const token = lexer.nextToken();
    expect(token.type).toBe(TokenType.String);
  });
});

describe('Lexer - Complex Expressions', () => {
  it('should tokenize variable declaration', () => {
    const lexer = createLexer('let x: i32 = 42;');
    expect(lexer.nextToken().type).toBe(TokenType.Let);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Colon);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Assign);
    expect(lexer.nextToken().type).toBe(TokenType.Number);
    expect(lexer.nextToken().type).toBe(TokenType.Semicolon);
  });

  it('should tokenize function signature', () => {
    const lexer = createLexer('fn add(a: i32, b: i32) -> i32');
    expect(lexer.nextToken().type).toBe(TokenType.Fn);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.LParen);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Colon);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Comma);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Colon);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.RParen);
    expect(lexer.nextToken().type).toBe(TokenType.Arrow);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
  });

  it('should tokenize struct definition', () => {
    const lexer = createLexer('struct Point { x: f32, y: f32 }');
    expect(lexer.nextToken().type).toBe(TokenType.Struct);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.LBrace);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Colon);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Comma);
  });

  it('should tokenize generic types', () => {
    const lexer = createLexer('Vec<i32>');
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Lt);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Gt);
  });

  it('should tokenize method calls', () => {
    const lexer = createLexer('obj.method()');
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.Dot);
    expect(lexer.nextToken().type).toBe(TokenType.Identifier);
    expect(lexer.nextToken().type).toBe(TokenType.LParen);
    expect(lexer.nextToken().type).toBe(TokenType.RParen);
  });

  it('should tokenize array literals', () => {
    const lexer = createLexer('[1, 2, 3]');
    expect(lexer.nextToken().type).toBe(TokenType.LBracket);
    expect(lexer.nextToken().type).toBe(TokenType.Number);
    expect(lexer.nextToken().type).toBe(TokenType.Comma);
    expect(lexer.nextToken().type).toBe(TokenType.Number);
    expect(lexer.nextToken().type).toBe(TokenType.Comma);
    expect(lexer.nextToken().type).toBe(TokenType.Number);
    expect(lexer.nextToken().type).toBe(TokenType.RBracket);
  });
});

describe('Lexer - EOF Handling', () => {
  it('should return EOF token at end', () => {
    const lexer = createLexer('let x');
    lexer.nextToken();
    lexer.nextToken();
    const eof = lexer.nextToken();
    expect(eof.type).toBe(TokenType.Eof);
  });

  it('should continue returning EOF', () => {
    const lexer = createLexer('x');
    lexer.nextToken();
    expect(lexer.nextToken().type).toBe(TokenType.Eof);
    expect(lexer.nextToken().type).toBe(TokenType.Eof);
    expect(lexer.nextToken().type).toBe(TokenType.Eof);
  });

  it('should handle empty input', () => {
    const lexer = createLexer('');
    expect(lexer.nextToken().type).toBe(TokenType.Eof);
  });

  it('should handle whitespace-only input', () => {
    const lexer = createLexer('   \n\t  ');
    expect(lexer.nextToken().type).toBe(TokenType.Eof);
  });
});

describe('Lexer - Peek and Lookahead', () => {
  it('should peek without consuming', () => {
    const lexer = createLexer('let x');
    const peeked = lexer.peek();
    expect(peeked.type).toBe(TokenType.Let);
    const consumed = lexer.nextToken();
    expect(consumed.type).toBe(TokenType.Let);
  });

  it('should peek consistently', () => {
    const lexer = createLexer('let x');
    expect(lexer.peek().type).toBe(TokenType.Let);
    expect(lexer.peek().type).toBe(TokenType.Let);
    expect(lexer.peek().type).toBe(TokenType.Let);
  });

  it('should hasNext return true when tokens remain', () => {
    const lexer = createLexer('let x');
    expect(lexer.hasNext()).toBe(true);
    lexer.nextToken();
    expect(lexer.hasNext()).toBe(true);
    lexer.nextToken();
    expect(lexer.hasNext()).toBe(false);
  });
});
