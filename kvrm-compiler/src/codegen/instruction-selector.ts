/**
 * Instruction Selector for KVRM Code Generator
 * Maps IR operations to KVRM assembly instructions
 */

import type { IRInstruction, IRValue, IROpcode } from '../ir/types.js';
import { isConstant, isMemory } from '../ir/types.js';
import type { KVRMRegister } from './register-allocator.js';

/**
 * KVRM Assembly instruction
 */
export interface KVRMInstruction {
  mnemonic: string;
  operands: string[];
  comment?: string;
}

/**
 * Addressing mode for KVRM instructions
 */
export enum AddressingMode {
  Register,      // R0
  Immediate,     // #42
  RegisterIndirect, // [R0]
  RegisterOffset,   // [R0, #4]
  Label,         // main, .L1
}

/**
 * Instruction selection context
 */
interface SelectionContext {
  registerMap: Map<number, KVRMRegister | { stack: number }>;
  tempRegister: KVRMRegister;
  labelCounter: number;
}

/**
 * Instruction Selector - Maps IR to KVRM assembly
 */
export class InstructionSelector {
  private context: SelectionContext;

  constructor(
    registerMap: Map<number, KVRMRegister | { stack: number }>,
    tempRegister: KVRMRegister = 12 // R12 as scratch register
  ) {
    this.context = {
      registerMap,
      tempRegister,
      labelCounter: 0,
    };
  }

  /**
   * Select instructions for an IR instruction
   */
  public select(ir: IRInstruction): KVRMInstruction[] {
    const instructions: KVRMInstruction[] = [];

    switch (ir.opcode) {
      // Arithmetic operations
      case 'ADD':
        instructions.push(...this.selectBinaryOp('ADD', ir));
        break;
      case 'SUB':
        instructions.push(...this.selectBinaryOp('SUB', ir));
        break;
      case 'MUL':
        instructions.push(...this.selectBinaryOp('MUL', ir));
        break;
      case 'DIV':
        instructions.push(...this.selectBinaryOp('DIV', ir));
        break;

      // Bitwise operations
      case 'AND':
        instructions.push(...this.selectBinaryOp('AND', ir));
        break;
      case 'OR':
        instructions.push(...this.selectBinaryOp('OR', ir));
        break;
      case 'XOR':
        instructions.push(...this.selectBinaryOp('XOR', ir));
        break;
      case 'NOT':
        instructions.push(...this.selectUnaryOp('NOT', ir));
        break;
      case 'SHL':
        instructions.push(...this.selectBinaryOp('SHL', ir));
        break;
      case 'SHR':
        instructions.push(...this.selectBinaryOp('SHR', ir));
        break;

      // Comparison operations
      case 'EQ':
      case 'NE':
      case 'LT':
      case 'LE':
      case 'GT':
      case 'GE':
        instructions.push(...this.selectComparison(ir));
        break;

      // Memory operations
      case 'LOAD':
        instructions.push(...this.selectLoad(ir));
        break;
      case 'STORE':
        instructions.push(...this.selectStore(ir));
        break;
      case 'LOAD_ADDR':
        instructions.push(...this.selectLoadAddr(ir));
        break;

      // Control flow
      case 'LABEL':
        if (ir.label) {
          instructions.push({ mnemonic: ir.label + ':', operands: [] });
        }
        break;
      case 'JUMP':
        instructions.push(...this.selectJump(ir));
        break;
      case 'JUMP_IF':
        instructions.push(...this.selectJumpIf(ir));
        break;
      case 'CALL':
        instructions.push(...this.selectCall(ir));
        break;
      case 'RETURN':
        instructions.push({ mnemonic: 'RET', operands: [] });
        break;

      // Data movement
      case 'MOVE':
      case 'COPY':
        instructions.push(...this.selectMove(ir));
        break;

      // Stack operations
      case 'PUSH':
        instructions.push(...this.selectPush(ir));
        break;
      case 'POP':
        instructions.push(...this.selectPop(ir));
        break;

      // Special
      case 'NOP':
        instructions.push({ mnemonic: 'NOP', operands: [] });
        break;
      case 'HALT':
        instructions.push({ mnemonic: 'HLT', operands: [] });
        break;

      default:
        throw new Error(`Unsupported IR opcode: ${ir.opcode}`);
    }

    // Add comments from IR instruction
    if (ir.comment && instructions.length > 0) {
      instructions[0].comment = ir.comment;
    }

    return instructions;
  }

  /**
   * Select binary operation (ADD, SUB, etc.)
   */
  private selectBinaryOp(op: string, ir: IRInstruction): KVRMInstruction[] {
    const instructions: KVRMInstruction[] = [];

    if (!ir.dest || !ir.src1 || !ir.src2) {
      throw new Error(`Binary operation ${op} requires dest, src1, and src2`);
    }

    const dest = this.getOperandString(ir.dest);
    const src1 = this.getOperandString(ir.src1);
    const src2 = this.getOperandString(ir.src2);

    // Handle immediate operands
    if (isConstant(ir.src2)) {
      const imm = this.getImmediateValue(ir.src2);
      if (this.isValidImmediate(imm)) {
        // dest = src1 op #imm
        if (dest !== src1) {
          instructions.push({ mnemonic: 'MOV', operands: [dest, src1] });
        }
        instructions.push({ mnemonic: op, operands: [dest, dest, `#${imm}`] });
      } else {
        // Load immediate into temp register
        instructions.push(...this.loadLargeImmediate('R12', imm));
        if (dest !== src1) {
          instructions.push({ mnemonic: 'MOV', operands: [dest, src1] });
        }
        instructions.push({ mnemonic: op, operands: [dest, dest, 'R12'] });
      }
    } else {
      // dest = src1 op src2
      if (dest !== src1) {
        instructions.push({ mnemonic: 'MOV', operands: [dest, src1] });
      }
      instructions.push({ mnemonic: op, operands: [dest, dest, src2] });
    }

    return instructions;
  }

  /**
   * Select unary operation (NOT)
   */
  private selectUnaryOp(op: string, ir: IRInstruction): KVRMInstruction[] {
    if (!ir.dest || !ir.src1) {
      throw new Error(`Unary operation ${op} requires dest and src1`);
    }

    const dest = this.getOperandString(ir.dest);
    const src = this.getOperandString(ir.src1);

    return [{ mnemonic: op, operands: [dest, src] }];
  }

  /**
   * Select comparison operation
   */
  private selectComparison(ir: IRInstruction): KVRMInstruction[] {
    const instructions: KVRMInstruction[] = [];

    if (!ir.dest || !ir.src1 || !ir.src2) {
      throw new Error(`Comparison requires dest, src1, and src2`);
    }

    const dest = this.getOperandString(ir.dest);
    const src1 = this.getOperandString(ir.src1);
    const src2 = this.getOperandString(ir.src2);

    // Compare src1 with src2
    instructions.push({ mnemonic: 'CMP', operands: [src1, src2] });

    // Set destination based on comparison result
    const condition = this.getConditionCode(ir.opcode);
    instructions.push({ mnemonic: 'MOV', operands: [dest, '#0'] });
    instructions.push({ mnemonic: `MOV${condition}`, operands: [dest, '#1'] });

    return instructions;
  }

  /**
   * Select load operation
   */
  private selectLoad(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.dest || !ir.src1) {
      throw new Error('LOAD requires dest and src1 (address)');
    }

    const dest = this.getOperandString(ir.dest);

    if (isMemory(ir.src1)) {
      const base = this.getOperandString(ir.src1.base);
      const offset = ir.src1.offset || 0;

      if (offset === 0) {
        return [{ mnemonic: 'LDR', operands: [dest, `[${base}]`] }];
      } else {
        return [{ mnemonic: 'LDR', operands: [dest, `[${base}, #${offset}]`] }];
      }
    } else {
      const addr = this.getOperandString(ir.src1);
      return [{ mnemonic: 'LDR', operands: [dest, `[${addr}]`] }];
    }
  }

  /**
   * Select store operation
   */
  private selectStore(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.dest || !ir.src1) {
      throw new Error('STORE requires dest (address) and src1 (value)');
    }

    const src = this.getOperandString(ir.src1);

    if (isMemory(ir.dest)) {
      const base = this.getOperandString(ir.dest.base);
      const offset = ir.dest.offset || 0;

      if (offset === 0) {
        return [{ mnemonic: 'STR', operands: [src, `[${base}]`] }];
      } else {
        return [{ mnemonic: 'STR', operands: [src, `[${base}, #${offset}]`] }];
      }
    } else {
      const addr = this.getOperandString(ir.dest);
      return [{ mnemonic: 'STR', operands: [src, `[${addr}]`] }];
    }
  }

  /**
   * Select load address operation
   */
  private selectLoadAddr(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.dest || !ir.src1) {
      throw new Error('LOAD_ADDR requires dest and src1');
    }

    const dest = this.getOperandString(ir.dest);
    const src = this.getOperandString(ir.src1);

    return [{ mnemonic: 'LEA', operands: [dest, src] }];
  }

  /**
   * Select jump operation
   */
  private selectJump(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.src1 || ir.src1.kind !== 'label') {
      throw new Error('JUMP requires label operand');
    }

    return [{ mnemonic: 'JMP', operands: [ir.src1.name] }];
  }

  /**
   * Select conditional jump
   */
  private selectJumpIf(ir: IRInstruction): KVRMInstruction[] {
    const instructions: KVRMInstruction[] = [];

    if (!ir.src1 || !ir.src2 || ir.src2.kind !== 'label') {
      throw new Error('JUMP_IF requires condition and label');
    }

    const condition = this.getOperandString(ir.src1);
    const label = ir.src2.name;

    // Compare condition with zero and jump if not zero
    instructions.push({ mnemonic: 'CMP', operands: [condition, '#0'] });
    instructions.push({ mnemonic: 'JNZ', operands: [label] });

    return instructions;
  }

  /**
   * Select function call
   */
  private selectCall(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.src1 || ir.src1.kind !== 'label') {
      throw new Error('CALL requires function label');
    }

    return [{ mnemonic: 'CALL', operands: [ir.src1.name] }];
  }

  /**
   * Select move operation
   */
  private selectMove(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.dest || !ir.src1) {
      throw new Error('MOVE requires dest and src1');
    }

    const dest = this.getOperandString(ir.dest);
    const src = this.getOperandString(ir.src1);

    if (isConstant(ir.src1)) {
      const imm = this.getImmediateValue(ir.src1);
      if (this.isValidImmediate(imm)) {
        return [{ mnemonic: 'MOV', operands: [dest, `#${imm}`] }];
      } else {
        return this.loadLargeImmediate(dest, imm);
      }
    }

    return [{ mnemonic: 'MOV', operands: [dest, src] }];
  }

  /**
   * Select push operation
   */
  private selectPush(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.src1) {
      throw new Error('PUSH requires src1');
    }

    const src = this.getOperandString(ir.src1);
    return [{ mnemonic: 'PUSH', operands: [src] }];
  }

  /**
   * Select pop operation
   */
  private selectPop(ir: IRInstruction): KVRMInstruction[] {
    if (!ir.dest) {
      throw new Error('POP requires dest');
    }

    const dest = this.getOperandString(ir.dest);
    return [{ mnemonic: 'POP', operands: [dest] }];
  }

  /**
   * Get operand string representation
   */
  private getOperandString(value: IRValue): string {
    switch (value.kind) {
      case 'constant':
        return `#${value.value}`;
      case 'register':
        return value.name || `R${value.id}`;
      case 'variable':
      case 'temp': {
        const assignment = this.context.registerMap.get(value.id);
        if (assignment && typeof assignment === 'number') {
          return `R${assignment}`;
        } else if (assignment && 'stack' in assignment) {
          return `[SP, #${assignment.stack}]`;
        }
        return `T${value.id}`;
      }
      case 'label':
        return value.name;
      case 'global':
        return value.name;
      case 'argument':
        return `R${Math.min(value.index, 3)}`;
      case 'memory':
        return `[${this.getOperandString(value.base)}]`;
      default:
        throw new Error(`Unknown value kind: ${(value as any).kind}`);
    }
  }

  /**
   * Get immediate value from constant
   */
  private getImmediateValue(value: IRValue): number {
    if (!isConstant(value)) {
      throw new Error('Expected constant value');
    }
    if (typeof value.value === 'boolean') {
      return value.value ? 1 : 0;
    }
    if (typeof value.value === 'string') {
      throw new Error('Cannot convert string to immediate');
    }
    return value.value;
  }

  /**
   * Check if value fits in immediate field (12-bit signed)
   */
  private isValidImmediate(value: number): boolean {
    return value >= -2048 && value <= 2047;
  }

  /**
   * Load large immediate value (requires multiple instructions)
   */
  private loadLargeImmediate(dest: string, value: number): KVRMInstruction[] {
    const instructions: KVRMInstruction[] = [];

    // Load upper 16 bits
    const upper = (value >>> 16) & 0xFFFF;
    const lower = value & 0xFFFF;

    if (upper !== 0) {
      instructions.push({ mnemonic: 'MOVH', operands: [dest, `#${upper}`] });
      if (lower !== 0) {
        instructions.push({ mnemonic: 'OR', operands: [dest, dest, `#${lower}`] });
      }
    } else {
      instructions.push({ mnemonic: 'MOV', operands: [dest, `#${lower}`] });
    }

    return instructions;
  }

  /**
   * Get condition code for comparison
   */
  private getConditionCode(opcode: IROpcode): string {
    switch (opcode) {
      case 'EQ': return 'EQ';
      case 'NE': return 'NE';
      case 'LT': return 'LT';
      case 'LE': return 'LE';
      case 'GT': return 'GT';
      case 'GE': return 'GE';
      default: return '';
    }
  }

  /**
   * Get new label
   */
  public getNewLabel(prefix: string = 'L'): string {
    return `.${prefix}${this.context.labelCounter++}`;
  }
}
