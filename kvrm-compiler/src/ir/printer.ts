/**
 * IR Pretty Printer for KVRM Compiler
 *
 * Converts IR to human-readable text format for debugging and analysis.
 * Displays SSA values, types, control flow, and instruction details.
 */

import {
  IRProgram,
  IRFunction,
  IRBlock,
  IRInstr,
  IRValue,
  IRType,
  IRStructDef,
  IRGlobalVar,
} from './ir-nodes.js';

/**
 * Options for IR printing
 */
export interface PrintOptions {
  showTypes: boolean;
  showBlockPredecessors: boolean;
  showDebugInfo: boolean;
  indent: string;
}

const DEFAULT_OPTIONS: PrintOptions = {
  showTypes: true,
  showBlockPredecessors: true,
  showDebugInfo: false,
  indent: '  ',
};

/**
 * IR Printer class
 */
export class IRPrinter {
  private options: PrintOptions;

  constructor(options: Partial<PrintOptions> = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
  }

  /**
   * Print entire IR program
   */
  print(program: IRProgram): string {
    const parts: string[] = [];

    // Print global variables
    if (program.globalVariables.size > 0) {
      parts.push('; Global Variables');
      for (const [name, globalVar] of program.globalVariables) {
        parts.push(this.printGlobalVar(name, globalVar));
      }
      parts.push('');
    }

    // Print struct definitions
    if (program.structs.size > 0) {
      parts.push('; Struct Definitions');
      for (const [name, struct] of program.structs) {
        parts.push(this.printStruct(name, struct));
      }
      parts.push('');
    }

    // Print functions
    for (const func of program.functions) {
      parts.push(this.printFunction(func));
      parts.push('');
    }

    return parts.join('\n');
  }

  /**
   * Print a global variable
   */
  private printGlobalVar(name: string, globalVar: IRGlobalVar): string {
    const constStr = globalVar.isConstant ? 'const' : 'var';
    const typeStr = this.printType(globalVar.type);
    const initStr = globalVar.initialValue !== undefined ? ` = ${globalVar.initialValue}` : '';
    return `@${name}: ${constStr} ${typeStr}${initStr}`;
  }

  /**
   * Print a struct definition
   */
  private printStruct(name: string, struct: IRStructDef): string {
    const parts: string[] = [];
    parts.push(`%${name} = struct {`);
    for (const field of struct.fields) {
      const typeStr = this.printType(field.type);
      parts.push(`${this.options.indent}${field.name}: ${typeStr} (offset ${field.offset})`);
    }
    parts.push(`} ; size=${struct.size}, align=${struct.alignment}`);
    return parts.join('\n');
  }

  /**
   * Print a function
   */
  printFunction(func: IRFunction): string {
    const parts: string[] = [];

    // Function signature
    const params = func.parameters.map((p) => this.printValueWithType(p)).join(', ');
    const returnType = this.printType(func.returnType);
    parts.push(`fn @${func.name}(${params}) -> ${returnType} {`);

    // Function body (blocks)
    for (const block of func.blocks) {
      parts.push(this.printBlock(block));
    }

    parts.push('}');

    return parts.join('\n');
  }

  /**
   * Print a basic block
   */
  private printBlock(block: IRBlock): string {
    const parts: string[] = [];
    const indent = this.options.indent;

    // Block label
    let labelLine = `${block.label}:`;

    // Add predecessors if enabled
    if (this.options.showBlockPredecessors && block.predecessors.length > 0) {
      labelLine += ` ; preds: ${block.predecessors.join(', ')}`;
    }

    parts.push(labelLine);

    // Instructions
    for (const instr of block.instructions) {
      const instrStr = this.printInstruction(instr);
      parts.push(indent + instrStr);
    }

    return parts.join('\n');
  }

  /**
   * Print an instruction
   */
  private printInstruction(instr: IRInstr): string {
    let str = '';

    switch (instr.kind) {
      case 'const': {
        const resultStr = this.printValueWithType(instr.result);
        const valueStr = typeof instr.value === 'string' ? `"${instr.value}"` : instr.value;
        str = `${resultStr} = const ${valueStr}`;
        break;
      }

      case 'binop': {
        const resultStr = this.printValueWithType(instr.result);
        const leftStr = this.printValue(instr.left);
        const rightStr = this.printValue(instr.right);
        str = `${resultStr} = ${instr.op} ${leftStr}, ${rightStr}`;
        break;
      }

      case 'unaryop': {
        const resultStr = this.printValueWithType(instr.result);
        const operandStr = this.printValue(instr.operand);
        str = `${resultStr} = ${instr.op} ${operandStr}`;
        break;
      }

      case 'load': {
        const resultStr = this.printValueWithType(instr.result);
        const addrStr = this.printValue(instr.address);
        str = `${resultStr} = load ${addrStr}`;
        break;
      }

      case 'store': {
        const addrStr = this.printValue(instr.address);
        const valueStr = this.printValue(instr.value);
        str = `store ${valueStr}, ${addrStr}`;
        break;
      }

      case 'alloc': {
        const resultStr = this.printValueWithType(instr.result);
        const typeStr = this.printType(instr.allocatedType);
        str = `${resultStr} = alloc ${typeStr}`;
        break;
      }

      case 'call': {
        const resultStr = instr.result ? this.printValueWithType(instr.result) + ' = ' : '';
        const argsStr = instr.arguments.map((a) => this.printValue(a)).join(', ');
        str = `${resultStr}call @${instr.functionName}(${argsStr})`;
        break;
      }

      case 'return': {
        const valueStr = instr.value ? ' ' + this.printValue(instr.value) : '';
        str = `return${valueStr}`;
        break;
      }

      case 'jump': {
        str = `jump ${instr.target}`;
        break;
      }

      case 'condjump': {
        const condStr = this.printValue(instr.condition);
        str = `condjump ${condStr}, ${instr.trueTarget}, ${instr.falseTarget}`;
        break;
      }

      case 'phi': {
        const resultStr = this.printValueWithType(instr.result);
        const incomingStr = instr.incomingValues
          .map((inc) => `[${this.printValue(inc.value)}, ${inc.block}]`)
          .join(', ');
        str = `${resultStr} = phi ${incomingStr}`;
        break;
      }

      case 'getelementptr': {
        const resultStr = this.printValueWithType(instr.result);
        const basePtrStr = this.printValue(instr.basePtr);
        const indicesStr = instr.indices.map((i) => this.printValue(i)).join(', ');
        str = `${resultStr} = getelementptr ${basePtrStr}, ${indicesStr}`;
        break;
      }

      default:
        str = `<unknown instruction: ${(instr as IRInstr).kind}>`;
    }

    // Add debug info if enabled
    if (this.options.showDebugInfo && instr.debugInfo) {
      str += ` ; line ${instr.debugInfo.line}:${instr.debugInfo.column}`;
    }

    return str;
  }

  /**
   * Print SSA value with type
   */
  private printValueWithType(value: IRValue): string {
    const name = value.name ? `%${value.name}` : `%${value.id}`;
    if (this.options.showTypes) {
      return `${name}: ${this.printType(value.type)}`;
    }
    return name;
  }

  /**
   * Print SSA value without type
   */
  private printValue(value: IRValue): string {
    return value.name ? `%${value.name}` : `%${value.id}`;
  }

  /**
   * Print IR type
   */
  private printType(type: IRType): string {
    switch (type.kind) {
      case 'i32':
      case 'i64':
      case 'f32':
      case 'f64':
      case 'bool':
      case 'void':
        return type.kind;
      case 'ptr':
        return type.pointeeType ? `*${this.printType(type.pointeeType)}` : '*void';
      case 'struct':
        return type.structName ? `%${type.structName}` : 'struct';
      default:
        return '<unknown type>';
    }
  }
}

/**
 * Convenience function to print IR program with default options
 */
export function printIR(program: IRProgram, options?: Partial<PrintOptions>): string {
  const printer = new IRPrinter(options);
  return printer.print(program);
}

/**
 * Convenience function to print a single function
 */
export function printFunction(func: IRFunction, options?: Partial<PrintOptions>): string {
  const printer = new IRPrinter(options);
  return printer.printFunction(func);
}

/**
 * Print IR to console with syntax highlighting (if terminal supports it)
 */
export function printIRToConsole(program: IRProgram, options?: Partial<PrintOptions>): void {
  const output = printIR(program, options);
  console.log(output);
}

/**
 * Generate a control flow graph in DOT format for visualization
 */
export function generateCFGDot(func: IRFunction): string {
  const lines: string[] = [];
  lines.push(`digraph "${func.name}" {`);
  lines.push('  node [shape=box];');

  // Add nodes for each block
  for (const block of func.blocks) {
    const label = `${block.label}\\n${block.instructions.length} instructions`;
    lines.push(`  ${block.label} [label="${label}"];`);
  }

  // Add edges based on control flow
  for (const block of func.blocks) {
    const lastInstr = block.instructions[block.instructions.length - 1];
    if (lastInstr?.kind === 'jump') {
      lines.push(`  ${block.label} -> ${lastInstr.target};`);
    } else if (lastInstr?.kind === 'condjump') {
      lines.push(`  ${block.label} -> ${lastInstr.trueTarget} [label="true"];`);
      lines.push(`  ${block.label} -> ${lastInstr.falseTarget} [label="false"];`);
    }
  }

  lines.push('}');
  return lines.join('\n');
}

/**
 * Generate statistics about the IR program
 */
export interface IRStats {
  totalFunctions: number;
  totalBlocks: number;
  totalInstructions: number;
  instructionCounts: Map<string, number>;
  averageBlockSize: number;
  maxBlockSize: number;
}

export function generateStats(program: IRProgram): IRStats {
  let totalBlocks = 0;
  let totalInstructions = 0;
  let maxBlockSize = 0;
  const instructionCounts = new Map<string, number>();

  for (const func of program.functions) {
    totalBlocks += func.blocks.length;

    for (const block of func.blocks) {
      const blockSize = block.instructions.length;
      totalInstructions += blockSize;
      maxBlockSize = Math.max(maxBlockSize, blockSize);

      for (const instr of block.instructions) {
        instructionCounts.set(instr.kind, (instructionCounts.get(instr.kind) || 0) + 1);
      }
    }
  }

  return {
    totalFunctions: program.functions.length,
    totalBlocks,
    totalInstructions,
    instructionCounts,
    averageBlockSize: totalBlocks > 0 ? totalInstructions / totalBlocks : 0,
    maxBlockSize,
  };
}

/**
 * Print IR statistics in a formatted way
 */
export function printStats(stats: IRStats): string {
  const lines: string[] = [];
  lines.push('=== IR Statistics ===');
  lines.push(`Functions: ${stats.totalFunctions}`);
  lines.push(`Basic Blocks: ${stats.totalBlocks}`);
  lines.push(`Instructions: ${stats.totalInstructions}`);
  lines.push(`Average Block Size: ${stats.averageBlockSize.toFixed(2)}`);
  lines.push(`Max Block Size: ${stats.maxBlockSize}`);
  lines.push('');
  lines.push('Instruction Counts:');

  const sortedCounts = Array.from(stats.instructionCounts.entries()).sort((a, b) => b[1] - a[1]);

  for (const [kind, count] of sortedCounts) {
    const percentage = ((count / stats.totalInstructions) * 100).toFixed(1);
    lines.push(`  ${kind}: ${count} (${percentage}%)`);
  }

  return lines.join('\n');
}
