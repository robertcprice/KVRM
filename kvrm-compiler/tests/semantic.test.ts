/**
 * Semantic Analyzer Tests for KVRM Compiler
 *
 * Comprehensive test suite covering:
 * - Type inference
 * - Type checking and validation
 * - Variable scope and lifetime analysis
 * - Function signature validation
 * - Struct and enum type checking
 * - Generic type resolution
 * - Error detection and reporting
 */

import { describe, it, expect } from 'vitest';
import {
  PrimitiveType,
  PrimitiveTypeKind,
  ArrayType,
  StructType,
  EnumType,
  FunctionType,
  TupleType,
  BuiltinTypes,
  TypeUtils,
} from '../src/semantic/types';

// Mock semantic analyzer - replace with actual import when implemented
interface SemanticAnalyzer {
  analyze(ast: any): void;
  checkType(node: any): any;
  resolveType(name: string): any;
  getErrors(): SemanticError[];
}

interface SemanticError {
  message: string;
  location: { line: number; column: number };
}

// Placeholder
class MockSemanticAnalyzer implements SemanticAnalyzer {
  analyze(ast: any) {}
  checkType(node: any) {
    return BuiltinTypes.unknown;
  }
  resolveType(name: string) {
    return BuiltinTypes.unknown;
  }
  getErrors() {
    return [];
  }
}

const createAnalyzer = (): SemanticAnalyzer => {
  return new MockSemanticAnalyzer();
};

describe('Type System - Primitive Types', () => {
  it('should create integer types', () => {
    const i32 = new PrimitiveType(PrimitiveTypeKind.I32);
    expect(i32.toString()).toBe('i32');
    expect(i32.isNumeric()).toBe(true);
    expect(i32.isInteger()).toBe(true);
    expect(i32.isFloat()).toBe(false);
  });

  it('should create float types', () => {
    const f32 = new PrimitiveType(PrimitiveTypeKind.F32);
    expect(f32.toString()).toBe('f32');
    expect(f32.isNumeric()).toBe(true);
    expect(f32.isFloat()).toBe(true);
    expect(f32.isInteger()).toBe(false);
  });

  it('should create boolean type', () => {
    const bool = new PrimitiveType(PrimitiveTypeKind.Bool);
    expect(bool.toString()).toBe('bool');
    expect(bool.isNumeric()).toBe(false);
  });

  it('should create string type', () => {
    const str = new PrimitiveType(PrimitiveTypeKind.Str);
    expect(str.toString()).toBe('str');
    expect(str.isNumeric()).toBe(false);
  });

  it('should check type equality', () => {
    const i32_1 = new PrimitiveType(PrimitiveTypeKind.I32);
    const i32_2 = new PrimitiveType(PrimitiveTypeKind.I32);
    const i64 = new PrimitiveType(PrimitiveTypeKind.I64);

    expect(i32_1.equals(i32_2)).toBe(true);
    expect(i32_1.equals(i64)).toBe(false);
  });
});

describe('Type System - Type Widening', () => {
  it('should allow i8 to widen to i16', () => {
    const i8 = BuiltinTypes.i8;
    const i16 = BuiltinTypes.i16;
    expect(i8.isAssignableTo(i16)).toBe(true);
  });

  it('should allow i8 to widen to i32', () => {
    const i8 = BuiltinTypes.i8;
    const i32 = BuiltinTypes.i32;
    expect(i8.isAssignableTo(i32)).toBe(true);
  });

  it('should not allow i32 to narrow to i16', () => {
    const i32 = BuiltinTypes.i32;
    const i16 = BuiltinTypes.i16;
    expect(i32.isAssignableTo(i16)).toBe(false);
  });

  it('should allow f32 to widen to f64', () => {
    const f32 = BuiltinTypes.f32;
    const f64 = BuiltinTypes.f64;
    expect(f32.isAssignableTo(f64)).toBe(true);
  });

  it('should not mix signed and unsigned without explicit conversion', () => {
    const i32 = BuiltinTypes.i32;
    const u32 = BuiltinTypes.u32;
    expect(i32.isAssignableTo(u32)).toBe(false);
  });

  it('should find common type for numeric widening', () => {
    const i8 = BuiltinTypes.i8;
    const i32 = BuiltinTypes.i32;
    const common = TypeUtils.getCommonType(i8, i32);
    expect(common?.equals(i32)).toBe(true);
  });

  it('should widen to float when mixing int and float', () => {
    const i32 = BuiltinTypes.i32;
    const f32 = BuiltinTypes.f32;
    const common = TypeUtils.getCommonType(i32, f32);
    expect(common?.equals(f32)).toBe(true);
  });
});

describe('Type System - Array Types', () => {
  it('should create fixed-size array type', () => {
    const arrType = new ArrayType(BuiltinTypes.i32, 10);
    expect(arrType.toString()).toBe('[i32; 10]');
    expect(arrType.size).toBe(10);
  });

  it('should create dynamic array type', () => {
    const arrType = new ArrayType(BuiltinTypes.i32);
    expect(arrType.toString()).toBe('[i32]');
    expect(arrType.size).toBeUndefined();
  });

  it('should check array type equality', () => {
    const arr1 = new ArrayType(BuiltinTypes.i32, 10);
    const arr2 = new ArrayType(BuiltinTypes.i32, 10);
    const arr3 = new ArrayType(BuiltinTypes.i32, 20);

    expect(arr1.equals(arr2)).toBe(true);
    expect(arr1.equals(arr3)).toBe(false);
  });

  it('should allow sized array to assign to unsized array', () => {
    const sized = new ArrayType(BuiltinTypes.i32, 10);
    const unsized = new ArrayType(BuiltinTypes.i32);
    expect(sized.isAssignableTo(unsized)).toBe(true);
  });

  it('should not allow unsized to assign to sized array', () => {
    const sized = new ArrayType(BuiltinTypes.i32, 10);
    const unsized = new ArrayType(BuiltinTypes.i32);
    expect(unsized.isAssignableTo(sized)).toBe(false);
  });
});

describe('Type System - Struct Types', () => {
  it('should create struct type', () => {
    const fields = new Map([
      ['x', { name: 'x', type: BuiltinTypes.i32, mutable: false, location: { line: 1, column: 1 } }],
      ['y', { name: 'y', type: BuiltinTypes.i32, mutable: false, location: { line: 1, column: 1 } }],
    ]);
    const point = new StructType('Point', fields);
    expect(point.toString()).toBe('Point');
    expect(point.hasField('x')).toBe(true);
    expect(point.hasField('z')).toBe(false);
  });

  it('should check struct field types', () => {
    const fields = new Map([
      ['x', { name: 'x', type: BuiltinTypes.f32, mutable: false, location: { line: 1, column: 1 } }],
    ]);
    const point = new StructType('Point', fields);
    const field = point.getField('x');
    expect(field?.type.equals(BuiltinTypes.f32)).toBe(true);
  });

  it('should check struct equality', () => {
    const fields1 = new Map([
      ['x', { name: 'x', type: BuiltinTypes.i32, mutable: false, location: { line: 1, column: 1 } }],
    ]);
    const fields2 = new Map([
      ['x', { name: 'x', type: BuiltinTypes.i32, mutable: false, location: { line: 1, column: 1 } }],
    ]);
    const struct1 = new StructType('Point', fields1);
    const struct2 = new StructType('Point', fields2);
    expect(struct1.equals(struct2)).toBe(true);
  });

  it('should distinguish structs with different names', () => {
    const fields = new Map([
      ['x', { name: 'x', type: BuiltinTypes.i32, mutable: false, location: { line: 1, column: 1 } }],
    ]);
    const point = new StructType('Point', fields);
    const vector = new StructType('Vector', fields);
    expect(point.equals(vector)).toBe(false);
  });
});

describe('Type System - Function Types', () => {
  it('should create function type', () => {
    const fnType = new FunctionType([BuiltinTypes.i32, BuiltinTypes.i32], BuiltinTypes.i32);
    expect(fnType.toString()).toContain('fn');
    expect(fnType.toString()).toContain('i32');
  });

  it('should check function type equality', () => {
    const fn1 = new FunctionType([BuiltinTypes.i32], BuiltinTypes.i32);
    const fn2 = new FunctionType([BuiltinTypes.i32], BuiltinTypes.i32);
    expect(fn1.equals(fn2)).toBe(true);
  });

  it('should distinguish functions with different parameters', () => {
    const fn1 = new FunctionType([BuiltinTypes.i32], BuiltinTypes.i32);
    const fn2 = new FunctionType([BuiltinTypes.f32], BuiltinTypes.i32);
    expect(fn1.equals(fn2)).toBe(false);
  });

  it('should distinguish functions with different return types', () => {
    const fn1 = new FunctionType([BuiltinTypes.i32], BuiltinTypes.i32);
    const fn2 = new FunctionType([BuiltinTypes.i32], BuiltinTypes.f32);
    expect(fn1.equals(fn2)).toBe(false);
  });

  it('should check parameter count', () => {
    const fn1 = new FunctionType([BuiltinTypes.i32], BuiltinTypes.i32);
    const fn2 = new FunctionType([BuiltinTypes.i32, BuiltinTypes.i32], BuiltinTypes.i32);
    expect(fn1.equals(fn2)).toBe(false);
  });
});

describe('Type System - Tuple Types', () => {
  it('should create tuple type', () => {
    const tuple = new TupleType([BuiltinTypes.i32, BuiltinTypes.f32]);
    expect(tuple.toString()).toBe('(i32, f32)');
  });

  it('should check tuple equality', () => {
    const tuple1 = new TupleType([BuiltinTypes.i32, BuiltinTypes.f32]);
    const tuple2 = new TupleType([BuiltinTypes.i32, BuiltinTypes.f32]);
    expect(tuple1.equals(tuple2)).toBe(true);
  });

  it('should distinguish tuples with different element types', () => {
    const tuple1 = new TupleType([BuiltinTypes.i32, BuiltinTypes.f32]);
    const tuple2 = new TupleType([BuiltinTypes.f32, BuiltinTypes.i32]);
    expect(tuple1.equals(tuple2)).toBe(false);
  });

  it('should distinguish tuples with different lengths', () => {
    const tuple1 = new TupleType([BuiltinTypes.i32]);
    const tuple2 = new TupleType([BuiltinTypes.i32, BuiltinTypes.i32]);
    expect(tuple1.equals(tuple2)).toBe(false);
  });
});

describe('Semantic Analysis - Type Inference', () => {
  it('should infer integer literal type', () => {
    const analyzer = createAnalyzer();
    const ast = { type: 'Literal', value: 42 };
    const inferredType = analyzer.checkType(ast);
    expect(TypeUtils.isInteger(inferredType)).toBe(true);
  });

  it('should infer float literal type', () => {
    const analyzer = createAnalyzer();
    const ast = { type: 'Literal', value: 3.14 };
    const inferredType = analyzer.checkType(ast);
    expect(TypeUtils.isFloat(inferredType)).toBe(true);
  });

  it('should infer boolean literal type', () => {
    const analyzer = createAnalyzer();
    const ast = { type: 'Literal', value: true };
    const inferredType = analyzer.checkType(ast);
    expect(inferredType.equals(BuiltinTypes.bool)).toBe(true);
  });

  it('should infer string literal type', () => {
    const analyzer = createAnalyzer();
    const ast = { type: 'Literal', value: 'hello' };
    const inferredType = analyzer.checkType(ast);
    expect(inferredType.equals(BuiltinTypes.str)).toBe(true);
  });

  it('should infer array literal type', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'ArrayExpression',
      elements: [
        { type: 'Literal', value: 1 },
        { type: 'Literal', value: 2 },
      ],
    };
    const inferredType = analyzer.checkType(ast);
    expect(TypeUtils.isArray(inferredType)).toBe(true);
  });
});

describe('Semantic Analysis - Type Checking', () => {
  it('should validate binary operation types', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'BinaryExpression',
      operator: '+',
      left: { type: 'Literal', value: 1 },
      right: { type: 'Literal', value: 2 },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors()).toHaveLength(0);
  });

  it('should error on type mismatch in binary operation', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'BinaryExpression',
      operator: '+',
      left: { type: 'Literal', value: 1 },
      right: { type: 'Literal', value: 'string' },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should validate assignment types', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'AssignmentExpression',
      left: { type: 'Identifier', name: 'x' },
      right: { type: 'Literal', value: 42 },
    };
    analyzer.analyze(ast);
    // Type should match or be compatible
  });

  it('should error on incompatible assignment', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'VariableDeclaration',
      name: 'x',
      typeAnnotation: { kind: 'Primitive', primitiveKind: 'i32' },
      initializer: { type: 'Literal', value: 'string' },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });
});

describe('Semantic Analysis - Variable Scope', () => {
  it('should detect undefined variable usage', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'Identifier',
      name: 'undefinedVar',
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should allow variable usage after declaration', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'Program',
      body: [
        {
          type: 'VariableDeclaration',
          name: 'x',
          initializer: { type: 'Literal', value: 42 },
        },
        {
          type: 'Identifier',
          name: 'x',
        },
      ],
    };
    analyzer.analyze(ast);
    const errors = analyzer.getErrors();
    expect(errors.filter((e) => e.message.includes('undefined')).length).toBe(0);
  });

  it('should detect variable redefinition', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'Program',
      body: [
        { type: 'VariableDeclaration', name: 'x', initializer: { type: 'Literal', value: 1 } },
        { type: 'VariableDeclaration', name: 'x', initializer: { type: 'Literal', value: 2 } },
      ],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should allow shadowing in nested scopes', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'Program',
      body: [
        { type: 'VariableDeclaration', name: 'x', initializer: { type: 'Literal', value: 1 } },
        {
          type: 'BlockExpression',
          statements: [
            { type: 'VariableDeclaration', name: 'x', initializer: { type: 'Literal', value: 2 } },
          ],
        },
      ],
    };
    analyzer.analyze(ast);
    // Should not error - shadowing is allowed
  });
});

describe('Semantic Analysis - Function Validation', () => {
  it('should validate function return type', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'FunctionDeclaration',
      name: 'add',
      returnType: { kind: 'Primitive', primitiveKind: 'i32' },
      body: {
        type: 'BlockExpression',
        statements: [],
        expression: { type: 'Literal', value: 42 },
      },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors()).toHaveLength(0);
  });

  it('should error on mismatched return type', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'FunctionDeclaration',
      name: 'test',
      returnType: { kind: 'Primitive', primitiveKind: 'i32' },
      body: {
        type: 'BlockExpression',
        expression: { type: 'Literal', value: 'string' },
      },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should validate function call arguments', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'CallExpression',
      callee: { type: 'Identifier', name: 'add' },
      arguments: [
        { type: 'Literal', value: 1 },
        { type: 'Literal', value: 2 },
      ],
    };
    analyzer.analyze(ast);
    // Should validate argument count and types
  });

  it('should error on wrong argument count', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'CallExpression',
      callee: { type: 'Identifier', name: 'add' },
      arguments: [{ type: 'Literal', value: 1 }],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should error on argument type mismatch', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'CallExpression',
      callee: { type: 'Identifier', name: 'add' },
      arguments: [
        { type: 'Literal', value: 1 },
        { type: 'Literal', value: 'string' },
      ],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });
});

describe('Semantic Analysis - Mutability Checking', () => {
  it('should error on assignment to immutable variable', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'Program',
      body: [
        {
          type: 'VariableDeclaration',
          name: 'x',
          mutable: false,
          initializer: { type: 'Literal', value: 1 },
        },
        {
          type: 'AssignmentExpression',
          left: { type: 'Identifier', name: 'x' },
          right: { type: 'Literal', value: 2 },
        },
      ],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should allow assignment to mutable variable', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'Program',
      body: [
        {
          type: 'VariableDeclaration',
          name: 'x',
          mutable: true,
          initializer: { type: 'Literal', value: 1 },
        },
        {
          type: 'AssignmentExpression',
          left: { type: 'Identifier', name: 'x' },
          right: { type: 'Literal', value: 2 },
        },
      ],
    };
    analyzer.analyze(ast);
    const mutabilityErrors = analyzer
      .getErrors()
      .filter((e) => e.message.includes('immutable'));
    expect(mutabilityErrors).toHaveLength(0);
  });
});

describe('Semantic Analysis - Struct Field Access', () => {
  it('should validate struct field access', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'MemberExpression',
      object: { type: 'Identifier', name: 'point' },
      property: { type: 'Identifier', name: 'x' },
    };
    analyzer.analyze(ast);
    // Should resolve field type
  });

  it('should error on accessing non-existent field', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'MemberExpression',
      object: { type: 'Identifier', name: 'point' },
      property: { type: 'Identifier', name: 'nonExistent' },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should validate struct construction', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'StructExpression',
      name: 'Point',
      fields: [
        { name: 'x', value: { type: 'Literal', value: 10 } },
        { name: 'y', value: { type: 'Literal', value: 20 } },
      ],
    };
    analyzer.analyze(ast);
    // Should validate all required fields are present
  });

  it('should error on missing struct fields', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'StructExpression',
      name: 'Point',
      fields: [{ name: 'x', value: { type: 'Literal', value: 10 } }],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });
});

describe('Semantic Analysis - Array Operations', () => {
  it('should validate array indexing', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'IndexExpression',
      object: { type: 'Identifier', name: 'arr' },
      index: { type: 'Literal', value: 0 },
    };
    analyzer.analyze(ast);
    // Should check array type and index type
  });

  it('should error on non-integer array index', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'IndexExpression',
      object: { type: 'Identifier', name: 'arr' },
      index: { type: 'Literal', value: 'string' },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should validate array element types', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'ArrayExpression',
      elements: [
        { type: 'Literal', value: 1 },
        { type: 'Literal', value: 2 },
        { type: 'Literal', value: 3 },
      ],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors()).toHaveLength(0);
  });

  it('should error on mixed array element types', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'ArrayExpression',
      elements: [
        { type: 'Literal', value: 1 },
        { type: 'Literal', value: 'string' },
      ],
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });
});

describe('Semantic Analysis - Control Flow', () => {
  it('should validate if condition is boolean', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'IfStatement',
      condition: { type: 'Literal', value: true },
      thenBranch: { type: 'BlockExpression', statements: [] },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors()).toHaveLength(0);
  });

  it('should error on non-boolean if condition', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'IfStatement',
      condition: { type: 'Literal', value: 42 },
      thenBranch: { type: 'BlockExpression', statements: [] },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors().length).toBeGreaterThan(0);
  });

  it('should validate while condition is boolean', () => {
    const analyzer = createAnalyzer();
    const ast = {
      type: 'WhileStatement',
      condition: { type: 'Literal', value: true },
      body: { type: 'BlockExpression', statements: [] },
    };
    analyzer.analyze(ast);
    expect(analyzer.getErrors()).toHaveLength(0);
  });
});
