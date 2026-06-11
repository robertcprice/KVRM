/**
 * KVRM Semantic Analysis Module
 *
 * Main exports for semantic analysis components:
 * - SemanticAnalyzer: Main entry point for semantic analysis
 * - Type system: Type definitions and utilities
 * - Symbol table: Symbol management and scoping
 * - Type checker: Expression and statement type checking
 * - Errors: Comprehensive error types with helpful messages
 */

// Main analyzer
export { SemanticAnalyzer, type SemanticResult } from './analyzer';

// Type system
export {
  Type,
  TypeKind,
  PrimitiveType,
  PrimitiveTypeKind,
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
  type SourceLocation,
  type StructField,
  type EnumVariant,
} from './types';

// Symbol table
export {
  SymbolTable,
  ScopedSymbolTable,
  SymbolKind,
  ScopeKind,
  type SymbolEntry,
  type SymbolFlags,
} from './symbol-table';

// Type checker
export { TypeChecker } from './type-checker';

// Errors
export {
  SemanticError,
  ErrorSeverity,
  TypeError,
  BinaryOpTypeError,
  UnaryOpTypeError,
  UndefinedSymbolError,
  RedefinitionError,
  MutabilityError,
  ImmutableFieldError,
  OwnershipError,
  FieldAccessError,
  MethodCallError,
  ArgumentCountError,
  ReturnTypeError,
  MissingReturnError,
  TypeParameterError,
  ArrayIndexError,
  ControlFlowError,
  NonExhaustivePatternError,
  UnusedVariableWarning,
  UnreachableCodeWarning,
  ErrorCollector,
} from './errors';
