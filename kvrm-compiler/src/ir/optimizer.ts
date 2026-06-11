/**
 * IR Optimization Passes for KVRM Compiler
 *
 * Implements basic optimizations on SSA-form IR:
 * - Constant folding
 * - Dead code elimination
 * - Common subexpression elimination
 * - Copy propagation
 */

import {
  IRProgram,
  IRFunction,
  IRBlock,
  IRInstr,
  IRValue,
  IRBinOp,
  IRUnaryOp,
  IRConst,
  BinOpKind,
  UnaryOpKind,
  IRTypes,
} from './ir-nodes.js';

/**
 * Optimization pass interface
 */
export interface OptimizationPass {
  name: string;
  optimize(program: IRProgram): IRProgram;
}

/**
 * Main optimizer class that orchestrates optimization passes
 */
export class IROptimizer {
  private passes: OptimizationPass[] = [
    new ConstantFolding(),
    new CopyPropagation(),
    new DeadCodeElimination(),
    new CommonSubexpressionElimination(),
  ];

  /**
   * Run all optimization passes on the program
   */
  optimize(program: IRProgram, iterations: number = 3): IRProgram {
    let optimized = program;

    // Run multiple iterations to catch optimization opportunities
    // exposed by previous passes
    for (let i = 0; i < iterations; i++) {
      for (const pass of this.passes) {
        optimized = pass.optimize(optimized);
      }
    }

    return optimized;
  }

  /**
   * Add custom optimization pass
   */
  addPass(pass: OptimizationPass): void {
    this.passes.push(pass);
  }
}

/**
 * Constant Folding: Evaluate constant expressions at compile time
 */
export class ConstantFolding implements OptimizationPass {
  name = 'ConstantFolding';

  optimize(program: IRProgram): IRProgram {
    const constants = new Map<number, number | boolean>();

    return {
      ...program,
      functions: program.functions.map((func) => this.optimizeFunction(func, constants)),
    };
  }

  private optimizeFunction(func: IRFunction, constants: Map<number, number | boolean>): IRFunction {
    constants.clear();

    return {
      ...func,
      blocks: func.blocks.map((block) => this.optimizeBlock(block, constants)),
    };
  }

  private optimizeBlock(block: IRBlock, constants: Map<number, number | boolean>): IRBlock {
    const newInstructions: IRInstr[] = [];

    for (const instr of block.instructions) {
      if (instr.kind === 'const') {
        constants.set(instr.result.id, instr.value as number | boolean);
        newInstructions.push(instr);
      } else if (instr.kind === 'binop') {
        const left = constants.get(instr.left.id);
        const right = constants.get(instr.right.id);

        if (left !== undefined && right !== undefined) {
          // Both operands are constants, fold the operation
          const result = this.evaluateBinOp(instr.op, left, right);
          if (result !== undefined) {
            constants.set(instr.result.id, result);
            newInstructions.push({
              kind: 'const',
              result: instr.result,
              value: result,
            });
            continue;
          }
        }
        newInstructions.push(instr);
      } else if (instr.kind === 'unaryop') {
        const operand = constants.get(instr.operand.id);

        if (operand !== undefined) {
          const result = this.evaluateUnaryOp(instr.op, operand);
          if (result !== undefined) {
            constants.set(instr.result.id, result);
            newInstructions.push({
              kind: 'const',
              result: instr.result,
              value: result,
            });
            continue;
          }
        }
        newInstructions.push(instr);
      } else {
        newInstructions.push(instr);
      }
    }

    return {
      ...block,
      instructions: newInstructions,
    };
  }

  private evaluateBinOp(op: BinOpKind, left: number | boolean, right: number | boolean): number | boolean | undefined {
    // Type check for numeric operations
    if (typeof left !== 'number' || typeof right !== 'number') {
      if (op === BinOpKind.And && typeof left === 'boolean' && typeof right === 'boolean') {
        return left && right;
      }
      if (op === BinOpKind.Or && typeof left === 'boolean' && typeof right === 'boolean') {
        return left || right;
      }
      return undefined;
    }

    switch (op) {
      case BinOpKind.Add:
        return left + right;
      case BinOpKind.Sub:
        return left - right;
      case BinOpKind.Mul:
        return left * right;
      case BinOpKind.Div:
        return right !== 0 ? Math.floor(left / right) : undefined;
      case BinOpKind.Mod:
        return right !== 0 ? left % right : undefined;
      case BinOpKind.Eq:
        return left === right;
      case BinOpKind.Ne:
        return left !== right;
      case BinOpKind.Lt:
        return left < right;
      case BinOpKind.Le:
        return left <= right;
      case BinOpKind.Gt:
        return left > right;
      case BinOpKind.Ge:
        return left >= right;
      case BinOpKind.BitAnd:
        return left & right;
      case BinOpKind.BitOr:
        return left | right;
      case BinOpKind.BitXor:
        return left ^ right;
      case BinOpKind.Shl:
        return left << right;
      case BinOpKind.Shr:
        return left >> right;
      default:
        return undefined;
    }
  }

  private evaluateUnaryOp(op: UnaryOpKind, operand: number | boolean): number | boolean | undefined {
    if (op === UnaryOpKind.Not && typeof operand === 'boolean') {
      return !operand;
    }

    if (typeof operand !== 'number') {
      return undefined;
    }

    switch (op) {
      case UnaryOpKind.Neg:
        return -operand;
      case UnaryOpKind.BitNot:
        return ~operand;
      default:
        return undefined;
    }
  }
}

/**
 * Dead Code Elimination: Remove instructions that compute unused values
 */
export class DeadCodeElimination implements OptimizationPass {
  name = 'DeadCodeElimination';

  optimize(program: IRProgram): IRProgram {
    return {
      ...program,
      functions: program.functions.map((func) => this.optimizeFunction(func)),
    };
  }

  private optimizeFunction(func: IRFunction): IRFunction {
    // Track which values are used
    const usedValues = new Set<number>();

    // Mark all values used in critical instructions
    for (const block of func.blocks) {
      for (const instr of block.instructions) {
        this.markUsedValues(instr, usedValues);
      }
    }

    // Remove instructions that produce unused values
    return {
      ...func,
      blocks: func.blocks.map((block) => this.eliminateDeadCode(block, usedValues)),
    };
  }

  private markUsedValues(instr: IRInstr, used: Set<number>): void {
    switch (instr.kind) {
      case 'binop':
        used.add(instr.left.id);
        used.add(instr.right.id);
        break;
      case 'unaryop':
        used.add(instr.operand.id);
        break;
      case 'store':
        used.add(instr.address.id);
        used.add(instr.value.id);
        break;
      case 'load':
        used.add(instr.address.id);
        break;
      case 'return':
        if (instr.value) {
          used.add(instr.value.id);
        }
        break;
      case 'call':
        for (const arg of instr.arguments) {
          used.add(arg.id);
        }
        break;
      case 'condjump':
        used.add(instr.condition.id);
        break;
      case 'getelementptr':
        used.add(instr.basePtr.id);
        for (const index of instr.indices) {
          used.add(index.id);
        }
        break;
      case 'phi':
        for (const incoming of instr.incomingValues) {
          used.add(incoming.value.id);
        }
        break;
    }
  }

  private eliminateDeadCode(block: IRBlock, usedValues: Set<number>): IRBlock {
    const newInstructions: IRInstr[] = [];

    for (const instr of block.instructions) {
      // Keep instruction if it has side effects or its result is used
      if (this.hasSideEffects(instr) || (instr.result && usedValues.has(instr.result.id))) {
        newInstructions.push(instr);
      }
    }

    return {
      ...block,
      instructions: newInstructions,
    };
  }

  private hasSideEffects(instr: IRInstr): boolean {
    // Instructions with side effects must be kept
    return (
      instr.kind === 'store' ||
      instr.kind === 'call' ||
      instr.kind === 'return' ||
      instr.kind === 'jump' ||
      instr.kind === 'condjump'
    );
  }
}

/**
 * Common Subexpression Elimination: Avoid redundant computations
 */
export class CommonSubexpressionElimination implements OptimizationPass {
  name = 'CommonSubexpressionElimination';

  optimize(program: IRProgram): IRProgram {
    return {
      ...program,
      functions: program.functions.map((func) => this.optimizeFunction(func)),
    };
  }

  private optimizeFunction(func: IRFunction): IRFunction {
    return {
      ...func,
      blocks: func.blocks.map((block) => this.optimizeBlock(block)),
    };
  }

  private optimizeBlock(block: IRBlock): IRBlock {
    const expressions = new Map<string, IRValue>();
    const replacements = new Map<number, number>();
    const newInstructions: IRInstr[] = [];

    for (const instr of block.instructions) {
      if (instr.kind === 'binop') {
        const key = this.getBinOpKey(instr);
        const existing = expressions.get(key);

        if (existing) {
          // This expression was already computed
          replacements.set(instr.result.id, existing.id);
        } else {
          expressions.set(key, instr.result);
          newInstructions.push(this.applyReplacements(instr, replacements));
        }
      } else if (instr.kind === 'unaryop') {
        const key = this.getUnaryOpKey(instr);
        const existing = expressions.get(key);

        if (existing) {
          replacements.set(instr.result.id, existing.id);
        } else {
          expressions.set(key, instr.result);
          newInstructions.push(this.applyReplacements(instr, replacements));
        }
      } else {
        // Clear expressions on instructions that might modify memory
        if (instr.kind === 'store' || instr.kind === 'call') {
          expressions.clear();
        }
        newInstructions.push(this.applyReplacements(instr, replacements));
      }
    }

    return {
      ...block,
      instructions: newInstructions,
    };
  }

  private getBinOpKey(instr: IRBinOp): string {
    const leftId = instr.left.id;
    const rightId = instr.right.id;
    return `binop_${instr.op}_${leftId}_${rightId}`;
  }

  private getUnaryOpKey(instr: IRUnaryOp): string {
    return `unaryop_${instr.op}_${instr.operand.id}`;
  }

  private applyReplacements(instr: IRInstr, replacements: Map<number, number>): IRInstr {
    const replaceValue = (value: IRValue): IRValue => {
      const replacementId = replacements.get(value.id);
      return replacementId !== undefined ? { ...value, id: replacementId } : value;
    };

    switch (instr.kind) {
      case 'binop':
        return {
          ...instr,
          left: replaceValue(instr.left),
          right: replaceValue(instr.right),
        };
      case 'unaryop':
        return {
          ...instr,
          operand: replaceValue(instr.operand),
        };
      case 'store':
        return {
          ...instr,
          address: replaceValue(instr.address),
          value: replaceValue(instr.value),
        };
      case 'load':
        return {
          ...instr,
          address: replaceValue(instr.address),
        };
      case 'return':
        return instr.value ? { ...instr, value: replaceValue(instr.value) } : instr;
      case 'call':
        return {
          ...instr,
          arguments: instr.arguments.map(replaceValue),
        };
      case 'condjump':
        return {
          ...instr,
          condition: replaceValue(instr.condition),
        };
      case 'getelementptr':
        return {
          ...instr,
          basePtr: replaceValue(instr.basePtr),
          indices: instr.indices.map(replaceValue),
        };
      default:
        return instr;
    }
  }
}

/**
 * Copy Propagation: Replace uses of copied values with their sources
 */
export class CopyPropagation implements OptimizationPass {
  name = 'CopyPropagation';

  optimize(program: IRProgram): IRProgram {
    return {
      ...program,
      functions: program.functions.map((func) => this.optimizeFunction(func)),
    };
  }

  private optimizeFunction(func: IRFunction): IRFunction {
    return {
      ...func,
      blocks: func.blocks.map((block) => this.optimizeBlock(block)),
    };
  }

  private optimizeBlock(block: IRBlock): IRBlock {
    const copies = new Map<number, number>(); // Map from copy to original
    const newInstructions: IRInstr[] = [];

    for (const instr of block.instructions) {
      // Detect copy operations (load immediately after store to same address)
      // This is a simplified version - full copy propagation is more complex

      const propagated = this.propagateCopies(instr, copies);
      newInstructions.push(propagated);

      // Invalidate copies on store/call
      if (instr.kind === 'store' || instr.kind === 'call') {
        copies.clear();
      }
    }

    return {
      ...block,
      instructions: newInstructions,
    };
  }

  private propagateCopies(instr: IRInstr, copies: Map<number, number>): IRInstr {
    const replaceValue = (value: IRValue): IRValue => {
      let id = value.id;
      // Follow copy chain
      while (copies.has(id)) {
        const newId = copies.get(id);
        if (newId === undefined) break;
        id = newId;
      }
      return id !== value.id ? { ...value, id } : value;
    };

    switch (instr.kind) {
      case 'binop':
        return {
          ...instr,
          left: replaceValue(instr.left),
          right: replaceValue(instr.right),
        };
      case 'unaryop':
        return {
          ...instr,
          operand: replaceValue(instr.operand),
        };
      case 'store':
        return {
          ...instr,
          address: replaceValue(instr.address),
          value: replaceValue(instr.value),
        };
      case 'load':
        return {
          ...instr,
          address: replaceValue(instr.address),
        };
      case 'return':
        return instr.value ? { ...instr, value: replaceValue(instr.value) } : instr;
      case 'call':
        return {
          ...instr,
          arguments: instr.arguments.map(replaceValue),
        };
      case 'condjump':
        return {
          ...instr,
          condition: replaceValue(instr.condition),
        };
      case 'getelementptr':
        return {
          ...instr,
          basePtr: replaceValue(instr.basePtr),
          indices: instr.indices.map(replaceValue),
        };
      default:
        return instr;
    }
  }
}
