/**
 * Example usage of the KVRM IR generator
 *
 * Demonstrates how to use the IR generator with sample typed AST programs.
 */

import { IRGenerator, TypedProgram } from './generator.js';
import { IROptimizer } from './optimizer.js';
import { printIR, printStats, generateStats, generateCFGDot } from './printer.js';

/**
 * Example 1: Simple arithmetic function
 *
 * fn add(a: i32, b: i32) -> i32 {
 *   return a + b;
 * }
 */
const example1: TypedProgram = {
  functions: [
    {
      name: 'add',
      parameters: [
        { name: 'a', type: { kind: 'i32' } },
        { name: 'b', type: { kind: 'i32' } },
      ],
      returnType: { kind: 'i32' },
      body: [
        {
          kind: 'return',
          value: {
            kind: 'binary',
            op: '+',
            left: { kind: 'identifier', name: 'a', type: { kind: 'i32' } },
            right: { kind: 'identifier', name: 'b', type: { kind: 'i32' } },
            type: { kind: 'i32' },
          },
        },
      ],
    },
  ],
  structs: [],
  globalVariables: [],
};

/**
 * Example 2: Factorial with control flow
 *
 * fn factorial(n: i32) -> i32 {
 *   let mut result = 1;
 *   let mut i = n;
 *   while i > 0 {
 *     result = result * i;
 *     i = i - 1;
 *   }
 *   return result;
 * }
 */
const example2: TypedProgram = {
  functions: [
    {
      name: 'factorial',
      parameters: [{ name: 'n', type: { kind: 'i32' } }],
      returnType: { kind: 'i32' },
      body: [
        {
          kind: 'let',
          name: 'result',
          type: { kind: 'i32' },
          mutable: true,
          initializer: { kind: 'number', value: 1, type: { kind: 'i32' } },
        },
        {
          kind: 'let',
          name: 'i',
          type: { kind: 'i32' },
          mutable: true,
          initializer: { kind: 'identifier', name: 'n', type: { kind: 'i32' } },
        },
        {
          kind: 'while',
          condition: {
            kind: 'binary',
            op: '>',
            left: { kind: 'identifier', name: 'i', type: { kind: 'i32' } },
            right: { kind: 'number', value: 0, type: { kind: 'i32' } },
            type: { kind: 'bool' },
          },
          body: [
            {
              kind: 'assign',
              target: { kind: 'identifier', name: 'result', type: { kind: 'i32' } },
              value: {
                kind: 'binary',
                op: '*',
                left: { kind: 'identifier', name: 'result', type: { kind: 'i32' } },
                right: { kind: 'identifier', name: 'i', type: { kind: 'i32' } },
                type: { kind: 'i32' },
              },
            },
            {
              kind: 'assign',
              target: { kind: 'identifier', name: 'i', type: { kind: 'i32' } },
              value: {
                kind: 'binary',
                op: '-',
                left: { kind: 'identifier', name: 'i', type: { kind: 'i32' } },
                right: { kind: 'number', value: 1, type: { kind: 'i32' } },
                type: { kind: 'i32' },
              },
            },
          ],
        },
        {
          kind: 'return',
          value: { kind: 'identifier', name: 'result', type: { kind: 'i32' } },
        },
      ],
    },
  ],
  structs: [],
  globalVariables: [],
};

/**
 * Example 3: Conditional with constant folding opportunity
 *
 * fn compute() -> i32 {
 *   let x = 5 + 3;        // Will be folded to 8
 *   let y = 10 * 2;       // Will be folded to 20
 *   if x > 5 {            // Will be folded to true
 *     return x + y;
 *   } else {
 *     return 0;
 *   }
 * }
 */
const example3: TypedProgram = {
  functions: [
    {
      name: 'compute',
      parameters: [],
      returnType: { kind: 'i32' },
      body: [
        {
          kind: 'let',
          name: 'x',
          type: { kind: 'i32' },
          mutable: false,
          initializer: {
            kind: 'binary',
            op: '+',
            left: { kind: 'number', value: 5, type: { kind: 'i32' } },
            right: { kind: 'number', value: 3, type: { kind: 'i32' } },
            type: { kind: 'i32' },
          },
        },
        {
          kind: 'let',
          name: 'y',
          type: { kind: 'i32' },
          mutable: false,
          initializer: {
            kind: 'binary',
            op: '*',
            left: { kind: 'number', value: 10, type: { kind: 'i32' } },
            right: { kind: 'number', value: 2, type: { kind: 'i32' } },
            type: { kind: 'i32' },
          },
        },
        {
          kind: 'if',
          condition: {
            kind: 'binary',
            op: '>',
            left: { kind: 'identifier', name: 'x', type: { kind: 'i32' } },
            right: { kind: 'number', value: 5, type: { kind: 'i32' } },
            type: { kind: 'bool' },
          },
          thenBody: [
            {
              kind: 'return',
              value: {
                kind: 'binary',
                op: '+',
                left: { kind: 'identifier', name: 'x', type: { kind: 'i32' } },
                right: { kind: 'identifier', name: 'y', type: { kind: 'i32' } },
                type: { kind: 'i32' },
              },
            },
          ],
          elseBody: [
            {
              kind: 'return',
              value: { kind: 'number', value: 0, type: { kind: 'i32' } },
            },
          ],
        },
      ],
    },
  ],
  structs: [],
  globalVariables: [],
};

/**
 * Example 4: Struct operations
 *
 * struct Point {
 *   x: i32,
 *   y: i32,
 * }
 *
 * fn distance_squared(p: Point) -> i32 {
 *   return p.x * p.x + p.y * p.y;
 * }
 */
const example4: TypedProgram = {
  structs: [
    {
      name: 'Point',
      fields: [
        { name: 'x', type: { kind: 'i32' } },
        { name: 'y', type: { kind: 'i32' } },
      ],
    },
  ],
  functions: [
    {
      name: 'distance_squared',
      parameters: [{ name: 'p', type: { kind: 'struct', structName: 'Point' } }],
      returnType: { kind: 'i32' },
      body: [
        {
          kind: 'return',
          value: {
            kind: 'binary',
            op: '+',
            left: {
              kind: 'binary',
              op: '*',
              left: {
                kind: 'fieldAccess',
                object: { kind: 'identifier', name: 'p', type: { kind: 'struct', structName: 'Point' } },
                field: 'x',
                type: { kind: 'i32' },
              },
              right: {
                kind: 'fieldAccess',
                object: { kind: 'identifier', name: 'p', type: { kind: 'struct', structName: 'Point' } },
                field: 'x',
                type: { kind: 'i32' },
              },
              type: { kind: 'i32' },
            },
            right: {
              kind: 'binary',
              op: '*',
              left: {
                kind: 'fieldAccess',
                object: { kind: 'identifier', name: 'p', type: { kind: 'struct', structName: 'Point' } },
                field: 'y',
                type: { kind: 'i32' },
              },
              right: {
                kind: 'fieldAccess',
                object: { kind: 'identifier', name: 'p', type: { kind: 'struct', structName: 'Point' } },
                field: 'y',
                type: { kind: 'i32' },
              },
              type: { kind: 'i32' },
            },
            type: { kind: 'i32' },
          },
        },
      ],
    },
  ],
  globalVariables: [],
};

/**
 * Run all examples
 */
export function runExamples(): void {
  const generator = new IRGenerator();
  const optimizer = new IROptimizer();

  const examples = [
    { name: 'Simple Addition', program: example1 },
    { name: 'Factorial Loop', program: example2 },
    { name: 'Constant Folding', program: example3 },
    { name: 'Struct Operations', program: example4 },
  ];

  for (const example of examples) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Example: ${example.name}`);
    console.log('='.repeat(60));

    // Generate IR
    const ir = generator.generate(example.program);
    console.log('\n--- Unoptimized IR ---\n');
    console.log(printIR(ir));

    // Print statistics
    const stats = generateStats(ir);
    console.log('\n--- Statistics (Unoptimized) ---\n');
    console.log(printStats(stats));

    // Optimize
    const optimizedIR = optimizer.optimize(ir);
    console.log('\n--- Optimized IR ---\n');
    console.log(printIR(optimizedIR));

    // Print optimized statistics
    const optimizedStats = generateStats(optimizedIR);
    console.log('\n--- Statistics (Optimized) ---\n');
    console.log(printStats(optimizedStats));

    // Generate CFG for first function
    if (ir.functions.length > 0) {
      console.log('\n--- Control Flow Graph (DOT format) ---\n');
      console.log(generateCFGDot(ir.functions[0]!));
    }
  }
}

// Run examples if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runExamples();
}
