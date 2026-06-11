/**
 * Unit tests for token types and utilities.
 */

import { describe, it, expect } from 'vitest';
import {
  TokenType,
  KEYWORDS,
  OPERATOR_PRECEDENCE,
  isKeyword,
  isLiteral,
  isBinaryOperator,
  isAssignmentOperator,
  isUnaryOperator,
  getPrecedence,
  createToken,
  createLocation,
  formatToken,
  type Token,
} from '../src/types/tokens.js';

describe('TokenType', () => {
  it('should have all expected keyword types', () => {
    const keywords = [
      TokenType.FN,
      TokenType.LET,
      TokenType.MUT,
      TokenType.IF,
      TokenType.ELSE,
      TokenType.WHILE,
      TokenType.FOR,
      TokenType.RETURN,
      TokenType.STRUCT,
      TokenType.ENUM,
      TokenType.IMPL,
      TokenType.TRAIT,
    ];

    keywords.forEach((keyword) => {
      expect(keyword).toBeDefined();
    });
  });

  it('should have all expected operator types', () => {
    const operators = [
      TokenType.PLUS,
      TokenType.MINUS,
      TokenType.STAR,
      TokenType.SLASH,
      TokenType.EQ,
      TokenType.NE,
      TokenType.LT,
      TokenType.GT,
      TokenType.AND,
      TokenType.OR,
    ];

    operators.forEach((operator) => {
      expect(operator).toBeDefined();
    });
  });
});

describe('KEYWORDS', () => {
  it('should map keyword strings to token types', () => {
    expect(KEYWORDS.get('fn')).toBe(TokenType.FN);
    expect(KEYWORDS.get('let')).toBe(TokenType.LET);
    expect(KEYWORDS.get('mut')).toBe(TokenType.MUT);
    expect(KEYWORDS.get('if')).toBe(TokenType.IF);
    expect(KEYWORDS.get('struct')).toBe(TokenType.STRUCT);
  });

  it('should not have entries for non-keywords', () => {
    expect(KEYWORDS.get('foo')).toBeUndefined();
    expect(KEYWORDS.get('bar')).toBeUndefined();
    expect(KEYWORDS.get('123')).toBeUndefined();
  });

  it('should be case-sensitive', () => {
    expect(KEYWORDS.get('fn')).toBe(TokenType.FN);
    expect(KEYWORDS.get('FN')).toBeUndefined();
    expect(KEYWORDS.get('Fn')).toBeUndefined();
  });
});

describe('OPERATOR_PRECEDENCE', () => {
  it('should assign correct precedence levels', () => {
    expect(OPERATOR_PRECEDENCE.get(TokenType.ASSIGN)).toBe(1);
    expect(OPERATOR_PRECEDENCE.get(TokenType.OR)).toBe(2);
    expect(OPERATOR_PRECEDENCE.get(TokenType.AND)).toBe(3);
    expect(OPERATOR_PRECEDENCE.get(TokenType.EQ)).toBe(7);
    expect(OPERATOR_PRECEDENCE.get(TokenType.PLUS)).toBe(10);
    expect(OPERATOR_PRECEDENCE.get(TokenType.STAR)).toBe(11);
    expect(OPERATOR_PRECEDENCE.get(TokenType.POWER)).toBe(12);
  });

  it('should give multiplication higher precedence than addition', () => {
    const addPrec = OPERATOR_PRECEDENCE.get(TokenType.PLUS)!;
    const mulPrec = OPERATOR_PRECEDENCE.get(TokenType.STAR)!;
    expect(mulPrec).toBeGreaterThan(addPrec);
  });

  it('should give logical AND higher precedence than OR', () => {
    const orPrec = OPERATOR_PRECEDENCE.get(TokenType.OR)!;
    const andPrec = OPERATOR_PRECEDENCE.get(TokenType.AND)!;
    expect(andPrec).toBeGreaterThan(orPrec);
  });
});

describe('isKeyword', () => {
  it('should return true for keyword tokens', () => {
    const loc = createLocation(0, 1, 1, 2);
    expect(isKeyword(createToken(TokenType.FN, 'fn', loc))).toBe(true);
    expect(isKeyword(createToken(TokenType.LET, 'let', loc))).toBe(true);
    expect(isKeyword(createToken(TokenType.IF, 'if', loc))).toBe(true);
  });

  it('should return false for non-keyword tokens', () => {
    const loc = createLocation(0, 1, 1, 3);
    expect(isKeyword(createToken(TokenType.IDENTIFIER, 'foo', loc))).toBe(false);
    expect(isKeyword(createToken(TokenType.NUMBER, '123', loc))).toBe(false);
    expect(isKeyword(createToken(TokenType.PLUS, '+', loc))).toBe(false);
  });
});

describe('isLiteral', () => {
  it('should return true for literal tokens', () => {
    const loc = createLocation(0, 1, 1, 3);
    expect(isLiteral(createToken(TokenType.NUMBER, '123', loc))).toBe(true);
    expect(isLiteral(createToken(TokenType.STRING, '"hello"', loc))).toBe(true);
    expect(isLiteral(createToken(TokenType.CHAR, "'a'", loc))).toBe(true);
    expect(isLiteral(createToken(TokenType.TRUE, 'true', loc))).toBe(true);
    expect(isLiteral(createToken(TokenType.FALSE, 'false', loc))).toBe(true);
    expect(isLiteral(createToken(TokenType.NULL, 'null', loc))).toBe(true);
  });

  it('should return false for non-literal tokens', () => {
    const loc = createLocation(0, 1, 1, 3);
    expect(isLiteral(createToken(TokenType.IDENTIFIER, 'foo', loc))).toBe(false);
    expect(isLiteral(createToken(TokenType.PLUS, '+', loc))).toBe(false);
  });
});

describe('isBinaryOperator', () => {
  it('should return true for binary operator tokens', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(isBinaryOperator(createToken(TokenType.PLUS, '+', loc))).toBe(true);
    expect(isBinaryOperator(createToken(TokenType.MINUS, '-', loc))).toBe(true);
    expect(isBinaryOperator(createToken(TokenType.STAR, '*', loc))).toBe(true);
    expect(isBinaryOperator(createToken(TokenType.EQ, '==', loc))).toBe(true);
    expect(isBinaryOperator(createToken(TokenType.AND, '&&', loc))).toBe(true);
  });

  it('should return false for non-operator tokens', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(isBinaryOperator(createToken(TokenType.IDENTIFIER, 'x', loc))).toBe(false);
    expect(isBinaryOperator(createToken(TokenType.NUMBER, '1', loc))).toBe(false);
  });
});

describe('isAssignmentOperator', () => {
  it('should return true for assignment operator tokens', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(isAssignmentOperator(createToken(TokenType.ASSIGN, '=', loc))).toBe(true);
    expect(isAssignmentOperator(createToken(TokenType.PLUS_ASSIGN, '+=', loc))).toBe(true);
    expect(isAssignmentOperator(createToken(TokenType.MINUS_ASSIGN, '-=', loc))).toBe(true);
  });

  it('should return false for non-assignment tokens', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(isAssignmentOperator(createToken(TokenType.PLUS, '+', loc))).toBe(false);
    expect(isAssignmentOperator(createToken(TokenType.EQ, '==', loc))).toBe(false);
  });
});

describe('isUnaryOperator', () => {
  it('should return true for unary operator tokens', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(isUnaryOperator(createToken(TokenType.NOT, '!', loc))).toBe(true);
    expect(isUnaryOperator(createToken(TokenType.MINUS, '-', loc))).toBe(true);
    expect(isUnaryOperator(createToken(TokenType.BIT_NOT, '~', loc))).toBe(true);
  });

  it('should handle operators that can be both unary and binary', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(isUnaryOperator(createToken(TokenType.MINUS, '-', loc))).toBe(true);
    expect(isBinaryOperator(createToken(TokenType.MINUS, '-', loc))).toBe(true);
  });
});

describe('getPrecedence', () => {
  it('should return correct precedence for operators', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(getPrecedence(createToken(TokenType.PLUS, '+', loc))).toBe(10);
    expect(getPrecedence(createToken(TokenType.STAR, '*', loc))).toBe(11);
    expect(getPrecedence(createToken(TokenType.OR, '||', loc))).toBe(2);
  });

  it('should return 0 for non-operators', () => {
    const loc = createLocation(0, 1, 1, 1);
    expect(getPrecedence(createToken(TokenType.IDENTIFIER, 'x', loc))).toBe(0);
    expect(getPrecedence(createToken(TokenType.NUMBER, '42', loc))).toBe(0);
  });
});

describe('createToken', () => {
  it('should create a valid token', () => {
    const loc = createLocation(0, 1, 1, 2);
    const token = createToken(TokenType.FN, 'fn', loc);

    expect(token.type).toBe(TokenType.FN);
    expect(token.value).toBe('fn');
    expect(token.location).toBe(loc);
  });

  it('should create immutable tokens', () => {
    const loc = createLocation(0, 1, 1, 2);
    const token = createToken(TokenType.FN, 'fn', loc);

    expect(Object.isFrozen(token)).toBe(true);
  });
});

describe('createLocation', () => {
  it('should create a valid location', () => {
    const loc = createLocation(10, 2, 5, 3);

    expect(loc.offset).toBe(10);
    expect(loc.line).toBe(2);
    expect(loc.column).toBe(5);
    expect(loc.length).toBe(3);
    expect(loc.file).toBeUndefined();
  });

  it('should include file path when provided', () => {
    const loc = createLocation(10, 2, 5, 3, 'test.kvrm');

    expect(loc.file).toBe('test.kvrm');
  });

  it('should create immutable locations', () => {
    const loc = createLocation(0, 1, 1, 1);

    expect(Object.isFrozen(loc)).toBe(true);
  });
});

describe('formatToken', () => {
  it('should format token without file path', () => {
    const loc = createLocation(0, 2, 5, 2);
    const token = createToken(TokenType.FN, 'fn', loc);

    expect(formatToken(token)).toBe("FN('fn') at 2:5");
  });

  it('should format token with file path', () => {
    const loc = createLocation(0, 2, 5, 2, 'test.kvrm');
    const token = createToken(TokenType.FN, 'fn', loc);

    expect(formatToken(token)).toBe("FN('fn') at test.kvrm:2:5");
  });

  it('should format tokens with different types', () => {
    const loc = createLocation(0, 1, 1, 3);

    expect(formatToken(createToken(TokenType.NUMBER, '123', loc))).toBe("NUMBER('123') at 1:1");
    expect(formatToken(createToken(TokenType.STRING, '"hi"', loc))).toBe('STRING(\'"hi"\') at 1:1');
    expect(formatToken(createToken(TokenType.PLUS, '+', loc))).toBe("PLUS('+') at 1:1");
  });
});
