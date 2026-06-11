/**
 * Source mapping for debugging support
 * Maps generated assembly back to original source locations
 */

import { SourceLocation } from '../types/tokens.js';

/**
 * Mapping from generated code position to source position
 */
export interface SourceMapping {
  readonly generatedLine: number;
  readonly generatedColumn: number;
  readonly sourceLine: number;
  readonly sourceColumn: number;
  readonly name?: string;
}

/**
 * Source map for tracking code transformations
 */
export class SourceMap {
  private mappings: SourceMapping[] = [];

  constructor(
    private readonly sourceFile: string,
    private readonly generatedFile: string
  ) {}

  /**
   * Add a mapping from generated position to source position
   */
  addMapping(
    generatedLine: number,
    generatedColumn: number,
    sourceLocation: SourceLocation,
    name?: string
  ): void {
    this.mappings.push({
      generatedLine,
      generatedColumn,
      sourceLine: sourceLocation.line,
      sourceColumn: sourceLocation.column,
      ...(name !== undefined && { name }),
    });
  }

  /**
   * Get source location for a generated position
   */
  getSourceLocation(
    generatedLine: number,
    generatedColumn: number
  ): SourceLocation | null {
    // Find the closest mapping
    let closest: SourceMapping | null = null;
    let minDistance = Infinity;

    for (const mapping of this.mappings) {
      if (mapping.generatedLine > generatedLine) {
        continue;
      }

      if (
        mapping.generatedLine === generatedLine &&
        mapping.generatedColumn > generatedColumn
      ) {
        continue;
      }

      const distance =
        (generatedLine - mapping.generatedLine) * 1000 +
        (generatedColumn - mapping.generatedColumn);

      if (distance < minDistance) {
        minDistance = distance;
        closest = mapping;
      }
    }

    if (!closest) {
      return null;
    }

    return {
      line: closest.sourceLine,
      column: closest.sourceColumn,
      offset: 0,
      length: 1,
    };
  }

  /**
   * Get all mappings
   */
  getMappings(): readonly SourceMapping[] {
    return this.mappings;
  }

  /**
   * Export as JSON source map (Source Map v3 format)
   */
  toJSON(): string {
    const sourceMap = {
      version: 3,
      file: this.generatedFile,
      sourceRoot: '',
      sources: [this.sourceFile],
      names: [] as string[],
      mappings: this.encodeVLQ(),
    };

    return JSON.stringify(sourceMap, null, 2);
  }

  /**
   * Encode mappings in VLQ format (simplified version)
   * Full implementation would use proper Base64 VLQ encoding
   */
  private encodeVLQ(): string {
    // Simplified: just return empty for now
    // Full implementation would encode mappings as Base64 VLQ
    return '';
  }

  /**
   * Create a human-readable mapping table
   */
  toTable(): string {
    const lines: string[] = [];
    lines.push('Source Mappings:');
    lines.push(
      '  Generated (line:col) -> Source (line:col)' + (this.mappings.some((m) => m.name) ? ' [Name]' : '')
    );
    lines.push('  ' + '-'.repeat(60));

    for (const mapping of this.mappings) {
      const gen = `${mapping.generatedLine}:${mapping.generatedColumn}`;
      const src = `${mapping.sourceLine}:${mapping.sourceColumn}`;
      const name = mapping.name ? ` [${mapping.name}]` : '';
      lines.push(`  ${gen.padEnd(15)} -> ${src.padEnd(15)}${name}`);
    }

    return lines.join('\n');
  }
}

/**
 * Create a new source map
 */
export function createSourceMap(
  sourceFile: string,
  generatedFile: string
): SourceMap {
  return new SourceMap(sourceFile, generatedFile);
}
