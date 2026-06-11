/**
 * Code Generator for KVRM Compiler
 * Orchestrates register allocation, instruction selection, and assembly emission
 */

import type { IRProgram, IRFunction, IRInstruction, IRBasicBlock } from '../ir/types.js';
import { RegisterAllocator, type RegisterAssignment } from './register-allocator.js';
import { InstructionSelector, type KVRMInstruction } from './instruction-selector.js';
import { AssemblyEmitter, AsmSection } from './asm-emitter.js';

/**
 * Code generation options
 */
export interface CodeGenOptions {
  optimize: boolean;
  debugInfo: boolean;
  commentLevel: 'none' | 'minimal' | 'detailed';
  formatOptions?: {
    indent?: string;
    commentColumn?: number;
    uppercase?: boolean;
  };
}

/**
 * Code generation statistics
 */
export interface CodeGenStats {
  functionsGenerated: number;
  instructionsGenerated: number;
  registersSpilled: number;
  maxStackFrameSize: number;
}

/**
 * Code Generator - Main code generation orchestrator
 */
export class CodeGenerator {
  private options: CodeGenOptions;
  private stats: CodeGenStats;
  private emitter: AssemblyEmitter;

  constructor(options: Partial<CodeGenOptions> = {}) {
    this.options = {
      optimize: true,
      debugInfo: false,
      commentLevel: 'minimal',
      ...options,
    };

    this.emitter = new AssemblyEmitter(options.formatOptions);

    this.stats = {
      functionsGenerated: 0,
      instructionsGenerated: 0,
      registersSpilled: 0,
      maxStackFrameSize: 0,
    };
  }

  /**
   * Generate assembly code from IR program
   */
  public generate(program: IRProgram): string {
    // Reset statistics
    this.resetStats();

    // Emit program preamble
    const entryPoint = this.findEntryPoint(program);
    this.emitter.emitPreamble(entryPoint);

    // Emit data section (globals, constants, strings)
    this.emitter.emitDataSection(program);

    // Emit text section (code)
    this.emitter.emitSection(AsmSection.Text);

    // Generate code for each function
    for (const func of program.functions) {
      this.generateFunction(func);
      this.emitter.emitBlank();
    }

    // Return formatted assembly
    return this.emitter.toString();
  }

  /**
   * Generate code for a function
   */
  public generateFunction(func: IRFunction): void {
    if (this.shouldEmitComment('minimal')) {
      this.emitter.emitComment('========================================');
      this.emitter.emitComment(`Function: ${func.name}`);
      this.emitter.emitComment(`Parameters: ${func.parameters.length}`);
      this.emitter.emitComment('========================================');
    }

    // Step 1: Register allocation
    const allocator = new RegisterAllocator();
    const allocation = allocator.allocate(func);

    // Update statistics
    this.stats.registersSpilled += allocation.spilledValues.size;
    this.stats.maxStackFrameSize = Math.max(
      this.stats.maxStackFrameSize,
      allocation.stackFrameSize
    );

    if (this.shouldEmitComment('detailed')) {
      this.emitter.emitComment(`Stack frame size: ${allocation.stackFrameSize} bytes`);
      this.emitter.emitComment(`Spilled values: ${allocation.spilledValues.size}`);
      this.emitter.emitComment(`Callee-saved registers: ${allocation.calleeSavedUsed.size}`);
    }

    // Step 2: Emit function prologue
    const isGlobal = func.isEntryPoint || func.name === 'main';
    this.emitter.emitFunctionPrologue(
      func.name,
      allocation.stackFrameSize,
      allocation.calleeSavedUsed,
      isGlobal
    );

    // Step 3: Generate instructions for each basic block
    const selector = new InstructionSelector(allocation.assignments);

    for (const block of func.blocks) {
      this.generateBasicBlock(block, selector, allocation);
    }

    // Step 4: Emit function epilogue
    this.emitter.emitFunctionEpilogue(
      allocation.stackFrameSize,
      allocation.calleeSavedUsed
    );

    this.stats.functionsGenerated++;
  }

  /**
   * Generate code for a basic block
   */
  private generateBasicBlock(
    block: IRBasicBlock,
    selector: InstructionSelector,
    allocation: RegisterAssignment
  ): void {
    // Emit block label
    if (block.label && block.id > 0) { // Skip entry block label
      this.emitter.emitLabel(block.label);
    }

    if (this.shouldEmitComment('detailed')) {
      this.emitter.emitComment(`Block ${block.id}: ${block.label}`);
      this.emitter.emitComment(
        `Predecessors: [${block.predecessors.join(', ')}]`
      );
      this.emitter.emitComment(
        `Successors: [${block.successors.join(', ')}]`
      );
    }

    // Generate instructions
    for (const ir of block.instructions) {
      this.generateInstruction(ir, selector);
    }
  }

  /**
   * Generate assembly instructions from IR instruction
   */
  private generateInstruction(
    ir: IRInstruction,
    selector: InstructionSelector
  ): void {
    try {
      // Add debug info as comment if enabled
      if (this.options.debugInfo && ir.debugInfo && this.shouldEmitComment('detailed')) {
        this.emitter.emitComment(
          `Line ${ir.debugInfo.line}:${ir.debugInfo.column}`
        );
      }

      // Select and emit assembly instructions
      const instructions = selector.select(ir);

      for (const instr of instructions) {
        this.emitter.emitInstruction(instr);
        this.stats.instructionsGenerated++;
      }

      // Add IR instruction as comment if detailed
      if (this.shouldEmitComment('detailed') && ir.comment) {
        // Comment was already added to first instruction by selector
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.emitter.emitComment(`ERROR: ${errorMsg}`);
      throw new Error(`Code generation failed for instruction: ${errorMsg}`);
    }
  }

  /**
   * Find entry point function
   */
  private findEntryPoint(program: IRProgram): string {
    // Look for function marked as entry point
    for (const func of program.functions) {
      if (func.isEntryPoint) {
        return func.name;
      }
    }

    // Look for 'main' function
    for (const func of program.functions) {
      if (func.name === 'main') {
        return 'main';
      }
    }

    // Default to first function
    return program.functions[0]?.name || 'main';
  }

  /**
   * Check if comment should be emitted at current level
   */
  private shouldEmitComment(level: 'minimal' | 'detailed'): boolean {
    if (this.options.commentLevel === 'none') {
      return false;
    }
    if (this.options.commentLevel === 'minimal') {
      return level === 'minimal';
    }
    return true; // detailed
  }

  /**
   * Reset statistics
   */
  private resetStats(): void {
    this.stats = {
      functionsGenerated: 0,
      instructionsGenerated: 0,
      registersSpilled: 0,
      maxStackFrameSize: 0,
    };
  }

  /**
   * Get generation statistics
   */
  public getStats(): Readonly<CodeGenStats> {
    return { ...this.stats };
  }

  /**
   * Get the assembly emitter
   */
  public getEmitter(): AssemblyEmitter {
    return this.emitter;
  }
}

/**
 * Convenience function to generate assembly from IR
 */
export function generateAssembly(
  program: IRProgram,
  options?: Partial<CodeGenOptions>
): string {
  const generator = new CodeGenerator(options);
  return generator.generate(program);
}

/**
 * Generate assembly with statistics
 */
export function generateWithStats(
  program: IRProgram,
  options?: Partial<CodeGenOptions>
): { assembly: string; stats: CodeGenStats } {
  const generator = new CodeGenerator(options);
  const assembly = generator.generate(program);
  const stats = generator.getStats();

  return { assembly, stats };
}
