/**
 * Example usage of KVRM Code Generator
 * Demonstrates creating IR and generating assembly
 */

import type { IRProgram, IRFunction, IRBasicBlock } from '../ir/types.js';
import { IROpcode, IRValueFactory, createInstruction } from '../ir/types.js';
import { generateAssembly, generateWithStats } from './generator.js';

/**
 * Create a simple example function: add(a, b) -> a + b
 */
function createAddFunction(): IRFunction {
  const block: IRBasicBlock = {
    id: 0,
    label: 'entry',
    instructions: [
      // t0 = arg0 + arg1
      createInstruction(IROpcode.Add, {
        dest: IRValueFactory.temp(0),
        src1: IRValueFactory.argument(0, 'a'),
        src2: IRValueFactory.argument(1, 'b'),
        comment: 'Add parameters a and b',
      }),
      // return t0
      createInstruction(IROpcode.Move, {
        dest: IRValueFactory.register(0), // R0 = return value
        src1: IRValueFactory.temp(0),
        comment: 'Move result to return register',
      }),
      createInstruction(IROpcode.Return, {
        comment: 'Return from function',
      }),
    ],
    predecessors: [],
    successors: [],
  };

  return {
    name: 'add',
    parameters: [
      { name: 'a', type: 'i32' },
      { name: 'b', type: 'i32' },
    ],
    returnType: 'i32',
    blocks: [block],
    localVars: new Map(),
    tempCount: 1,
    stackSize: 0,
    isEntryPoint: false,
  };
}

/**
 * Create a factorial function: factorial(n)
 */
function createFactorialFunction(): IRFunction {
  const entryBlock: IRBasicBlock = {
    id: 0,
    label: 'entry',
    instructions: [
      // if (n <= 1) goto base_case
      createInstruction(IROpcode.Le, {
        dest: IRValueFactory.temp(0),
        src1: IRValueFactory.argument(0, 'n'),
        src2: IRValueFactory.constant(1),
        comment: 'Check if n <= 1',
      }),
      createInstruction(IROpcode.JumpIf, {
        src1: IRValueFactory.temp(0),
        src2: IRValueFactory.label('base_case'),
      }),
    ],
    predecessors: [],
    successors: [1, 2],
  };

  const recursiveBlock: IRBasicBlock = {
    id: 1,
    label: 'recursive',
    instructions: [
      // t1 = n - 1
      createInstruction(IROpcode.Sub, {
        dest: IRValueFactory.temp(1),
        src1: IRValueFactory.argument(0, 'n'),
        src2: IRValueFactory.constant(1),
        comment: 'Calculate n - 1',
      }),
      // t2 = call factorial(t1)
      createInstruction(IROpcode.Push, {
        src1: IRValueFactory.temp(1),
        comment: 'Push argument for recursive call',
      }),
      createInstruction(IROpcode.Call, {
        src1: IRValueFactory.label('factorial'),
        dest: IRValueFactory.temp(2),
        comment: 'Recursive call to factorial',
      }),
      // t3 = n * t2
      createInstruction(IROpcode.Mul, {
        dest: IRValueFactory.temp(3),
        src1: IRValueFactory.argument(0, 'n'),
        src2: IRValueFactory.temp(2),
        comment: 'Multiply n * factorial(n-1)',
      }),
      // return t3
      createInstruction(IROpcode.Move, {
        dest: IRValueFactory.register(0),
        src1: IRValueFactory.temp(3),
      }),
      createInstruction(IROpcode.Return),
    ],
    predecessors: [0],
    successors: [],
  };

  const baseBlock: IRBasicBlock = {
    id: 2,
    label: 'base_case',
    instructions: [
      // return 1
      createInstruction(IROpcode.Move, {
        dest: IRValueFactory.register(0),
        src1: IRValueFactory.constant(1),
        comment: 'Base case: return 1',
      }),
      createInstruction(IROpcode.Return),
    ],
    predecessors: [0],
    successors: [],
  };

  return {
    name: 'factorial',
    parameters: [{ name: 'n', type: 'i32' }],
    returnType: 'i32',
    blocks: [entryBlock, recursiveBlock, baseBlock],
    localVars: new Map([['n', { id: 0, type: 'i32' }]]),
    tempCount: 4,
    stackSize: 16,
    isEntryPoint: false,
  };
}

/**
 * Create main function
 */
function createMainFunction(): IRFunction {
  const block: IRBasicBlock = {
    id: 0,
    label: 'entry',
    instructions: [
      // t0 = add(5, 3)
      createInstruction(IROpcode.Push, {
        src1: IRValueFactory.constant(5),
        comment: 'Push first argument',
      }),
      createInstruction(IROpcode.Push, {
        src1: IRValueFactory.constant(3),
        comment: 'Push second argument',
      }),
      createInstruction(IROpcode.Call, {
        src1: IRValueFactory.label('add'),
        dest: IRValueFactory.temp(0),
        comment: 'Call add(5, 3)',
      }),
      // t1 = factorial(5)
      createInstruction(IROpcode.Push, {
        src1: IRValueFactory.constant(5),
        comment: 'Push argument for factorial',
      }),
      createInstruction(IROpcode.Call, {
        src1: IRValueFactory.label('factorial'),
        dest: IRValueFactory.temp(1),
        comment: 'Call factorial(5)',
      }),
      // return t1
      createInstruction(IROpcode.Move, {
        dest: IRValueFactory.register(0),
        src1: IRValueFactory.temp(1),
        comment: 'Return factorial result',
      }),
      createInstruction(IROpcode.Return),
    ],
    predecessors: [],
    successors: [],
  };

  return {
    name: 'main',
    parameters: [],
    returnType: 'i32',
    blocks: [block],
    localVars: new Map(),
    tempCount: 2,
    stackSize: 8,
    isEntryPoint: true,
  };
}

/**
 * Create example program
 */
export function createExampleProgram(): IRProgram {
  return {
    functions: [
      createMainFunction(),
      createAddFunction(),
      createFactorialFunction(),
    ],
    globals: new Map([
      ['counter', { type: 'i32', initialValue: IRValueFactory.constant(0) }],
    ]),
    constants: new Map([
      ['PI', { type: 'f32', value: 3.14159 }],
      ['MAX_SIZE', { type: 'i32', value: 1024 }],
    ]),
    stringLiterals: new Map([
      ['.str0', 'Hello, KVRM!'],
      ['.str1', 'Factorial result: %d\\n'],
    ]),
  };
}

/**
 * Run example code generation
 */
export function runExample(): void {
  console.log('=== KVRM Code Generator Example ===\n');

  const program = createExampleProgram();

  console.log('Generating assembly with detailed comments...\n');

  const { assembly, stats } = generateWithStats(program, {
    optimize: true,
    debugInfo: false,
    commentLevel: 'detailed',
    formatOptions: {
      uppercase: true,
      commentColumn: 40,
    },
  });

  console.log(assembly);

  console.log('\n=== Code Generation Statistics ===');
  console.log(`Functions generated: ${stats.functionsGenerated}`);
  console.log(`Instructions generated: ${stats.instructionsGenerated}`);
  console.log(`Registers spilled: ${stats.registersSpilled}`);
  console.log(`Max stack frame size: ${stats.maxStackFrameSize} bytes`);
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runExample();
}
