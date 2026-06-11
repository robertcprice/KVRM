/**
 * KVRM Compiler Lexer
 * Production-quality tokenization with comprehensive error handling
 * Supports Rust-like syntax including lifetimes, generics, and modern operators
 */

import { TokenType, KEYWORDS, Token, createToken, createLocation } from '../types/tokens.js';

/**
 * Lexer error with detailed position information
 */
export class LexerError extends Error {
  constructor(
    message: string,
    public readonly line: number,
    public readonly column: number,
    public readonly offset: number,
    public readonly file?: string
  ) {
    const location = file ? `${file}:${line}:${column}` : `${line}:${column}`;
    super(`Lexer error at ${location}: ${message}`);
    this.name = 'LexerError';
    Error.captureStackTrace?.(this, LexerError);
  }
}

/**
 * Lexer state snapshot for lookahead operations
 */
interface LexerState {
  readonly pos: number;
  readonly line: number;
  readonly column: number;
  readonly tokens: ReadonlyArray<Token>;
}

/**
 * Main Lexer class for KVRM source code tokenization
 */
export class Lexer {
  private readonly source: string;
  private readonly file?: string;
  private pos: number = 0;
  private line: number = 1;
  private column: number = 1;
  private tokens: Token[] = [];

  constructor(source: string, file?: string) {
    this.source = source;
    this.file = file;
  }

  /**
   * Tokenize the entire source code
   * @returns Array of tokens including EOF
   */
  tokenize(): Token[] {
    this.reset();

    while (!this.isAtEnd()) {
      this.skipWhitespaceAndComments();
      if (this.isAtEnd()) break;
      this.scanToken();
    }

    this.addToken(TokenType.EOF, '');
    return [...this.tokens];
  }

  /**
   * Get next token without consuming it
   */
  peek(): Token | null {
    const state = this.saveState();
    try {
      this.skipWhitespaceAndComments();
      if (this.isAtEnd()) return null;
      this.scanToken();
      return this.tokens[this.tokens.length - 1];
    } finally {
      this.restoreState(state);
    }
  }

  /**
   * Peek ahead n tokens (1-indexed)
   */
  peekAhead(n: number): Token | null {
    if (n < 1) {
      throw new Error('peekAhead requires n >= 1');
    }

    const state = this.saveState();
    try {
      for (let i = 0; i < n; i++) {
        this.skipWhitespaceAndComments();
        if (this.isAtEnd()) return null;
        this.scanToken();
      }
      return this.tokens[this.tokens.length - 1];
    } finally {
      this.restoreState(state);
    }
  }

  /**
   * Reset lexer state for re-tokenization
   */
  private reset(): void {
    this.pos = 0;
    this.line = 1;
    this.column = 1;
    this.tokens = [];
  }

  /**
   * Scan a single token from current position
   */
  private scanToken(): void {
    const char = this.advance();

    switch (char) {
      // Single-character delimiters
      case '(':
        this.addToken(TokenType.LPAREN, char);
        break;
      case ')':
        this.addToken(TokenType.RPAREN, char);
        break;
      case '{':
        this.addToken(TokenType.LBRACE, char);
        break;
      case '}':
        this.addToken(TokenType.RBRACE, char);
        break;
      case '[':
        this.addToken(TokenType.LBRACKET, char);
        break;
      case ']':
        this.addToken(TokenType.RBRACKET, char);
        break;

      // Single-character punctuation
      case ',':
        this.addToken(TokenType.COMMA, char);
        break;
      case ';':
        this.addToken(TokenType.SEMICOLON, char);
        break;
      case '?':
        this.addToken(TokenType.QUESTION, char);
        break;
      case '@':
        this.addToken(TokenType.AT, char);
        break;
      case '#':
        this.addToken(TokenType.HASH, char);
        break;
      case '$':
        this.addToken(TokenType.DOLLAR, char);
        break;
      case '~':
        this.addToken(TokenType.BIT_NOT, char);
        break;

      // Multi-character operators and punctuation
      case '+':
        if (this.match('=')) {
          this.addToken(TokenType.PLUS_ASSIGN, '+=');
        } else {
          this.addToken(TokenType.PLUS, char);
        }
        break;

      case '-':
        if (this.match('>')) {
          this.addToken(TokenType.ARROW, '->');
        } else if (this.match('=')) {
          this.addToken(TokenType.MINUS_ASSIGN, '-=');
        } else {
          this.addToken(TokenType.MINUS, char);
        }
        break;

      case '*':
        if (this.match('*')) {
          this.addToken(TokenType.POWER, '**');
        } else if (this.match('=')) {
          this.addToken(TokenType.STAR_ASSIGN, '*=');
        } else {
          this.addToken(TokenType.STAR, char);
        }
        break;

      case '/':
        if (this.match('=')) {
          this.addToken(TokenType.SLASH_ASSIGN, '/=');
        } else {
          this.addToken(TokenType.SLASH, char);
        }
        break;

      case '%':
        if (this.match('=')) {
          this.addToken(TokenType.PERCENT_ASSIGN, '%=');
        } else {
          this.addToken(TokenType.PERCENT, char);
        }
        break;

      case '!':
        if (this.match('=')) {
          this.addToken(TokenType.NE, '!=');
        } else {
          this.addToken(TokenType.NOT, char);
        }
        break;

      case '=':
        if (this.match('=')) {
          this.addToken(TokenType.EQ, '==');
        } else if (this.match('>')) {
          this.addToken(TokenType.FAT_ARROW, '=>');
        } else {
          this.addToken(TokenType.ASSIGN, char);
        }
        break;

      case '<':
        if (this.match('<')) {
          if (this.match('=')) {
            this.addToken(TokenType.LEFT_SHIFT_ASSIGN, '<<=');
          } else {
            this.addToken(TokenType.LEFT_SHIFT, '<<');
          }
        } else if (this.match('=')) {
          this.addToken(TokenType.LE, '<=');
        } else {
          this.addToken(TokenType.LT, char);
        }
        break;

      case '>':
        if (this.match('>')) {
          if (this.match('=')) {
            this.addToken(TokenType.RIGHT_SHIFT_ASSIGN, '>>=');
          } else {
            this.addToken(TokenType.RIGHT_SHIFT, '>>');
          }
        } else if (this.match('=')) {
          this.addToken(TokenType.GE, '>=');
        } else {
          this.addToken(TokenType.GT, char);
        }
        break;

      case '&':
        if (this.match('&')) {
          this.addToken(TokenType.AND, '&&');
        } else if (this.match('=')) {
          this.addToken(TokenType.BIT_AND_ASSIGN, '&=');
        } else {
          this.addToken(TokenType.BIT_AND, char);
        }
        break;

      case '|':
        if (this.match('|')) {
          this.addToken(TokenType.OR, '||');
        } else if (this.match('=')) {
          this.addToken(TokenType.BIT_OR_ASSIGN, '|=');
        } else {
          this.addToken(TokenType.BIT_OR, char);
        }
        break;

      case '^':
        if (this.match('=')) {
          this.addToken(TokenType.BIT_XOR_ASSIGN, '^=');
        } else {
          this.addToken(TokenType.BIT_XOR, char);
        }
        break;

      case ':':
        if (this.match(':')) {
          this.addToken(TokenType.DOUBLE_COLON, '::');
        } else {
          this.addToken(TokenType.COLON, char);
        }
        break;

      case '.':
        if (this.match('.')) {
          if (this.match('.')) {
            this.addToken(TokenType.TRIPLE_DOT, '...');
          } else {
            this.addToken(TokenType.DOUBLE_DOT, '..');
          }
        } else if (this.isDigit(this.peekChar())) {
          // Handle .5 style floats
          this.pos--;
          this.column--;
          this.scanNumber();
        } else {
          this.addToken(TokenType.DOT, char);
        }
        break;

      case "'":
        // Could be lifetime or char literal
        this.scanLifetimeOrChar();
        break;

      case '"':
        this.scanString();
        break;

      case '\n':
        this.addToken(TokenType.NEWLINE, '\\n');
        this.line++;
        this.column = 0;
        break;

      default:
        if (this.isDigit(char)) {
          this.pos--;
          this.column--;
          this.scanNumber();
        } else if (this.isAlpha(char) || char === '_') {
          this.pos--;
          this.column--;
          this.scanIdentifier();
        } else {
          this.throwError(
            `Unexpected character: '${char}' (Unicode: U+${char.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')})`
          );
        }
    }
  }

  /**
   * Scan numeric literal: integer, float, hex (0x), binary (0b)
   */
  private scanNumber(): void {
    const start = this.pos;
    const startColumn = this.column;

    // Check for special prefixes
    if (this.peekChar() === '0') {
      this.advance();
      const next = this.peekChar();

      if (next === 'x' || next === 'X') {
        this.scanHexNumber(start, startColumn);
        return;
      } else if (next === 'b' || next === 'B') {
        this.scanBinaryNumber(start, startColumn);
        return;
      } else if (this.isDigit(next)) {
        // Leading zero in decimal is allowed but may be a lint warning
        // Continue scanning decimal
      } else if (next === '.') {
        // 0.xxx float
      } else {
        // Just "0"
        this.addTokenAt(TokenType.NUMBER, '0', startColumn, 1);
        return;
      }
    }

    // Scan integer part
    while (this.isDigit(this.peekChar())) {
      this.advance();
    }

    // Check for decimal point
    if (this.peekChar() === '.' && this.isDigit(this.peekNext())) {
      this.advance(); // consume '.'
      while (this.isDigit(this.peekChar())) {
        this.advance();
      }
    }

    // Check for exponent (e or E)
    if (this.peekChar() === 'e' || this.peekChar() === 'E') {
      this.advance();
      if (this.peekChar() === '+' || this.peekChar() === '-') {
        this.advance();
      }
      if (!this.isDigit(this.peekChar())) {
        this.throwError('Invalid number: expected digit after exponent');
      }
      while (this.isDigit(this.peekChar())) {
        this.advance();
      }
    }

    const value = this.source.substring(start, this.pos);
    const length = this.pos - start;
    this.addTokenAt(TokenType.NUMBER, value, startColumn, length);
  }

  /**
   * Scan hexadecimal number (0x...)
   */
  private scanHexNumber(start: number, startColumn: number): void {
    this.advance(); // consume 'x' or 'X'

    if (!this.isHexDigit(this.peekChar())) {
      this.throwError('Invalid hex literal: expected hex digit after 0x');
    }

    while (this.isHexDigit(this.peekChar()) || this.peekChar() === '_') {
      this.advance();
    }

    const value = this.source.substring(start, this.pos);
    const length = this.pos - start;
    this.addTokenAt(TokenType.NUMBER, value, startColumn, length);
  }

  /**
   * Scan binary number (0b...)
   */
  private scanBinaryNumber(start: number, startColumn: number): void {
    this.advance(); // consume 'b' or 'B'

    if (!this.isBinaryDigit(this.peekChar())) {
      this.throwError('Invalid binary literal: expected binary digit after 0b');
    }

    while (this.isBinaryDigit(this.peekChar()) || this.peekChar() === '_') {
      this.advance();
    }

    const value = this.source.substring(start, this.pos);
    const length = this.pos - start;
    this.addTokenAt(TokenType.NUMBER, value, startColumn, length);
  }

  /**
   * Scan string literal with escape sequences
   */
  private scanString(): void {
    const startColumn = this.column - 1;
    const startLine = this.line;
    const startOffset = this.pos - 1;
    let value = '';

    while (this.peekChar() !== '"' && !this.isAtEnd()) {
      const char = this.advance();

      if (char === '\n') {
        this.line++;
        this.column = 0;
        value += char;
      } else if (char === '\\') {
        if (this.isAtEnd()) {
          this.throwError('Unterminated string literal');
        }
        const escaped = this.advance();
        switch (escaped) {
          case 'n':
            value += '\n';
            break;
          case 't':
            value += '\t';
            break;
          case 'r':
            value += '\r';
            break;
          case '\\':
            value += '\\';
            break;
          case '"':
            value += '"';
            break;
          case "'":
            value += "'";
            break;
          case '0':
            value += '\0';
            break;
          case 'x':
            value += this.scanHexEscape();
            break;
          case 'u':
            value += this.scanUnicodeEscape();
            break;
          default:
            this.throwError(`Invalid escape sequence: \\${escaped}`);
        }
      } else {
        value += char;
      }
    }

    if (this.isAtEnd()) {
      this.line = startLine;
      this.column = startColumn + 1;
      this.throwError('Unterminated string literal');
    }

    this.advance(); // consume closing quote
    const length = this.pos - startOffset;
    this.addTokenAt(TokenType.STRING, value, startColumn, length);
  }

  /**
   * Scan hex escape sequence (\xNN)
   */
  private scanHexEscape(): string {
    const digits: string[] = [];
    for (let i = 0; i < 2; i++) {
      if (!this.isHexDigit(this.peekChar())) {
        this.throwError('Invalid hex escape: expected 2 hex digits');
      }
      digits.push(this.advance());
    }
    const code = parseInt(digits.join(''), 16);
    return String.fromCharCode(code);
  }

  /**
   * Scan Unicode escape sequence (\u{NNNNNN})
   */
  private scanUnicodeEscape(): string {
    if (this.peekChar() !== '{') {
      this.throwError('Invalid Unicode escape: expected {');
    }
    this.advance(); // consume '{'

    const digits: string[] = [];
    while (this.peekChar() !== '}' && !this.isAtEnd()) {
      if (!this.isHexDigit(this.peekChar())) {
        this.throwError('Invalid Unicode escape: expected hex digit');
      }
      digits.push(this.advance());
    }

    if (this.isAtEnd()) {
      this.throwError('Unterminated Unicode escape');
    }
    this.advance(); // consume '}'

    if (digits.length === 0 || digits.length > 6) {
      this.throwError('Invalid Unicode escape: expected 1-6 hex digits');
    }

    const code = parseInt(digits.join(''), 16);
    if (code > 0x10ffff) {
      this.throwError(`Invalid Unicode escape: code point too large (max: U+10FFFF)`);
    }

    return String.fromCodePoint(code);
  }

  /**
   * Scan identifier or keyword
   */
  private scanIdentifier(): void {
    const start = this.pos;
    const startColumn = this.column;

    while (this.isAlphaNumeric(this.peekChar())) {
      this.advance();
    }

    const text = this.source.substring(start, this.pos);
    const type = KEYWORDS.get(text) ?? TokenType.IDENTIFIER;
    const length = this.pos - start;
    this.addTokenAt(type, text, startColumn, length);
  }

  /**
   * Scan lifetime annotation ('a, 'static) or character literal
   */
  private scanLifetimeOrChar(): void {
    const startColumn = this.column - 1;
    const startOffset = this.pos - 1;

    // Peek ahead to distinguish lifetime from char
    if (this.isAlpha(this.peekChar())) {
      // Lifetime annotation
      const start = this.pos - 1;
      while (this.isAlphaNumeric(this.peekChar())) {
        this.advance();
      }
      const text = this.source.substring(start, this.pos);
      const length = this.pos - start;
      this.addTokenAt(TokenType.LIFETIME, text, startColumn, length);
    } else {
      // Character literal
      if (this.isAtEnd()) {
        this.throwError('Unterminated character literal');
      }

      let char = this.advance();
      if (char === '\\') {
        // Escape sequence
        if (this.isAtEnd()) {
          this.throwError('Unterminated character literal');
        }
        const escaped = this.advance();
        switch (escaped) {
          case 'n':
            char = '\n';
            break;
          case 't':
            char = '\t';
            break;
          case 'r':
            char = '\r';
            break;
          case '\\':
            char = '\\';
            break;
          case "'":
            char = "'";
            break;
          case '0':
            char = '\0';
            break;
          default:
            this.throwError(`Invalid escape sequence in character literal: \\${escaped}`);
        }
      }

      if (this.peekChar() !== "'") {
        this.throwError("Expected closing ' for character literal");
      }
      this.advance(); // consume closing quote

      const length = this.pos - startOffset;
      this.addTokenAt(TokenType.CHAR, char, startColumn, length);
    }
  }

  /**
   * Skip whitespace (spaces, tabs, CR) and comments
   */
  private skipWhitespaceAndComments(): void {
    while (true) {
      const char = this.peekChar();

      if (char === ' ' || char === '\t' || char === '\r') {
        this.advance();
      } else if (char === '/' && this.peekNext() === '/') {
        this.skipLineComment();
      } else if (char === '/' && this.peekNext() === '*') {
        this.skipBlockComment();
      } else {
        break;
      }
    }
  }

  /**
   * Skip line comment (// ... \n)
   */
  private skipLineComment(): void {
    this.advance(); // consume first '/'
    this.advance(); // consume second '/'

    while (this.peekChar() !== '\n' && !this.isAtEnd()) {
      this.advance();
    }
  }

  /**
   * Skip block comment with nesting support
   */
  private skipBlockComment(): void {
    const startLine = this.line;
    const startColumn = this.column;

    this.advance(); // consume '/'
    this.advance(); // consume '*'

    let depth = 1;

    while (depth > 0 && !this.isAtEnd()) {
      if (this.peekChar() === '/' && this.peekNext() === '*') {
        // Nested comment
        depth++;
        this.advance();
        this.advance();
      } else if (this.peekChar() === '*' && this.peekNext() === '/') {
        // End of comment
        depth--;
        this.advance();
        this.advance();
      } else {
        const char = this.advance();
        if (char === '\n') {
          this.line++;
          this.column = 0;
        }
      }
    }

    if (depth > 0) {
      this.line = startLine;
      this.column = startColumn;
      this.throwError('Unterminated block comment');
    }
  }

  /**
   * Character classification helpers
   */
  private isDigit(char: string): boolean {
    return char >= '0' && char <= '9';
  }

  private isHexDigit(char: string): boolean {
    return this.isDigit(char) || (char >= 'a' && char <= 'f') || (char >= 'A' && char <= 'F');
  }

  private isBinaryDigit(char: string): boolean {
    return char === '0' || char === '1';
  }

  private isAlpha(char: string): boolean {
    return (char >= 'a' && char <= 'z') || (char >= 'A' && char <= 'Z') || char === '_';
  }

  private isAlphaNumeric(char: string): boolean {
    return this.isAlpha(char) || this.isDigit(char);
  }

  /**
   * Navigation helpers
   */
  private advance(): string {
    const char = this.source[this.pos++];
    this.column++;
    return char;
  }

  private match(expected: string): boolean {
    if (this.isAtEnd() || this.source[this.pos] !== expected) {
      return false;
    }
    this.pos++;
    this.column++;
    return true;
  }

  private peekChar(): string {
    return this.isAtEnd() ? '\0' : this.source[this.pos];
  }

  private peekNext(): string {
    return this.pos + 1 >= this.source.length ? '\0' : this.source[this.pos + 1];
  }

  private isAtEnd(): boolean {
    return this.pos >= this.source.length;
  }

  /**
   * Token creation helpers
   */
  private addToken(type: TokenType, value: string): void {
    const length = value === '\\n' ? 1 : value.length;
    const location = createLocation(this.pos - length, this.line, this.column - length, length, this.file);
    const token = createToken(type, value, location);
    this.tokens.push(token);
  }

  private addTokenAt(type: TokenType, value: string, column: number, length: number): void {
    const location = createLocation(this.pos - length, this.line, column, length, this.file);
    const token = createToken(type, value, location);
    this.tokens.push(token);
  }

  /**
   * Error handling
   */
  private throwError(message: string): never {
    throw new LexerError(message, this.line, this.column, this.pos, this.file);
  }

  /**
   * State management for lookahead
   */
  private saveState(): LexerState {
    return {
      pos: this.pos,
      line: this.line,
      column: this.column,
      tokens: [...this.tokens],
    };
  }

  private restoreState(state: LexerState): void {
    this.pos = state.pos;
    this.line = state.line;
    this.column = state.column;
    this.tokens = [...state.tokens];
  }
}
