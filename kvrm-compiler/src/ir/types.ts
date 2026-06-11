/**
 * Intermediate Representation (IR) types for KVRM compiler
 * Three-address code representation for code generation
 */

/**
 * IR Operation types
 */
export enum IROpcode {
  // Arithmetic
  Add = 'ADD',
  Sub = 'SUB',
  Mul = 'MUL',
  Div = 'DIV',
  Mod = 'MOD',

  // Bitwise
  And = 'AND',
  Or = 'OR',
  Xor = 'XOR',
  Not = 'NOT',
  Shl = 'SHL',
  Shr = 'SHR',

  // Comparison
  Eq = 'EQ',
  Ne = 'NE',
  Lt = 'LT',
  Le = 'LE',
  Gt = 'GT',
  Ge = 'GE',

  // Memory
  Load = 'LOAD',
  Store = 'STORE',
  LoadAddr = 'LOAD_ADDR',

  // Control flow
  Label = 'LABEL',
  Jump = 'JUMP',
  JumpIf = 'JUMP_IF',
  Call = 'CALL',
  Return = 'RETURN',

  // Data movement
  Move = 'MOVE',
  Copy = 'COPY',

  // Stack
  Push = 'PUSH',
  Pop = 'POP',

  // Special
  Nop = 'NOP',
  Halt = 'HALT',
  Phi = 'PHI', // SSA phi node
}

/**
 * IR Value - represents operands in IR instructions
 */
export type IRValue =
  | { kind: 'constant'; value: number | string | boolean }
  | { kind: 'register'; id: number; name?: string }
  | { kind: 'variable'; name: string; id: number }
  | { kind: 'temp'; id: number }
  | { kind: 'label'; name: string }
  | { kind: 'global'; name: string }
  | { kind: 'argument'; index: number; name?: string }
  | { kind: 'memory'; base: IRValue; offset?: number };

/**
 * IR Instruction - three-address code instruction
 */
export interface IRInstruction {
  opcode: IROpcode;
  dest?: IRValue;
  src1?: IRValue;
  src2?: IRValue;
  operands?: IRValue[];
  label?: string;
  comment?: string;
  debugInfo?: {
    line: number;
    column: number;
    file?: string;
  };
}

/**
 * IR Basic Block - sequence of instructions with single entry/exit
 */
export interface IRBasicBlock {
  id: number;
  label: string;
  instructions: IRInstruction[];
  predecessors: number[];
  successors: number[];
  liveIn?: Set<number>;   // Live variable analysis
  liveOut?: Set<number>;
  dominatedBy?: Set<number>; // Dominator analysis
}

/**
 * IR Function
 */
export interface IRFunction {
  name: string;
  parameters: Array<{ name: string; type?: string }>;
  returnType?: string;
  blocks: IRBasicBlock[];
  localVars: Map<string, { id: number; type?: string }>;
  tempCount: number;
  stackSize?: number;
  isEntryPoint?: boolean;
}

/**
 * IR Program - complete compilation unit
 */
export interface IRProgram {
  functions: IRFunction[];
  globals: Map<string, { type?: string; initialValue?: IRValue }>;
  constants: Map<string, { type: string; value: any }>;
  stringLiterals: Map<string, string>; // label -> string content
}

/**
 * Helper functions for IR value creation
 */
export const IRValueFactory = {
  constant(value: number | string | boolean): IRValue {
    return { kind: 'constant', value };
  },

  register(id: number, name?: string): IRValue {
    return { kind: 'register', id, name };
  },

  variable(name: string, id: number): IRValue {
    return { kind: 'variable', name, id };
  },

  temp(id: number): IRValue {
    return { kind: 'temp', id };
  },

  label(name: string): IRValue {
    return { kind: 'label', name };
  },

  global(name: string): IRValue {
    return { kind: 'global', name };
  },

  argument(index: number, name?: string): IRValue {
    return { kind: 'argument', index, name };
  },

  memory(base: IRValue, offset?: number): IRValue {
    return { kind: 'memory', base, offset };
  },
};

/**
 * Helper to create IR instructions
 */
export function createInstruction(
  opcode: IROpcode,
  options: {
    dest?: IRValue;
    src1?: IRValue;
    src2?: IRValue;
    operands?: IRValue[];
    label?: string;
    comment?: string;
  } = {}
): IRInstruction {
  return {
    opcode,
    ...options,
  };
}

/**
 * Type guards for IR values
 */
export function isConstant(value: IRValue): value is { kind: 'constant'; value: number | string | boolean } {
  return value.kind === 'constant';
}

export function isRegister(value: IRValue): value is { kind: 'register'; id: number; name?: string } {
  return value.kind === 'register';
}

export function isVariable(value: IRValue): value is { kind: 'variable'; name: string; id: number } {
  return value.kind === 'variable';
}

export function isTemp(value: IRValue): value is { kind: 'temp'; id: number } {
  return value.kind === 'temp';
}

export function isLabel(value: IRValue): value is { kind: 'label'; name: string } {
  return value.kind === 'label';
}

export function isMemory(value: IRValue): value is { kind: 'memory'; base: IRValue; offset?: number } {
  return value.kind === 'memory';
}
