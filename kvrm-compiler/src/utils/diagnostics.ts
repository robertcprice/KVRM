/**
 * Diagnostic formatting and error reporting system
 * Provides rich, colorized error messages with source context
 */

import chalk from 'chalk';
import { SourceLocation } from '../types/tokens.js';

/**
 * Diagnostic severity levels
 */
export enum DiagnosticLevel {
  Error = 'error',
  Warning = 'warning',
  Info = 'info',
}

/**
 * Diagnostic error codes
 */
export enum DiagnosticCode {
  // Lexer errors (L000-L999)
  L001_UNTERMINATED_STRING = 'L001',
  L002_INVALID_NUMBER = 'L002',
  L003_UNEXPECTED_CHARACTER = 'L003',
  L004_INVALID_ESCAPE_SEQUENCE = 'L004',

  // Parser errors (P000-P999)
  P001_UNEXPECTED_TOKEN = 'P001',
  P002_EXPECTED_TOKEN = 'P002',
  P003_INVALID_SYNTAX = 'P003',
  P004_UNCLOSED_DELIMITER = 'P004',

  // Semantic errors (S000-S999)
  S001_TYPE_MISMATCH = 'S001',
  S002_UNDEFINED_VARIABLE = 'S002',
  S003_DUPLICATE_DECLARATION = 'S003',
  S004_INVALID_OPERATION = 'S004',
  S005_IMMUTABLE_ASSIGNMENT = 'S005',
  S006_RETURN_TYPE_MISMATCH = 'S006',

  // IR errors (I000-I999)
  I001_INVALID_IR = 'I001',
  I002_OPTIMIZATION_FAILED = 'I002',

  // Codegen errors (C000-C999)
  C001_UNSUPPORTED_FEATURE = 'C001',
  C002_CODEGEN_FAILED = 'C002',
}

/**
 * Source span for error highlighting
 */
export interface SourceSpan {
  readonly start: SourceLocation;
  readonly end?: SourceLocation;
}

/**
 * Diagnostic message with context
 */
export interface Diagnostic {
  readonly level: DiagnosticLevel;
  readonly code: DiagnosticCode;
  readonly message: string;
  readonly span?: SourceSpan;
  readonly hint?: string;
  readonly relatedInfo?: Array<{
    message: string;
    span: SourceSpan;
  }>;
}

/**
 * Options for diagnostic formatting
 */
export interface DiagnosticOptions {
  readonly color: boolean;
  readonly showCode: boolean;
  readonly maxContextLines: number;
}

const DEFAULT_OPTIONS: DiagnosticOptions = {
  color: true,
  showCode: true,
  maxContextLines: 3,
};

/**
 * Diagnostic reporter for formatting and displaying errors
 */
export class DiagnosticReporter {
  private diagnostics: Diagnostic[] = [];
  private sourceLines: Map<string, string[]> = new Map();

  constructor(
    private readonly options: DiagnosticOptions = DEFAULT_OPTIONS,
    private readonly filename?: string
  ) {}

  /**
   * Register source code for context display
   */
  setSource(source: string, filename?: string): void {
    const lines = source.split('\n');
    const key = filename ?? 'input';
    this.sourceLines.set(key, lines);
  }

  /**
   * Add a diagnostic
   */
  report(diagnostic: Diagnostic): void {
    this.diagnostics.push(diagnostic);
  }

  /**
   * Add an error diagnostic
   */
  error(
    code: DiagnosticCode,
    message: string,
    span?: SourceSpan,
    hint?: string
  ): void {
    this.report({
      level: DiagnosticLevel.Error,
      code,
      message,
      ...(span !== undefined && { span }),
      ...(hint !== undefined && { hint }),
    });
  }

  /**
   * Add a warning diagnostic
   */
  warning(
    code: DiagnosticCode,
    message: string,
    span?: SourceSpan,
    hint?: string
  ): void {
    this.report({
      level: DiagnosticLevel.Warning,
      code,
      message,
      ...(span !== undefined && { span }),
      ...(hint !== undefined && { hint }),
    });
  }

  /**
   * Add an info diagnostic
   */
  info(
    code: DiagnosticCode,
    message: string,
    span?: SourceSpan,
    hint?: string
  ): void {
    this.report({
      level: DiagnosticLevel.Info,
      code,
      message,
      ...(span !== undefined && { span }),
      ...(hint !== undefined && { hint }),
    });
  }

  /**
   * Check if there are any errors
   */
  hasErrors(): boolean {
    return this.diagnostics.some((d) => d.level === DiagnosticLevel.Error);
  }

  /**
   * Get error count
   */
  errorCount(): number {
    return this.diagnostics.filter((d) => d.level === DiagnosticLevel.Error)
      .length;
  }

  /**
   * Get warning count
   */
  warningCount(): number {
    return this.diagnostics.filter((d) => d.level === DiagnosticLevel.Warning)
      .length;
  }

  /**
   * Get all diagnostics
   */
  getDiagnostics(): readonly Diagnostic[] {
    return this.diagnostics;
  }

  /**
   * Clear all diagnostics
   */
  clear(): void {
    this.diagnostics = [];
  }

  /**
   * Format all diagnostics as a string
   */
  format(): string {
    if (this.diagnostics.length === 0) {
      return '';
    }

    const output: string[] = [];

    for (const diagnostic of this.diagnostics) {
      output.push(this.formatDiagnostic(diagnostic));
    }

    // Add summary
    const errors = this.errorCount();
    const warnings = this.warningCount();
    if (errors > 0 || warnings > 0) {
      output.push('');
      const parts: string[] = [];
      if (errors > 0) {
        parts.push(
          this.colorize(
            `${errors} error${errors > 1 ? 's' : ''}`,
            DiagnosticLevel.Error
          )
        );
      }
      if (warnings > 0) {
        parts.push(
          this.colorize(
            `${warnings} warning${warnings > 1 ? 's' : ''}`,
            DiagnosticLevel.Warning
          )
        );
      }
      output.push(parts.join(', '));
    }

    return output.join('\n');
  }

  /**
   * Format a single diagnostic
   */
  private formatDiagnostic(diagnostic: Diagnostic): string {
    const output: string[] = [];
    const { level, code, message, span, hint } = diagnostic;

    // Header: error[E001]: message
    const header = this.options.showCode
      ? `${level}[${code}]: ${message}`
      : `${level}: ${message}`;

    output.push(this.colorize(header, level));

    // Location and context
    if (span) {
      const filename = this.filename ?? 'input';
      const location = `${filename}:${span.start.line}:${span.start.column}`;
      output.push(this.colorize(`  --> ${location}`, DiagnosticLevel.Info));

      // Source context
      const sourceLines = this.sourceLines.get(
        this.filename ?? 'input'
      ) ?? [];
      if (sourceLines.length > 0) {
        output.push(this.formatSourceContext(span, sourceLines, level));
      }
    }

    // Hint
    if (hint) {
      output.push(this.colorize(`  help: ${hint}`, DiagnosticLevel.Info));
    }

    return output.join('\n');
  }

  /**
   * Format source context with highlighting
   */
  private formatSourceContext(
    span: SourceSpan,
    sourceLines: string[],
    level: DiagnosticLevel
  ): string {
    const output: string[] = [];
    const lineNum = span.start.line;
    const column = span.start.column;

    // Line number width for alignment
    const maxLineNum = Math.min(lineNum + 1, sourceLines.length);
    const lineNumWidth = String(maxLineNum).length;

    // Show the line with the error
    if (lineNum >= 1 && lineNum <= sourceLines.length) {
      const line = sourceLines[lineNum - 1];
      const lineNumStr = String(lineNum).padStart(lineNumWidth, ' ');

      output.push(`   ${this.colorize(lineNumStr, DiagnosticLevel.Info)} | `);
      output.push(
        `   ${this.colorize(lineNumStr, DiagnosticLevel.Info)} | ${line}`
      );

      // Highlight the error position
      const endColumn = span.end?.column ?? column + 1;
      const length = Math.max(1, endColumn - column);
      const spaces = ' '.repeat(column - 1);
      const carets = this.colorize('^'.repeat(length), level);
      const padding = ' '.repeat(lineNumWidth);
      output.push(`   ${padding} | ${spaces}${carets}`);
    }

    return output.join('\n');
  }

  /**
   * Colorize text based on diagnostic level
   */
  private colorize(text: string, level: DiagnosticLevel): string {
    if (!this.options.color) {
      return text;
    }

    switch (level) {
      case DiagnosticLevel.Error:
        return chalk.red.bold(text);
      case DiagnosticLevel.Warning:
        return chalk.yellow.bold(text);
      case DiagnosticLevel.Info:
        return chalk.blue(text);
      default:
        return text;
    }
  }
}

/**
 * Create a diagnostic reporter
 */
export function createDiagnosticReporter(
  options?: Partial<DiagnosticOptions>,
  filename?: string
): DiagnosticReporter {
  return new DiagnosticReporter(
    { ...DEFAULT_OPTIONS, ...options },
    filename
  );
}
