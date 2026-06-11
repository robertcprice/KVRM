/**
 * KVRM Semantic Error Definitions
 *
 * Comprehensive error types for semantic analysis with:
 * - Detailed error messages
 * - Source location tracking
 * - Helpful suggestions for common mistakes
 * - Error severity levels
 */

import { Type } from './types';
import type { SourceLocation } from './types';

export enum ErrorSeverity {
  Error = 'error',
  Warning = 'warning',
  Info = 'info',
}

/**
 * Base class for all semantic errors
 */
export abstract class SemanticError extends Error {
  abstract readonly code: string;
  abstract readonly severity: ErrorSeverity;

  constructor(
    message: string,
    public location: SourceLocation,
    public suggestions: string[] = []
  ) {
    super(message);
    this.name = this.constructor.name;
    Object.setPrototypeOf(this, new.target.prototype);
  }

  /**
   * Format error for display with location and suggestions
   */
  format(): string {
    const loc = `${this.location.file || '<unknown>'}:${this.location.line}:${this.location.column}`;
    let output = `${this.severity}: [${this.code}] ${this.message}\n`;
    output += `  --> ${loc}\n`;

    if (this.suggestions.length > 0) {
      output += '\nSuggestions:\n';
      for (const suggestion of this.suggestions) {
        output += `  - ${suggestion}\n`;
      }
    }

    return output;
  }
}

/**
 * Type mismatch error
 */
export class TypeError extends SemanticError {
  readonly code = 'E0001';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public expected: Type,
    public actual: Type,
    location: SourceLocation,
    context?: string
  ) {
    const contextMsg = context ? ` ${context}` : '';
    super(
      `Type mismatch${contextMsg}: expected '${expected.toString()}', found '${actual.toString()}'`,
      location,
      TypeError.generateSuggestions(expected, actual)
    );
  }

  private static generateSuggestions(expected: Type, actual: Type): string[] {
    const suggestions: string[] = [];

    // Suggest explicit cast for numeric types
    if (
      expected.kind === 'Primitive' &&
      actual.kind === 'Primitive'
    ) {
      suggestions.push(
        `Consider using an explicit cast: 'value as ${expected.toString()}'`
      );
    }

    // Suggest adding reference or dereference
    if (actual.toString().includes('&') && !expected.toString().includes('&')) {
      suggestions.push('Did you mean to dereference with *?');
    } else if (
      !actual.toString().includes('&') &&
      expected.toString().includes('&')
    ) {
      suggestions.push('Did you mean to take a reference with &?');
    }

    return suggestions;
  }
}

/**
 * Binary operation type error
 */
export class BinaryOpTypeError extends SemanticError {
  readonly code = 'E0002';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public operator: string,
    public leftType: Type,
    public rightType: Type,
    location: SourceLocation
  ) {
    super(
      `Binary operator '${operator}' cannot be applied to types '${leftType.toString()}' and '${rightType.toString()}'`,
      location,
      BinaryOpTypeError.generateSuggestions(operator, leftType, rightType)
    );
  }

  private static generateSuggestions(
    op: string,
    left: Type,
    right: Type
  ): string[] {
    const suggestions: string[] = [];

    // Numeric operator on non-numeric types
    if (['+', '-', '*', '/', '%'].includes(op)) {
      if (left.kind !== 'Primitive' || right.kind !== 'Primitive') {
        suggestions.push('This operator requires numeric types');
      } else {
        suggestions.push(
          `Convert both operands to the same numeric type (e.g., both as ${left.toString()})`
        );
      }
    }

    // Comparison operators
    if (['==', '!=', '<', '>', '<=', '>='].includes(op)) {
      if (!left.equals(right)) {
        suggestions.push(
          'Comparison operators require both operands to be the same type'
        );
      }
    }

    return suggestions;
  }
}

/**
 * Unary operation type error
 */
export class UnaryOpTypeError extends SemanticError {
  readonly code = 'E0003';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public operator: string,
    public operandType: Type,
    location: SourceLocation
  ) {
    super(
      `Unary operator '${operator}' cannot be applied to type '${operandType.toString()}'`,
      location,
      UnaryOpTypeError.generateSuggestions(operator, operandType)
    );
  }

  private static generateSuggestions(op: string, type: Type): string[] {
    const suggestions: string[] = [];

    if (op === '-' || op === '+') {
      suggestions.push('This operator requires a numeric type');
    } else if (op === '!') {
      suggestions.push('This operator requires a boolean type');
    }

    return suggestions;
  }
}

/**
 * Undefined symbol error
 */
export class UndefinedSymbolError extends SemanticError {
  readonly code = 'E0004';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public symbolName: string,
    location: SourceLocation,
    public similarNames: string[] = []
  ) {
    super(
      `Cannot find symbol '${symbolName}' in this scope`,
      location,
      UndefinedSymbolError.generateSuggestions(symbolName, similarNames)
    );
  }

  private static generateSuggestions(
    name: string,
    similarNames: string[]
  ): string[] {
    const suggestions: string[] = [];

    if (similarNames.length > 0) {
      const closest = similarNames[0];
      suggestions.push(`Did you mean '${closest}'?`);

      if (similarNames.length > 1) {
        suggestions.push(
          `Other similar names: ${similarNames.slice(1).join(', ')}`
        );
      }
    }

    suggestions.push('Make sure the symbol is declared before use');
    suggestions.push('Check for typos in the symbol name');

    return suggestions;
  }
}

/**
 * Symbol redefinition error
 */
export class RedefinitionError extends SemanticError {
  readonly code = 'E0005';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public symbolName: string,
    location: SourceLocation,
    public previousLocation?: SourceLocation
  ) {
    const prevMsg = previousLocation
      ? ` (previously defined at line ${previousLocation.line})`
      : '';
    super(
      `Symbol '${symbolName}' is already defined in this scope${prevMsg}`,
      location,
      ['Use a different name', 'Remove the duplicate definition']
    );
  }
}

/**
 * Mutability error
 */
export class MutabilityError extends SemanticError {
  readonly code = 'E0006';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public symbolName: string,
    location: SourceLocation,
    public operation: 'assign' | 'borrow_mut'
  ) {
    const action =
      operation === 'assign' ? 'assign to' : 'mutably borrow';
    super(
      `Cannot ${action} immutable variable '${symbolName}'`,
      location,
      [
        `Declare '${symbolName}' as mutable: 'let mut ${symbolName} = ...'`,
        'Immutable variables cannot be modified after initialization',
      ]
    );
  }
}

/**
 * Assignment to immutable field error
 */
export class ImmutableFieldError extends SemanticError {
  readonly code = 'E0007';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public structName: string,
    public fieldName: string,
    location: SourceLocation
  ) {
    super(
      `Cannot assign to immutable field '${fieldName}' of struct '${structName}'`,
      location,
      [
        `Mark field as mutable in struct definition: 'mut ${fieldName}: ...'`,
        'Consider making the entire struct mutable if all fields need mutation',
      ]
    );
  }
}

/**
 * Ownership/borrowing error
 */
export class OwnershipError extends SemanticError {
  readonly code = 'E0008';
  readonly severity = ErrorSeverity.Error;

  constructor(
    message: string,
    location: SourceLocation,
    suggestions: string[] = []
  ) {
    super(message, location, suggestions);
  }

  static moveAfterMove(
    symbolName: string,
    location: SourceLocation,
    moveLocation: SourceLocation
  ): OwnershipError {
    return new OwnershipError(
      `Use of moved value '${symbolName}' (moved at line ${moveLocation.line})`,
      location,
      [
        `Value was moved at line ${moveLocation.line} and can no longer be used`,
        `Consider cloning the value: '${symbolName}.clone()'`,
        `Use a reference instead: '&${symbolName}'`,
      ]
    );
  }

  static borrowWhileMutablyBorrowed(
    symbolName: string,
    location: SourceLocation
  ): OwnershipError {
    return new OwnershipError(
      `Cannot borrow '${symbolName}' as immutable because it is already mutably borrowed`,
      location,
      [
        'A value cannot be borrowed immutably while a mutable borrow exists',
        'Consider restructuring code to avoid simultaneous borrows',
      ]
    );
  }

  static mutablyBorrowWhileBorrowed(
    symbolName: string,
    location: SourceLocation
  ): OwnershipError {
    return new OwnershipError(
      `Cannot borrow '${symbolName}' as mutable because it is already borrowed`,
      location,
      [
        'A value cannot be mutably borrowed while any borrows exist',
        'Only one mutable borrow is allowed at a time',
      ]
    );
  }
}

/**
 * Invalid field access error
 */
export class FieldAccessError extends SemanticError {
  readonly code = 'E0009';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public typeName: string,
    public fieldName: string,
    location: SourceLocation,
    public availableFields: string[] = []
  ) {
    super(
      `Type '${typeName}' has no field named '${fieldName}'`,
      location,
      FieldAccessError.generateSuggestions(fieldName, availableFields)
    );
  }

  private static generateSuggestions(
    field: string,
    available: string[]
  ): string[] {
    const suggestions: string[] = [];

    // Find similar field names using Levenshtein distance
    const similar = available
      .map((name) => ({ name, dist: levenshteinDistance(field, name) }))
      .filter((item) => item.dist <= 2)
      .sort((a, b) => a.dist - b.dist)
      .map((item) => item.name);

    if (similar.length > 0) {
      suggestions.push(`Did you mean '${similar[0]}'?`);
    }

    if (available.length > 0) {
      suggestions.push(`Available fields: ${available.join(', ')}`);
    }

    return suggestions;
  }
}

/**
 * Invalid method call error
 */
export class MethodCallError extends SemanticError {
  readonly code = 'E0010';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public typeName: string,
    public methodName: string,
    location: SourceLocation
  ) {
    super(
      `Type '${typeName}' has no method named '${methodName}'`,
      location,
      ['Check the type\'s available methods', 'Ensure required traits are implemented']
    );
  }
}

/**
 * Function argument count mismatch error
 */
export class ArgumentCountError extends SemanticError {
  readonly code = 'E0011';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public functionName: string,
    public expected: number,
    public actual: number,
    location: SourceLocation
  ) {
    super(
      `Function '${functionName}' expects ${expected} argument(s), but ${actual} were provided`,
      location,
      [
        expected > actual
          ? `Add ${expected - actual} more argument(s)`
          : `Remove ${actual - expected} argument(s)`,
      ]
    );
  }
}

/**
 * Return type mismatch error
 */
export class ReturnTypeError extends SemanticError {
  readonly code = 'E0012';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public expected: Type,
    public actual: Type,
    location: SourceLocation
  ) {
    super(
      `Function returns '${actual.toString()}' but expected '${expected.toString()}'`,
      location,
      ['Ensure all return statements match the function signature']
    );
  }
}

/**
 * Missing return statement error
 */
export class MissingReturnError extends SemanticError {
  readonly code = 'E0013';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public functionName: string,
    public returnType: Type,
    location: SourceLocation
  ) {
    super(
      `Function '${functionName}' must return a value of type '${returnType.toString()}'`,
      location,
      [
        'Add a return statement at the end of the function',
        'Ensure all code paths return a value',
      ]
    );
  }
}

/**
 * Type parameter error
 */
export class TypeParameterError extends SemanticError {
  readonly code = 'E0014';
  readonly severity = ErrorSeverity.Error;

  constructor(
    message: string,
    location: SourceLocation,
    suggestions: string[] = []
  ) {
    super(message, location, suggestions);
  }

  static wrongCount(
    name: string,
    expected: number,
    actual: number,
    location: SourceLocation
  ): TypeParameterError {
    return new TypeParameterError(
      `'${name}' expects ${expected} type parameter(s), but ${actual} were provided`,
      location,
      [
        expected > actual
          ? `Add ${expected - actual} more type parameter(s)`
          : `Remove ${actual - expected} type parameter(s)`,
      ]
    );
  }

  static boundViolation(
    paramName: string,
    actualType: Type,
    bound: Type,
    location: SourceLocation
  ): TypeParameterError {
    return new TypeParameterError(
      `Type '${actualType.toString()}' does not satisfy bound '${bound.toString()}' for type parameter '${paramName}'`,
      location,
      [
        'Ensure the type argument implements all required traits',
        `Type parameter bound: ${paramName}: ${bound.toString()}`,
      ]
    );
  }
}

/**
 * Array index error
 */
export class ArrayIndexError extends SemanticError {
  readonly code = 'E0015';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public indexType: Type,
    location: SourceLocation
  ) {
    super(
      `Array index must be an integer type, found '${indexType.toString()}'`,
      location,
      ['Use an integer type for array indexing (i32, u32, usize, etc.)']
    );
  }
}

/**
 * Break/continue outside loop error
 */
export class ControlFlowError extends SemanticError {
  readonly code = 'E0016';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public keyword: 'break' | 'continue',
    location: SourceLocation
  ) {
    super(
      `'${keyword}' statement used outside of loop`,
      location,
      [`'${keyword}' can only be used inside while, for, or loop statements`]
    );
  }
}

/**
 * Pattern matching exhaustiveness error
 */
export class NonExhaustivePatternError extends SemanticError {
  readonly code = 'E0017';
  readonly severity = ErrorSeverity.Error;

  constructor(
    public missingPatterns: string[],
    location: SourceLocation
  ) {
    super(
      `Pattern matching is not exhaustive. Missing patterns: ${missingPatterns.join(', ')}`,
      location,
      [
        'Add cases for missing patterns',
        "Add a wildcard pattern '_' to catch all remaining cases",
      ]
    );
  }
}

/**
 * Warning for unused variable
 */
export class UnusedVariableWarning extends SemanticError {
  readonly code = 'W0001';
  readonly severity = ErrorSeverity.Warning;

  constructor(
    public variableName: string,
    location: SourceLocation
  ) {
    super(
      `Variable '${variableName}' is never used`,
      location,
      [
        'Remove the unused variable',
        `Prefix with '_' to suppress warning: '_${variableName}'`,
      ]
    );
  }
}

/**
 * Warning for unreachable code
 */
export class UnreachableCodeWarning extends SemanticError {
  readonly code = 'W0002';
  readonly severity = ErrorSeverity.Warning;

  constructor(location: SourceLocation) {
    super(
      'Unreachable code detected',
      location,
      ['Remove unreachable code', 'Check for early returns or breaks']
    );
  }
}

/**
 * Error collector for accumulating multiple errors
 */
export class ErrorCollector {
  private errors: SemanticError[] = [];
  private warnings: SemanticError[] = [];

  add(error: SemanticError): void {
    if (error.severity === ErrorSeverity.Error) {
      this.errors.push(error);
    } else if (error.severity === ErrorSeverity.Warning) {
      this.warnings.push(error);
    }
  }

  hasErrors(): boolean {
    return this.errors.length > 0;
  }

  hasWarnings(): boolean {
    return this.warnings.length > 0;
  }

  getErrors(): SemanticError[] {
    return [...this.errors];
  }

  getWarnings(): SemanticError[] {
    return [...this.warnings];
  }

  getAllIssues(): SemanticError[] {
    return [...this.errors, ...this.warnings];
  }

  clear(): void {
    this.errors = [];
    this.warnings = [];
  }

  /**
   * Format all errors and warnings for display
   */
  formatAll(): string {
    const all = this.getAllIssues();
    if (all.length === 0) return '';

    let output = '';
    for (const issue of all) {
      output += issue.format() + '\n';
    }

    const errorCount = this.errors.length;
    const warningCount = this.warnings.length;

    output += '\n';
    if (errorCount > 0) {
      output += `${errorCount} error(s) found`;
    }
    if (warningCount > 0) {
      if (errorCount > 0) output += ', ';
      output += `${warningCount} warning(s) found`;
    }

    return output;
  }
}

/**
 * Compute Levenshtein distance between two strings for spell-checking
 */
function levenshteinDistance(a: string, b: string): number {
  const matrix: number[][] = [];

  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }

  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1, // insertion
          matrix[i - 1][j] + 1 // deletion
        );
      }
    }
  }

  return matrix[b.length][a.length];
}
