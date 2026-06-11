/**
 * KVRM Code Generator Module
 * Exports all code generation components
 */

// Main code generator (works with existing IR)
export { KVRMCodeGenerator, generateCode } from './codegen.js';

// Advanced code generator (three-address code)
export { CodeGenerator, generateAssembly, generateWithStats } from './generator.js';
export type { CodeGenOptions, CodeGenStats } from './generator.js';

// Register allocation
export { RegisterAllocator, KVRMRegister, REGISTER_NAMES } from './register-allocator.js';
export type { RegisterAssignment } from './register-allocator.js';

// Instruction selection
export { InstructionSelector, AddressingMode } from './instruction-selector.js';
export type { KVRMInstruction } from './instruction-selector.js';

// Assembly emission
export { AssemblyEmitter, AsmSection } from './asm-emitter.js';
export type { AsmDirective, AsmLabel, AsmData, AsmLine, FormatOptions } from './asm-emitter.js';
