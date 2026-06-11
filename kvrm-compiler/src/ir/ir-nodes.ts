/**
 * IR Node Definitions for KVRM Compiler
 *
 * SSA-based intermediate representation designed for the KVRM CPU architecture:
 * - 16 general-purpose registers (R0-R15)
 * - Stack-based calling convention
 * - Load/Store architecture
 * - Basic arithmetic and logic operations
 */

/**
 * IR-level type representation
 */
export enum IRTypeKind {
  I32 = 'i32',      // 32-bit signed integer
  I64 = 'i64',      // 64-bit signed integer
  F32 = 'f32',      // 32-bit float
  F64 = 'f64',      // 64-bit float
  Bool = 'bool',    // Boolean (1-bit logical, stored as i32)
  Ptr = 'ptr',      // Pointer type
  Void = 'void',    // No return value
  Struct = 'struct', // Struct type
}

export interface IRType {
  kind: IRTypeKind;
  size: number; // Size in bytes
  structName?: string; // For struct types
  pointeeType?: IRType; // For pointer types
}

/**
 * SSA value representation
 * Each value has a unique ID for SSA form
 */
export interface IRValue {
  id: number;
  type: IRType;
  name?: string; // Optional debug name
}

/**
 * Binary operation types
 */
export enum BinOpKind {
  // Arithmetic
  Add = 'add',
  Sub = 'sub',
  Mul = 'mul',
  Div = 'div',
  Mod = 'mod',

  // Comparison
  Eq = 'eq',
  Ne = 'ne',
  Lt = 'lt',
  Le = 'le',
  Gt = 'gt',
  Ge = 'ge',

  // Logical
  And = 'and',
  Or = 'or',

  // Bitwise
  BitAnd = 'bitand',
  BitOr = 'bitor',
  BitXor = 'bitxor',
  Shl = 'shl',
  Shr = 'shr',
}

/**
 * Unary operation types
 */
export enum UnaryOpKind {
  Neg = 'neg',       // Arithmetic negation
  Not = 'not',       // Logical NOT
  BitNot = 'bitnot', // Bitwise NOT
}

/**
 * Base instruction interface
 */
export interface IRInstruction {
  kind: string;
  result?: IRValue; // SSA result value (if any)
  debugInfo?: {
    line: number;
    column: number;
    sourceFile?: string;
  };
}

/**
 * Load constant value
 */
export interface IRConst extends IRInstruction {
  kind: 'const';
  result: IRValue;
  value: number | string | boolean;
}

/**
 * Load from memory
 */
export interface IRLoad extends IRInstruction {
  kind: 'load';
  result: IRValue;
  address: IRValue; // Pointer to load from
}

/**
 * Store to memory
 */
export interface IRStore extends IRInstruction {
  kind: 'store';
  address: IRValue; // Pointer to store to
  value: IRValue;   // Value to store
}

/**
 * Binary operation
 */
export interface IRBinOp extends IRInstruction {
  kind: 'binop';
  result: IRValue;
  op: BinOpKind;
  left: IRValue;
  right: IRValue;
}

/**
 * Unary operation
 */
export interface IRUnaryOp extends IRInstruction {
  kind: 'unaryop';
  result: IRValue;
  op: UnaryOpKind;
  operand: IRValue;
}

/**
 * Function call
 */
export interface IRCall extends IRInstruction {
  kind: 'call';
  result?: IRValue; // void functions have no result
  functionName: string;
  arguments: IRValue[];
}

/**
 * Unconditional jump
 */
export interface IRJump extends IRInstruction {
  kind: 'jump';
  target: string; // Target block label
}

/**
 * Conditional jump
 */
export interface IRCondJump extends IRInstruction {
  kind: 'condjump';
  condition: IRValue;
  trueTarget: string;  // Block label if condition is true
  falseTarget: string; // Block label if condition is false
}

/**
 * SSA phi node for merging values from different control flow paths
 */
export interface IRPhi extends IRInstruction {
  kind: 'phi';
  result: IRValue;
  incomingValues: Array<{
    value: IRValue;
    block: string; // Source block label
  }>;
}

/**
 * Return from function
 */
export interface IRReturn extends IRInstruction {
  kind: 'return';
  value?: IRValue; // void functions have no return value
}

/**
 * Stack allocation (for local variables)
 */
export interface IRAlloc extends IRInstruction {
  kind: 'alloc';
  result: IRValue; // Returns pointer to allocated space
  allocatedType: IRType;
}

/**
 * Get element pointer (for struct field access, array indexing)
 */
export interface IRGetElementPtr extends IRInstruction {
  kind: 'getelementptr';
  result: IRValue; // Returns pointer to element
  basePtr: IRValue;
  indices: IRValue[]; // For nested access
}

/**
 * Type union for all instruction types
 */
export type IRInstr =
  | IRConst
  | IRLoad
  | IRStore
  | IRBinOp
  | IRUnaryOp
  | IRCall
  | IRJump
  | IRCondJump
  | IRPhi
  | IRReturn
  | IRAlloc
  | IRGetElementPtr;

/**
 * Basic block in control flow graph
 */
export interface IRBlock {
  label: string;
  instructions: IRInstr[];
  predecessors: string[]; // Labels of blocks that jump here
  successors: string[];   // Labels of blocks this jumps to
}

/**
 * Function definition in IR
 */
export interface IRFunction {
  name: string;
  parameters: IRValue[];
  returnType: IRType;
  blocks: IRBlock[];
  entryBlock: string; // Label of entry block
  localCount: number; // Number of local variables allocated
}

/**
 * Complete IR program
 */
export interface IRProgram {
  functions: IRFunction[];
  structs: Map<string, IRStructDef>;
  globalVariables: Map<string, IRGlobalVar>;
}

/**
 * Struct definition
 */
export interface IRStructDef {
  name: string;
  fields: Array<{
    name: string;
    type: IRType;
    offset: number; // Byte offset in struct
  }>;
  size: number; // Total size in bytes
  alignment: number;
}

/**
 * Global variable definition
 */
export interface IRGlobalVar {
  name: string;
  type: IRType;
  initialValue?: number | string | boolean;
  isConstant: boolean;
}

/**
 * Type helper functions
 */
export const IRTypes = {
  i32(): IRType {
    return { kind: IRTypeKind.I32, size: 4 };
  },

  i64(): IRType {
    return { kind: IRTypeKind.I64, size: 8 };
  },

  f32(): IRType {
    return { kind: IRTypeKind.F32, size: 4 };
  },

  f64(): IRType {
    return { kind: IRTypeKind.F64, size: 8 };
  },

  bool(): IRType {
    return { kind: IRTypeKind.Bool, size: 4 }; // Stored as i32
  },

  void(): IRType {
    return { kind: IRTypeKind.Void, size: 0 };
  },

  ptr(pointeeType: IRType): IRType {
    return { kind: IRTypeKind.Ptr, size: 8, pointeeType };
  },

  struct(name: string, size: number): IRType {
    return { kind: IRTypeKind.Struct, size, structName: name };
  },
};

/**
 * Check if type is integer
 */
export function isIntegerType(type: IRType): boolean {
  return type.kind === IRTypeKind.I32 || type.kind === IRTypeKind.I64;
}

/**
 * Check if type is floating point
 */
export function isFloatType(type: IRType): boolean {
  return type.kind === IRTypeKind.F32 || type.kind === IRTypeKind.F64;
}

/**
 * Check if type is pointer
 */
export function isPointerType(type: IRType): boolean {
  return type.kind === IRTypeKind.Ptr;
}

/**
 * Get type alignment in bytes
 */
export function getTypeAlignment(type: IRType): number {
  switch (type.kind) {
    case IRTypeKind.Bool:
    case IRTypeKind.I32:
    case IRTypeKind.F32:
      return 4;
    case IRTypeKind.I64:
    case IRTypeKind.F64:
    case IRTypeKind.Ptr:
      return 8;
    case IRTypeKind.Struct:
      // Struct alignment is max of field alignments (simplified)
      return 8;
    default:
      return 1;
  }
}
