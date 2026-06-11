/**
 * IR Builder - Utility for constructing IR programs
 * Provides a fluent API for building IR structures
 */

import type {
  IRProgram,
  IRFunction,
  IRBasicBlock,
  IRInstruction,
  IRValue,
} from './types.js';
import { IROpcode, IRValueFactory, createInstruction } from './types.js';

/**
 * IR Program Builder
 */
export class IRProgramBuilder {
  private functions: IRFunction[] = [];
  private globals = new Map<string, { type?: string; initialValue?: IRValue }>();
  private constants = new Map<string, { type: string; value: any }>();
  private stringLiterals = new Map<string, string>();
  private stringCounter = 0;

  /**
   * Add a function to the program
   */
  public addFunction(func: IRFunction): this {
    this.functions.push(func);
    return this;
  }

  /**
   * Add a global variable
   */
  public addGlobal(name: string, type?: string, initialValue?: IRValue): this {
    this.globals.set(name, { type, initialValue });
    return this;
  }

  /**
   * Add a constant
   */
  public addConstant(name: string, type: string, value: any): this {
    this.constants.set(name, { type, value });
    return this;
  }

  /**
   * Add a string literal
   */
  public addString(value: string): string {
    const label = `.str${this.stringCounter++}`;
    this.stringLiterals.set(label, value);
    return label;
  }

  /**
   * Build the IR program
   */
  public build(): IRProgram {
    return {
      functions: this.functions,
      globals: this.globals,
      constants: this.constants,
      stringLiterals: this.stringLiterals,
    };
  }
}

/**
 * IR Function Builder
 */
export class IRFunctionBuilder {
  private name: string;
  private parameters: Array<{ name: string; type?: string }> = [];
  private returnType?: string;
  private blocks: IRBasicBlock[] = [];
  private localVars = new Map<string, { id: number; type?: string }>();
  private tempCount = 0;
  private stackSize = 0;
  private isEntryPoint = false;
  private nextBlockId = 0;

  constructor(name: string) {
    this.name = name;
  }

  /**
   * Add a parameter
   */
  public addParameter(name: string, type?: string): this {
    this.parameters.push({ name, type });
    return this;
  }

  /**
   * Set return type
   */
  public setReturnType(type: string): this {
    this.returnType = type;
    return this;
  }

  /**
   * Mark as entry point
   */
  public setEntryPoint(value: boolean = true): this {
    this.isEntryPoint = value;
    return this;
  }

  /**
   * Add a local variable
   */
  public addLocal(name: string, type?: string): number {
    const id = this.localVars.size;
    this.localVars.set(name, { id, type });
    return id;
  }

  /**
   * Allocate a new temporary
   */
  public newTemp(): number {
    return this.tempCount++;
  }

  /**
   * Add a basic block
   */
  public addBlock(block: IRBasicBlock): this {
    this.blocks.push(block);
    return this;
  }

  /**
   * Create a new basic block
   */
  public createBlock(label?: string): IRBasicBlockBuilder {
    const blockId = this.nextBlockId++;
    const blockLabel = label || `bb${blockId}`;
    return new IRBasicBlockBuilder(blockId, blockLabel);
  }

  /**
   * Set stack size
   */
  public setStackSize(size: number): this {
    this.stackSize = size;
    return this;
  }

  /**
   * Build the IR function
   */
  public build(): IRFunction {
    return {
      name: this.name,
      parameters: this.parameters,
      returnType: this.returnType,
      blocks: this.blocks,
      localVars: this.localVars,
      tempCount: this.tempCount,
      stackSize: this.stackSize,
      isEntryPoint: this.isEntryPoint,
    };
  }
}

/**
 * IR Basic Block Builder
 */
export class IRBasicBlockBuilder {
  private id: number;
  private label: string;
  private instructions: IRInstruction[] = [];
  private predecessors: number[] = [];
  private successors: number[] = [];

  constructor(id: number, label: string) {
    this.id = id;
    this.label = label;
  }

  /**
   * Add an instruction
   */
  public addInstruction(instr: IRInstruction): this {
    this.instructions.push(instr);
    return this;
  }

  /**
   * Add a binary operation
   */
  public addBinaryOp(
    opcode: IROpcode,
    dest: IRValue,
    src1: IRValue,
    src2: IRValue,
    comment?: string
  ): this {
    return this.addInstruction(
      createInstruction(opcode, { dest, src1, src2, comment })
    );
  }

  /**
   * Add a move instruction
   */
  public addMove(dest: IRValue, src: IRValue, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.Move, { dest, src1: src, comment })
    );
  }

  /**
   * Add a load instruction
   */
  public addLoad(dest: IRValue, addr: IRValue, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.Load, { dest, src1: addr, comment })
    );
  }

  /**
   * Add a store instruction
   */
  public addStore(addr: IRValue, value: IRValue, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.Store, { dest: addr, src1: value, comment })
    );
  }

  /**
   * Add a call instruction
   */
  public addCall(funcLabel: string, dest?: IRValue, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.Call, {
        src1: IRValueFactory.label(funcLabel),
        dest,
        comment,
      })
    );
  }

  /**
   * Add a return instruction
   */
  public addReturn(value?: IRValue, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.Return, { src1: value, comment })
    );
  }

  /**
   * Add a jump instruction
   */
  public addJump(targetLabel: string, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.Jump, {
        src1: IRValueFactory.label(targetLabel),
        comment,
      })
    );
  }

  /**
   * Add a conditional jump
   */
  public addJumpIf(condition: IRValue, targetLabel: string, comment?: string): this {
    return this.addInstruction(
      createInstruction(IROpcode.JumpIf, {
        src1: condition,
        src2: IRValueFactory.label(targetLabel),
        comment,
      })
    );
  }

  /**
   * Add predecessors
   */
  public addPredecessor(...ids: number[]): this {
    this.predecessors.push(...ids);
    return this;
  }

  /**
   * Add successors
   */
  public addSuccessor(...ids: number[]): this {
    this.successors.push(...ids);
    return this;
  }

  /**
   * Build the basic block
   */
  public build(): IRBasicBlock {
    return {
      id: this.id,
      label: this.label,
      instructions: this.instructions,
      predecessors: this.predecessors,
      successors: this.successors,
    };
  }
}

/**
 * Helper function to create a simple IR program
 */
export function createProgram(): IRProgramBuilder {
  return new IRProgramBuilder();
}

/**
 * Helper function to create a function
 */
export function createFunction(name: string): IRFunctionBuilder {
  return new IRFunctionBuilder(name);
}
