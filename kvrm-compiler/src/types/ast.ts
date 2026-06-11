/**
 * Abstract Syntax Tree (AST) node definitions for the KVRM programming language.
 * Complete type-safe representation of KVRM program structure.
 */

import type { SourceLocation } from './tokens.js';

/**
 * Base interface for all AST nodes.
 * Provides common properties for location tracking and visitor pattern support.
 */
export interface ASTNode {
  /** Discriminated union tag for type narrowing */
  readonly kind: NodeKind;

  /** Source location for error reporting */
  readonly location: SourceLocation;
}

/**
 * Enumeration of all AST node types for discriminated unions.
 */
export enum NodeKind {
  // Program
  Program = 'Program',

  // Declarations
  FunctionDeclaration = 'FunctionDeclaration',
  VariableDeclaration = 'VariableDeclaration',
  StructDeclaration = 'StructDeclaration',
  EnumDeclaration = 'EnumDeclaration',
  TraitDeclaration = 'TraitDeclaration',
  ImplBlock = 'ImplBlock',
  TypeAlias = 'TypeAlias',
  ModuleDeclaration = 'ModuleDeclaration',
  UseDeclaration = 'UseDeclaration',

  // Statements
  ExpressionStatement = 'ExpressionStatement',
  BlockStatement = 'BlockStatement',
  IfStatement = 'IfStatement',
  WhileStatement = 'WhileStatement',
  ForStatement = 'ForStatement',
  ReturnStatement = 'ReturnStatement',
  BreakStatement = 'BreakStatement',
  ContinueStatement = 'ContinueStatement',
  MatchStatement = 'MatchStatement',

  // Expressions
  BinaryExpression = 'BinaryExpression',
  UnaryExpression = 'UnaryExpression',
  AssignmentExpression = 'AssignmentExpression',
  CallExpression = 'CallExpression',
  MethodCallExpression = 'MethodCallExpression',
  IndexExpression = 'IndexExpression',
  MemberExpression = 'MemberExpression',
  ArrayExpression = 'ArrayExpression',
  StructExpression = 'StructExpression',
  LambdaExpression = 'LambdaExpression',
  CastExpression = 'CastExpression',
  Identifier = 'Identifier',

  // Literals
  NumberLiteral = 'NumberLiteral',
  StringLiteral = 'StringLiteral',
  CharLiteral = 'CharLiteral',
  BooleanLiteral = 'BooleanLiteral',
  NullLiteral = 'NullLiteral',

  // Types
  TypeReference = 'TypeReference',
  ArrayType = 'ArrayType',
  TupleType = 'TupleType',
  FunctionType = 'FunctionType',
  GenericType = 'GenericType',
  ReferenceType = 'ReferenceType',

  // Patterns
  MatchPattern = 'MatchPattern',
  MatchArm = 'MatchArm',

  // Other
  Parameter = 'Parameter',
  StructField = 'StructField',
  EnumVariant = 'EnumVariant',
  GenericParameter = 'GenericParameter',
}

// ============================================================================
// Program Root
// ============================================================================

/**
 * Root node of the AST representing a complete KVRM source file.
 */
export interface Program extends ASTNode {
  readonly kind: NodeKind.Program;
  readonly declarations: readonly Declaration[];
}

// ============================================================================
// Declarations
// ============================================================================

/**
 * Union type of all declaration nodes.
 */
export type Declaration =
  | FunctionDeclaration
  | VariableDeclaration
  | StructDeclaration
  | EnumDeclaration
  | TraitDeclaration
  | ImplBlock
  | TypeAlias
  | ModuleDeclaration
  | UseDeclaration;

/**
 * Function declaration node.
 * Example: pub fn add(x: i32, y: i32) -> i32 { x + y }
 */
export interface FunctionDeclaration extends ASTNode {
  readonly kind: NodeKind.FunctionDeclaration;
  readonly name: Identifier;
  readonly parameters: readonly Parameter[];
  readonly returnType: TypeExpression | null;
  readonly body: BlockStatement;
  readonly isPublic: boolean;
  readonly isAsync: boolean;
  readonly genericParams: readonly GenericParameter[];
}

/**
 * Variable declaration node.
 * Example: let mut x: i32 = 42;
 */
export interface VariableDeclaration extends ASTNode {
  readonly kind: NodeKind.VariableDeclaration;
  readonly name: Identifier;
  readonly type: TypeExpression | null;
  readonly initializer: Expression | null;
  readonly isMutable: boolean;
  readonly isPublic: boolean;
  readonly isConst: boolean;
  readonly isStatic: boolean;
}

/**
 * Struct declaration node.
 * Example: pub struct Point { x: f64, y: f64 }
 */
export interface StructDeclaration extends ASTNode {
  readonly kind: NodeKind.StructDeclaration;
  readonly name: Identifier;
  readonly fields: readonly StructField[];
  readonly isPublic: boolean;
  readonly genericParams: readonly GenericParameter[];
}

/**
 * Enum declaration node.
 * Example: enum Option<T> { Some(T), None }
 */
export interface EnumDeclaration extends ASTNode {
  readonly kind: NodeKind.EnumDeclaration;
  readonly name: Identifier;
  readonly variants: readonly EnumVariant[];
  readonly isPublic: boolean;
  readonly genericParams: readonly GenericParameter[];
}

/**
 * Trait declaration node.
 * Example: trait Display { fn fmt(&self) -> String; }
 */
export interface TraitDeclaration extends ASTNode {
  readonly kind: NodeKind.TraitDeclaration;
  readonly name: Identifier;
  readonly methods: readonly FunctionDeclaration[];
  readonly isPublic: boolean;
  readonly genericParams: readonly GenericParameter[];
}

/**
 * Implementation block node.
 * Example: impl Display for Point { fn fmt(&self) -> String { ... } }
 */
export interface ImplBlock extends ASTNode {
  readonly kind: NodeKind.ImplBlock;
  readonly type: TypeExpression;
  readonly trait: Identifier | null;
  readonly methods: readonly FunctionDeclaration[];
  readonly genericParams: readonly GenericParameter[];
}

/**
 * Type alias declaration node.
 * Example: type Result<T> = Option<T>;
 */
export interface TypeAlias extends ASTNode {
  readonly kind: NodeKind.TypeAlias;
  readonly name: Identifier;
  readonly type: TypeExpression;
  readonly isPublic: boolean;
  readonly genericParams: readonly GenericParameter[];
}

/**
 * Module declaration node.
 * Example: mod math { ... }
 */
export interface ModuleDeclaration extends ASTNode {
  readonly kind: NodeKind.ModuleDeclaration;
  readonly name: Identifier;
  readonly declarations: readonly Declaration[];
  readonly isPublic: boolean;
}

/**
 * Use/import declaration node.
 * Example: use std::collections::HashMap;
 */
export interface UseDeclaration extends ASTNode {
  readonly kind: NodeKind.UseDeclaration;
  readonly path: readonly Identifier[];
  readonly alias: Identifier | null;
  readonly isPublic: boolean;
}

// ============================================================================
// Statements
// ============================================================================

/**
 * Union type of all statement nodes.
 */
export type Statement =
  | VariableDeclaration
  | ExpressionStatement
  | BlockStatement
  | IfStatement
  | WhileStatement
  | ForStatement
  | ReturnStatement
  | BreakStatement
  | ContinueStatement
  | MatchStatement;

/**
 * Expression statement node.
 * Example: foo();
 */
export interface ExpressionStatement extends ASTNode {
  readonly kind: NodeKind.ExpressionStatement;
  readonly expression: Expression;
}

/**
 * Block statement node.
 * Example: { let x = 1; x + 2 }
 */
export interface BlockStatement extends ASTNode {
  readonly kind: NodeKind.BlockStatement;
  readonly statements: readonly Statement[];
}

/**
 * If statement node.
 * Example: if x > 0 { print("positive"); } else { print("non-positive"); }
 */
export interface IfStatement extends ASTNode {
  readonly kind: NodeKind.IfStatement;
  readonly condition: Expression;
  readonly thenBranch: BlockStatement;
  readonly elseBranch: BlockStatement | IfStatement | null;
}

/**
 * While loop statement node.
 * Example: while x < 10 { x += 1; }
 */
export interface WhileStatement extends ASTNode {
  readonly kind: NodeKind.WhileStatement;
  readonly condition: Expression;
  readonly body: BlockStatement;
}

/**
 * For loop statement node.
 * Example: for i in 0..10 { print(i); }
 */
export interface ForStatement extends ASTNode {
  readonly kind: NodeKind.ForStatement;
  readonly variable: Identifier;
  readonly iterator: Expression;
  readonly body: BlockStatement;
}

/**
 * Return statement node.
 * Example: return x + 1;
 */
export interface ReturnStatement extends ASTNode {
  readonly kind: NodeKind.ReturnStatement;
  readonly value: Expression | null;
}

/**
 * Break statement node.
 * Example: break;
 */
export interface BreakStatement extends ASTNode {
  readonly kind: NodeKind.BreakStatement;
}

/**
 * Continue statement node.
 * Example: continue;
 */
export interface ContinueStatement extends ASTNode {
  readonly kind: NodeKind.ContinueStatement;
}

/**
 * Match statement node.
 * Example: match x { 0 => "zero", _ => "other" }
 */
export interface MatchStatement extends ASTNode {
  readonly kind: NodeKind.MatchStatement;
  readonly scrutinee: Expression;
  readonly arms: readonly MatchArm[];
}

// ============================================================================
// Expressions
// ============================================================================

/**
 * Union type of all expression nodes.
 */
export type Expression =
  | BinaryExpression
  | UnaryExpression
  | AssignmentExpression
  | CallExpression
  | MethodCallExpression
  | IndexExpression
  | MemberExpression
  | ArrayExpression
  | StructExpression
  | LambdaExpression
  | CastExpression
  | Identifier
  | NumberLiteral
  | StringLiteral
  | CharLiteral
  | BooleanLiteral
  | NullLiteral;

/**
 * Binary operator types.
 */
export enum BinaryOperator {
  Add = 'Add',
  Subtract = 'Subtract',
  Multiply = 'Multiply',
  Divide = 'Divide',
  Modulo = 'Modulo',
  Power = 'Power',
  Equal = 'Equal',
  NotEqual = 'NotEqual',
  LessThan = 'LessThan',
  LessThanOrEqual = 'LessThanOrEqual',
  GreaterThan = 'GreaterThan',
  GreaterThanOrEqual = 'GreaterThanOrEqual',
  LogicalAnd = 'LogicalAnd',
  LogicalOr = 'LogicalOr',
  BitwiseAnd = 'BitwiseAnd',
  BitwiseOr = 'BitwiseOr',
  BitwiseXor = 'BitwiseXor',
  LeftShift = 'LeftShift',
  RightShift = 'RightShift',
}

/**
 * Unary operator types.
 */
export enum UnaryOperator {
  Not = 'Not',
  Negate = 'Negate',
  BitwiseNot = 'BitwiseNot',
  Reference = 'Reference',
  Dereference = 'Dereference',
}

/**
 * Assignment operator types.
 */
export enum AssignmentOperator {
  Assign = 'Assign',
  AddAssign = 'AddAssign',
  SubtractAssign = 'SubtractAssign',
  MultiplyAssign = 'MultiplyAssign',
  DivideAssign = 'DivideAssign',
  ModuloAssign = 'ModuloAssign',
  BitwiseAndAssign = 'BitwiseAndAssign',
  BitwiseOrAssign = 'BitwiseOrAssign',
  BitwiseXorAssign = 'BitwiseXorAssign',
  LeftShiftAssign = 'LeftShiftAssign',
  RightShiftAssign = 'RightShiftAssign',
}

/**
 * Binary expression node.
 * Example: x + y, a && b, 1 < 2
 */
export interface BinaryExpression extends ASTNode {
  readonly kind: NodeKind.BinaryExpression;
  readonly operator: BinaryOperator;
  readonly left: Expression;
  readonly right: Expression;
}

/**
 * Unary expression node.
 * Example: !x, -y, *ptr
 */
export interface UnaryExpression extends ASTNode {
  readonly kind: NodeKind.UnaryExpression;
  readonly operator: UnaryOperator;
  readonly operand: Expression;
}

/**
 * Assignment expression node.
 * Example: x = 5, y += 3
 */
export interface AssignmentExpression extends ASTNode {
  readonly kind: NodeKind.AssignmentExpression;
  readonly operator: AssignmentOperator;
  readonly target: Expression;
  readonly value: Expression;
}

/**
 * Function call expression node.
 * Example: add(1, 2)
 */
export interface CallExpression extends ASTNode {
  readonly kind: NodeKind.CallExpression;
  readonly callee: Expression;
  readonly arguments: readonly Expression[];
  readonly typeArguments: readonly TypeExpression[];
}

/**
 * Method call expression node.
 * Example: point.distance(other)
 */
export interface MethodCallExpression extends ASTNode {
  readonly kind: NodeKind.MethodCallExpression;
  readonly object: Expression;
  readonly method: Identifier;
  readonly arguments: readonly Expression[];
  readonly typeArguments: readonly TypeExpression[];
}

/**
 * Array index expression node.
 * Example: arr[0], matrix[i][j]
 */
export interface IndexExpression extends ASTNode {
  readonly kind: NodeKind.IndexExpression;
  readonly object: Expression;
  readonly index: Expression;
}

/**
 * Member access expression node.
 * Example: point.x, obj.field
 */
export interface MemberExpression extends ASTNode {
  readonly kind: NodeKind.MemberExpression;
  readonly object: Expression;
  readonly member: Identifier;
}

/**
 * Array literal expression node.
 * Example: [1, 2, 3]
 */
export interface ArrayExpression extends ASTNode {
  readonly kind: NodeKind.ArrayExpression;
  readonly elements: readonly Expression[];
}

/**
 * Struct literal expression node.
 * Example: Point { x: 1.0, y: 2.0 }
 */
export interface StructExpression extends ASTNode {
  readonly kind: NodeKind.StructExpression;
  readonly type: Identifier;
  readonly fields: readonly { name: Identifier; value: Expression }[];
}

/**
 * Lambda/closure expression node.
 * Example: |x, y| x + y
 */
export interface LambdaExpression extends ASTNode {
  readonly kind: NodeKind.LambdaExpression;
  readonly parameters: readonly Parameter[];
  readonly returnType: TypeExpression | null;
  readonly body: BlockStatement | Expression;
}

/**
 * Type cast expression node.
 * Example: x as f64
 */
export interface CastExpression extends ASTNode {
  readonly kind: NodeKind.CastExpression;
  readonly expression: Expression;
  readonly targetType: TypeExpression;
}

/**
 * Identifier node.
 * Example: x, foo, MyStruct
 */
export interface Identifier extends ASTNode {
  readonly kind: NodeKind.Identifier;
  readonly name: string;
}

// ============================================================================
// Literals
// ============================================================================

/**
 * Number literal node.
 * Example: 42, 3.14, 0xFF
 */
export interface NumberLiteral extends ASTNode {
  readonly kind: NodeKind.NumberLiteral;
  readonly value: number;
  readonly raw: string;
}

/**
 * String literal node.
 * Example: "hello world"
 */
export interface StringLiteral extends ASTNode {
  readonly kind: NodeKind.StringLiteral;
  readonly value: string;
  readonly raw: string;
}

/**
 * Character literal node.
 * Example: 'a', '\n'
 */
export interface CharLiteral extends ASTNode {
  readonly kind: NodeKind.CharLiteral;
  readonly value: string;
  readonly raw: string;
}

/**
 * Boolean literal node.
 * Example: true, false
 */
export interface BooleanLiteral extends ASTNode {
  readonly kind: NodeKind.BooleanLiteral;
  readonly value: boolean;
}

/**
 * Null literal node.
 * Example: null
 */
export interface NullLiteral extends ASTNode {
  readonly kind: NodeKind.NullLiteral;
}

// ============================================================================
// Types
// ============================================================================

/**
 * Union type of all type expression nodes.
 */
export type TypeExpression =
  | TypeReference
  | ArrayType
  | TupleType
  | FunctionType
  | GenericType
  | ReferenceType;

/**
 * Type reference node.
 * Example: i32, String, MyStruct
 */
export interface TypeReference extends ASTNode {
  readonly kind: NodeKind.TypeReference;
  readonly name: Identifier;
}

/**
 * Array type node.
 * Example: [i32; 10], [String]
 */
export interface ArrayType extends ASTNode {
  readonly kind: NodeKind.ArrayType;
  readonly elementType: TypeExpression;
  readonly size: Expression | null;
}

/**
 * Tuple type node.
 * Example: (i32, String), (f64, f64)
 */
export interface TupleType extends ASTNode {
  readonly kind: NodeKind.TupleType;
  readonly elements: readonly TypeExpression[];
}

/**
 * Function type node.
 * Example: fn(i32, i32) -> i32
 */
export interface FunctionType extends ASTNode {
  readonly kind: NodeKind.FunctionType;
  readonly parameters: readonly TypeExpression[];
  readonly returnType: TypeExpression;
}

/**
 * Generic type node.
 * Example: Option<T>, Vec<i32>
 */
export interface GenericType extends ASTNode {
  readonly kind: NodeKind.GenericType;
  readonly base: TypeExpression;
  readonly typeArguments: readonly TypeExpression[];
}

/**
 * Reference type node.
 * Example: &i32, &mut String
 */
export interface ReferenceType extends ASTNode {
  readonly kind: NodeKind.ReferenceType;
  readonly type: TypeExpression;
  readonly isMutable: boolean;
}

// ============================================================================
// Patterns and Other Nodes
// ============================================================================

/**
 * Match pattern node.
 * Example: 0, Some(x), Point { x, y }
 */
export interface MatchPattern extends ASTNode {
  readonly kind: NodeKind.MatchPattern;
  readonly pattern: Expression | Identifier;
}

/**
 * Match arm node.
 * Example: 0 => "zero", Some(x) => x.to_string()
 */
export interface MatchArm extends ASTNode {
  readonly kind: NodeKind.MatchArm;
  readonly pattern: MatchPattern;
  readonly guard: Expression | null;
  readonly body: Expression | BlockStatement;
}

/**
 * Function parameter node.
 * Example: x: i32, mut y: String
 */
export interface Parameter extends ASTNode {
  readonly kind: NodeKind.Parameter;
  readonly name: Identifier;
  readonly type: TypeExpression;
  readonly isMutable: boolean;
  readonly defaultValue: Expression | null;
}

/**
 * Struct field node.
 * Example: x: f64, pub name: String
 */
export interface StructField extends ASTNode {
  readonly kind: NodeKind.StructField;
  readonly name: Identifier;
  readonly type: TypeExpression;
  readonly isPublic: boolean;
}

/**
 * Enum variant node.
 * Example: Some(T), None, Error { code: i32 }
 */
export interface EnumVariant extends ASTNode {
  readonly kind: NodeKind.EnumVariant;
  readonly name: Identifier;
  readonly fields: readonly TypeExpression[] | readonly StructField[];
}

/**
 * Generic parameter node.
 * Example: T, T: Display, 'a
 */
export interface GenericParameter extends ASTNode {
  readonly kind: NodeKind.GenericParameter;
  readonly name: Identifier;
  readonly bounds: readonly Identifier[];
  readonly isLifetime: boolean;
}
