/**
 * KVRM Symbol Table
 *
 * Hierarchical symbol table for tracking:
 * - Variable bindings and their types
 * - Function definitions
 * - Struct and enum type definitions
 * - Scope management (global -> function -> block)
 * - Variable shadowing and lifetime tracking
 */

import { Type } from './types';
import type { SourceLocation } from './types';

export enum SymbolKind {
  Variable = 'Variable',
  Function = 'Function',
  Parameter = 'Parameter',
  Struct = 'Struct',
  Enum = 'Enum',
  TypeAlias = 'TypeAlias',
  TypeParameter = 'TypeParameter',
}

export interface SymbolFlags {
  mutable: boolean;
  initialized: boolean;
  moved: boolean;
  borrowed: boolean;
  mutablyBorrowed: boolean;
  used: boolean;
}

/**
 * Symbol table entry
 */
export interface SymbolEntry {
  name: string;
  kind: SymbolKind;
  type: Type;
  flags: SymbolFlags;
  location: SourceLocation;
  scopeLevel: number;
}

export enum ScopeKind {
  Global = 'Global',
  Function = 'Function',
  Block = 'Block',
  Loop = 'Loop',
}

/**
 * Scope information
 */
interface Scope {
  kind: ScopeKind;
  symbols: Map<string, SymbolEntry>;
  parent: Scope | null;
  level: number;
}

/**
 * Symbol table with hierarchical scoping
 */
export class SymbolTable {
  private currentScope: Scope;
  private globalScope: Scope;
  private scopeStack: Scope[] = [];

  constructor() {
    this.globalScope = {
      kind: ScopeKind.Global,
      symbols: new Map(),
      parent: null,
      level: 0,
    };
    this.currentScope = this.globalScope;
    this.scopeStack.push(this.globalScope);
  }

  /**
   * Enter a new scope
   */
  enterScope(kind: ScopeKind = ScopeKind.Block): void {
    const newScope: Scope = {
      kind,
      symbols: new Map(),
      parent: this.currentScope,
      level: this.currentScope.level + 1,
    };
    this.currentScope = newScope;
    this.scopeStack.push(newScope);
  }

  /**
   * Exit the current scope
   */
  exitScope(): void {
    if (this.currentScope === this.globalScope) {
      throw new Error('Cannot exit global scope');
    }

    this.scopeStack.pop();
    this.currentScope = this.currentScope.parent!;
  }

  /**
   * Get current scope kind
   */
  getCurrentScopeKind(): ScopeKind {
    return this.currentScope.kind;
  }

  /**
   * Get current scope level
   */
  getCurrentScopeLevel(): number {
    return this.currentScope.level;
  }

  /**
   * Check if currently in a loop
   */
  isInLoop(): boolean {
    for (const scope of this.scopeStack) {
      if (scope.kind === ScopeKind.Loop) return true;
    }
    return false;
  }

  /**
   * Check if currently in a function
   */
  isInFunction(): boolean {
    for (const scope of this.scopeStack) {
      if (scope.kind === ScopeKind.Function) return true;
    }
    return false;
  }

  /**
   * Define a new symbol in the current scope
   * Returns false if symbol already exists in current scope
   */
  define(
    name: string,
    kind: SymbolKind,
    type: Type,
    location: SourceLocation,
    flags: Partial<SymbolFlags> = {}
  ): boolean {
    // Check if already defined in current scope
    if (this.currentScope.symbols.has(name)) {
      return false;
    }

    const entry: SymbolEntry = {
      name,
      kind,
      type,
      location,
      scopeLevel: this.currentScope.level,
      flags: {
        mutable: flags.mutable ?? false,
        initialized: flags.initialized ?? false,
        moved: flags.moved ?? false,
        borrowed: flags.borrowed ?? false,
        mutablyBorrowed: flags.mutablyBorrowed ?? false,
        used: flags.used ?? false,
      },
    };

    this.currentScope.symbols.set(name, entry);
    return true;
  }

  /**
   * Look up a symbol in current scope only
   */
  lookupLocal(name: string): SymbolEntry | undefined {
    return this.currentScope.symbols.get(name);
  }

  /**
   * Look up a symbol in current scope and all parent scopes
   */
  lookup(name: string): SymbolEntry | undefined {
    let scope: Scope | null = this.currentScope;

    while (scope !== null) {
      const entry = scope.symbols.get(name);
      if (entry) return entry;
      scope = scope.parent;
    }

    return undefined;
  }

  /**
   * Check if symbol exists in any scope
   */
  has(name: string): boolean {
    return this.lookup(name) !== undefined;
  }

  /**
   * Update symbol flags
   */
  updateFlags(name: string, flags: Partial<SymbolFlags>): boolean {
    const entry = this.lookup(name);
    if (!entry) return false;

    Object.assign(entry.flags, flags);
    return true;
  }

  /**
   * Mark a symbol as used
   */
  markUsed(name: string): boolean {
    return this.updateFlags(name, { used: true });
  }

  /**
   * Mark a symbol as initialized
   */
  markInitialized(name: string): boolean {
    return this.updateFlags(name, { initialized: true });
  }

  /**
   * Mark a symbol as moved
   */
  markMoved(name: string): boolean {
    return this.updateFlags(name, { moved: true });
  }

  /**
   * Mark a symbol as borrowed
   */
  markBorrowed(name: string, mutable: boolean = false): boolean {
    return this.updateFlags(name, {
      borrowed: true,
      mutablyBorrowed: mutable,
    });
  }

  /**
   * Get all symbols in current scope
   */
  getLocalSymbols(): SymbolEntry[] {
    return Array.from(this.currentScope.symbols.values());
  }

  /**
   * Get all symbols in all scopes
   */
  getAllSymbols(): SymbolEntry[] {
    const symbols: SymbolEntry[] = [];
    let scope: Scope | null = this.currentScope;

    while (scope !== null) {
      symbols.push(...scope.symbols.values());
      scope = scope.parent;
    }

    return symbols;
  }

  /**
   * Get all unused variables in current scope for warnings
   */
  getUnusedVariables(): SymbolEntry[] {
    return this.getLocalSymbols().filter(
      (entry) =>
        entry.kind === SymbolKind.Variable &&
        !entry.flags.used &&
        !entry.name.startsWith('_')
    );
  }

  /**
   * Find similar symbol names for helpful error messages
   */
  findSimilarNames(name: string, maxDistance: number = 2): string[] {
    const allSymbols = this.getAllSymbols();
    const similar: Array<{ name: string; distance: number }> = [];

    for (const entry of allSymbols) {
      const dist = this.levenshteinDistance(name, entry.name);
      if (dist <= maxDistance) {
        similar.push({ name: entry.name, distance: dist });
      }
    }

    // Sort by distance, then alphabetically
    similar.sort((a, b) => {
      if (a.distance !== b.distance) return a.distance - b.distance;
      return a.name.localeCompare(b.name);
    });

    return similar.map((item) => item.name);
  }

  /**
   * Check if a symbol shadows another symbol from outer scope
   */
  isShadowing(name: string): SymbolEntry | undefined {
    // Skip current scope
    let scope: Scope | null = this.currentScope.parent;

    while (scope !== null) {
      const entry = scope.symbols.get(name);
      if (entry) return entry;
      scope = scope.parent;
    }

    return undefined;
  }

  /**
   * Clear all symbols (useful for testing)
   */
  clear(): void {
    this.globalScope = {
      kind: ScopeKind.Global,
      symbols: new Map(),
      parent: null,
      level: 0,
    };
    this.currentScope = this.globalScope;
    this.scopeStack = [this.globalScope];
  }

  /**
   * Get a snapshot of current scope for debugging
   */
  debugSnapshot(): object {
    const snapshot: any = {
      currentScopeKind: this.currentScope.kind,
      scopeLevel: this.currentScope.level,
      scopeStackDepth: this.scopeStack.length,
      localSymbols: {},
      allSymbols: {},
    };

    // Local symbols
    for (const [name, entry] of this.currentScope.symbols) {
      snapshot.localSymbols[name] = {
        kind: entry.kind,
        type: entry.type.toString(),
        flags: entry.flags,
      };
    }

    // All accessible symbols
    const allSymbols = this.getAllSymbols();
    for (const entry of allSymbols) {
      snapshot.allSymbols[entry.name] = {
        kind: entry.kind,
        type: entry.type.toString(),
        scopeLevel: entry.scopeLevel,
        flags: entry.flags,
      };
    }

    return snapshot;
  }

  /**
   * Compute Levenshtein distance for spell-checking
   */
  private levenshteinDistance(a: string, b: string): number {
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
}

/**
 * Scoped symbol table for easier scope management
 */
export class ScopedSymbolTable {
  private symbolTable: SymbolTable;

  constructor(symbolTable: SymbolTable) {
    this.symbolTable = symbolTable;
  }

  /**
   * Execute a function within a new scope
   */
  withScope<T>(kind: ScopeKind, fn: () => T): T {
    this.symbolTable.enterScope(kind);
    try {
      return fn();
    } finally {
      this.symbolTable.exitScope();
    }
  }

  /**
   * Execute a function within a function scope
   */
  withFunctionScope<T>(fn: () => T): T {
    return this.withScope(ScopeKind.Function, fn);
  }

  /**
   * Execute a function within a block scope
   */
  withBlockScope<T>(fn: () => T): T {
    return this.withScope(ScopeKind.Block, fn);
  }

  /**
   * Execute a function within a loop scope
   */
  withLoopScope<T>(fn: () => T): T {
    return this.withScope(ScopeKind.Loop, fn);
  }
}
