/**
 * Recursive descent parser for KVRM language.
 * Transforms tokens into an Abstract Syntax Tree (AST).
 */

import type { Token, TokenType, Lexer } from '../lexer';
import type {
  Program,
  Statement,
  Expression,
  FunctionDecl,
  TypeAnnotation,
  StructDecl,
  EnumDecl,
  ImplBlock,
  TraitDecl,
} from '../types/ast';
import {
  ParseError,
  UnexpectedTokenError,
  ExpectedTokenError,
  UnexpectedEOFError,
  SyntaxError,
  ParseErrorCollection,
  ErrorRecovery,
  RecoveryStrategy,
  SYNC_TOKENS,
} from './errors';

/**
 * Parser configuration options.
 */
export interface ParserOptions {
  /** Enable error recovery to continue parsing after errors */
  recoverFromErrors?: boolean;
  /** Maximum number of errors to collect before aborting */
  maxErrors?: number;
  /** Enable strict mode (no automatic semicolon insertion) */
  strictMode?: boolean;
}

/**
 * Operator precedence levels (lower number = lower precedence).
 */
enum Precedence {
  NONE = 0,
  ASSIGNMENT = 1,    // =, +=, -=, etc.
  LOGICAL_OR = 2,    // ||
  LOGICAL_AND = 3,   // &&
  EQUALITY = 4,      // ==, !=
  COMPARISON = 5,    // <, >, <=, >=
  BITWISE_OR = 6,    // |
  BITWISE_XOR = 7,   // ^
  BITWISE_AND = 8,   // &
  SHIFT = 9,         // <<, >>
  ADDITIVE = 10,     // +, -
  MULTIPLICATIVE = 11, // *, /, %
  UNARY = 12,        // !, -, ~, &, *
  CALL = 13,         // (), [], .
}

/**
 * Operator precedence mapping.
 */
const BINARY_PRECEDENCE: Record<string, Precedence> = {
  // Assignment
  'ASSIGN': Precedence.ASSIGNMENT,
  'PLUS_ASSIGN': Precedence.ASSIGNMENT,
  'MINUS_ASSIGN': Precedence.ASSIGNMENT,
  'STAR_ASSIGN': Precedence.ASSIGNMENT,
  'SLASH_ASSIGN': Precedence.ASSIGNMENT,

  // Logical
  'OR': Precedence.LOGICAL_OR,
  'AND': Precedence.LOGICAL_AND,

  // Equality
  'EQ': Precedence.EQUALITY,
  'NE': Precedence.EQUALITY,

  // Comparison
  'LT': Precedence.COMPARISON,
  'GT': Precedence.COMPARISON,
  'LE': Precedence.COMPARISON,
  'GE': Precedence.COMPARISON,

  // Bitwise
  'PIPE': Precedence.BITWISE_OR,
  'CARET': Precedence.BITWISE_XOR,
  'AMPERSAND': Precedence.BITWISE_AND,

  // Shift
  'SHL': Precedence.SHIFT,
  'SHR': Precedence.SHIFT,

  // Additive
  'PLUS': Precedence.ADDITIVE,
  'MINUS': Precedence.ADDITIVE,

  // Multiplicative
  'STAR': Precedence.MULTIPLICATIVE,
  'SLASH': Precedence.MULTIPLICATIVE,
  'PERCENT': Precedence.MULTIPLICATIVE,
};

/**
 * Recursive descent parser for KVRM language.
 */
export class Parser {
  private tokens: Token[];
  private current: number = 0;
  private errors: ParseError[] = [];
  private options: Required<ParserOptions>;

  /**
   * Create a new parser.
   * @param lexer - Lexer instance or token array
   * @param options - Parser configuration options
   */
  constructor(lexer: Lexer | Token[], options: ParserOptions = {}) {
    this.tokens = Array.isArray(lexer) ? lexer : lexer.tokenize();
    this.options = {
      recoverFromErrors: options.recoverFromErrors ?? true,
      maxErrors: options.maxErrors ?? 100,
      strictMode: options.strictMode ?? false,
    };
  }

  /**
   * Parse tokens into a Program AST node.
   */
  parse(): Program {
    this.current = 0;
    this.errors = [];

    const statements: Statement[] = [];

    while (!this.isAtEnd()) {
      try {
        const stmt = this.parseTopLevelStatement();
        if (stmt) {
          statements.push(stmt);
        }
      } catch (error) {
        if (error instanceof ParseError) {
          this.handleError(error);

          if (!this.options.recoverFromErrors) {
            throw error;
          }

          // Attempt recovery
          this.synchronize();
        } else {
          throw error;
        }
      }
    }

    // If we collected errors, throw them
    if (this.errors.length > 0) {
      throw new ParseErrorCollection(this.errors);
    }

    return {
      type: 'Program',
      statements,
      location: this.getLocation(),
    };
  }

  // ============================================================================
  // Top-level declarations
  // ============================================================================

  /**
   * Parse a top-level statement (function, struct, enum, impl, trait, or statement).
   */
  private parseTopLevelStatement(): Statement | null {
    this.skipNewlines();

    if (this.isAtEnd()) {
      return null;
    }

    // Function declaration
    if (this.check('FN')) {
      return this.parseFunction();
    }

    // Struct declaration
    if (this.check('STRUCT')) {
      return this.parseStruct();
    }

    // Enum declaration
    if (this.check('ENUM')) {
      return this.parseEnum();
    }

    // Trait declaration
    if (this.check('TRAIT')) {
      return this.parseTrait();
    }

    // Impl block
    if (this.check('IMPL')) {
      return this.parseImpl();
    }

    // Regular statement
    return this.parseStatement();
  }

  /**
   * Parse a function declaration.
   * fn name(params) -> returnType { body }
   */
  private parseFunction(): FunctionDecl {
    const start = this.peek();
    this.consume('FN', "Expected 'fn' keyword");

    const name = this.consume('IDENT', 'Expected function name');

    this.consume('LPAREN', "Expected '(' after function name");

    // Parse parameters
    const params: Array<{ name: string; type?: TypeAnnotation }> = [];

    if (!this.check('RPAREN')) {
      do {
        const paramName = this.consume('IDENT', 'Expected parameter name');

        let paramType: TypeAnnotation | undefined;
        if (this.match('COLON')) {
          paramType = this.parseType();
        }

        params.push({
          name: paramName.value as string,
          type: paramType,
        });
      } while (this.match('COMMA'));
    }

    this.consume('RPAREN', "Expected ')' after parameters");

    // Parse return type
    let returnType: TypeAnnotation | undefined;
    if (this.match('ARROW')) {
      returnType = this.parseType();
    }

    // Parse body
    this.consume('LBRACE', "Expected '{' before function body");
    const body = this.parseBlockStatements();
    this.consume('RBRACE', "Expected '}' after function body");

    return {
      type: 'FunctionDecl',
      name: name.value as string,
      params,
      returnType,
      body,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse a struct declaration.
   * struct Name { fields }
   */
  private parseStruct(): StructDecl {
    const start = this.peek();
    this.consume('STRUCT', "Expected 'struct' keyword");

    const name = this.consume('IDENT', 'Expected struct name');

    this.consume('LBRACE', "Expected '{' after struct name");

    const fields: Array<{ name: string; type: TypeAnnotation }> = [];

    while (!this.check('RBRACE') && !this.isAtEnd()) {
      this.skipNewlines();

      if (this.check('RBRACE')) break;

      const fieldName = this.consume('IDENT', 'Expected field name');
      this.consume('COLON', "Expected ':' after field name");
      const fieldType = this.parseType();

      fields.push({
        name: fieldName.value as string,
        type: fieldType,
      });

      // Optional comma or newline separator
      this.match('COMMA');
      this.skipNewlines();
    }

    this.consume('RBRACE', "Expected '}' after struct fields");

    return {
      type: 'StructDecl',
      name: name.value as string,
      fields,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse an enum declaration.
   * enum Name { Variant1, Variant2(type), ... }
   */
  private parseEnum(): EnumDecl {
    const start = this.peek();
    this.consume('ENUM', "Expected 'enum' keyword");

    const name = this.consume('IDENT', 'Expected enum name');

    this.consume('LBRACE', "Expected '{' after enum name");

    const variants: Array<{ name: string; type?: TypeAnnotation }> = [];

    while (!this.check('RBRACE') && !this.isAtEnd()) {
      this.skipNewlines();

      if (this.check('RBRACE')) break;

      const variantName = this.consume('IDENT', 'Expected variant name');

      let variantType: TypeAnnotation | undefined;
      if (this.match('LPAREN')) {
        variantType = this.parseType();
        this.consume('RPAREN', "Expected ')' after variant type");
      }

      variants.push({
        name: variantName.value as string,
        type: variantType,
      });

      this.match('COMMA');
      this.skipNewlines();
    }

    this.consume('RBRACE', "Expected '}' after enum variants");

    return {
      type: 'EnumDecl',
      name: name.value as string,
      variants,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse a trait declaration.
   * trait Name { methods }
   */
  private parseTrait(): TraitDecl {
    const start = this.peek();
    this.consume('TRAIT', "Expected 'trait' keyword");

    const name = this.consume('IDENT', 'Expected trait name');

    this.consume('LBRACE', "Expected '{' after trait name");

    const methods: FunctionDecl[] = [];

    while (!this.check('RBRACE') && !this.isAtEnd()) {
      this.skipNewlines();

      if (this.check('RBRACE')) break;

      if (this.check('FN')) {
        methods.push(this.parseFunction());
      } else {
        throw this.error('Expected method declaration in trait');
      }

      this.skipNewlines();
    }

    this.consume('RBRACE', "Expected '}' after trait methods");

    return {
      type: 'TraitDecl',
      name: name.value as string,
      methods,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse an impl block.
   * impl Name { methods }
   * impl Trait for Name { methods }
   */
  private parseImpl(): ImplBlock {
    const start = this.peek();
    this.consume('IMPL', "Expected 'impl' keyword");

    const firstIdent = this.consume('IDENT', 'Expected type or trait name');

    let traitName: string | undefined;
    let typeName: string;

    // Check for "for" keyword (trait implementation)
    if (this.match('FOR')) {
      traitName = firstIdent.value as string;
      const typeToken = this.consume('IDENT', 'Expected type name after "for"');
      typeName = typeToken.value as string;
    } else {
      typeName = firstIdent.value as string;
    }

    this.consume('LBRACE', "Expected '{' after impl declaration");

    const methods: FunctionDecl[] = [];

    while (!this.check('RBRACE') && !this.isAtEnd()) {
      this.skipNewlines();

      if (this.check('RBRACE')) break;

      if (this.check('FN')) {
        methods.push(this.parseFunction());
      } else {
        throw this.error('Expected method declaration in impl block');
      }

      this.skipNewlines();
    }

    this.consume('RBRACE', "Expected '}' after impl methods");

    return {
      type: 'ImplBlock',
      typeName,
      traitName,
      methods,
      location: this.getLocationFrom(start),
    };
  }

  // ============================================================================
  // Statements
  // ============================================================================

  /**
   * Parse a statement.
   */
  private parseStatement(): Statement {
    this.skipNewlines();

    // Let binding
    if (this.check('LET')) {
      return this.parseLetStatement();
    }

    // Return statement
    if (this.check('RETURN')) {
      return this.parseReturnStatement();
    }

    // If statement
    if (this.check('IF')) {
      return this.parseIfStatement();
    }

    // While loop
    if (this.check('WHILE')) {
      return this.parseWhileStatement();
    }

    // For loop
    if (this.check('FOR')) {
      return this.parseForStatement();
    }

    // Block statement
    if (this.check('LBRACE')) {
      return this.parseBlockStatement();
    }

    // Expression statement
    return this.parseExpressionStatement();
  }

  /**
   * Parse a let statement.
   * let name: type = expr;
   */
  private parseLetStatement(): Statement {
    const start = this.peek();
    this.consume('LET', "Expected 'let' keyword");

    const name = this.consume('IDENT', 'Expected variable name');

    let typeAnnotation: TypeAnnotation | undefined;
    if (this.match('COLON')) {
      typeAnnotation = this.parseType();
    }

    let initializer: Expression | undefined;
    if (this.match('ASSIGN')) {
      initializer = this.parseExpression();
    }

    this.consumeSemicolon();

    return {
      type: 'LetStatement',
      name: name.value as string,
      typeAnnotation,
      initializer,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse a return statement.
   * return expr;
   */
  private parseReturnStatement(): Statement {
    const start = this.peek();
    this.consume('RETURN', "Expected 'return' keyword");

    let value: Expression | undefined;
    if (!this.check('SEMICOLON') && !this.check('NEWLINE') && !this.check('RBRACE')) {
      value = this.parseExpression();
    }

    this.consumeSemicolon();

    return {
      type: 'ReturnStatement',
      value,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse an if statement.
   * if condition { thenBranch } else { elseBranch }
   */
  private parseIfStatement(): Statement {
    const start = this.peek();
    this.consume('IF', "Expected 'if' keyword");

    const condition = this.parseExpression();

    this.consume('LBRACE', "Expected '{' after if condition");
    const thenBranch = this.parseBlockStatements();
    this.consume('RBRACE', "Expected '}' after if body");

    let elseBranch: Statement[] | undefined;
    if (this.match('ELSE')) {
      if (this.check('IF')) {
        // else if - parse as another if statement
        elseBranch = [this.parseIfStatement()];
      } else {
        this.consume('LBRACE', "Expected '{' after 'else'");
        elseBranch = this.parseBlockStatements();
        this.consume('RBRACE', "Expected '}' after else body");
      }
    }

    return {
      type: 'IfStatement',
      condition,
      thenBranch,
      elseBranch,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse a while loop.
   * while condition { body }
   */
  private parseWhileStatement(): Statement {
    const start = this.peek();
    this.consume('WHILE', "Expected 'while' keyword");

    const condition = this.parseExpression();

    this.consume('LBRACE', "Expected '{' after while condition");
    const body = this.parseBlockStatements();
    this.consume('RBRACE', "Expected '}' after while body");

    return {
      type: 'WhileStatement',
      condition,
      body,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse a for loop.
   * for init; condition; update { body }
   */
  private parseForStatement(): Statement {
    const start = this.peek();
    this.consume('FOR', "Expected 'for' keyword");

    // Parse initializer
    let initializer: Statement | undefined;
    if (!this.check('SEMICOLON')) {
      if (this.check('LET')) {
        initializer = this.parseLetStatement();
      } else {
        initializer = this.parseExpressionStatement();
      }
    } else {
      this.advance();
    }

    // Parse condition
    let condition: Expression | undefined;
    if (!this.check('SEMICOLON')) {
      condition = this.parseExpression();
    }
    this.consume('SEMICOLON', "Expected ';' after for condition");

    // Parse update
    let update: Expression | undefined;
    if (!this.check('LBRACE')) {
      update = this.parseExpression();
    }

    this.consume('LBRACE', "Expected '{' after for clauses");
    const body = this.parseBlockStatements();
    this.consume('RBRACE', "Expected '}' after for body");

    return {
      type: 'ForStatement',
      initializer,
      condition,
      update,
      body,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse a block statement.
   * { statements }
   */
  private parseBlockStatement(): Statement {
    const start = this.peek();
    this.consume('LBRACE', "Expected '{'");

    const statements = this.parseBlockStatements();

    this.consume('RBRACE', "Expected '}'");

    return {
      type: 'BlockStatement',
      statements,
      location: this.getLocationFrom(start),
    };
  }

  /**
   * Parse statements inside a block.
   */
  private parseBlockStatements(): Statement[] {
    const statements: Statement[] = [];

    while (!this.check('RBRACE') && !this.isAtEnd()) {
      this.skipNewlines();

      if (this.check('RBRACE')) break;

      statements.push(this.parseStatement());
    }

    return statements;
  }

  /**
   * Parse an expression statement.
   * expr;
   */
  private parseExpressionStatement(): Statement {
    const start = this.peek();
    const expression = this.parseExpression();

    this.consumeSemicolon();

    return {
      type: 'ExpressionStatement',
      expression,
      location: this.getLocationFrom(start),
    };
  }

  // ============================================================================
  // Expressions
  // ============================================================================

  /**
   * Parse an expression with proper precedence handling.
   */
  private parseExpression(minPrecedence: Precedence = Precedence.NONE): Expression {
    return this.parseBinaryExpression(minPrecedence);
  }

  /**
   * Parse binary expression with precedence climbing.
   */
  private parseBinaryExpression(minPrecedence: Precedence): Expression {
    let left = this.parseUnaryExpression();

    while (true) {
      const tokenType = this.peek().type;
      const precedence = BINARY_PRECEDENCE[tokenType] ?? Precedence.NONE;

      if (precedence <= minPrecedence) {
        break;
      }

      const operator = this.advance();
      const right = this.parseBinaryExpression(precedence);

      left = {
        type: 'BinaryExpression',
        operator: operator.type,
        left,
        right,
        location: this.getLocationFrom(operator),
      };
    }

    return left;
  }

  /**
   * Parse unary expression.
   * !expr, -expr, ~expr, &expr, *expr
   */
  private parseUnaryExpression(): Expression {
    const unaryOps: Set<TokenType> = new Set(['BANG', 'MINUS', 'TILDE', 'AMPERSAND', 'STAR']);

    if (unaryOps.has(this.peek().type)) {
      const operator = this.advance();
      const operand = this.parseUnaryExpression();

      return {
        type: 'UnaryExpression',
        operator: operator.type,
        operand,
        location: this.getLocationFrom(operator),
      };
    }

    return this.parsePostfixExpression();
  }

  /**
   * Parse postfix expression (call, index, member access).
   */
  private parsePostfixExpression(): Expression {
    let expr = this.parsePrimaryExpression();

    while (true) {
      // Function call
      if (this.match('LPAREN')) {
        expr = this.parseCallExpression(expr);
      }
      // Array/index access
      else if (this.match('LBRACKET')) {
        expr = this.parseIndexExpression(expr);
      }
      // Member access
      else if (this.match('DOT')) {
        expr = this.parseMemberExpression(expr);
      }
      else {
        break;
      }
    }

    return expr;
  }

  /**
   * Parse primary expression (literals, identifiers, grouping).
   */
  private parsePrimaryExpression(): Expression {
    const token = this.peek();

    // Literals
    if (this.check('NUMBER')) {
      this.advance();
      return {
        type: 'NumberLiteral',
        value: token.value as number,
        location: this.getLocationFrom(token),
      };
    }

    if (this.check('STRING')) {
      this.advance();
      return {
        type: 'StringLiteral',
        value: token.value as string,
        location: this.getLocationFrom(token),
      };
    }

    if (this.check('TRUE') || this.check('FALSE')) {
      this.advance();
      return {
        type: 'BooleanLiteral',
        value: token.type === 'TRUE',
        location: this.getLocationFrom(token),
      };
    }

    // Identifier
    if (this.check('IDENT')) {
      this.advance();
      return {
        type: 'Identifier',
        name: token.value as string,
        location: this.getLocationFrom(token),
      };
    }

    // Grouped expression
    if (this.match('LPAREN')) {
      const expr = this.parseExpression();
      this.consume('RPAREN', "Expected ')' after expression");
      return expr;
    }

    throw this.error(`Unexpected token in expression: ${token.type}`);
  }

  /**
   * Parse function call expression.
   */
  private parseCallExpression(callee: Expression): Expression {
    const args: Expression[] = [];

    if (!this.check('RPAREN')) {
      do {
        args.push(this.parseExpression());
      } while (this.match('COMMA'));
    }

    const closeParen = this.consume('RPAREN', "Expected ')' after arguments");

    return {
      type: 'CallExpression',
      callee,
      args,
      location: this.getLocationFrom(closeParen),
    };
  }

  /**
   * Parse index expression.
   */
  private parseIndexExpression(object: Expression): Expression {
    const index = this.parseExpression();
    const closeBracket = this.consume('RBRACKET', "Expected ']' after index");

    return {
      type: 'IndexExpression',
      object,
      index,
      location: this.getLocationFrom(closeBracket),
    };
  }

  /**
   * Parse member access expression.
   */
  private parseMemberExpression(object: Expression): Expression {
    const property = this.consume('IDENT', 'Expected property name after "."');

    return {
      type: 'MemberExpression',
      object,
      property: property.value as string,
      location: this.getLocationFrom(property),
    };
  }

  // ============================================================================
  // Type annotations
  // ============================================================================

  /**
   * Parse a type annotation.
   */
  private parseType(): TypeAnnotation {
    const start = this.peek();

    // Named type
    if (this.check('IDENT')) {
      const name = this.advance();

      // Generic type arguments
      if (this.match('LT')) {
        const typeArgs: TypeAnnotation[] = [];

        do {
          typeArgs.push(this.parseType());
        } while (this.match('COMMA'));

        this.consume('GT', "Expected '>' after type arguments");

        return {
          type: 'GenericType',
          name: name.value as string,
          typeArgs,
          location: this.getLocationFrom(start),
        };
      }

      return {
        type: 'NamedType',
        name: name.value as string,
        location: this.getLocationFrom(start),
      };
    }

    // Array type
    if (this.match('LBRACKET')) {
      const elementType = this.parseType();
      this.consume('RBRACKET', "Expected ']' after array type");

      return {
        type: 'ArrayType',
        elementType,
        location: this.getLocationFrom(start),
      };
    }

    throw this.error('Expected type annotation');
  }

  // ============================================================================
  // Helper methods
  // ============================================================================

  /**
   * Check if current token matches the expected type.
   */
  private check(type: TokenType): boolean {
    if (this.isAtEnd()) return false;
    return this.peek().type === type;
  }

  /**
   * Consume current token if it matches expected type.
   */
  private match(...types: TokenType[]): boolean {
    for (const type of types) {
      if (this.check(type)) {
        this.advance();
        return true;
      }
    }
    return false;
  }

  /**
   * Consume current token and verify it matches expected type.
   */
  private consume(type: TokenType, message: string): Token {
    if (this.check(type)) {
      return this.advance();
    }

    throw new ExpectedTokenError(type, this.peek(), message);
  }

  /**
   * Advance to next token.
   */
  private advance(): Token {
    if (!this.isAtEnd()) {
      this.current++;
    }
    return this.previous();
  }

  /**
   * Check if at end of token stream.
   */
  private isAtEnd(): boolean {
    return this.peek().type === 'EOF';
  }

  /**
   * Get current token without consuming.
   */
  private peek(): Token {
    return this.tokens[this.current];
  }

  /**
   * Get previous token.
   */
  private previous(): Token {
    return this.tokens[this.current - 1];
  }

  /**
   * Skip newline tokens.
   */
  private skipNewlines(): void {
    while (this.match('NEWLINE')) {
      // Skip
    }
  }

  /**
   * Consume optional semicolon (or newline in non-strict mode).
   */
  private consumeSemicolon(): void {
    if (this.match('SEMICOLON', 'NEWLINE')) {
      return;
    }

    // In non-strict mode, allow implicit semicolons at EOF or before }
    if (!this.options.strictMode) {
      if (this.isAtEnd() || this.check('RBRACE')) {
        return;
      }
    }

    throw this.error("Expected ';' after statement");
  }

  /**
   * Create parse error at current position.
   */
  private error(message: string): ParseError {
    const token = this.peek();
    return new SyntaxError(message, {
      line: token.line,
      column: token.column,
      offset: token.offset || 0,
    }, token);
  }

  /**
   * Handle parse error with optional recovery.
   */
  private handleError(error: ParseError): void {
    this.errors.push(error);

    // Check if we've hit max errors
    if (this.errors.length >= this.options.maxErrors) {
      throw new ParseErrorCollection(this.errors);
    }
  }

  /**
   * Synchronize parser state after error.
   */
  private synchronize(): void {
    this.advance();

    while (!this.isAtEnd()) {
      // Stop at statement boundaries
      if (this.previous().type === 'SEMICOLON') {
        return;
      }

      // Stop at sync tokens
      if (SYNC_TOKENS.has(this.peek().type)) {
        return;
      }

      this.advance();
    }
  }

  /**
   * Get current source location.
   */
  private getLocation() {
    const token = this.peek();
    return {
      line: token.line,
      column: token.column,
      offset: token.offset || 0,
    };
  }

  /**
   * Get source location from start token to current position.
   */
  private getLocationFrom(start: Token) {
    return {
      line: start.line,
      column: start.column,
      offset: start.offset || 0,
    };
  }
}
