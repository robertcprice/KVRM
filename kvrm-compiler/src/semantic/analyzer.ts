/**
 * KVRM Semantic Analyzer
 *
 * Main entry point for semantic analysis:
 * - Build symbol tables
 * - Type check all expressions and statements
 * - Validate function signatures
 * - Check struct/enum definitions
 * - Basic ownership and mutability checks
 * - Type inference for let bindings
 */

import {
  Type,
  PrimitiveType,
  ArrayType,
  StructType,
  EnumType,
  FunctionType,
  TypeParameter,
  BuiltinTypes,
  PrimitiveTypeKind,
  StructField as SemanticStructField,
  EnumVariant as SemanticEnumVariant,
  type SourceLocation,
} from './types';

import {
  SemanticError,
  TypeError,
  UndefinedSymbolError,
  RedefinitionError,
  ReturnTypeError,
  MissingReturnError,
  ControlFlowError,
  UnusedVariableWarning,
  ErrorCollector,
} from './errors';

import { SymbolTable, SymbolKind, ScopeKind } from './symbol-table';
import { TypeChecker } from './type-checker';

import type {
  Program,
  Declaration,
  FunctionDeclaration,
  VariableDeclaration,
  StructDeclaration,
  EnumDeclaration,
  TraitDeclaration,
  Statement,
  BlockStatement,
  IfStatement,
  WhileStatement,
  ForStatement,
  ReturnStatement,
  BreakStatement,
  ContinueStatement,
  ExpressionStatement,
  Expression,
  Parameter,
  TypeExpression,
  StructField,
  EnumVariant,
  GenericParameter,
} from '../types/ast';

/**
 * Result of semantic analysis
 */
export interface SemanticResult {
  success: boolean;
  errors: SemanticError[];
  warnings: SemanticError[];
  symbolTable: SymbolTable;
}

/**
 * Semantic analyzer for KVRM programs
 */
export class SemanticAnalyzer {
  private symbolTable: SymbolTable;
  private typeChecker: TypeChecker;
  private errors: ErrorCollector;
  private currentFunction: FunctionDeclaration | null = null;

  constructor() {
    this.symbolTable = new SymbolTable();
    this.errors = new ErrorCollector();
    this.typeChecker = new TypeChecker(this.symbolTable, this.errors);
  }

  /**
   * Analyze a program and return semantic analysis results
   */
  analyze(program: Program): SemanticResult {
    // Reset state
    this.errors.clear();
    this.currentFunction = null;

    try {
      // First pass: Register all type declarations
      this.registerTypeDeclarations(program.declarations);

      // Second pass: Analyze all declarations
      for (const decl of program.declarations) {
        this.analyzeDeclaration(decl);
      }

      // Check for unused variables (warnings)
      this.checkUnusedVariables();

      return {
        success: !this.errors.hasErrors(),
        errors: this.errors.getErrors(),
        warnings: this.errors.getWarnings(),
        symbolTable: this.symbolTable,
      };
    } catch (error) {
      // Catch any unexpected errors
      console.error('Semantic analysis error:', error);
      return {
        success: false,
        errors: this.errors.getErrors(),
        warnings: this.errors.getWarnings(),
        symbolTable: this.symbolTable,
      };
    }
  }

  /**
   * First pass: Register all type declarations (structs, enums, etc.)
   */
  private registerTypeDeclarations(declarations: readonly Declaration[]): void {
    for (const decl of declarations) {
      switch (decl.kind) {
        case 'StructDeclaration':
          this.registerStructType(decl as StructDeclaration);
          break;

        case 'EnumDeclaration':
          this.registerEnumType(decl as EnumDeclaration);
          break;

        case 'FunctionDeclaration':
          this.registerFunctionType(decl as FunctionDeclaration);
          break;

        case 'VariableDeclaration':
          // Global variables registered in second pass
          break;

        default:
          // Other declaration types handled in second pass
          break;
      }
    }
  }

  /**
   * Register a struct type in the symbol table
   */
  private registerStructType(decl: StructDeclaration): void {
    const name = decl.name.name;

    // Check for redefinition
    if (this.symbolTable.lookupLocal(name)) {
      const existing = this.symbolTable.lookup(name)!;
      this.errors.add(
        new RedefinitionError(name, decl.location, existing.location)
      );
      return;
    }

    // Parse type parameters
    const typeParams = this.parseGenericParameters(decl.genericParams);

    // Parse fields
    const fields = new Map<string, SemanticStructField>();
    for (const field of decl.fields) {
      const fieldType = this.resolveTypeExpression(field.type);
      fields.set(field.name.name, {
        name: field.name.name,
        type: fieldType,
        mutable: false, // Field-level mutability from AST if available
        location: field.location,
      });
    }

    const structType = new StructType(name, fields, typeParams);

    // Define in symbol table
    this.symbolTable.define(
      name,
      SymbolKind.Struct,
      structType,
      decl.location
    );
  }

  /**
   * Register an enum type in the symbol table
   */
  private registerEnumType(decl: EnumDeclaration): void {
    const name = decl.name.name;

    // Check for redefinition
    if (this.symbolTable.lookupLocal(name)) {
      const existing = this.symbolTable.lookup(name)!;
      this.errors.add(
        new RedefinitionError(name, decl.location, existing.location)
      );
      return;
    }

    // Parse type parameters
    const typeParams = this.parseGenericParameters(decl.genericParams);

    // Parse variants
    const variants = new Map<string, SemanticEnumVariant>();
    for (const variant of decl.variants) {
      let associatedType: Type | undefined;

      // Check if variant has associated data (tuple or struct style)
      if (Array.isArray(variant.fields) && variant.fields.length > 0) {
        // Simplified: treat first field as associated type
        const firstField = variant.fields[0];
        if ('name' in firstField) {
          // Struct-style variant - would need full handling
          associatedType = BuiltinTypes.unknown;
        } else {
          // Tuple-style variant
          associatedType = this.resolveTypeExpression(
            firstField as TypeExpression
          );
        }
      }

      variants.set(variant.name.name, {
        name: variant.name.name,
        associatedType,
        location: variant.location,
      });
    }

    const enumType = new EnumType(name, variants, typeParams);

    // Define in symbol table
    this.symbolTable.define(name, SymbolKind.Enum, enumType, decl.location);
  }

  /**
   * Register a function type in the symbol table
   */
  private registerFunctionType(decl: FunctionDeclaration): void {
    const name = decl.name.name;

    // Check for redefinition
    if (this.symbolTable.lookupLocal(name)) {
      const existing = this.symbolTable.lookup(name)!;
      this.errors.add(
        new RedefinitionError(name, decl.location, existing.location)
      );
      return;
    }

    // Parse type parameters
    const typeParams = this.parseGenericParameters(decl.genericParams);

    // Parse parameter types
    const paramTypes: Type[] = [];
    for (const param of decl.parameters) {
      paramTypes.push(this.resolveTypeExpression(param.type));
    }

    // Parse return type
    const returnType = decl.returnType
      ? this.resolveTypeExpression(decl.returnType)
      : BuiltinTypes.void;

    const functionType = new FunctionType(paramTypes, returnType, typeParams);

    // Define in symbol table
    this.symbolTable.define(
      name,
      SymbolKind.Function,
      functionType,
      decl.location
    );
  }

  /**
   * Analyze a declaration
   */
  private analyzeDeclaration(decl: Declaration): void {
    switch (decl.kind) {
      case 'FunctionDeclaration':
        this.analyzeFunctionDeclaration(decl as FunctionDeclaration);
        break;

      case 'VariableDeclaration':
        this.analyzeVariableDeclaration(decl as VariableDeclaration);
        break;

      case 'StructDeclaration':
      case 'EnumDeclaration':
        // Already registered in first pass
        break;

      case 'TraitDeclaration':
        // Trait analysis would go here
        break;

      default:
        // Other declarations
        break;
    }
  }

  /**
   * Analyze a function declaration
   */
  private analyzeFunctionDeclaration(decl: FunctionDeclaration): void {
    const functionSymbol = this.symbolTable.lookup(decl.name.name);
    if (!functionSymbol) return; // Should have been registered

    const functionType = functionSymbol.type as FunctionType;

    // Enter function scope
    this.symbolTable.enterScope(ScopeKind.Function);
    this.currentFunction = decl;

    try {
      // Define parameters in function scope
      for (const param of decl.parameters) {
        const paramType = this.resolveTypeExpression(param.type);
        this.symbolTable.define(
          param.name.name,
          SymbolKind.Parameter,
          paramType,
          param.location,
          {
            mutable: param.isMutable,
            initialized: true,
          }
        );
      }

      // Analyze function body
      this.analyzeStatement(decl.body);

      // Check return type matches (simplified - full analysis would track all paths)
      if (!functionType.returnType.equals(BuiltinTypes.void)) {
        // In a full implementation, verify all code paths return
        // For now, just check if there's at least one return statement
        if (!this.hasReturnStatement(decl.body)) {
          this.errors.add(
            new MissingReturnError(
              decl.name.name,
              functionType.returnType,
              decl.location
            )
          );
        }
      }
    } finally {
      this.symbolTable.exitScope();
      this.currentFunction = null;
    }
  }

  /**
   * Check if a block has a return statement (simplified check)
   */
  private hasReturnStatement(block: BlockStatement): boolean {
    for (const stmt of block.statements) {
      if (stmt.kind === 'ReturnStatement') return true;

      // Recursively check nested blocks
      if (stmt.kind === 'BlockStatement') {
        if (this.hasReturnStatement(stmt as BlockStatement)) return true;
      }

      if (stmt.kind === 'IfStatement') {
        const ifStmt = stmt as IfStatement;
        if (
          this.hasReturnStatement(ifStmt.thenBranch) &&
          ifStmt.elseBranch &&
          (ifStmt.elseBranch.kind === 'BlockStatement'
            ? this.hasReturnStatement(ifStmt.elseBranch as BlockStatement)
            : true)
        ) {
          return true;
        }
      }
    }
    return false;
  }

  /**
   * Analyze a variable declaration
   */
  private analyzeVariableDeclaration(decl: VariableDeclaration): void {
    const name = decl.name.name;

    // Check for redefinition in current scope
    if (this.symbolTable.lookupLocal(name)) {
      const existing = this.symbolTable.lookup(name)!;
      this.errors.add(
        new RedefinitionError(name, decl.location, existing.location)
      );
      return;
    }

    // Determine variable type
    let varType: Type;

    if (decl.type) {
      // Explicit type annotation
      varType = this.resolveTypeExpression(decl.type);

      // If there's an initializer, check compatibility
      if (decl.initializer) {
        const initType = this.typeChecker.checkExpression(decl.initializer);
        if (!initType.isAssignableTo(varType)) {
          this.errors.add(
            new TypeError(
              varType,
              initType,
              decl.initializer.location,
              'in variable initialization'
            )
          );
        }
      }
    } else if (decl.initializer) {
      // Type inference from initializer
      varType = this.typeChecker.checkExpression(decl.initializer);
    } else {
      // No type annotation and no initializer - error
      this.errors.add(
        new TypeError(
          BuiltinTypes.unknown,
          BuiltinTypes.unknown,
          decl.location,
          'variable requires either type annotation or initializer'
        )
      );
      varType = BuiltinTypes.unknown;
    }

    // Define variable in symbol table
    this.symbolTable.define(
      name,
      SymbolKind.Variable,
      varType,
      decl.location,
      {
        mutable: decl.isMutable,
        initialized: decl.initializer !== null,
      }
    );
  }

  /**
   * Analyze a statement
   */
  private analyzeStatement(stmt: Statement): void {
    switch (stmt.kind) {
      case 'VariableDeclaration':
        this.analyzeVariableDeclaration(stmt as VariableDeclaration);
        break;

      case 'ExpressionStatement':
        this.typeChecker.checkExpression(
          (stmt as ExpressionStatement).expression
        );
        break;

      case 'BlockStatement':
        this.analyzeBlockStatement(stmt as BlockStatement);
        break;

      case 'IfStatement':
        this.analyzeIfStatement(stmt as IfStatement);
        break;

      case 'WhileStatement':
        this.analyzeWhileStatement(stmt as WhileStatement);
        break;

      case 'ForStatement':
        this.analyzeForStatement(stmt as ForStatement);
        break;

      case 'ReturnStatement':
        this.analyzeReturnStatement(stmt as ReturnStatement);
        break;

      case 'BreakStatement':
        this.analyzeBreakStatement(stmt as BreakStatement);
        break;

      case 'ContinueStatement':
        this.analyzeContinueStatement(stmt as ContinueStatement);
        break;

      default:
        // Other statement types
        break;
    }
  }

  /**
   * Analyze a block statement
   */
  private analyzeBlockStatement(stmt: BlockStatement): void {
    this.symbolTable.enterScope(ScopeKind.Block);

    try {
      for (const innerStmt of stmt.statements) {
        this.analyzeStatement(innerStmt);
      }
    } finally {
      this.symbolTable.exitScope();
    }
  }

  /**
   * Analyze an if statement
   */
  private analyzeIfStatement(stmt: IfStatement): void {
    // Check condition is boolean
    const condType = this.typeChecker.checkExpression(stmt.condition);
    this.typeChecker.expectType(
      BuiltinTypes.bool,
      condType,
      stmt.condition.location,
      'in if condition'
    );

    // Analyze branches
    this.analyzeStatement(stmt.thenBranch);
    if (stmt.elseBranch) {
      this.analyzeStatement(stmt.elseBranch);
    }
  }

  /**
   * Analyze a while statement
   */
  private analyzeWhileStatement(stmt: WhileStatement): void {
    // Check condition is boolean
    const condType = this.typeChecker.checkExpression(stmt.condition);
    this.typeChecker.expectType(
      BuiltinTypes.bool,
      condType,
      stmt.condition.location,
      'in while condition'
    );

    // Analyze body in loop scope
    this.symbolTable.enterScope(ScopeKind.Loop);
    try {
      this.analyzeStatement(stmt.body);
    } finally {
      this.symbolTable.exitScope();
    }
  }

  /**
   * Analyze a for statement
   */
  private analyzeForStatement(stmt: ForStatement): void {
    // Analyze iterator expression
    const iterType = this.typeChecker.checkExpression(stmt.iterator);

    // Enter loop scope
    this.symbolTable.enterScope(ScopeKind.Loop);
    try {
      // Define loop variable
      // In a full implementation, would extract element type from iterator
      const elemType = BuiltinTypes.unknown;

      this.symbolTable.define(
        stmt.variable.name,
        SymbolKind.Variable,
        elemType,
        stmt.variable.location,
        {
          mutable: false,
          initialized: true,
        }
      );

      // Analyze body
      this.analyzeStatement(stmt.body);
    } finally {
      this.symbolTable.exitScope();
    }
  }

  /**
   * Analyze a return statement
   */
  private analyzeReturnStatement(stmt: ReturnStatement): void {
    if (!this.currentFunction) {
      this.errors.add(
        new TypeError(
          BuiltinTypes.unknown,
          BuiltinTypes.unknown,
          stmt.location,
          'return statement outside function'
        )
      );
      return;
    }

    const functionSymbol = this.symbolTable.lookup(
      this.currentFunction.name.name
    );
    if (!functionSymbol) return;

    const functionType = functionSymbol.type as FunctionType;
    const expectedReturnType = functionType.returnType;

    if (stmt.value) {
      const returnType = this.typeChecker.checkExpression(stmt.value);
      if (!returnType.isAssignableTo(expectedReturnType)) {
        this.errors.add(
          new ReturnTypeError(expectedReturnType, returnType, stmt.location)
        );
      }
    } else {
      // No return value - must be void function
      if (!expectedReturnType.equals(BuiltinTypes.void)) {
        this.errors.add(
          new ReturnTypeError(
            expectedReturnType,
            BuiltinTypes.void,
            stmt.location
          )
        );
      }
    }
  }

  /**
   * Analyze a break statement
   */
  private analyzeBreakStatement(stmt: BreakStatement): void {
    if (!this.symbolTable.isInLoop()) {
      this.errors.add(new ControlFlowError('break', stmt.location));
    }
  }

  /**
   * Analyze a continue statement
   */
  private analyzeContinueStatement(stmt: ContinueStatement): void {
    if (!this.symbolTable.isInLoop()) {
      this.errors.add(new ControlFlowError('continue', stmt.location));
    }
  }

  /**
   * Resolve a type expression to a concrete type
   */
  private resolveTypeExpression(typeExpr: TypeExpression): Type {
    switch (typeExpr.kind) {
      case 'TypeReference': {
        const name = typeExpr.name.name;

        // Check built-in types
        const builtinType = this.getBuiltinType(name);
        if (builtinType) return builtinType;

        // Look up user-defined type
        const symbol = this.symbolTable.lookup(name);
        if (!symbol) {
          this.errors.add(
            new UndefinedSymbolError(name, typeExpr.location, [])
          );
          return BuiltinTypes.unknown;
        }

        return symbol.type;
      }

      case 'ArrayType': {
        const elemType = this.resolveTypeExpression(typeExpr.elementType);
        // Size would need to be evaluated if it's an expression
        return new ArrayType(elemType);
      }

      case 'TupleType': {
        // Simplified tuple handling
        return BuiltinTypes.unknown;
      }

      case 'FunctionType': {
        const paramTypes = typeExpr.parameters.map((p) =>
          this.resolveTypeExpression(p)
        );
        const returnType = this.resolveTypeExpression(typeExpr.returnType);
        return new FunctionType(paramTypes, returnType);
      }

      case 'GenericType': {
        // Simplified generic handling
        return BuiltinTypes.unknown;
      }

      case 'ReferenceType': {
        // Reference type handling
        const innerType = this.resolveTypeExpression(typeExpr.type);
        return innerType; // Simplified - would wrap in reference type
      }

      default:
        return BuiltinTypes.unknown;
    }
  }

  /**
   * Get built-in type by name
   */
  private getBuiltinType(name: string): Type | null {
    const builtinMap: Record<string, Type> = {
      i8: BuiltinTypes.i8,
      i16: BuiltinTypes.i16,
      i32: BuiltinTypes.i32,
      i64: BuiltinTypes.i64,
      u8: BuiltinTypes.u8,
      u16: BuiltinTypes.u16,
      u32: BuiltinTypes.u32,
      u64: BuiltinTypes.u64,
      f32: BuiltinTypes.f32,
      f64: BuiltinTypes.f64,
      bool: BuiltinTypes.bool,
      char: BuiltinTypes.char,
      str: BuiltinTypes.str,
      void: BuiltinTypes.void,
    };

    return builtinMap[name] || null;
  }

  /**
   * Parse generic parameters
   */
  private parseGenericParameters(
    params: readonly GenericParameter[]
  ): TypeParameter[] {
    if (!params || params.length === 0) return [];

    return params.map((param) => {
      const bounds: Type[] = []; // Simplified - would resolve bounds
      return new TypeParameter(param.name.name, bounds);
    });
  }

  /**
   * Check for unused variables and generate warnings
   */
  private checkUnusedVariables(): void {
    const unused = this.symbolTable.getUnusedVariables();
    for (const symbol of unused) {
      this.errors.add(
        new UnusedVariableWarning(symbol.name, symbol.location)
      );
    }
  }

  /**
   * Get the symbol table (for debugging/testing)
   */
  getSymbolTable(): SymbolTable {
    return this.symbolTable;
  }

  /**
   * Get all errors
   */
  getErrors(): SemanticError[] {
    return this.errors.getAllIssues();
  }
}
