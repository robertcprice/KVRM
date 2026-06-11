/**
 * Register Allocator for KVRM Code Generator
 * Implements linear scan register allocation with spilling
 */

import type { IRFunction, IRBasicBlock, IRInstruction, IRValue } from '../ir/types.js';
import { isRegister, isTemp, isVariable } from '../ir/types.js';

/**
 * KVRM CPU registers
 */
export enum KVRMRegister {
  R0 = 0, R1 = 1, R2 = 2, R3 = 3,
  R4 = 4, R5 = 5, R6 = 6, R7 = 7,
  R8 = 8, R9 = 9, R10 = 10, R11 = 11,
  R12 = 12,
  R13 = 13, // LR - Link Register
  R14 = 14, // SP - Stack Pointer
  R15 = 15, // PC - Program Counter
}

/**
 * Register names for assembly output
 */
export const REGISTER_NAMES: readonly string[] = [
  'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7',
  'R8', 'R9', 'R10', 'R11', 'R12', 'LR', 'SP', 'PC',
] as const;

/**
 * Registers available for allocation (excluding SP, LR, PC)
 */
const ALLOCATABLE_REGISTERS = [
  KVRMRegister.R0, KVRMRegister.R1, KVRMRegister.R2, KVRMRegister.R3,
  KVRMRegister.R4, KVRMRegister.R5, KVRMRegister.R6, KVRMRegister.R7,
  KVRMRegister.R8, KVRMRegister.R9, KVRMRegister.R10, KVRMRegister.R11,
  KVRMRegister.R12,
] as const;

/**
 * Argument passing registers (first 4 args in R0-R3)
 */
const ARG_REGISTERS = [
  KVRMRegister.R0,
  KVRMRegister.R1,
  KVRMRegister.R2,
  KVRMRegister.R3,
] as const;

/**
 * Caller-saved registers (need to be saved by caller across calls)
 */
const CALLER_SAVED = [
  KVRMRegister.R0, KVRMRegister.R1, KVRMRegister.R2, KVRMRegister.R3,
  KVRMRegister.R12,
] as const;

/**
 * Callee-saved registers (need to be saved by callee)
 */
const CALLEE_SAVED = [
  KVRMRegister.R4, KVRMRegister.R5, KVRMRegister.R6, KVRMRegister.R7,
  KVRMRegister.R8, KVRMRegister.R9, KVRMRegister.R10, KVRMRegister.R11,
] as const;

/**
 * Live interval for a value
 */
interface LiveInterval {
  valueId: number;
  valueName?: string;
  start: number;
  end: number;
  ranges: Array<{ start: number; end: number }>;
  spillCost: number;
}

/**
 * Register assignment result
 */
export interface RegisterAssignment {
  // Maps value ID to physical register or stack offset
  assignments: Map<number, KVRMRegister | { stack: number }>;
  // Spilled values requiring stack space
  spilledValues: Set<number>;
  // Stack frame size in bytes
  stackFrameSize: number;
  // Callee-saved registers used
  calleeSavedUsed: Set<KVRMRegister>;
}

/**
 * Register Allocator using Linear Scan algorithm
 */
export class RegisterAllocator {
  private liveIntervals: Map<number, LiveInterval> = new Map();
  private activeIntervals: LiveInterval[] = [];
  private assignments: Map<number, KVRMRegister | { stack: number }> = new Map();
  private spilledValues: Set<number> = new Set();
  private stackOffset = 0;
  private freeRegisters: Set<KVRMRegister>;
  private calleeSavedUsed: Set<KVRMRegister> = new Set();

  constructor() {
    this.freeRegisters = new Set(ALLOCATABLE_REGISTERS);
  }

  /**
   * Allocate registers for a function
   */
  public allocate(func: IRFunction): RegisterAssignment {
    // Reset state
    this.reset();

    // Step 1: Compute live intervals
    this.computeLiveIntervals(func);

    // Step 2: Reserve argument registers
    this.reserveArgumentRegisters(func);

    // Step 3: Perform linear scan allocation
    this.linearScanAllocation();

    // Step 4: Calculate final stack frame size
    const stackFrameSize = this.calculateStackFrameSize(func);

    return {
      assignments: this.assignments,
      spilledValues: this.spilledValues,
      stackFrameSize,
      calleeSavedUsed: this.calleeSavedUsed,
    };
  }

  private reset(): void {
    this.liveIntervals.clear();
    this.activeIntervals = [];
    this.assignments.clear();
    this.spilledValues.clear();
    this.stackOffset = 0;
    this.freeRegisters = new Set(ALLOCATABLE_REGISTERS);
    this.calleeSavedUsed.clear();
  }

  /**
   * Compute live intervals for all values
   */
  private computeLiveIntervals(func: IRFunction): void {
    const intervals = new Map<number, LiveInterval>();

    // Number all instructions sequentially
    let position = 0;
    const instructionPositions = new Map<IRInstruction, number>();

    for (const block of func.blocks) {
      for (const instr of block.instructions) {
        instructionPositions.set(instr, position++);
      }
    }

    // Analyze each instruction
    position = 0;
    for (const block of func.blocks) {
      for (const instr of block.instructions) {
        const pos = position++;

        // Process source operands (use)
        const sources = this.getSourceOperands(instr);
        for (const src of sources) {
          const valueId = this.getValueId(src);
          if (valueId !== null) {
            if (!intervals.has(valueId)) {
              intervals.set(valueId, {
                valueId,
                valueName: this.getValueName(src),
                start: pos,
                end: pos,
                ranges: [{ start: pos, end: pos }],
                spillCost: this.computeSpillCost(instr, src),
              });
            } else {
              const interval = intervals.get(valueId)!;
              interval.end = pos;
              interval.spillCost += this.computeSpillCost(instr, src);
            }
          }
        }

        // Process destination operand (def)
        if (instr.dest) {
          const valueId = this.getValueId(instr.dest);
          if (valueId !== null) {
            if (!intervals.has(valueId)) {
              intervals.set(valueId, {
                valueId,
                valueName: this.getValueName(instr.dest),
                start: pos,
                end: pos,
                ranges: [{ start: pos, end: pos }],
                spillCost: this.computeSpillCost(instr, instr.dest),
              });
            } else {
              const interval = intervals.get(valueId)!;
              interval.start = Math.min(interval.start, pos);
              interval.end = pos;
              interval.spillCost += this.computeSpillCost(instr, instr.dest);
            }
          }
        }
      }
    }

    this.liveIntervals = intervals;
  }

  /**
   * Reserve registers for function arguments
   */
  private reserveArgumentRegisters(func: IRFunction): void {
    for (let i = 0; i < Math.min(func.parameters.length, ARG_REGISTERS.length); i++) {
      const argReg = ARG_REGISTERS[i];
      const param = func.parameters[i];

      // Find the value ID for this parameter
      const paramVar = func.localVars.get(param.name);
      if (paramVar) {
        this.assignments.set(paramVar.id, argReg);
        this.freeRegisters.delete(argReg);
      }
    }
  }

  /**
   * Linear scan register allocation
   */
  private linearScanAllocation(): void {
    // Sort intervals by start position
    const sortedIntervals = Array.from(this.liveIntervals.values())
      .filter(interval => !this.assignments.has(interval.valueId))
      .sort((a, b) => a.start - b.start);

    for (const interval of sortedIntervals) {
      this.expireOldIntervals(interval);

      if (this.freeRegisters.size === 0) {
        this.spillAtInterval(interval);
      } else {
        // Allocate a register
        const reg = this.selectRegister(interval);
        this.assignments.set(interval.valueId, reg);
        this.freeRegisters.delete(reg);
        this.activeIntervals.push(interval);

        // Track callee-saved register usage
        if (CALLEE_SAVED.includes(reg)) {
          this.calleeSavedUsed.add(reg);
        }
      }
    }
  }

  /**
   * Expire intervals that are no longer active
   */
  private expireOldIntervals(interval: LiveInterval): void {
    this.activeIntervals.sort((a, b) => a.end - b.end);

    for (let i = 0; i < this.activeIntervals.length; ) {
      const active = this.activeIntervals[i];

      if (active.end >= interval.start) {
        break;
      }

      // Remove from active and free the register
      this.activeIntervals.splice(i, 1);
      const assignment = this.assignments.get(active.valueId);

      if (assignment && typeof assignment === 'number') {
        this.freeRegisters.add(assignment);
      }
    }
  }

  /**
   * Spill an interval to memory
   */
  private spillAtInterval(interval: LiveInterval): void {
    // Sort active intervals by end position (latest first)
    this.activeIntervals.sort((a, b) => b.end - a.end);

    const spillCandidate = this.activeIntervals[this.activeIntervals.length - 1];

    if (spillCandidate.end > interval.end) {
      // Spill the candidate and allocate its register to current interval
      const reg = this.assignments.get(spillCandidate.valueId) as KVRMRegister;
      this.assignments.set(interval.valueId, reg);

      // Spill the candidate to stack
      this.spillValue(spillCandidate.valueId);
      this.activeIntervals.pop();
      this.activeIntervals.push(interval);
    } else {
      // Spill current interval
      this.spillValue(interval.valueId);
    }
  }

  /**
   * Spill a value to the stack
   */
  private spillValue(valueId: number): void {
    this.spilledValues.add(valueId);
    const stackLoc = { stack: this.stackOffset };
    this.assignments.set(valueId, stackLoc);
    this.stackOffset += 4; // 4 bytes per spilled value
  }

  /**
   * Select best register for interval
   */
  private selectRegister(interval: LiveInterval): KVRMRegister {
    // Prefer callee-saved for long-lived values
    const isLongLived = (interval.end - interval.start) > 20;

    if (isLongLived) {
      for (const reg of CALLEE_SAVED) {
        if (this.freeRegisters.has(reg)) {
          return reg;
        }
      }
    }

    // Otherwise use any available register
    return this.freeRegisters.values().next().value!;
  }

  /**
   * Calculate final stack frame size
   */
  private calculateStackFrameSize(func: IRFunction): number {
    // Spilled values + local variables + saved registers
    const spilledSize = this.stackOffset;
    const localVarsSize = func.localVars.size * 4;
    const savedRegsSize = this.calleeSavedUsed.size * 4;

    // Align to 16 bytes for ABI compliance
    const totalSize = spilledSize + localVarsSize + savedRegsSize;
    return Math.ceil(totalSize / 16) * 16;
  }

  /**
   * Get source operands from instruction
   */
  private getSourceOperands(instr: IRInstruction): IRValue[] {
    const sources: IRValue[] = [];

    if (instr.src1) sources.push(instr.src1);
    if (instr.src2) sources.push(instr.src2);
    if (instr.operands) sources.push(...instr.operands);

    return sources;
  }

  /**
   * Extract value ID from IR value
   */
  private getValueId(value: IRValue): number | null {
    if (isTemp(value)) return value.id;
    if (isVariable(value)) return value.id;
    if (isRegister(value)) return value.id;
    return null;
  }

  /**
   * Extract value name from IR value
   */
  private getValueName(value: IRValue): string | undefined {
    if (isVariable(value)) return value.name;
    if (isRegister(value)) return value.name;
    return undefined;
  }

  /**
   * Compute spill cost (higher = more expensive to spill)
   */
  private computeSpillCost(instr: IRInstruction, value: IRValue): number {
    // Higher cost for values in loops, lower for infrequent use
    let cost = 1;

    // Increase cost for function calls (expensive to reload)
    if (instr.opcode === 'CALL') cost += 5;

    // Increase cost for memory operations
    if (instr.opcode === 'LOAD' || instr.opcode === 'STORE') cost += 2;

    return cost;
  }

  /**
   * Get register name for display
   */
  public static getRegisterName(reg: KVRMRegister): string {
    return REGISTER_NAMES[reg];
  }

  /**
   * Check if register is callee-saved
   */
  public static isCalleeSaved(reg: KVRMRegister): boolean {
    return CALLEE_SAVED.includes(reg);
  }

  /**
   * Check if register is caller-saved
   */
  public static isCallerSaved(reg: KVRMRegister): boolean {
    return CALLER_SAVED.includes(reg);
  }
}
