/**
 * Parser error types and recovery strategies for KVRM compiler.
 */

import type { Token, TokenType } from '../lexer';

/**
 * Source location information for error reporting.
 */
export interface SourceLocation {
  line: number;
  column: number;
  offset: number;
}

/**
 * Base class for parser errors with location information.
 */
export class ParseError extends Error {
  public readonly location: SourceLocation;
  public readonly token?: Token;

  constructor(message: string, location: SourceLocation, token?: Token) {
    super(message);
    this.name = 'ParseError';
    this.location = location;
    this.token = token;

    // Maintain proper stack trace for where error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ParseError);
    }
  }

  /**
   * Format error message with location information.
   */
  public toString(): string {
    const loc = `${this.location.line}:${this.location.column}`;
    const tokenInfo = this.token ? ` (got ${this.token.type})` : '';
    return `${this.name} at ${loc}: ${this.message}${tokenInfo}`;
  }

  /**
   * Create detailed error report for diagnostics.
   */
  public toDetailedString(source?: string): string {
    const header = this.toString();

    if (!source) {
      return header;
    }

    // Extract relevant line from source
    const lines = source.split('\n');
    const lineIdx = this.location.line - 1;

    if (lineIdx < 0 || lineIdx >= lines.length) {
      return header;
    }

    const line = lines[lineIdx];
    const pointer = ' '.repeat(this.location.column - 1) + '^';

    return [
      header,
      '',
      `  ${this.location.line} | ${line}`,
      `    | ${pointer}`,
    ].join('\n');
  }
}

/**
 * Error thrown when an unexpected token is encountered.
 */
export class UnexpectedTokenError extends ParseError {
  public readonly expected?: TokenType[];

  constructor(
    token: Token,
    expected?: TokenType[],
    customMessage?: string
  ) {
    const expectedStr = expected && expected.length > 0
      ? ` (expected ${expected.join(', ')})`
      : '';

    const message = customMessage
      || `Unexpected token '${token.value}'${expectedStr}`;

    super(message, {
      line: token.line,
      column: token.column,
      offset: token.offset || 0,
    }, token);

    this.name = 'UnexpectedTokenError';
    this.expected = expected;
  }
}

/**
 * Error thrown when a specific expected token is not found.
 */
export class ExpectedTokenError extends ParseError {
  public readonly expectedType: TokenType;
  public readonly actualToken: Token;

  constructor(expectedType: TokenType, actualToken: Token, context?: string) {
    const contextStr = context ? ` ${context}` : '';
    const message = `Expected ${expectedType}, but got ${actualToken.type}${contextStr}`;

    super(message, {
      line: actualToken.line,
      column: actualToken.column,
      offset: actualToken.offset || 0,
    }, actualToken);

    this.name = 'ExpectedTokenError';
    this.expectedType = expectedType;
    this.actualToken = actualToken;
  }
}

/**
 * Error thrown when invalid syntax is detected.
 */
export class SyntaxError extends ParseError {
  constructor(message: string, location: SourceLocation, token?: Token) {
    super(message, location, token);
    this.name = 'SyntaxError';
  }
}

/**
 * Error thrown when unexpected end of file is reached.
 */
export class UnexpectedEOFError extends ParseError {
  public readonly context: string;

  constructor(location: SourceLocation, context: string) {
    super(`Unexpected end of file while parsing ${context}`, location);
    this.name = 'UnexpectedEOFError';
    this.context = context;
  }
}

/**
 * Recovery strategy options for error handling.
 */
export enum RecoveryStrategy {
  /** Skip tokens until synchronization point */
  SKIP_TO_SYNC,
  /** Insert missing token and continue */
  INSERT_MISSING,
  /** Abort parsing with error */
  ABORT,
  /** Skip current statement/declaration */
  SKIP_STATEMENT,
  /** Skip to end of block */
  SKIP_BLOCK,
}

/**
 * Synchronization points for error recovery.
 */
export const SYNC_TOKENS: Set<TokenType> = new Set([
  'SEMICOLON',
  'RBRACE',
  'LET',
  'FN',
  'IF',
  'WHILE',
  'FOR',
  'RETURN',
  'STRUCT',
  'ENUM',
  'IMPL',
  'TRAIT',
  'EOF',
]);

/**
 * Error recovery helper functions.
 */
export class ErrorRecovery {
  /**
   * Check if a token is a synchronization point.
   */
  static isSyncToken(tokenType: TokenType): boolean {
    return SYNC_TOKENS.has(tokenType);
  }

  /**
   * Determine recovery strategy based on error type and context.
   */
  static determineStrategy(error: ParseError): RecoveryStrategy {
    if (error instanceof UnexpectedEOFError) {
      return RecoveryStrategy.ABORT;
    }

    if (error instanceof ExpectedTokenError) {
      // Try to insert missing delimiter tokens
      const insertableTokens: Set<TokenType> = new Set([
        'SEMICOLON',
        'RPAREN',
        'RBRACE',
        'RBRACKET',
      ]);

      if (insertableTokens.has(error.expectedType)) {
        return RecoveryStrategy.INSERT_MISSING;
      }
    }

    // Default: skip to synchronization point
    return RecoveryStrategy.SKIP_TO_SYNC;
  }

  /**
   * Create helpful suggestions for common errors.
   */
  static getSuggestion(error: ParseError): string | null {
    if (error instanceof ExpectedTokenError) {
      const { expectedType, actualToken } = error;

      // Common missing delimiter suggestions
      if (expectedType === 'SEMICOLON') {
        return "Did you forget a semicolon at the end of the statement?";
      }

      if (expectedType === 'RPAREN' && actualToken.type === 'SEMICOLON') {
        return "Did you forget to close the parenthesis?";
      }

      if (expectedType === 'RBRACE' && actualToken.type === 'EOF') {
        return "Did you forget to close a brace? Check your block structure.";
      }

      // Type annotation suggestions
      if (expectedType === 'COLON' && actualToken.type === 'ASSIGN') {
        return "Type annotations use ':' not '='. Did you mean to declare a type?";
      }
    }

    if (error instanceof UnexpectedTokenError) {
      const { token, expected } = error;

      // Assignment vs equality
      if (token.type === 'ASSIGN' && expected?.includes('EQ')) {
        return "Did you mean '==' for comparison instead of '=' for assignment?";
      }

      // Missing let/const/var
      if (token.type === 'IDENT' && expected?.includes('LET')) {
        return "Variables must be declared with 'let'. Did you forget 'let'?";
      }
    }

    return null;
  }
}

/**
 * Aggregate multiple parse errors for batch reporting.
 */
export class ParseErrorCollection extends Error {
  public readonly errors: ParseError[];

  constructor(errors: ParseError[]) {
    super(`${errors.length} parse error(s) found`);
    this.name = 'ParseErrorCollection';
    this.errors = errors;
  }

  /**
   * Get all errors sorted by location.
   */
  getSorted(): ParseError[] {
    return [...this.errors].sort((a, b) => {
      if (a.location.line !== b.location.line) {
        return a.location.line - b.location.line;
      }
      return a.location.column - b.location.column;
    });
  }

  /**
   * Format all errors with source context.
   */
  formatAll(source: string): string {
    return this.getSorted()
      .map((error, idx) => `Error ${idx + 1}:\n${error.toDetailedString(source)}`)
      .join('\n\n');
  }
}
