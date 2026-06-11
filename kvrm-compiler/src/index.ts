/**
 * KVRM Compiler Library
 * Public API for programmatic use
 */

// Core compiler exports
import { Compiler as CompilerClass } from './compiler.js';
export { Compiler } from './compiler.js';
export { compile, check } from './compiler.js';
export type {
  CompileOptions,
  CompileResult,
  CompileStats,
} from './compiler.js';

// Diagnostic system exports
export {
  DiagnosticReporter,
  createDiagnosticReporter,
  DiagnosticLevel,
  DiagnosticCode,
} from './utils/diagnostics.js';
export type {
  Diagnostic,
  DiagnosticOptions,
  SourceSpan,
} from './utils/diagnostics.js';

// Source mapping exports
export { SourceMap, createSourceMap } from './utils/source-map.js';
export type { SourceMapping } from './utils/source-map.js';

// Token system exports
export type { Token, SourceLocation } from './types/tokens.js';
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
} from './types/tokens.js';

// Lexer exports
export { Lexer, LexerError } from './lexer/index.js';

/**
 * Library version
 */
export const VERSION = '0.1.0';

/**
 * Quick compile helper with defaults
 */
export function quickCompile(source: string): string | null {
  const compiler = new CompilerClass({ color: false });
  const result = compiler.compile(source);
  return result.success ? result.output ?? null : null;
}

/**
 * Quick check helper
 */
export function quickCheck(source: string): boolean {
  const compiler = new CompilerClass({ color: false });
  const result = compiler.check(source);
  return result.success;
}
