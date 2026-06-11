/**
 * IR Generator for KVRM Compiler
 *
 * Converts typed AST to SSA-form intermediate representation.
 * Handles SSA value numbering, basic block construction, and control flow graph building.
 */

import {
  IRProgram,
  IRFunction,
  IRBlock,
  IRInstr,
  IRValue,
  IRType,
  IRTypes,
  BinOpKind,
  UnaryOpKind,
  IRStructDef,
  IRGlobalVar,
  IRConst,
  IRBinOp,
  IRUnaryOp,
  IRCall,
  IRAlloc,
  IRLoad,
  IRStore,
  IRReturn,
  IRJump,
  IRCondJump,
  IRGetElementPtr,
} from './ir-nodes.js';

/**
 * Placeholder typed AST interfaces
 * These would come from the semantic analyzer in a complete implementation
 */
export interface TypedProgram {
  functions: TypedFunction[];
  structs: TypedStruct[];
  globalVariables: TypedGlobalVar[];
}

export interface TypedFunction {
  name: string;
  parameters: Array<{ name: string; type: Type }>;
  returnType: Type;
  body: TypedStatement[];
}

export interface TypedStruct {
  name: string;
  fields: Array<{ name: string; type: Type }>;
}

export interface TypedGlobalVar {
  name: string;
  type: Type;
  initialValue?: unknown;
  isConstant: boolean;
}

export interface Type {
  kind: 'i32' | 'i64' | 'f32' | 'f64' | 'bool' | 'void' | 'ptr' | 'struct';
  structName?: string;
  pointeeType?: Type;
}

export type TypedStatement =
  | { kind: 'let'; name: string; type: Type; initializer?: TypedExpression; mutable: boolean }
  | { kind: 'assign'; target: TypedExpression; value: TypedExpression }
  | { kind: 'return'; value?: TypedExpression }
  | { kind: 'if'; condition: TypedExpression; thenBody: TypedStatement[]; elseBody?: TypedStatement[] }
  | { kind: 'while'; condition: TypedExpression; body: TypedStatement[] }
  | { kind: 'expression'; expression: TypedExpression };

export type TypedExpression =
  | { kind: 'number'; value: number; type: Type }
  | { kind: 'boolean'; value: boolean; type: Type }
  | { kind: 'string'; value: string; type: Type }
  | { kind: 'identifier'; name: string; type: Type }
  | { kind: 'binary'; op: string; left: TypedExpression; right: TypedExpression; type: Type }
  | { kind: 'unary'; op: string; operand: TypedExpression; type: Type }
  | { kind: 'call'; functionName: string; arguments: TypedExpression[]; type: Type }
  | { kind: 'fieldAccess'; object: TypedExpression; field: string; type: Type }
  | { kind: 'structLiteral'; structName: string; fields: Map<string, TypedExpression>; type: Type };

/**
 * IR Generator class
 */
export class IRGenerator {
  private valueCounter = 0;
  private blockCounter = 0;
  private currentFunction: IRFunction | null = null;
  private currentBlock: IRBlock | null = null;
  private symbolTable = new Map<string, IRValue>();
  private structs = new Map<string, IRStructDef>();

  /**
   * Generate IR from typed AST program
   */
  generate(program: TypedProgram): IRProgram {
    this.valueCounter = 0;
    this.blockCounter = 0;

    // Process struct definitions
    this.processStructs(program.structs);

    // Process global variables
    const globalVariables = new Map<string, IRGlobalVar>();
    for (const globalVar of program.globalVariables) {
      globalVariables.set(globalVar.name, {
        name: globalVar.name,
        type: this.convertType(globalVar.type),
        initialValue: globalVar.initialValue as number | string | boolean | undefined,
        isConstant: globalVar.isConstant,
      });
    }

    // Generate IR for each function
    const functions = program.functions.map((fn) => this.generateFunction(fn));

    return {
      functions,
      structs: this.structs,
      globalVariables,
    };
  }

  /**
   * Process struct definitions
   */
  private processStructs(structs: TypedStruct[]): void {
    for (const struct of structs) {
      let offset = 0;
      const fields = struct.fields.map((field) => {
        const irType = this.convertType(field.type);
        const fieldDef = {
          name: field.name,
          type: irType,
          offset,
        };
        offset += irType.size;
        return fieldDef;
      });

      this.structs.set(struct.name, {
        name: struct.name,
        fields,
        size: offset,
        alignment: 8, // Default alignment
      });
    }
  }

  /**
   * Generate IR for a function
   */
  private generateFunction(func: TypedFunction): IRFunction {
    this.symbolTable.clear();
    this.blockCounter = 0;

    // Create entry block
    const entryBlock = this.createBlock('entry');
    this.currentBlock = entryBlock;

    // Convert parameter types and create parameter values
    const parameters: IRValue[] = func.parameters.map((param, index) => {
      const irType = this.convertType(param.type);
      const value = this.newValue(irType, `param_${param.name}`);
      this.symbolTable.set(param.name, value);
      return value;
    });

    const irFunc: IRFunction = {
      name: func.name,
      parameters,
      returnType: this.convertType(func.returnType),
      blocks: [entryBlock],
      entryBlock: entryBlock.label,
      localCount: 0,
    };

    this.currentFunction = irFunc;

    // Generate IR for function body
    for (const stmt of func.body) {
      this.generateStatement(stmt);
    }

    // Ensure function ends with a return
    if (
      this.currentBlock &&
      (this.currentBlock.instructions.length === 0 ||
        this.currentBlock.instructions[this.currentBlock.instructions.length - 1]?.kind !== 'return')
    ) {
      if (func.returnType.kind === 'void') {
        this.emit({ kind: 'return' });
      }
    }

    this.currentFunction = null;
    this.currentBlock = null;

    return irFunc;
  }

  /**
   * Generate IR for a statement
   */
  private generateStatement(stmt: TypedStatement): void {
    switch (stmt.kind) {
      case 'let': {
        const irType = this.convertType(stmt.type);
        // Allocate space on stack
        const ptr = this.newValue(IRTypes.ptr(irType), `${stmt.name}_ptr`);
        this.emit({ kind: 'alloc', result: ptr, allocatedType: irType });

        // Store initial value if provided
        if (stmt.initializer) {
          const value = this.generateExpression(stmt.initializer);
          this.emit({ kind: 'store', address: ptr, value });
        }

        this.symbolTable.set(stmt.name, ptr);
        break;
      }

      case 'assign': {
        const targetAddr = this.generateLValue(stmt.target);
        const value = this.generateExpression(stmt.value);
        this.emit({ kind: 'store', address: targetAddr, value });
        break;
      }

      case 'return': {
        const value = stmt.value ? this.generateExpression(stmt.value) : undefined;
        this.emit({ kind: 'return', value });
        break;
      }

      case 'if': {
        const condition = this.generateExpression(stmt.condition);
        const thenBlock = this.createBlock('if_then');
        const elseBlock = stmt.elseBody ? this.createBlock('if_else') : null;
        const mergeBlock = this.createBlock('if_merge');

        // Emit conditional jump
        this.emit({
          kind: 'condjump',
          condition,
          trueTarget: thenBlock.label,
          falseTarget: elseBlock ? elseBlock.label : mergeBlock.label,
        });

        // Generate then block
        this.switchToBlock(thenBlock);
        for (const s of stmt.thenBody) {
          this.generateStatement(s);
        }
        if (!this.blockEndsWithTerminator()) {
          this.emit({ kind: 'jump', target: mergeBlock.label });
        }

        // Generate else block if present
        if (elseBlock && stmt.elseBody) {
          this.switchToBlock(elseBlock);
          for (const s of stmt.elseBody) {
            this.generateStatement(s);
          }
          if (!this.blockEndsWithTerminator()) {
            this.emit({ kind: 'jump', target: mergeBlock.label });
          }
        }

        // Continue with merge block
        this.switchToBlock(mergeBlock);
        break;
      }

      case 'while': {
        const headerBlock = this.createBlock('while_header');
        const bodyBlock = this.createBlock('while_body');
        const exitBlock = this.createBlock('while_exit');

        // Jump to header
        this.emit({ kind: 'jump', target: headerBlock.label });

        // Generate header (condition check)
        this.switchToBlock(headerBlock);
        const condition = this.generateExpression(stmt.condition);
        this.emit({
          kind: 'condjump',
          condition,
          trueTarget: bodyBlock.label,
          falseTarget: exitBlock.label,
        });

        // Generate body
        this.switchToBlock(bodyBlock);
        for (const s of stmt.body) {
          this.generateStatement(s);
        }
        if (!this.blockEndsWithTerminator()) {
          this.emit({ kind: 'jump', target: headerBlock.label });
        }

        // Continue with exit
        this.switchToBlock(exitBlock);
        break;
      }

      case 'expression': {
        this.generateExpression(stmt.expression);
        break;
      }
    }
  }

  /**
   * Generate IR for an expression, returning the computed value
   */
  private generateExpression(expr: TypedExpression): IRValue {
    switch (expr.kind) {
      case 'number': {
        const result = this.newValue(this.convertType(expr.type));
        this.emit({ kind: 'const', result, value: expr.value });
        return result;
      }

      case 'boolean': {
        const result = this.newValue(IRTypes.bool());
        this.emit({ kind: 'const', result, value: expr.value });
        return result;
      }

      case 'string': {
        const result = this.newValue(IRTypes.ptr(IRTypes.i32())); // String as ptr to i32
        this.emit({ kind: 'const', result, value: expr.value });
        return result;
      }

      case 'identifier': {
        const ptr = this.symbolTable.get(expr.name);
        if (!ptr) {
          throw new Error(`Undefined variable: ${expr.name}`);
        }
        // Load the value from memory
        const result = this.newValue(this.convertType(expr.type));
        this.emit({ kind: 'load', result, address: ptr });
        return result;
      }

      case 'binary': {
        const left = this.generateExpression(expr.left);
        const right = this.generateExpression(expr.right);
        const result = this.newValue(this.convertType(expr.type));
        const op = this.convertBinOp(expr.op);
        this.emit({ kind: 'binop', result, op, left, right });
        return result;
      }

      case 'unary': {
        const operand = this.generateExpression(expr.operand);
        const result = this.newValue(this.convertType(expr.type));
        const op = this.convertUnaryOp(expr.op);
        this.emit({ kind: 'unaryop', result, op, operand });
        return result;
      }

      case 'call': {
        const args = expr.arguments.map((arg) => this.generateExpression(arg));
        const returnType = this.convertType(expr.type);
        const result = returnType.kind !== 'void' ? this.newValue(returnType) : undefined;
        this.emit({
          kind: 'call',
          result,
          functionName: expr.functionName,
          arguments: args,
        });
        return result || this.newValue(IRTypes.void());
      }

      case 'fieldAccess': {
        const objectAddr = this.generateLValue(expr.object);
        const objectType = expr.object.type;
        if (objectType.kind !== 'struct' || !objectType.structName) {
          throw new Error('Field access on non-struct type');
        }

        const structDef = this.structs.get(objectType.structName);
        if (!structDef) {
          throw new Error(`Unknown struct: ${objectType.structName}`);
        }

        const field = structDef.fields.find((f) => f.name === expr.field);
        if (!field) {
          throw new Error(`Unknown field: ${expr.field}`);
        }

        // Calculate field address
        const offsetValue = this.newValue(IRTypes.i32());
        this.emit({ kind: 'const', result: offsetValue, value: field.offset });

        const fieldPtr = this.newValue(IRTypes.ptr(field.type));
        this.emit({
          kind: 'getelementptr',
          result: fieldPtr,
          basePtr: objectAddr,
          indices: [offsetValue],
        });

        // Load field value
        const result = this.newValue(field.type);
        this.emit({ kind: 'load', result, address: fieldPtr });
        return result;
      }

      case 'structLiteral': {
        const structDef = this.structs.get(expr.structName);
        if (!structDef) {
          throw new Error(`Unknown struct: ${expr.structName}`);
        }

        // Allocate space for struct
        const structType = IRTypes.struct(expr.structName, structDef.size);
        const ptr = this.newValue(IRTypes.ptr(structType));
        this.emit({ kind: 'alloc', result: ptr, allocatedType: structType });

        // Store field values
        for (const [fieldName, fieldExpr] of expr.fields) {
          const field = structDef.fields.find((f) => f.name === fieldName);
          if (!field) {
            throw new Error(`Unknown field: ${fieldName}`);
          }

          const offsetValue = this.newValue(IRTypes.i32());
          this.emit({ kind: 'const', result: offsetValue, value: field.offset });

          const fieldPtr = this.newValue(IRTypes.ptr(field.type));
          this.emit({
            kind: 'getelementptr',
            result: fieldPtr,
            basePtr: ptr,
            indices: [offsetValue],
          });

          const fieldValue = this.generateExpression(fieldExpr);
          this.emit({ kind: 'store', address: fieldPtr, value: fieldValue });
        }

        // Load the struct as a value
        const result = this.newValue(structType);
        this.emit({ kind: 'load', result, address: ptr });
        return result;
      }

      default:
        throw new Error(`Unknown expression kind`);
    }
  }

  /**
   * Generate lvalue (address) for assignment targets
   */
  private generateLValue(expr: TypedExpression): IRValue {
    switch (expr.kind) {
      case 'identifier': {
        const ptr = this.symbolTable.get(expr.name);
        if (!ptr) {
          throw new Error(`Undefined variable: ${expr.name}`);
        }
        return ptr;
      }

      case 'fieldAccess': {
        const objectAddr = this.generateLValue(expr.object);
        const objectType = expr.object.type;
        if (objectType.kind !== 'struct' || !objectType.structName) {
          throw new Error('Field access on non-struct type');
        }

        const structDef = this.structs.get(objectType.structName);
        if (!structDef) {
          throw new Error(`Unknown struct: ${objectType.structName}`);
        }

        const field = structDef.fields.find((f) => f.name === expr.field);
        if (!field) {
          throw new Error(`Unknown field: ${expr.field}`);
        }

        const offsetValue = this.newValue(IRTypes.i32());
        this.emit({ kind: 'const', result: offsetValue, value: field.offset });

        const fieldPtr = this.newValue(IRTypes.ptr(field.type));
        this.emit({
          kind: 'getelementptr',
          result: fieldPtr,
          basePtr: objectAddr,
          indices: [offsetValue],
        });

        return fieldPtr;
      }

      default:
        throw new Error('Expression is not an lvalue');
    }
  }

  /**
   * Helper methods
   */

  private newValue(type: IRType, name?: string): IRValue {
    return {
      id: this.valueCounter++,
      type,
      name,
    };
  }

  private createBlock(hint: string): IRBlock {
    const block: IRBlock = {
      label: `${hint}_${this.blockCounter++}`,
      instructions: [],
      predecessors: [],
      successors: [],
    };
    this.currentFunction?.blocks.push(block);
    return block;
  }

  private switchToBlock(block: IRBlock): void {
    this.currentBlock = block;
  }

  private emit(instr: IRInstr): void {
    if (!this.currentBlock) {
      throw new Error('No current block to emit to');
    }
    this.currentBlock.instructions.push(instr);
  }

  private blockEndsWithTerminator(): boolean {
    if (!this.currentBlock || this.currentBlock.instructions.length === 0) {
      return false;
    }
    const last = this.currentBlock.instructions[this.currentBlock.instructions.length - 1];
    return last?.kind === 'return' || last?.kind === 'jump' || last?.kind === 'condjump';
  }

  private convertType(type: Type): IRType {
    switch (type.kind) {
      case 'i32':
        return IRTypes.i32();
      case 'i64':
        return IRTypes.i64();
      case 'f32':
        return IRTypes.f32();
      case 'f64':
        return IRTypes.f64();
      case 'bool':
        return IRTypes.bool();
      case 'void':
        return IRTypes.void();
      case 'ptr':
        return IRTypes.ptr(type.pointeeType ? this.convertType(type.pointeeType) : IRTypes.i32());
      case 'struct':
        if (!type.structName) {
          throw new Error('Struct type missing name');
        }
        const structDef = this.structs.get(type.structName);
        if (!structDef) {
          throw new Error(`Unknown struct: ${type.structName}`);
        }
        return IRTypes.struct(type.structName, structDef.size);
      default:
        throw new Error(`Unknown type kind: ${type}`);
    }
  }

  private convertBinOp(op: string): BinOpKind {
    const mapping: Record<string, BinOpKind> = {
      '+': BinOpKind.Add,
      '-': BinOpKind.Sub,
      '*': BinOpKind.Mul,
      '/': BinOpKind.Div,
      '%': BinOpKind.Mod,
      '==': BinOpKind.Eq,
      '!=': BinOpKind.Ne,
      '<': BinOpKind.Lt,
      '<=': BinOpKind.Le,
      '>': BinOpKind.Gt,
      '>=': BinOpKind.Ge,
      '&&': BinOpKind.And,
      '||': BinOpKind.Or,
      '&': BinOpKind.BitAnd,
      '|': BinOpKind.BitOr,
      '^': BinOpKind.BitXor,
      '<<': BinOpKind.Shl,
      '>>': BinOpKind.Shr,
    };
    const result = mapping[op];
    if (!result) {
      throw new Error(`Unknown binary operator: ${op}`);
    }
    return result;
  }

  private convertUnaryOp(op: string): UnaryOpKind {
    const mapping: Record<string, UnaryOpKind> = {
      '-': UnaryOpKind.Neg,
      '!': UnaryOpKind.Not,
      '~': UnaryOpKind.BitNot,
    };
    const result = mapping[op];
    if (!result) {
      throw new Error(`Unknown unary operator: ${op}`);
    }
    return result;
  }
}
