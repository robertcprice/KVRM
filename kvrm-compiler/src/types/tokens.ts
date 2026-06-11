/**
 * Token types for the KVRM programming language.
 * Comprehensive token enumeration for lexical analysis with production-quality type safety.
 */

/**
 * Token type enumeration covering all lexical elements of KVRM.
 */
export enum TokenType {
  // Keywords - Control Flow
  FN = 'FN',
  LET = 'LET',
  MUT = 'MUT',
  IF = 'IF',
  ELSE = 'ELSE',
  WHILE = 'WHILE',
  FOR = 'FOR',
  IN = 'IN',
  RETURN = 'RETURN',
  BREAK = 'BREAK',
  CONTINUE = 'CONTINUE',
  MATCH = 'MATCH',

  // Keywords - Type System
  STRUCT = 'STRUCT',
  ENUM = 'ENUM',
  IMPL = 'IMPL',
  TRAIT = 'TRAIT',
  TYPE = 'TYPE',
  AS = 'AS',

  // Keywords - Module System
  USE = 'USE',
  MOD = 'MOD',
  PUB = 'PUB',

  // Keywords - Special
  SELF = 'SELF',
  SUPER = 'SUPER',
  CONST = 'CONST',
  STATIC = 'STATIC',

  // Literals - Boolean & Null
  TRUE = 'TRUE',
  FALSE = 'FALSE',
  NULL = 'NULL',

  // Identifiers and Literals
  IDENTIFIER = 'IDENTIFIER',
  NUMBER = 'NUMBER',
  STRING = 'STRING',
  CHAR = 'CHAR',
  LIFETIME = 'LIFETIME', // 'a, 'static, etc.

  // Arithmetic Operators
  PLUS = 'PLUS', // +
  MINUS = 'MINUS', // -
  STAR = 'STAR', // *
  SLASH = 'SLASH', // /
  PERCENT = 'PERCENT', // %
  POWER = 'POWER', // **

  // Comparison Operators
  EQ = 'EQ', // ==
  NE = 'NE', // !=
  LT = 'LT', // <
  GT = 'GT', // >
  LE = 'LE', // <=
  GE = 'GE', // >=

  // Logical Operators
  AND = 'AND', // &&
  OR = 'OR', // ||
  NOT = 'NOT', // !

  // Bitwise Operators
  BIT_AND = 'BIT_AND', // &
  BIT_OR = 'BIT_OR', // |
  BIT_XOR = 'BIT_XOR', // ^
  BIT_NOT = 'BIT_NOT', // ~
  LEFT_SHIFT = 'LEFT_SHIFT', // <<
  RIGHT_SHIFT = 'RIGHT_SHIFT', // >>

  // Assignment Operators
  ASSIGN = 'ASSIGN', // =
  PLUS_ASSIGN = 'PLUS_ASSIGN', // +=
  MINUS_ASSIGN = 'MINUS_ASSIGN', // -=
  STAR_ASSIGN = 'STAR_ASSIGN', // *=
  SLASH_ASSIGN = 'SLASH_ASSIGN', // /=
  PERCENT_ASSIGN = 'PERCENT_ASSIGN', // %=
  BIT_AND_ASSIGN = 'BIT_AND_ASSIGN', // &=
  BIT_OR_ASSIGN = 'BIT_OR_ASSIGN', // |=
  BIT_XOR_ASSIGN = 'BIT_XOR_ASSIGN', // ^=
  LEFT_SHIFT_ASSIGN = 'LEFT_SHIFT_ASSIGN', // <<=
  RIGHT_SHIFT_ASSIGN = 'RIGHT_SHIFT_ASSIGN', // >>=

  // Delimiters
  LPAREN = 'LPAREN', // (
  RPAREN = 'RPAREN', // )
  LBRACE = 'LBRACE', // {
  RBRACE = 'RBRACE', // }
  LBRACKET = 'LBRACKET', // [
  RBRACKET = 'RBRACKET', // ]

  // Punctuation
  COMMA = 'COMMA', // ,
  SEMICOLON = 'SEMICOLON', // ;
  COLON = 'COLON', // :
  DOUBLE_COLON = 'DOUBLE_COLON', // ::
  ARROW = 'ARROW', // ->
  FAT_ARROW = 'FAT_ARROW', // =>
  DOT = 'DOT', // .
  DOUBLE_DOT = 'DOUBLE_DOT', // ..
  TRIPLE_DOT = 'TRIPLE_DOT', // ...
  QUESTION = 'QUESTION', // ?
  AT = 'AT', // @
  HASH = 'HASH', // #
  DOLLAR = 'DOLLAR', // $
  UNDERSCORE = 'UNDERSCORE', // _

  // Special Tokens
  NEWLINE = 'NEWLINE',
  COMMENT = 'COMMENT',
  EOF = 'EOF',
  ILLEGAL = 'ILLEGAL',
}

/**
 * Represents a single token in the source code.
 * Immutable and contains all information needed for parsing and error reporting.
 */
export interface Token {
  /** The type of this token */
  readonly type: TokenType;

  /** The literal value from source code */
  readonly value: string;

  /** Location information for error reporting */
  readonly location: SourceLocation;
}

/**
 * Source code location information for error reporting and debugging.
 * All positions are 1-indexed for human readability.
 */
export interface SourceLocation {
  /** Absolute character position in source (0-indexed) */
  readonly offset: number;

  /** Line number (1-indexed) */
  readonly line: number;

  /** Column number (1-indexed) */
  readonly column: number;

  /** Length of the token in characters */
  readonly length: number;

  /** Optional source file path for multi-file compilation */
  readonly file?: string;
}

/**
 * Keyword mapping for efficient lookup during lexing.
 * ReadonlyMap ensures immutability and type safety.
 */
export const KEYWORDS: ReadonlyMap<string, TokenType> = new Map([
  // Control Flow
  ['fn', TokenType.FN],
  ['let', TokenType.LET],
  ['mut', TokenType.MUT],
  ['if', TokenType.IF],
  ['else', TokenType.ELSE],
  ['while', TokenType.WHILE],
  ['for', TokenType.FOR],
  ['in', TokenType.IN],
  ['return', TokenType.RETURN],
  ['break', TokenType.BREAK],
  ['continue', TokenType.CONTINUE],
  ['match', TokenType.MATCH],

  // Type System
  ['struct', TokenType.STRUCT],
  ['enum', TokenType.ENUM],
  ['impl', TokenType.IMPL],
  ['trait', TokenType.TRAIT],
  ['type', TokenType.TYPE],
  ['as', TokenType.AS],

  // Module System
  ['use', TokenType.USE],
  ['mod', TokenType.MOD],
  ['pub', TokenType.PUB],

  // Special
  ['self', TokenType.SELF],
  ['super', TokenType.SUPER],
  ['const', TokenType.CONST],
  ['static', TokenType.STATIC],

  // Literals
  ['true', TokenType.TRUE],
  ['false', TokenType.FALSE],
  ['null', TokenType.NULL],
]);

/**
 * Operator precedence levels (higher number = higher precedence).
 * Used by the parser for expression parsing.
 */
export const OPERATOR_PRECEDENCE: ReadonlyMap<TokenType, number> = new Map([
  // Assignment (lowest precedence)
  [TokenType.ASSIGN, 1],
  [TokenType.PLUS_ASSIGN, 1],
  [TokenType.MINUS_ASSIGN, 1],
  [TokenType.STAR_ASSIGN, 1],
  [TokenType.SLASH_ASSIGN, 1],
  [TokenType.PERCENT_ASSIGN, 1],
  [TokenType.BIT_AND_ASSIGN, 1],
  [TokenType.BIT_OR_ASSIGN, 1],
  [TokenType.BIT_XOR_ASSIGN, 1],
  [TokenType.LEFT_SHIFT_ASSIGN, 1],
  [TokenType.RIGHT_SHIFT_ASSIGN, 1],

  // Logical OR
  [TokenType.OR, 2],

  // Logical AND
  [TokenType.AND, 3],

  // Bitwise OR
  [TokenType.BIT_OR, 4],

  // Bitwise XOR
  [TokenType.BIT_XOR, 5],

  // Bitwise AND
  [TokenType.BIT_AND, 6],

  // Equality
  [TokenType.EQ, 7],
  [TokenType.NE, 7],

  // Comparison
  [TokenType.LT, 8],
  [TokenType.GT, 8],
  [TokenType.LE, 8],
  [TokenType.GE, 8],

  // Bitwise Shift
  [TokenType.LEFT_SHIFT, 9],
  [TokenType.RIGHT_SHIFT, 9],

  // Addition/Subtraction
  [TokenType.PLUS, 10],
  [TokenType.MINUS, 10],

  // Multiplication/Division/Modulo
  [TokenType.STAR, 11],
  [TokenType.SLASH, 11],
  [TokenType.PERCENT, 11],

  // Power (highest precedence)
  [TokenType.POWER, 12],
]);

/**
 * Type guard to check if a token is a keyword.
 */
export function isKeyword(token: Token): boolean {
  return Array.from(KEYWORDS.values()).includes(token.type);
}

/**
 * Type guard to check if a token is a literal value.
 */
export function isLiteral(token: Token): boolean {
  return (
    token.type === TokenType.NUMBER ||
    token.type === TokenType.STRING ||
    token.type === TokenType.CHAR ||
    token.type === TokenType.TRUE ||
    token.type === TokenType.FALSE ||
    token.type === TokenType.NULL
  );
}

/**
 * Type guard to check if a token is a binary operator.
 */
export function isBinaryOperator(token: Token): boolean {
  return OPERATOR_PRECEDENCE.has(token.type);
}

/**
 * Type guard to check if a token is an assignment operator.
 */
export function isAssignmentOperator(token: Token): boolean {
  const assignmentTypes = [
    TokenType.ASSIGN,
    TokenType.PLUS_ASSIGN,
    TokenType.MINUS_ASSIGN,
    TokenType.STAR_ASSIGN,
    TokenType.SLASH_ASSIGN,
    TokenType.PERCENT_ASSIGN,
    TokenType.BIT_AND_ASSIGN,
    TokenType.BIT_OR_ASSIGN,
    TokenType.BIT_XOR_ASSIGN,
    TokenType.LEFT_SHIFT_ASSIGN,
    TokenType.RIGHT_SHIFT_ASSIGN,
  ];
  return assignmentTypes.includes(token.type);
}

/**
 * Type guard to check if a token is a unary operator.
 */
export function isUnaryOperator(token: Token): boolean {
  return (
    token.type === TokenType.NOT ||
    token.type === TokenType.MINUS ||
    token.type === TokenType.BIT_NOT ||
    token.type === TokenType.STAR || // Dereference
    token.type === TokenType.BIT_AND // Reference
  );
}

/**
 * Get the precedence of an operator token.
 * Returns 0 if the token is not an operator.
 */
export function getPrecedence(token: Token): number {
  return OPERATOR_PRECEDENCE.get(token.type) ?? 0;
}

/**
 * Creates a new token with the given properties.
 */
export function createToken(type: TokenType, value: string, location: SourceLocation): Token {
  return Object.freeze({ type, value, location });
}

/**
 * Creates a source location object.
 */
export function createLocation(
  offset: number,
  line: number,
  column: number,
  length: number,
  file?: string
): SourceLocation {
  return Object.freeze({ offset, line, column, length, file });
}

/**
 * Format a token for debugging and error messages.
 */
export function formatToken(token: Token): string {
  const loc = token.location;
  const position = loc.file
    ? `${loc.file}:${loc.line}:${loc.column}`
    : `${loc.line}:${loc.column}`;
  return `${token.type}('${token.value}') at ${position}`;
}
