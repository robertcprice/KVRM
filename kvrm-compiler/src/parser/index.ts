/**
 * KVRM Parser Module
 *
 * Exports parser components for transforming tokens into AST.
 */

export { Parser, ParserOptions, Precedence } from './parser';

export {
  ParseError,
  UnexpectedTokenError,
  ExpectedTokenError,
  SyntaxError,
  UnexpectedEOFError,
  ParseErrorCollection,
  ErrorRecovery,
  RecoveryStrategy,
  SourceLocation,
  SYNC_TOKENS,
} from './errors';

/**
 * Convenience function to parse source code directly.
 *
 * @param tokens - Token array from lexer
 * @param options - Parser configuration options
 * @returns Parsed Program AST
 */
export function parse(tokens: any[], options?: any) {
  const parser = new Parser(tokens, options);
  return parser.parse();
}
