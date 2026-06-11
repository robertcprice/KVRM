/**
 * KVRM Compiler orchestration
 * Coordinates the compilation pipeline from source to assembly
 */

import {
  DiagnosticReporter,
  createDiagnosticReporter,
  DiagnosticCode,
} from './utils/diagnostics.js';
import { SourceMap, createSourceMap } from './utils/source-map.js';
import { Lexer } from './lexer/index.js';
import { Token } from './types/tokens.js';

/**
 * Compilation options
 */
export interface CompileOptions {
  readonly filename?: string;
  readonly optimize?: boolean;
  readonly emitIR?: boolean;
  readonly emitAST?: boolean;
  readonly verbose?: boolean;
  readonly color?: boolean;
}

/**
 * Compilation result
 */
export interface CompileResult {
  readonly success: boolean;
  readonly output?: string;
  readonly ir?: string;
  readonly ast?: string;
  readonly diagnostics: DiagnosticReporter;
  readonly sourceMap?: SourceMap;
  readonly stats?: CompileStats;
}

/**
 * Compilation statistics
 */
export interface CompileStats {
  readonly tokens: number;
  readonly astNodes: number;
  readonly irInstructions: number;
  readonly asmLines: number;
  readonly timeMs: number;
}

/**
 * Main compiler class
 */
export class Compiler {
  private diagnostics: DiagnosticReporter;

  constructor(private readonly options: CompileOptions = {}) {
    this.diagnostics = createDiagnosticReporter(
      {
        color: options.color ?? true,
        showCode: true,
        maxContextLines: 3,
      },
      options.filename
    );
  }

  /**
   * Compile source code to assembly
   */
  compile(source: string): CompileResult {
    const startTime = Date.now();
    this.diagnostics.clear();
    this.diagnostics.setSource(source, this.options.filename);

    try {
      // Stage 1: Lexical analysis
      const tokens = this.lex(source);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Stage 2: Syntax analysis
      const ast = this.parse(tokens);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Stage 3: Semantic analysis
      const semanticResult = this.analyze(ast);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Stage 4: IR generation
      const ir = this.generateIR(semanticResult);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Stage 5: Optimization (if enabled)
      const optimizedIR = this.options.optimize
        ? this.optimize(ir)
        : ir;
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Stage 6: Code generation
      const { output, sourceMap } = this.codegen(optimizedIR);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      const timeMs = Date.now() - startTime;

      return {
        success: true,
        output,
        ir: this.options.emitIR ? this.formatIR(optimizedIR) : undefined,
        ast: this.options.emitAST ? this.formatAST(ast) : undefined,
        diagnostics: this.diagnostics,
        sourceMap,
        stats: {
          tokens: tokens?.length ?? 0,
          astNodes: this.countASTNodes(ast),
          irInstructions: this.countIRInstructions(optimizedIR),
          asmLines: output.split('\n').length,
          timeMs,
        },
      };
    } catch (error) {
      // Handle unexpected compilation errors
      this.diagnostics.error(
        DiagnosticCode.C002_CODEGEN_FAILED,
        `Internal compiler error: ${error instanceof Error ? error.message : String(error)}`
      );
      return this.createFailureResult(startTime);
    }
  }

  /**
   * Check source code for errors (no code generation)
   */
  check(source: string): CompileResult {
    const startTime = Date.now();
    this.diagnostics.clear();
    this.diagnostics.setSource(source, this.options.filename);

    try {
      // Lexical analysis
      const tokens = this.lex(source);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Syntax analysis
      const ast = this.parse(tokens);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      // Semantic analysis
      this.analyze(ast);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      const timeMs = Date.now() - startTime;

      return {
        success: true,
        diagnostics: this.diagnostics,
        stats: {
          tokens: tokens?.length ?? 0,
          astNodes: this.countASTNodes(ast),
          irInstructions: 0,
          asmLines: 0,
          timeMs,
        },
      };
    } catch (error) {
      this.diagnostics.error(
        DiagnosticCode.P003_INVALID_SYNTAX,
        `Check failed: ${error instanceof Error ? error.message : String(error)}`
      );
      return this.createFailureResult(startTime);
    }
  }

  /**
   * Parse source code to AST only
   */
  parseOnly(source: string): CompileResult {
    const startTime = Date.now();
    this.diagnostics.clear();
    this.diagnostics.setSource(source, this.options.filename);

    try {
      const tokens = this.lex(source);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      const ast = this.parse(tokens);
      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      const timeMs = Date.now() - startTime;

      return {
        success: true,
        ast: this.formatAST(ast),
        diagnostics: this.diagnostics,
        stats: {
          tokens: tokens?.length ?? 0,
          astNodes: this.countASTNodes(ast),
          irInstructions: 0,
          asmLines: 0,
          timeMs,
        },
      };
    } catch (error) {
      this.diagnostics.error(
        DiagnosticCode.P003_INVALID_SYNTAX,
        `Parse failed: ${error instanceof Error ? error.message : String(error)}`
      );
      return this.createFailureResult(startTime);
    }
  }

  /**
   * Tokenize source code only
   */
  lexOnly(source: string): CompileResult {
    const startTime = Date.now();
    this.diagnostics.clear();
    this.diagnostics.setSource(source, this.options.filename);

    try {
      const tokens = this.lex(source);
      const timeMs = Date.now() - startTime;

      if (this.diagnostics.hasErrors()) {
        return this.createFailureResult(startTime);
      }

      return {
        success: true,
        output: this.formatTokens(tokens),
        diagnostics: this.diagnostics,
        stats: {
          tokens: tokens?.length ?? 0,
          astNodes: 0,
          irInstructions: 0,
          asmLines: 0,
          timeMs,
        },
      };
    } catch (error) {
      this.diagnostics.error(
        DiagnosticCode.L003_UNEXPECTED_CHARACTER,
        `Lexing failed: ${error instanceof Error ? error.message : String(error)}`
      );
      return this.createFailureResult(startTime);
    }
  }

  /**
   * Stage 1: Lexical analysis
   */
  private lex(source: string): Token[] {
    try {
      const lexer = new Lexer(source, this.options.filename);
      return lexer.tokenize();
    } catch (error) {
      this.diagnostics.error(
        DiagnosticCode.L003_UNEXPECTED_CHARACTER,
        error instanceof Error ? error.message : String(error)
      );
      return [];
    }
  }

  /**
   * Stage 2: Syntax analysis
   */
  private parse(tokens: any[]): any {
    // TODO: Implement parser integration
    this.diagnostics.warning(
      DiagnosticCode.C001_UNSUPPORTED_FEATURE,
      'Parser not yet implemented'
    );
    return null;
  }

  /**
   * Stage 3: Semantic analysis
   */
  private analyze(ast: any): any {
    // TODO: Implement semantic analyzer integration
    this.diagnostics.warning(
      DiagnosticCode.C001_UNSUPPORTED_FEATURE,
      'Semantic analyzer not yet implemented'
    );
    return null;
  }

  /**
   * Stage 4: IR generation
   */
  private generateIR(semanticResult: any): any {
    // TODO: Implement IR generator integration
    this.diagnostics.warning(
      DiagnosticCode.C001_UNSUPPORTED_FEATURE,
      'IR generator not yet implemented'
    );
    return null;
  }

  /**
   * Stage 5: Optimization
   */
  private optimize(ir: any): any {
    // TODO: Implement optimizer integration
    return ir;
  }

  /**
   * Stage 6: Code generation
   */
  private codegen(ir: any): { output: string; sourceMap: SourceMap } {
    // TODO: Implement code generator integration
    this.diagnostics.warning(
      DiagnosticCode.C001_UNSUPPORTED_FEATURE,
      'Code generator not yet implemented'
    );

    const sourceMap = createSourceMap(
      this.options.filename ?? 'input.kv',
      'output.asm'
    );

    return {
      output: '; Placeholder assembly output\n; TODO: Implement codegen',
      sourceMap,
    };
  }

  /**
   * Format tokens for display
   */
  private formatTokens(tokens: Token[]): string {
    const lines: string[] = [];
    lines.push(`Total tokens: ${tokens.length}\n`);
    lines.push('Line  Col   Type                Value');
    lines.push('-'.repeat(60));

    for (const token of tokens) {
      const line = String(token.location.line).padStart(4);
      const col = String(token.location.column).padStart(5);
      const type = token.type.padEnd(20);
      const value =
        token.value.length > 30
          ? token.value.substring(0, 27) + '...'
          : token.value;
      lines.push(`${line}  ${col} ${type} ${value}`);
    }

    return lines.join('\n');
  }

  /**
   * Format AST for display
   */
  private formatAST(ast: any): string {
    // TODO: Implement AST formatting
    return 'AST: (not yet implemented)';
  }

  /**
   * Format IR for display
   */
  private formatIR(ir: any): string {
    // TODO: Implement IR formatting
    return 'IR: (not yet implemented)';
  }

  /**
   * Count AST nodes
   */
  private countASTNodes(ast: any): number {
    // TODO: Implement AST node counting
    return 0;
  }

  /**
   * Count IR instructions
   */
  private countIRInstructions(ir: any): number {
    // TODO: Implement IR instruction counting
    return 0;
  }

  /**
   * Create a failure result
   */
  private createFailureResult(startTime: number): CompileResult {
    return {
      success: false,
      diagnostics: this.diagnostics,
      stats: {
        tokens: 0,
        astNodes: 0,
        irInstructions: 0,
        asmLines: 0,
        timeMs: Date.now() - startTime,
      },
    };
  }
}

/**
 * Compile source code with options
 */
export function compile(
  source: string,
  options?: CompileOptions
): CompileResult {
  const compiler = new Compiler(options);
  return compiler.compile(source);
}

/**
 * Check source code for errors
 */
export function check(
  source: string,
  options?: CompileOptions
): CompileResult {
  const compiler = new Compiler(options);
  return compiler.check(source);
}
