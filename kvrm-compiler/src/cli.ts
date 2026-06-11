#!/usr/bin/env node
/**
 * KVRM Compiler CLI
 * Command-line interface for the KVRM compiler
 */

import { Command } from 'commander';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve, basename, extname } from 'path';
import chalk from 'chalk';
import { Compiler, CompileOptions } from './compiler.js';

/**
 * CLI version from package.json
 */
const VERSION = '0.1.0';

/**
 * Main CLI program
 */
const program = new Command();

program
  .name('kvrmc')
  .description('KVRM language compiler - A modern systems programming language')
  .version(VERSION);

/**
 * Compile command - Full compilation to assembly
 */
program
  .command('compile')
  .description('Compile KVRM source code to assembly')
  .argument('<file>', 'source file to compile')
  .option('-o, --output <file>', 'output file path')
  .option('-O, --optimize', 'enable optimizations', false)
  .option('--emit-ir', 'also emit IR to file', false)
  .option('--emit-ast', 'also emit AST to file', false)
  .option('-v, --verbose', 'verbose output', false)
  .option('--no-color', 'disable colored output')
  .action(async (file: string, options: any) => {
    try {
      const result = await compileFile(file, {
        output: options.output,
        optimize: options.optimize,
        emitIR: options.emitIr,
        emitAST: options.emitAst,
        verbose: options.verbose,
        color: options.color,
      });

      if (!result.success) {
        process.exit(1);
      }
    } catch (error) {
      console.error(
        chalk.red(`Fatal error: ${error instanceof Error ? error.message : String(error)}`)
      );
      process.exit(1);
    }
  });

/**
 * Check command - Type check only, no code generation
 */
program
  .command('check')
  .description('Type check KVRM source code without generating output')
  .argument('<file>', 'source file to check')
  .option('-v, --verbose', 'verbose output', false)
  .option('--no-color', 'disable colored output')
  .action(async (file: string, options: any) => {
    try {
      const result = await checkFile(file, {
        verbose: options.verbose,
        color: options.color,
      });

      if (!result.success) {
        process.exit(1);
      }
    } catch (error) {
      console.error(
        chalk.red(`Fatal error: ${error instanceof Error ? error.message : String(error)}`)
      );
      process.exit(1);
    }
  });

/**
 * Parse command - Parse and show AST
 */
program
  .command('parse')
  .description('Parse KVRM source code and display AST')
  .argument('<file>', 'source file to parse')
  .option('-o, --output <file>', 'output AST to file')
  .option('-v, --verbose', 'verbose output', false)
  .option('--no-color', 'disable colored output')
  .action(async (file: string, options: any) => {
    try {
      const result = await parseFile(file, {
        output: options.output,
        verbose: options.verbose,
        color: options.color,
      });

      if (!result.success) {
        process.exit(1);
      }
    } catch (error) {
      console.error(
        chalk.red(`Fatal error: ${error instanceof Error ? error.message : String(error)}`)
      );
      process.exit(1);
    }
  });

/**
 * Lex command - Tokenize and show tokens
 */
program
  .command('lex')
  .description('Tokenize KVRM source code and display tokens')
  .argument('<file>', 'source file to tokenize')
  .option('-o, --output <file>', 'output tokens to file')
  .option('-v, --verbose', 'verbose output', false)
  .option('--no-color', 'disable colored output')
  .action(async (file: string, options: any) => {
    try {
      const result = await lexFile(file, {
        output: options.output,
        verbose: options.verbose,
        color: options.color,
      });

      if (!result.success) {
        process.exit(1);
      }
    } catch (error) {
      console.error(
        chalk.red(`Fatal error: ${error instanceof Error ? error.message : String(error)}`)
      );
      process.exit(1);
    }
  });

/**
 * IR command - Generate and show IR
 */
program
  .command('ir')
  .description('Generate intermediate representation')
  .argument('<file>', 'source file to process')
  .option('-o, --output <file>', 'output IR to file')
  .option('-O, --optimize', 'enable optimizations', false)
  .option('-v, --verbose', 'verbose output', false)
  .option('--no-color', 'disable colored output')
  .action(async (file: string, options: any) => {
    try {
      const result = await compileFile(file, {
        output: options.output,
        optimize: options.optimize,
        emitIR: true,
        verbose: options.verbose,
        color: options.color,
        irOnly: true,
      });

      if (!result.success) {
        process.exit(1);
      }
    } catch (error) {
      console.error(
        chalk.red(`Fatal error: ${error instanceof Error ? error.message : String(error)}`)
      );
      process.exit(1);
    }
  });

/**
 * Compile a file
 */
async function compileFile(
  inputPath: string,
  options: {
    output?: string;
    optimize?: boolean;
    emitIR?: boolean;
    emitAST?: boolean;
    verbose?: boolean;
    color?: boolean;
    irOnly?: boolean;
  }
): Promise<{ success: boolean }> {
  // Read source file
  const absolutePath = resolve(inputPath);
  if (!existsSync(absolutePath)) {
    console.error(chalk.red(`Error: File not found: ${inputPath}`));
    return { success: false };
  }

  const source = readFileSync(absolutePath, 'utf-8');
  const filename = basename(absolutePath);

  // Determine output path
  const outputPath =
    options.output ??
    absolutePath.replace(extname(absolutePath), '.asm');

  // Show compilation start
  if (options.verbose || !options.color) {
    console.log(`Compiling ${chalk.cyan(filename)}...`);
  } else {
    console.log(chalk.bold(`Compiling ${chalk.cyan(filename)}...`));
  }

  // Compile
  const compileOptions: CompileOptions = {
    filename: absolutePath,
    ...(options.optimize !== undefined && { optimize: options.optimize }),
    ...(options.emitIR !== undefined && { emitIR: options.emitIR }),
    ...(options.emitAST !== undefined && { emitAST: options.emitAST }),
    ...(options.verbose !== undefined && { verbose: options.verbose }),
    ...(options.color !== undefined && { color: options.color }),
  };

  const compiler = new Compiler(compileOptions);
  const result = compiler.compile(source);

  // Show progress
  if (options.verbose && result.stats) {
    const tick = chalk.green('✓');
    console.log(`  Lexing: ${tick} ${result.stats.tokens} tokens`);
    console.log(`  Parsing: ${tick}`);
    console.log(`  Type checking: ${tick}`);
    console.log(`  IR generation: ${tick}`);
    if (options.optimize) {
      console.log(`  Optimization: ${tick}`);
    }
    console.log(`  Code generation: ${tick}`);
  }

  // Show diagnostics
  const diagnosticsOutput = result.diagnostics.format();
  if (diagnosticsOutput) {
    console.log(diagnosticsOutput);
  }

  if (!result.success) {
    return { success: false };
  }

  // Write output files
  if (result.output && !options.irOnly) {
    writeFileSync(outputPath, result.output, 'utf-8');
    const size = (result.output.length / 1024).toFixed(1);
    console.log(
      chalk.green(
        `Written to ${chalk.cyan(basename(outputPath))} (${size}KB)`
      )
    );
  }

  if (result.ir && options.emitIR) {
    const irPath = outputPath.replace(/\.[^.]+$/, '.ir');
    writeFileSync(irPath, result.ir, 'utf-8');
    if (options.verbose) {
      console.log(chalk.green(`IR written to ${chalk.cyan(basename(irPath))}`));
    }
  }

  if (result.ir && options.irOnly && options.output) {
    writeFileSync(options.output, result.ir, 'utf-8');
    console.log(
      chalk.green(`IR written to ${chalk.cyan(basename(options.output))}`)
    );
  } else if (result.ir && options.irOnly) {
    console.log(result.ir);
  }

  if (result.ast && options.emitAST) {
    const astPath = outputPath.replace(/\.[^.]+$/, '.ast.json');
    writeFileSync(astPath, result.ast, 'utf-8');
    if (options.verbose) {
      console.log(
        chalk.green(`AST written to ${chalk.cyan(basename(astPath))}`)
      );
    }
  }

  // Show stats
  if (options.verbose && result.stats) {
    console.log(
      chalk.dim(`Compiled in ${result.stats.timeMs}ms`)
    );
  }

  return { success: true };
}

/**
 * Check a file
 */
async function checkFile(
  inputPath: string,
  options: {
    verbose?: boolean;
    color?: boolean;
  }
): Promise<{ success: boolean }> {
  // Read source file
  const absolutePath = resolve(inputPath);
  if (!existsSync(absolutePath)) {
    console.error(chalk.red(`Error: File not found: ${inputPath}`));
    return { success: false };
  }

  const source = readFileSync(absolutePath, 'utf-8');
  const filename = basename(absolutePath);

  // Show checking start
  console.log(chalk.bold(`Checking ${chalk.cyan(filename)}...`));

  // Check
  const compileOptions: CompileOptions = {
    filename: absolutePath,
    ...(options.verbose !== undefined && { verbose: options.verbose }),
    ...(options.color !== undefined && { color: options.color }),
  };

  const compiler = new Compiler(compileOptions);
  const result = compiler.check(source);

  // Show progress
  if (options.verbose && result.stats) {
    const tick = chalk.green('✓');
    console.log(`  Lexing: ${tick} ${result.stats.tokens} tokens`);
    console.log(`  Parsing: ${tick}`);
    console.log(`  Type checking: ${tick}`);
  }

  // Show diagnostics
  const diagnosticsOutput = result.diagnostics.format();
  if (diagnosticsOutput) {
    console.log(diagnosticsOutput);
  }

  if (result.success) {
    console.log(chalk.green('✓ No errors found'));
  }

  return { success: result.success };
}

/**
 * Parse a file
 */
async function parseFile(
  inputPath: string,
  options: {
    output?: string;
    verbose?: boolean;
    color?: boolean;
  }
): Promise<{ success: boolean }> {
  // Read source file
  const absolutePath = resolve(inputPath);
  if (!existsSync(absolutePath)) {
    console.error(chalk.red(`Error: File not found: ${inputPath}`));
    return { success: false };
  }

  const source = readFileSync(absolutePath, 'utf-8');
  const filename = basename(absolutePath);

  // Show parsing start
  console.log(chalk.bold(`Parsing ${chalk.cyan(filename)}...`));

  // Parse
  const compileOptions: CompileOptions = {
    filename: absolutePath,
    emitAST: true,
    ...(options.verbose !== undefined && { verbose: options.verbose }),
    ...(options.color !== undefined && { color: options.color }),
  };

  const compiler = new Compiler(compileOptions);
  const result = compiler.parseOnly(source);

  // Show diagnostics
  const diagnosticsOutput = result.diagnostics.format();
  if (diagnosticsOutput) {
    console.log(diagnosticsOutput);
  }

  if (!result.success) {
    return { success: false };
  }

  // Output AST
  if (result.ast) {
    if (options.output) {
      writeFileSync(options.output, result.ast, 'utf-8');
      console.log(
        chalk.green(`AST written to ${chalk.cyan(basename(options.output))}`)
      );
    } else {
      console.log(result.ast);
    }
  }

  return { success: true };
}

/**
 * Lex a file
 */
async function lexFile(
  inputPath: string,
  options: {
    output?: string;
    verbose?: boolean;
    color?: boolean;
  }
): Promise<{ success: boolean }> {
  // Read source file
  const absolutePath = resolve(inputPath);
  if (!existsSync(absolutePath)) {
    console.error(chalk.red(`Error: File not found: ${inputPath}`));
    return { success: false };
  }

  const source = readFileSync(absolutePath, 'utf-8');
  const filename = basename(absolutePath);

  // Show lexing start
  console.log(chalk.bold(`Tokenizing ${chalk.cyan(filename)}...`));

  // Lex
  const compileOptions: CompileOptions = {
    filename: absolutePath,
    ...(options.verbose !== undefined && { verbose: options.verbose }),
    ...(options.color !== undefined && { color: options.color }),
  };

  const compiler = new Compiler(compileOptions);
  const result = compiler.lexOnly(source);

  // Show diagnostics
  const diagnosticsOutput = result.diagnostics.format();
  if (diagnosticsOutput) {
    console.log(diagnosticsOutput);
  }

  if (!result.success) {
    return { success: false };
  }

  // Output tokens
  if (result.output) {
    if (options.output) {
      writeFileSync(options.output, result.output, 'utf-8');
      console.log(
        chalk.green(`Tokens written to ${chalk.cyan(basename(options.output))}`)
      );
    } else {
      console.log(result.output);
    }
  }

  if (options.verbose && result.stats) {
    console.log(chalk.green(`✓ ${result.stats.tokens} tokens`));
  }

  return { success: true };
}

/**
 * Parse and run CLI
 */
program.parse();
