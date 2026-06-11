/**
 * KVRM Compiler Lexer Module
 * Exports lexer components for tokenization
 */

export { Lexer, LexerError } from './lexer.js';

// Re-export token types and utilities from types module
export type { Token, SourceLocation } from '../types/tokens.js';
export {
  TokenType,
  KEYWORDS,
  OPERATOR_PRECEDENCE,
  createToken,
  createLocation,
  formatToken,
  isKeyword,
  isLiteral,
  isBinaryOperator,
  isAssignmentOperator,
  isUnaryOperator,
  getPrecedence,
} from '../types/tokens.js';
