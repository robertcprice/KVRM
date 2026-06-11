/**
 * Parser Tests for KVRM Compiler
 *
 * Comprehensive test suite covering:
 * - Function declarations
 * - Variable declarations
 * - Expression parsing with precedence
 * - Control flow structures
 * - Type definitions (structs, enums)
 * - Implementation blocks
 * - Error recovery and reporting
 */

import { describe, it, expect } from 'vitest';

// Mock AST node types - replace with actual imports when implemented
interface ASTNode {
  type: string;
  [key: string]: any;
}

interface Parser {
  parse(): ASTNode;
  parseExpression(): ASTNode;
  parseStatement(): ASTNode;
  parseDeclaration(): ASTNode;
}

// Placeholder - replace with actual Parser import
// import { Parser } from '../src/parser';
class MockParser implements Parser {
  parse(): ASTNode {
    return { type: 'Program', body: [] };
  }
  parseExpression(): ASTNode {
    return { type: 'Expression' };
  }
  parseStatement(): ASTNode {
    return { type: 'Statement' };
  }
  parseDeclaration(): ASTNode {
    return { type: 'Declaration' };
  }
}

const createParser = (input: string): Parser => {
  // Replace with: return new Parser(input);
  return new MockParser();
};

describe('Parser - Variable Declarations', () => {
  it('should parse simple let declaration', () => {
    const parser = createParser('let x = 5;');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('VariableDeclaration');
    expect(ast.name).toBe('x');
    expect(ast.mutable).toBe(false);
    expect(ast.initializer).toBeDefined();
  });

  it('should parse mutable variable declaration', () => {
    const parser = createParser('let mut x = 5;');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('VariableDeclaration');
    expect(ast.name).toBe('x');
    expect(ast.mutable).toBe(true);
  });

  it('should parse variable with type annotation', () => {
    const parser = createParser('let x: i32 = 5;');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('VariableDeclaration');
    expect(ast.typeAnnotation).toBeDefined();
    expect(ast.typeAnnotation.name).toBe('i32');
  });

  it('should parse variable without initializer', () => {
    const parser = createParser('let x: i32;');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('VariableDeclaration');
    expect(ast.initializer).toBeUndefined();
  });

  it('should parse destructuring assignment', () => {
    const parser = createParser('let (x, y) = (1, 2);');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('VariableDeclaration');
    expect(ast.pattern).toBeDefined();
  });

  it('should require semicolon after declaration', () => {
    const parser = createParser('let x = 5');
    expect(() => parser.parseDeclaration()).toThrow();
  });
});

describe('Parser - Function Declarations', () => {
  it('should parse simple function', () => {
    const parser = createParser('fn add(a: i32, b: i32) -> i32 { return a + b; }');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('FunctionDeclaration');
    expect(ast.name).toBe('add');
    expect(ast.parameters).toHaveLength(2);
    expect(ast.returnType).toBeDefined();
    expect(ast.body).toBeDefined();
  });

  it('should parse function without return type', () => {
    const parser = createParser('fn print() { }');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('FunctionDeclaration');
    expect(ast.returnType).toBeUndefined();
  });

  it('should parse function with no parameters', () => {
    const parser = createParser('fn main() { }');
    const ast = parser.parseDeclaration();
    expect(ast.parameters).toHaveLength(0);
  });

  it('should parse function with multiple parameters', () => {
    const parser = createParser('fn calculate(a: i32, b: i32, c: f32) -> f32 { }');
    const ast = parser.parseDeclaration();
    expect(ast.parameters).toHaveLength(3);
  });

  it('should parse generic function', () => {
    const parser = createParser('fn identity<T>(x: T) -> T { return x; }');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('FunctionDeclaration');
    expect(ast.typeParameters).toBeDefined();
    expect(ast.typeParameters).toHaveLength(1);
  });

  it('should parse public function', () => {
    const parser = createParser('pub fn visible() { }');
    const ast = parser.parseDeclaration();
    expect(ast.visibility).toBe('public');
  });

  it('should parse function with self parameter', () => {
    const parser = createParser('fn method(self) { }');
    const ast = parser.parseDeclaration();
    expect(ast.parameters[0].name).toBe('self');
  });
});

describe('Parser - Expressions', () => {
  it('should parse integer literals', () => {
    const parser = createParser('42');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('Literal');
    expect(ast.value).toBe(42);
  });

  it('should parse float literals', () => {
    const parser = createParser('3.14');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('Literal');
    expect(ast.value).toBe(3.14);
  });

  it('should parse string literals', () => {
    const parser = createParser('"hello"');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('Literal');
    expect(ast.value).toBe('hello');
  });

  it('should parse boolean literals', () => {
    const parser = createParser('true');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('Literal');
    expect(ast.value).toBe(true);
  });

  it('should parse identifiers', () => {
    const parser = createParser('variable');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('Identifier');
    expect(ast.name).toBe('variable');
  });

  it('should parse binary expressions', () => {
    const parser = createParser('a + b');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BinaryExpression');
    expect(ast.operator).toBe('+');
    expect(ast.left.name).toBe('a');
    expect(ast.right.name).toBe('b');
  });

  it('should parse unary expressions', () => {
    const parser = createParser('-x');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('UnaryExpression');
    expect(ast.operator).toBe('-');
    expect(ast.operand.name).toBe('x');
  });

  it('should parse logical NOT', () => {
    const parser = createParser('!condition');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('UnaryExpression');
    expect(ast.operator).toBe('!');
  });
});

describe('Parser - Expression Precedence', () => {
  it('should handle multiplication before addition', () => {
    const parser = createParser('a + b * c');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BinaryExpression');
    expect(ast.operator).toBe('+');
    expect(ast.right.type).toBe('BinaryExpression');
    expect(ast.right.operator).toBe('*');
  });

  it('should handle parentheses for precedence override', () => {
    const parser = createParser('(a + b) * c');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BinaryExpression');
    expect(ast.operator).toBe('*');
    expect(ast.left.type).toBe('BinaryExpression');
    expect(ast.left.operator).toBe('+');
  });

  it('should handle comparison operators', () => {
    const parser = createParser('a < b == c > d');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BinaryExpression');
    expect(ast.operator).toBe('==');
  });

  it('should handle logical AND before OR', () => {
    const parser = createParser('a || b && c');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BinaryExpression');
    expect(ast.operator).toBe('||');
    expect(ast.right.operator).toBe('&&');
  });

  it('should handle assignment as lowest precedence', () => {
    const parser = createParser('x = a + b');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('AssignmentExpression');
    expect(ast.right.type).toBe('BinaryExpression');
  });

  it('should handle chained comparisons', () => {
    const parser = createParser('a < b < c');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BinaryExpression');
  });
});

describe('Parser - Function Calls', () => {
  it('should parse function call with no arguments', () => {
    const parser = createParser('foo()');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('CallExpression');
    expect(ast.callee.name).toBe('foo');
    expect(ast.arguments).toHaveLength(0);
  });

  it('should parse function call with arguments', () => {
    const parser = createParser('add(1, 2)');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('CallExpression');
    expect(ast.arguments).toHaveLength(2);
  });

  it('should parse nested function calls', () => {
    const parser = createParser('foo(bar(x))');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('CallExpression');
    expect(ast.arguments[0].type).toBe('CallExpression');
  });

  it('should parse method calls', () => {
    const parser = createParser('obj.method()');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('CallExpression');
    expect(ast.callee.type).toBe('MemberExpression');
  });

  it('should parse chained method calls', () => {
    const parser = createParser('obj.method1().method2()');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('CallExpression');
  });
});

describe('Parser - Member Access', () => {
  it('should parse dot notation', () => {
    const parser = createParser('obj.field');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('MemberExpression');
    expect(ast.object.name).toBe('obj');
    expect(ast.property.name).toBe('field');
  });

  it('should parse bracket notation', () => {
    const parser = createParser('arr[0]');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('IndexExpression');
    expect(ast.object.name).toBe('arr');
    expect(ast.index.value).toBe(0);
  });

  it('should parse chained member access', () => {
    const parser = createParser('a.b.c');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('MemberExpression');
    expect(ast.object.type).toBe('MemberExpression');
  });
});

describe('Parser - Control Flow', () => {
  it('should parse if statement', () => {
    const parser = createParser('if (x > 0) { return x; }');
    const ast = parser.parseStatement();
    expect(ast.type).toBe('IfStatement');
    expect(ast.condition).toBeDefined();
    expect(ast.thenBranch).toBeDefined();
    expect(ast.elseBranch).toBeUndefined();
  });

  it('should parse if-else statement', () => {
    const parser = createParser('if (x > 0) { return x; } else { return -x; }');
    const ast = parser.parseStatement();
    expect(ast.type).toBe('IfStatement');
    expect(ast.elseBranch).toBeDefined();
  });

  it('should parse if-else-if chain', () => {
    const parser = createParser(
      'if (x > 0) { return 1; } else if (x < 0) { return -1; } else { return 0; }'
    );
    const ast = parser.parseStatement();
    expect(ast.elseBranch.type).toBe('IfStatement');
  });

  it('should parse while loop', () => {
    const parser = createParser('while (x > 0) { x = x - 1; }');
    const ast = parser.parseStatement();
    expect(ast.type).toBe('WhileStatement');
    expect(ast.condition).toBeDefined();
    expect(ast.body).toBeDefined();
  });

  it('should parse for loop', () => {
    const parser = createParser('for (i in 0..10) { }');
    const ast = parser.parseStatement();
    expect(ast.type).toBe('ForStatement');
    expect(ast.variable).toBeDefined();
    expect(ast.iterable).toBeDefined();
  });

  it('should parse return statement', () => {
    const parser = createParser('return 42;');
    const ast = parser.parseStatement();
    expect(ast.type).toBe('ReturnStatement');
    expect(ast.value).toBeDefined();
  });

  it('should parse return without value', () => {
    const parser = createParser('return;');
    const ast = parser.parseStatement();
    expect(ast.type).toBe('ReturnStatement');
    expect(ast.value).toBeUndefined();
  });
});

describe('Parser - Struct Declarations', () => {
  it('should parse simple struct', () => {
    const parser = createParser('struct Point { x: i32, y: i32 }');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('StructDeclaration');
    expect(ast.name).toBe('Point');
    expect(ast.fields).toHaveLength(2);
  });

  it('should parse empty struct', () => {
    const parser = createParser('struct Empty { }');
    const ast = parser.parseDeclaration();
    expect(ast.fields).toHaveLength(0);
  });

  it('should parse generic struct', () => {
    const parser = createParser('struct Vec<T> { data: T }');
    const ast = parser.parseDeclaration();
    expect(ast.typeParameters).toBeDefined();
    expect(ast.typeParameters).toHaveLength(1);
  });

  it('should parse public struct', () => {
    const parser = createParser('pub struct Point { x: i32 }');
    const ast = parser.parseDeclaration();
    expect(ast.visibility).toBe('public');
  });

  it('should parse struct with mutable fields', () => {
    const parser = createParser('struct Point { mut x: i32 }');
    const ast = parser.parseDeclaration();
    expect(ast.fields[0].mutable).toBe(true);
  });
});

describe('Parser - Enum Declarations', () => {
  it('should parse simple enum', () => {
    const parser = createParser('enum Color { Red, Green, Blue }');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('EnumDeclaration');
    expect(ast.name).toBe('Color');
    expect(ast.variants).toHaveLength(3);
  });

  it('should parse enum with associated types', () => {
    const parser = createParser('enum Option<T> { Some(T), None }');
    const ast = parser.parseDeclaration();
    expect(ast.variants[0].associatedType).toBeDefined();
  });

  it('should parse enum with discriminants', () => {
    const parser = createParser('enum Status { Active = 1, Inactive = 0 }');
    const ast = parser.parseDeclaration();
    expect(ast.variants[0].discriminant).toBeDefined();
  });
});

describe('Parser - Impl Blocks', () => {
  it('should parse impl block', () => {
    const parser = createParser('impl Point { fn new() -> Point { } }');
    const ast = parser.parseDeclaration();
    expect(ast.type).toBe('ImplDeclaration');
    expect(ast.typeName).toBe('Point');
    expect(ast.methods).toHaveLength(1);
  });

  it('should parse trait impl', () => {
    const parser = createParser('impl Display for Point { }');
    const ast = parser.parseDeclaration();
    expect(ast.traitName).toBe('Display');
    expect(ast.typeName).toBe('Point');
  });

  it('should parse generic impl', () => {
    const parser = createParser('impl<T> Container<T> { }');
    const ast = parser.parseDeclaration();
    expect(ast.typeParameters).toBeDefined();
  });
});

describe('Parser - Array Expressions', () => {
  it('should parse array literal', () => {
    const parser = createParser('[1, 2, 3]');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('ArrayExpression');
    expect(ast.elements).toHaveLength(3);
  });

  it('should parse empty array', () => {
    const parser = createParser('[]');
    const ast = parser.parseExpression();
    expect(ast.elements).toHaveLength(0);
  });

  it('should parse array with type annotation', () => {
    const parser = createParser('[1, 2, 3]: [i32; 3]');
    const ast = parser.parseExpression();
    expect(ast.typeAnnotation).toBeDefined();
  });

  it('should parse array indexing', () => {
    const parser = createParser('arr[i]');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('IndexExpression');
  });
});

describe('Parser - Block Expressions', () => {
  it('should parse block with statements', () => {
    const parser = createParser('{ let x = 5; x + 1 }');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('BlockExpression');
    expect(ast.statements).toBeDefined();
    expect(ast.expression).toBeDefined();
  });

  it('should parse empty block', () => {
    const parser = createParser('{ }');
    const ast = parser.parseExpression();
    expect(ast.statements).toHaveLength(0);
  });

  it('should treat last expression as block value', () => {
    const parser = createParser('{ let x = 5; x }');
    const ast = parser.parseExpression();
    expect(ast.expression.name).toBe('x');
  });
});

describe('Parser - Error Recovery', () => {
  it('should recover from missing semicolon', () => {
    const parser = createParser('let x = 5 let y = 10;');
    expect(() => parser.parse()).not.toThrow();
  });

  it('should recover from missing closing brace', () => {
    const parser = createParser('fn test() { let x = 5;');
    const ast = parser.parse();
    expect(ast).toBeDefined();
  });

  it('should recover from unexpected token', () => {
    const parser = createParser('let @ x = 5;');
    expect(() => parser.parse()).not.toThrow();
  });

  it('should provide error location', () => {
    const parser = createParser('let x = ;');
    try {
      parser.parse();
    } catch (error: any) {
      expect(error.location).toBeDefined();
      expect(error.location.line).toBe(1);
    }
  });

  it('should collect multiple errors', () => {
    const parser = createParser('let x = ; let y = ; let z = 5;');
    try {
      parser.parse();
    } catch (error: any) {
      if (error.errors) {
        expect(error.errors.length).toBeGreaterThan(1);
      }
    }
  });
});

describe('Parser - Type Expressions', () => {
  it('should parse primitive types', () => {
    const parser = createParser('let x: i32;');
    const ast = parser.parseDeclaration();
    expect(ast.typeAnnotation.kind).toBe('Primitive');
  });

  it('should parse array types', () => {
    const parser = createParser('let x: [i32; 10];');
    const ast = parser.parseDeclaration();
    expect(ast.typeAnnotation.kind).toBe('Array');
  });

  it('should parse generic types', () => {
    const parser = createParser('let x: Vec<i32>;');
    const ast = parser.parseDeclaration();
    expect(ast.typeAnnotation.kind).toBe('GenericInstance');
  });

  it('should parse function types', () => {
    const parser = createParser('let f: fn(i32) -> i32;');
    const ast = parser.parseDeclaration();
    expect(ast.typeAnnotation.kind).toBe('Function');
  });

  it('should parse tuple types', () => {
    const parser = createParser('let x: (i32, f32);');
    const ast = parser.parseDeclaration();
    expect(ast.typeAnnotation.kind).toBe('Tuple');
  });
});

describe('Parser - Pattern Matching', () => {
  it('should parse match expression', () => {
    const parser = createParser('match x { 0 => 1, _ => 0 }');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('MatchExpression');
    expect(ast.scrutinee).toBeDefined();
    expect(ast.arms).toHaveLength(2);
  });

  it('should parse literal patterns', () => {
    const parser = createParser('match x { 42 => true }');
    const ast = parser.parseExpression();
    expect(ast.arms[0].pattern.type).toBe('Literal');
  });

  it('should parse wildcard pattern', () => {
    const parser = createParser('match x { _ => 0 }');
    const ast = parser.parseExpression();
    expect(ast.arms[0].pattern.type).toBe('Wildcard');
  });

  it('should parse destructuring patterns', () => {
    const parser = createParser('match point { Point { x, y } => x }');
    const ast = parser.parseExpression();
    expect(ast.arms[0].pattern.type).toBe('Struct');
  });
});

describe('Parser - Range Expressions', () => {
  it('should parse inclusive range', () => {
    const parser = createParser('0..10');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('RangeExpression');
    expect(ast.inclusive).toBe(false);
  });

  it('should parse exclusive range', () => {
    const parser = createParser('0..=10');
    const ast = parser.parseExpression();
    expect(ast.type).toBe('RangeExpression');
    expect(ast.inclusive).toBe(true);
  });
});

describe('Parser - Complex Programs', () => {
  it('should parse complete program', () => {
    const code = `
      struct Point {
        x: i32,
        y: i32
      }

      fn main() {
        let p = Point { x: 10, y: 20 };
        if (p.x > 0) {
          return p.x + p.y;
        }
      }
    `;
    const parser = createParser(code);
    const ast = parser.parse();
    expect(ast.type).toBe('Program');
    expect(ast.body).toBeDefined();
  });

  it('should parse program with multiple declarations', () => {
    const code = `
      fn add(a: i32, b: i32) -> i32 { return a + b; }
      fn sub(a: i32, b: i32) -> i32 { return a - b; }
      fn main() { }
    `;
    const parser = createParser(code);
    const ast = parser.parse();
    expect(ast.body.length).toBeGreaterThanOrEqual(3);
  });
});
