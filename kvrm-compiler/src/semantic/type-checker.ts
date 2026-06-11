/**
 * KVRM Type Checker
 *
 * Comprehensive type checking with:
 * - Expression type inference
 * - Statement type validation
 * - Binary/unary operator type checking
 * - Function call type checking
 * - Type unification and compatibility
 */

import {
  Type,
  PrimitiveType,
  ArrayType,
  StructType,
  EnumType,
  FunctionType,
  TypeParameter,
  GenericInstanceType,
  TupleType,
  VoidType,
  NeverType,
  UnknownType,
  BuiltinTypes,
  TypeUtils,
  TypeKind,
  PrimitiveTypeKind,
  type SourceLocation,
} from './types';

import {
  TypeError,
  BinaryOpTypeError,
  UnaryOpTypeError,
  UndefinedSymbolError,
  ArgumentCountError,
  ReturnTypeError,
  FieldAccessError,
  ArrayIndexError,
  MutabilityError,
  ErrorCollector,
} from './errors';

import { SymbolTable, SymbolKind } from './symbol-table';

import type {
  Expression,
  Statement,
  BinaryExpression,
  UnaryExpression,
  CallExpression,
  MemberExpression,
  IndexExpression,
  AssignmentExpression,
  Identifier,
  NumberLiteral,
  StringLiteral,
  BooleanLiteral,
  ArrayExpression,
  StructExpression,
  BinaryOperator,
  UnaryOperator,
} from '../types/ast';

/**
 * Type checker for expressions and statements
 */
export class TypeChecker {
  constructor(
    private symbolTable: SymbolTable,
    private errors: ErrorCollector
  ) {}

  /**
   * Check expression and return its type
   */
  checkExpression(expr: Expression): Type {
    switch (expr.kind) {
      case 'BinaryExpression':
        return this.checkBinaryExpression(expr as BinaryExpression);

      case 'UnaryExpression':
        return this.checkUnaryExpression(expr as UnaryExpression);

      case 'CallExpression':
        return this.checkCallExpression(expr as CallExpression);

      case 'MemberExpression':
        return this.checkMemberExpression(expr as MemberExpression);

      case 'IndexExpression':
        return this.checkIndexExpression(expr as IndexExpression);

      case 'AssignmentExpression':
        return this.checkAssignmentExpression(expr as AssignmentExpression);

      case 'Identifier':
        return this.checkIdentifier(expr as Identifier);

      case 'NumberLiteral':
        return this.checkNumberLiteral(expr as NumberLiteral);

      case 'StringLiteral':
        return this.checkStringLiteral(expr as StringLiteral);

      case 'BooleanLiteral':
        return this.checkBooleanLiteral(expr as BooleanLiteral);

      case 'CharLiteral':
        return BuiltinTypes.char;

      case 'NullLiteral':
        // Null type would need special handling in a real implementation
        return BuiltinTypes.unknown;

      case 'ArrayExpression':
        return this.checkArrayExpression(expr as ArrayExpression);

      case 'StructExpression':
        return this.checkStructExpression(expr as StructExpression);

      case 'CastExpression':
        // For cast expressions, return the target type
        // In a full implementation, validate cast is valid
        return BuiltinTypes.unknown;

      default:
        return BuiltinTypes.unknown;
    }
  }

  /**
   * Check binary expression (e.g., a + b, x == y)
   */
  private checkBinaryExpression(expr: BinaryExpression): Type {
    const leftType = this.checkExpression(expr.left);
    const rightType = this.checkExpression(expr.right);

    const op = this.mapBinaryOperator(expr.operator);

    // Arithmetic operators: +, -, *, /, %
    if (['+', '-', '*', '/', '%'].includes(op)) {
      return this.checkArithmeticOp(op, leftType, rightType, expr.location);
    }

    // Comparison operators: ==, !=, <, >, <=, >=
    if (['==', '!=', '<', '>', '<=', '>='].includes(op)) {
      return this.checkComparisonOp(op, leftType, rightType, expr.location);
    }

    // Logical operators: &&, ||
    if (['&&', '||'].includes(op)) {
      return this.checkLogicalOp(op, leftType, rightType, expr.location);
    }

    // Bitwise operators: &, |, ^, <<, >>
    if (['&', '|', '^', '<<', '>>'].includes(op)) {
      return this.checkBitwiseOp(op, leftType, rightType, expr.location);
    }

    this.errors.add(
      new BinaryOpTypeError(op, leftType, rightType, expr.location)
    );
    return BuiltinTypes.unknown;
  }

  /**
   * Map AST binary operator to string representation
   */
  private mapBinaryOperator(op: BinaryOperator): string {
    const opMap: Record<string, string> = {
      Add: '+',
      Subtract: '-',
      Multiply: '*',
      Divide: '/',
      Modulo: '%',
      Equal: '==',
      NotEqual: '!=',
      LessThan: '<',
      LessThanOrEqual: '<=',
      GreaterThan: '>',
      GreaterThanOrEqual: '>=',
      LogicalAnd: '&&',
      LogicalOr: '||',
      BitwiseAnd: '&',
      BitwiseOr: '|',
      BitwiseXor: '^',
      LeftShift: '<<',
      RightShift: '>>',
    };
    return opMap[op as unknown as string] || '?';
  }

  /**
   * Map AST unary operator to string representation
   */
  private mapUnaryOperator(op: UnaryOperator): string {
    const opMap: Record<string, string> = {
      Not: '!',
      Negate: '-',
      BitwiseNot: '~',
      Reference: '&',
      Dereference: '*',
    };
    return opMap[op as unknown as string] || '?';
  }

  /**
   * Check arithmetic operation
   */
  private checkArithmeticOp(
    op: string,
    left: Type,
    right: Type,
    location: SourceLocation
  ): Type {
    // Both operands must be numeric
    if (!TypeUtils.isNumeric(left) || !TypeUtils.isNumeric(right)) {
      this.errors.add(new BinaryOpTypeError(op, left, right, location));
      return BuiltinTypes.unknown;
    }

    // Get common type
    const commonType = TypeUtils.getCommonType(left, right);
    if (!commonType) {
      this.errors.add(new BinaryOpTypeError(op, left, right, location));
      return BuiltinTypes.unknown;
    }

    return commonType;
  }

  /**
   * Check comparison operation
   */
  private checkComparisonOp(
    op: string,
    left: Type,
    right: Type,
    location: SourceLocation
  ): Type {
    // Operands must be compatible
    if (!left.isAssignableTo(right) && !right.isAssignableTo(left)) {
      this.errors.add(new BinaryOpTypeError(op, left, right, location));
      return BuiltinTypes.unknown;
    }

    // Comparison always returns bool
    return BuiltinTypes.bool;
  }

  /**
   * Check logical operation (&&, ||)
   */
  private checkLogicalOp(
    op: string,
    left: Type,
    right: Type,
    location: SourceLocation
  ): Type {
    // Both operands must be bool
    if (!left.equals(BuiltinTypes.bool) || !right.equals(BuiltinTypes.bool)) {
      this.errors.add(new BinaryOpTypeError(op, left, right, location));
      return BuiltinTypes.unknown;
    }

    return BuiltinTypes.bool;
  }

  /**
   * Check bitwise operation
   */
  private checkBitwiseOp(
    op: string,
    left: Type,
    right: Type,
    location: SourceLocation
  ): Type {
    // Both operands must be integers
    if (!TypeUtils.isInteger(left) || !TypeUtils.isInteger(right)) {
      this.errors.add(new BinaryOpTypeError(op, left, right, location));
      return BuiltinTypes.unknown;
    }

    // For shifts, return left type; for others, return common type
    if (op === '<<' || op === '>>') {
      return left;
    }

    const commonType = TypeUtils.getCommonType(left, right);
    if (!commonType) {
      this.errors.add(new BinaryOpTypeError(op, left, right, location));
      return BuiltinTypes.unknown;
    }

    return commonType;
  }

  /**
   * Check unary expression (e.g., -x, !bool, &var)
   */
  private checkUnaryExpression(expr: UnaryExpression): Type {
    const operandType = this.checkExpression(expr.operand);
    const op = this.mapUnaryOperator(expr.operator);

    switch (op) {
      case '-':
      case '+':
        // Numeric negation
        if (!TypeUtils.isNumeric(operandType)) {
          this.errors.add(
            new UnaryOpTypeError(op, operandType, expr.location)
          );
          return BuiltinTypes.unknown;
        }
        return operandType;

      case '!':
        // Logical not
        if (!operandType.equals(BuiltinTypes.bool)) {
          this.errors.add(
            new UnaryOpTypeError(op, operandType, expr.location)
          );
          return BuiltinTypes.unknown;
        }
        return BuiltinTypes.bool;

      case '~':
        // Bitwise not
        if (!TypeUtils.isInteger(operandType)) {
          this.errors.add(
            new UnaryOpTypeError(op, operandType, expr.location)
          );
          return BuiltinTypes.unknown;
        }
        return operandType;

      case '&':
        // Reference operator - return reference type (simplified)
        return operandType;

      case '*':
        // Dereference operator - return dereferenced type (simplified)
        return operandType;

      default:
        this.errors.add(new UnaryOpTypeError(op, operandType, expr.location));
        return BuiltinTypes.unknown;
    }
  }

  /**
   * Check function call expression
   */
  private checkCallExpression(expr: CallExpression): Type {
    const calleeType = this.checkExpression(expr.callee);

    // Callee must be a function type
    if (!TypeUtils.isFunction(calleeType)) {
      this.errors.add(
        new TypeError(
          BuiltinTypes.unknown,
          calleeType,
          expr.location,
          'in function call - callee must be a function'
        )
      );
      return BuiltinTypes.unknown;
    }

    const fnType = calleeType as FunctionType;

    // Check argument count
    if (expr.arguments.length !== fnType.paramTypes.length) {
      const functionName =
        expr.callee.kind === 'Identifier'
          ? (expr.callee as Identifier).name
          : '<anonymous>';

      this.errors.add(
        new ArgumentCountError(
          functionName,
          fnType.paramTypes.length,
          expr.arguments.length,
          expr.location
        )
      );
      return BuiltinTypes.unknown;
    }

    // Check each argument type
    for (let i = 0; i < expr.arguments.length; i++) {
      const argType = this.checkExpression(expr.arguments[i]);
      const paramType = fnType.paramTypes[i];

      if (!argType.isAssignableTo(paramType)) {
        this.errors.add(
          new TypeError(
            paramType,
            argType,
            expr.arguments[i].location,
            `in argument ${i + 1}`
          )
        );
      }
    }

    return fnType.returnType;
  }

  /**
   * Check member access expression (e.g., obj.field)
   */
  private checkMemberExpression(expr: MemberExpression): Type {
    const objectType = this.checkExpression(expr.object);

    // Object must be a struct
    if (!TypeUtils.isStruct(objectType)) {
      this.errors.add(
        new TypeError(
          BuiltinTypes.unknown,
          objectType,
          expr.location,
          'member access requires struct type'
        )
      );
      return BuiltinTypes.unknown;
    }

    const structType = objectType as StructType;
    const fieldName = expr.member.name;
    const field = structType.getField(fieldName);

    if (!field) {
      const availableFields = Array.from(structType.fields.keys());
      this.errors.add(
        new FieldAccessError(
          structType.name,
          fieldName,
          expr.location,
          availableFields
        )
      );
      return BuiltinTypes.unknown;
    }

    return field.type;
  }

  /**
   * Check array index expression (e.g., arr[i])
   */
  private checkIndexExpression(expr: IndexExpression): Type {
    const arrayType = this.checkExpression(expr.object);
    const indexType = this.checkExpression(expr.index);

    // Object must be an array
    if (!TypeUtils.isArray(arrayType)) {
      this.errors.add(
        new TypeError(
          BuiltinTypes.unknown,
          arrayType,
          expr.location,
          'index access requires array type'
        )
      );
      return BuiltinTypes.unknown;
    }

    // Index must be an integer
    if (!TypeUtils.isInteger(indexType)) {
      this.errors.add(new ArrayIndexError(indexType, expr.index.location));
      return BuiltinTypes.unknown;
    }

    return (arrayType as ArrayType).elementType;
  }

  /**
   * Check assignment expression
   */
  private checkAssignmentExpression(expr: AssignmentExpression): Type {
    const targetType = this.checkExpression(expr.target);
    const valueType = this.checkExpression(expr.value);

    // Check if target is mutable
    if (expr.target.kind === 'Identifier') {
      const name = (expr.target as Identifier).name;
      const symbol = this.symbolTable.lookup(name);

      if (symbol && !symbol.flags.mutable) {
        this.errors.add(
          new MutabilityError(name, expr.location, 'assign')
        );
      }
    }

    // Check type compatibility
    if (!valueType.isAssignableTo(targetType)) {
      this.errors.add(
        new TypeError(
          targetType,
          valueType,
          expr.location,
          'in assignment'
        )
      );
    }

    return targetType;
  }

  /**
   * Check identifier expression
   */
  private checkIdentifier(expr: Identifier): Type {
    const symbol = this.symbolTable.lookup(expr.name);

    if (!symbol) {
      const similar = this.symbolTable.findSimilarNames(expr.name);
      this.errors.add(
        new UndefinedSymbolError(expr.name, expr.location, similar)
      );
      return BuiltinTypes.unknown;
    }

    // Mark symbol as used
    this.symbolTable.markUsed(expr.name);

    return symbol.type;
  }

  /**
   * Check number literal
   */
  private checkNumberLiteral(expr: NumberLiteral): Type {
    // Infer type from literal format
    const raw = expr.raw.toLowerCase();

    // Check for explicit type suffix
    if (raw.endsWith('i8')) return BuiltinTypes.i8;
    if (raw.endsWith('i16')) return BuiltinTypes.i16;
    if (raw.endsWith('i32')) return BuiltinTypes.i32;
    if (raw.endsWith('i64')) return BuiltinTypes.i64;
    if (raw.endsWith('u8')) return BuiltinTypes.u8;
    if (raw.endsWith('u16')) return BuiltinTypes.u16;
    if (raw.endsWith('u32')) return BuiltinTypes.u32;
    if (raw.endsWith('u64')) return BuiltinTypes.u64;
    if (raw.endsWith('f32')) return BuiltinTypes.f32;
    if (raw.endsWith('f64')) return BuiltinTypes.f64;

    // Infer from value
    if (Number.isInteger(expr.value)) {
      return BuiltinTypes.i32; // Default integer type
    } else {
      return BuiltinTypes.f64; // Default float type
    }
  }

  /**
   * Check string literal
   */
  private checkStringLiteral(expr: StringLiteral): Type {
    return BuiltinTypes.str;
  }

  /**
   * Check boolean literal
   */
  private checkBooleanLiteral(expr: BooleanLiteral): Type {
    return BuiltinTypes.bool;
  }

  /**
   * Check array literal expression
   */
  private checkArrayExpression(expr: ArrayExpression): Type {
    if (expr.elements.length === 0) {
      // Empty array - type cannot be inferred without context
      return new ArrayType(BuiltinTypes.unknown);
    }

    // Infer element type from first element
    const firstType = this.checkExpression(expr.elements[0]);

    // Check all elements have compatible types
    for (let i = 1; i < expr.elements.length; i++) {
      const elemType = this.checkExpression(expr.elements[i]);

      if (!elemType.isAssignableTo(firstType)) {
        this.errors.add(
          new TypeError(
            firstType,
            elemType,
            expr.elements[i].location,
            `in array element ${i}`
          )
        );
      }
    }

    return new ArrayType(firstType, expr.elements.length);
  }

  /**
   * Check struct literal expression
   */
  private checkStructExpression(expr: StructExpression): Type {
    const structName = expr.type.name;
    const symbol = this.symbolTable.lookup(structName);

    if (!symbol || symbol.kind !== SymbolKind.Struct) {
      this.errors.add(
        new UndefinedSymbolError(structName, expr.location, [])
      );
      return BuiltinTypes.unknown;
    }

    const structType = symbol.type as StructType;

    // Check all provided fields exist
    for (const field of expr.fields) {
      const fieldName = field.name.name;
      const structField = structType.getField(fieldName);

      if (!structField) {
        const availableFields = Array.from(structType.fields.keys());
        this.errors.add(
          new FieldAccessError(
            structName,
            fieldName,
            field.name.location,
            availableFields
          )
        );
        continue;
      }

      // Check field value type
      const valueType = this.checkExpression(field.value);
      if (!valueType.isAssignableTo(structField.type)) {
        this.errors.add(
          new TypeError(
            structField.type,
            valueType,
            field.value.location,
            `in field '${fieldName}'`
          )
        );
      }
    }

    // Check all required fields are provided
    const providedFields = new Set(expr.fields.map((f) => f.name.name));
    for (const [fieldName, field] of structType.fields) {
      if (!providedFields.has(fieldName)) {
        this.errors.add(
          new TypeError(
            field.type,
            BuiltinTypes.unknown,
            expr.location,
            `missing field '${fieldName}' in struct literal`
          )
        );
      }
    }

    return structType;
  }

  /**
   * Unify two types - find a common type or error
   */
  unify(t1: Type, t2: Type, location: SourceLocation): Type {
    if (t1.equals(t2)) return t1;

    const common = TypeUtils.getCommonType(t1, t2);
    if (common) return common;

    this.errors.add(new TypeError(t1, t2, location));
    return BuiltinTypes.unknown;
  }

  /**
   * Expect a specific type, error if different
   */
  expectType(
    expected: Type,
    actual: Type,
    location: SourceLocation,
    context?: string
  ): void {
    if (!actual.isAssignableTo(expected)) {
      this.errors.add(new TypeError(expected, actual, location, context));
    }
  }
}
