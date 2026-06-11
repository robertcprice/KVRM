/**
 * Error handling utilities for the KVRM compiler.
 * Production-quality error types with source location tracking.
 */

import type { SourceLocation } from '../types/tokens.js';

/**
 * Base class for all KVRM compiler errors.
 * Provides structured error information with source location.
 */
export class CompilerError extends Error {
  constructor(
    message: string,
    public readonly location?: SourceLocation,
    public readonly code?: string
  ) {
    super(message);
    this.name = 'CompilerError';
    Object.setPrototypeOf(this, CompilerError.prototype);
  }

  /**
   * Format the error for display with location information.
   */
  format(): string {
    if (!this.location) {
      return `${this.name}: ${this.message}`;
    }

    const loc = this.location;
    const position = loc.file
      ? `${loc.file}:${loc.line}:${loc.column}`
      : `${loc.line}:${loc.column}`;

    return `${this.name} at ${position}: ${this.message}`;
  }
}

/**
 * Error thrown during lexical analysis.
 */
export class LexerError extends CompilerError {
  constructor(message: string, location?: SourceLocation, code?: string) {
    super(message, location, code);
    this.name = 'LexerError';
    Object.setPrototypeOf(this, LexerError.prototype);
  }
}

/**
 * Error thrown during parsing.
 */
export class ParserError extends CompilerError {
  constructor(message: string, location?: SourceLocation, code?: string) {
    super(message, location, code);
    this.name = 'ParserError';
    Object.setPrototypeOf(this, ParserError.prototype);
  }
}

/**
 * Error thrown during semantic analysis.
 */
export class SemanticError extends CompilerError {
  constructor(message: string, location?: SourceLocation, code?: string) {
    super(message, location, code);
    this.name = 'SemanticError';
    Object.setPrototypeOf(this, SemanticError.prototype);
  }
}

/**
 * Error thrown during code generation.
 */
export class CodegenError extends CompilerError {
  constructor(message: string, location?: SourceLocation, code?: string) {
    super(message, location, code);
    this.name = 'CodegenError';
    Object.setPrototypeOf(this, CodegenError.prototype);
  }
}

/**
 * Error thrown for internal compiler bugs.
 * These should never happen in production.
 */
export class InternalError extends CompilerError {
  constructor(message: string, location?: SourceLocation) {
    super(`Internal compiler error: ${message}`, location, 'INTERNAL');
    this.name = 'InternalError';
    Object.setPrototypeOf(this, InternalError.prototype);
  }
}

/**
 * Create a formatted error message with source context.
 */
export function formatErrorWithContext(
  error: CompilerError,
  source: string
): string {
  if (!error.location) {
    return error.format();
  }

  const lines = source.split('\n');
  const location = error.location;
  const line = lines[location.line - 1];

  if (!line) {
    return error.format();
  }

  const pointer = ' '.repeat(location.column - 1) + '^'.repeat(Math.max(1, location.length));

  return [
    error.format(),
    '',
    `${location.line.toString().padStart(4)} | ${line}`,
    `${' '.repeat(4)} | ${pointer}`,
    '',
  ].join('\n');
}

/**
 * Assert a condition and throw an InternalError if it fails.
 * Used for invariants that should never be violated.
 */
export function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new InternalError(message);
  }
}

/**
 * Type guard to check if an error is a CompilerError.
 */
export function isCompilerError(error: unknown): error is CompilerError {
  return error instanceof CompilerError;
}
