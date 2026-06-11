/**
 * KVRM Compiler IR Module
 *
 * Exports all IR-related functionality including:
 * - IR node definitions (SSA-form intermediate representation)
 * - IR generator (AST to IR conversion)
 * - IR optimizer (optimization passes)
 * - IR printer (human-readable output and visualization)
 */

// IR Node Definitions
export {
  IRProgram,
  IRFunction,
  IRBlock,
  IRInstr,
  IRValue,
  IRType,
  IRTypeKind,
  IRStructDef,
  IRGlobalVar,
  IRConst,
  IRLoad,
  IRStore,
  IRBinOp,
  IRUnaryOp,
  IRCall,
  IRJump,
  IRCondJump,
  IRPhi,
  IRReturn,
  IRAlloc,
  IRGetElementPtr,
  BinOpKind,
  UnaryOpKind,
  IRTypes,
  isIntegerType,
  isFloatType,
  isPointerType,
  getTypeAlignment,
} from './ir-nodes.js';

// IR Generator
export {
  IRGenerator,
  TypedProgram,
  TypedFunction,
  TypedStruct,
  TypedGlobalVar,
  Type,
  TypedStatement,
  TypedExpression,
} from './generator.js';

// IR Optimizer
export {
  IROptimizer,
  OptimizationPass,
  ConstantFolding,
  DeadCodeElimination,
  CommonSubexpressionElimination,
  CopyPropagation,
} from './optimizer.js';

// IR Printer
export {
  IRPrinter,
  PrintOptions,
  printIR,
  printFunction,
  printIRToConsole,
  generateCFGDot,
  generateStats,
  printStats,
  IRStats,
} from './printer.js';
