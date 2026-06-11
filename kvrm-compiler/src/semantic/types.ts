/**
 * KVRM Type System
 *
 * Defines the type hierarchy for semantic analysis including:
 * - Primitive types (integers, floats, bool, char, str)
 * - Composite types (arrays, structs, enums, tuples)
 * - Function types
 * - Generic types with type parameters
 * - Type aliases
 */

export interface SourceLocation {
  line: number;
  column: number;
  file?: string;
}

/**
 * Base interface for all types in the KVRM type system
 */
export interface Type {
  kind: TypeKind;
  toString(): string;
  equals(other: Type): boolean;
  isAssignableTo(other: Type): boolean;
}

export enum TypeKind {
  Primitive = 'Primitive',
  Array = 'Array',
  Struct = 'Struct',
  Enum = 'Enum',
  Function = 'Function',
  Generic = 'Generic',
  GenericInstance = 'GenericInstance',
  TypeParameter = 'TypeParameter',
  Tuple = 'Tuple',
  Never = 'Never',
  Unknown = 'Unknown',
  Void = 'Void',
}

export enum PrimitiveTypeKind {
  I8 = 'i8',
  I16 = 'i16',
  I32 = 'i32',
  I64 = 'i64',
  U8 = 'u8',
  U16 = 'u16',
  U32 = 'u32',
  U64 = 'u64',
  F32 = 'f32',
  F64 = 'f64',
  Bool = 'bool',
  Char = 'char',
  Str = 'str',
}

/**
 * Primitive types: integers, floats, bool, char, str
 */
export class PrimitiveType implements Type {
  readonly kind = TypeKind.Primitive;

  constructor(public primitiveKind: PrimitiveTypeKind) {}

  toString(): string {
    return this.primitiveKind;
  }

  equals(other: Type): boolean {
    return (
      other.kind === TypeKind.Primitive &&
      (other as PrimitiveType).primitiveKind === this.primitiveKind
    );
  }

  isAssignableTo(other: Type): boolean {
    if (this.equals(other)) return true;

    // Allow implicit numeric conversions (widening only)
    if (other.kind === TypeKind.Primitive) {
      const otherPrim = other as PrimitiveType;
      return this.canWidenTo(otherPrim.primitiveKind);
    }

    return false;
  }

  private canWidenTo(target: PrimitiveTypeKind): boolean {
    const widenRules: Record<PrimitiveTypeKind, PrimitiveTypeKind[]> = {
      [PrimitiveTypeKind.I8]: [
        PrimitiveTypeKind.I16,
        PrimitiveTypeKind.I32,
        PrimitiveTypeKind.I64,
      ],
      [PrimitiveTypeKind.I16]: [PrimitiveTypeKind.I32, PrimitiveTypeKind.I64],
      [PrimitiveTypeKind.I32]: [PrimitiveTypeKind.I64],
      [PrimitiveTypeKind.I64]: [],
      [PrimitiveTypeKind.U8]: [
        PrimitiveTypeKind.U16,
        PrimitiveTypeKind.U32,
        PrimitiveTypeKind.U64,
      ],
      [PrimitiveTypeKind.U16]: [PrimitiveTypeKind.U32, PrimitiveTypeKind.U64],
      [PrimitiveTypeKind.U32]: [PrimitiveTypeKind.U64],
      [PrimitiveTypeKind.U64]: [],
      [PrimitiveTypeKind.F32]: [PrimitiveTypeKind.F64],
      [PrimitiveTypeKind.F64]: [],
      [PrimitiveTypeKind.Bool]: [],
      [PrimitiveTypeKind.Char]: [],
      [PrimitiveTypeKind.Str]: [],
    };

    return widenRules[this.primitiveKind]?.includes(target) ?? false;
  }

  isNumeric(): boolean {
    return (
      this.primitiveKind !== PrimitiveTypeKind.Bool &&
      this.primitiveKind !== PrimitiveTypeKind.Char &&
      this.primitiveKind !== PrimitiveTypeKind.Str
    );
  }

  isInteger(): boolean {
    return (
      this.isNumeric() &&
      this.primitiveKind !== PrimitiveTypeKind.F32 &&
      this.primitiveKind !== PrimitiveTypeKind.F64
    );
  }

  isFloat(): boolean {
    return (
      this.primitiveKind === PrimitiveTypeKind.F32 ||
      this.primitiveKind === PrimitiveTypeKind.F64
    );
  }

  isSigned(): boolean {
    return (
      this.primitiveKind === PrimitiveTypeKind.I8 ||
      this.primitiveKind === PrimitiveTypeKind.I16 ||
      this.primitiveKind === PrimitiveTypeKind.I32 ||
      this.primitiveKind === PrimitiveTypeKind.I64
    );
  }
}

/**
 * Array type: [T; N] where T is element type and N is optional size
 */
export class ArrayType implements Type {
  readonly kind = TypeKind.Array;

  constructor(
    public elementType: Type,
    public size?: number
  ) {}

  toString(): string {
    return this.size !== undefined
      ? `[${this.elementType.toString()}; ${this.size}]`
      : `[${this.elementType.toString()}]`;
  }

  equals(other: Type): boolean {
    if (other.kind !== TypeKind.Array) return false;
    const otherArr = other as ArrayType;
    return (
      this.elementType.equals(otherArr.elementType) &&
      this.size === otherArr.size
    );
  }

  isAssignableTo(other: Type): boolean {
    if (other.kind !== TypeKind.Array) return false;
    const otherArr = other as ArrayType;

    // Element types must be compatible
    if (!this.elementType.isAssignableTo(otherArr.elementType)) return false;

    // Sized array can assign to unsized array of same element type
    if (otherArr.size === undefined) return true;

    // Otherwise sizes must match
    return this.size === otherArr.size;
  }
}

/**
 * Struct field definition
 */
export interface StructField {
  name: string;
  type: Type;
  mutable: boolean;
  location: SourceLocation;
}

/**
 * Struct type with named fields
 */
export class StructType implements Type {
  readonly kind = TypeKind.Struct;

  constructor(
    public name: string,
    public fields: Map<string, StructField>,
    public typeParams: TypeParameter[] = []
  ) {}

  toString(): string {
    const params =
      this.typeParams.length > 0
        ? `<${this.typeParams.map((p) => p.toString()).join(', ')}>`
        : '';
    return `${this.name}${params}`;
  }

  equals(other: Type): boolean {
    // Structural equality for structs
    if (other.kind !== TypeKind.Struct) return false;
    const otherStruct = other as StructType;

    if (this.name !== otherStruct.name) return false;
    if (this.fields.size !== otherStruct.fields.size) return false;

    for (const [name, field] of this.fields) {
      const otherField = otherStruct.fields.get(name);
      if (!otherField || !field.type.equals(otherField.type)) return false;
    }

    return true;
  }

  isAssignableTo(other: Type): boolean {
    return this.equals(other);
  }

  getField(name: string): StructField | undefined {
    return this.fields.get(name);
  }

  hasField(name: string): boolean {
    return this.fields.has(name);
  }
}

/**
 * Enum variant definition
 */
export interface EnumVariant {
  name: string;
  associatedType?: Type;
  location: SourceLocation;
}

/**
 * Enum type with variants
 */
export class EnumType implements Type {
  readonly kind = TypeKind.Enum;

  constructor(
    public name: string,
    public variants: Map<string, EnumVariant>,
    public typeParams: TypeParameter[] = []
  ) {}

  toString(): string {
    const params =
      this.typeParams.length > 0
        ? `<${this.typeParams.map((p) => p.toString()).join(', ')}>`
        : '';
    return `${this.name}${params}`;
  }

  equals(other: Type): boolean {
    if (other.kind !== TypeKind.Enum) return false;
    const otherEnum = other as EnumType;
    return this.name === otherEnum.name;
  }

  isAssignableTo(other: Type): boolean {
    return this.equals(other);
  }

  getVariant(name: string): EnumVariant | undefined {
    return this.variants.get(name);
  }

  hasVariant(name: string): boolean {
    return this.variants.has(name);
  }
}

/**
 * Function type: fn(param1: T1, param2: T2) -> ReturnType
 */
export class FunctionType implements Type {
  readonly kind = TypeKind.Function;

  constructor(
    public paramTypes: Type[],
    public returnType: Type,
    public typeParams: TypeParameter[] = []
  ) {}

  toString(): string {
    const params =
      this.typeParams.length > 0
        ? `<${this.typeParams.map((p) => p.toString()).join(', ')}>`
        : '';
    const paramStr = this.paramTypes.map((t) => t.toString()).join(', ');
    return `fn${params}(${paramStr}) -> ${this.returnType.toString()}`;
  }

  equals(other: Type): boolean {
    if (other.kind !== TypeKind.Function) return false;
    const otherFn = other as FunctionType;

    if (this.paramTypes.length !== otherFn.paramTypes.length) return false;
    if (!this.returnType.equals(otherFn.returnType)) return false;

    for (let i = 0; i < this.paramTypes.length; i++) {
      if (!this.paramTypes[i].equals(otherFn.paramTypes[i])) return false;
    }

    return true;
  }

  isAssignableTo(other: Type): boolean {
    if (other.kind !== TypeKind.Function) return false;
    const otherFn = other as FunctionType;

    // Function types are assignable if they're compatible (contravariant params, covariant return)
    if (this.paramTypes.length !== otherFn.paramTypes.length) return false;

    // Parameters are contravariant
    for (let i = 0; i < this.paramTypes.length; i++) {
      if (!otherFn.paramTypes[i].isAssignableTo(this.paramTypes[i]))
        return false;
    }

    // Return type is covariant
    return this.returnType.isAssignableTo(otherFn.returnType);
  }
}

/**
 * Type parameter for generics
 */
export class TypeParameter implements Type {
  readonly kind = TypeKind.TypeParameter;

  constructor(
    public name: string,
    public bounds: Type[] = []
  ) {}

  toString(): string {
    if (this.bounds.length === 0) return this.name;
    return `${this.name}: ${this.bounds.map((b) => b.toString()).join(' + ')}`;
  }

  equals(other: Type): boolean {
    if (other.kind !== TypeKind.TypeParameter) return false;
    return (other as TypeParameter).name === this.name;
  }

  isAssignableTo(other: Type): boolean {
    // Type parameters are only assignable to themselves or their bounds
    if (this.equals(other)) return true;

    for (const bound of this.bounds) {
      if (bound.isAssignableTo(other)) return true;
    }

    return false;
  }
}

/**
 * Generic instance type (e.g., Vec<i32>)
 */
export class GenericInstanceType implements Type {
  readonly kind = TypeKind.GenericInstance;

  constructor(
    public baseType: Type,
    public typeArgs: Type[]
  ) {}

  toString(): string {
    const args = this.typeArgs.map((t) => t.toString()).join(', ');
    return `${this.baseType.toString()}<${args}>`;
  }

  equals(other: Type): boolean {
    if (other.kind !== TypeKind.GenericInstance) return false;
    const otherGen = other as GenericInstanceType;

    if (!this.baseType.equals(otherGen.baseType)) return false;
    if (this.typeArgs.length !== otherGen.typeArgs.length) return false;

    for (let i = 0; i < this.typeArgs.length; i++) {
      if (!this.typeArgs[i].equals(otherGen.typeArgs[i])) return false;
    }

    return true;
  }

  isAssignableTo(other: Type): boolean {
    return this.equals(other);
  }
}

/**
 * Tuple type: (T1, T2, ...)
 */
export class TupleType implements Type {
  readonly kind = TypeKind.Tuple;

  constructor(public elementTypes: Type[]) {}

  toString(): string {
    return `(${this.elementTypes.map((t) => t.toString()).join(', ')})`;
  }

  equals(other: Type): boolean {
    if (other.kind !== TypeKind.Tuple) return false;
    const otherTuple = other as TupleType;

    if (this.elementTypes.length !== otherTuple.elementTypes.length)
      return false;

    for (let i = 0; i < this.elementTypes.length; i++) {
      if (!this.elementTypes[i].equals(otherTuple.elementTypes[i]))
        return false;
    }

    return true;
  }

  isAssignableTo(other: Type): boolean {
    if (other.kind !== TypeKind.Tuple) return false;
    const otherTuple = other as TupleType;

    if (this.elementTypes.length !== otherTuple.elementTypes.length)
      return false;

    for (let i = 0; i < this.elementTypes.length; i++) {
      if (!this.elementTypes[i].isAssignableTo(otherTuple.elementTypes[i]))
        return false;
    }

    return true;
  }
}

/**
 * Void type for functions that don't return a value
 */
export class VoidType implements Type {
  readonly kind = TypeKind.Void;

  toString(): string {
    return 'void';
  }

  equals(other: Type): boolean {
    return other.kind === TypeKind.Void;
  }

  isAssignableTo(other: Type): boolean {
    return other.kind === TypeKind.Void;
  }
}

/**
 * Never type for expressions that never complete normally
 */
export class NeverType implements Type {
  readonly kind = TypeKind.Never;

  toString(): string {
    return 'never';
  }

  equals(other: Type): boolean {
    return other.kind === TypeKind.Never;
  }

  isAssignableTo(other: Type): boolean {
    // Never is assignable to all types (bottom type)
    return true;
  }
}

/**
 * Unknown type for error recovery
 */
export class UnknownType implements Type {
  readonly kind = TypeKind.Unknown;

  toString(): string {
    return 'unknown';
  }

  equals(other: Type): boolean {
    return other.kind === TypeKind.Unknown;
  }

  isAssignableTo(other: Type): boolean {
    // Unknown is compatible with everything for error recovery
    return true;
  }
}

/**
 * Singleton instances for common types
 */
export const BuiltinTypes = {
  i8: new PrimitiveType(PrimitiveTypeKind.I8),
  i16: new PrimitiveType(PrimitiveTypeKind.I16),
  i32: new PrimitiveType(PrimitiveTypeKind.I32),
  i64: new PrimitiveType(PrimitiveTypeKind.I64),
  u8: new PrimitiveType(PrimitiveTypeKind.U8),
  u16: new PrimitiveType(PrimitiveTypeKind.U16),
  u32: new PrimitiveType(PrimitiveTypeKind.U32),
  u64: new PrimitiveType(PrimitiveTypeKind.U64),
  f32: new PrimitiveType(PrimitiveTypeKind.F32),
  f64: new PrimitiveType(PrimitiveTypeKind.F64),
  bool: new PrimitiveType(PrimitiveTypeKind.Bool),
  char: new PrimitiveType(PrimitiveTypeKind.Char),
  str: new PrimitiveType(PrimitiveTypeKind.Str),
  void: new VoidType(),
  never: new NeverType(),
  unknown: new UnknownType(),
};

/**
 * Type utilities
 */
export class TypeUtils {
  static isPrimitive(type: Type): type is PrimitiveType {
    return type.kind === TypeKind.Primitive;
  }

  static isArray(type: Type): type is ArrayType {
    return type.kind === TypeKind.Array;
  }

  static isStruct(type: Type): type is StructType {
    return type.kind === TypeKind.Struct;
  }

  static isEnum(type: Type): type is EnumType {
    return type.kind === TypeKind.Enum;
  }

  static isFunction(type: Type): type is FunctionType {
    return type.kind === TypeKind.Function;
  }

  static isNumeric(type: Type): boolean {
    return (
      TypeUtils.isPrimitive(type) &&
      (type as PrimitiveType).isNumeric()
    );
  }

  static isInteger(type: Type): boolean {
    return (
      TypeUtils.isPrimitive(type) &&
      (type as PrimitiveType).isInteger()
    );
  }

  static isFloat(type: Type): boolean {
    return (
      TypeUtils.isPrimitive(type) &&
      (type as PrimitiveType).isFloat()
    );
  }

  /**
   * Get the common supertype of two types, if one exists
   */
  static getCommonType(t1: Type, t2: Type): Type | null {
    if (t1.equals(t2)) return t1;
    if (t1.isAssignableTo(t2)) return t2;
    if (t2.isAssignableTo(t1)) return t1;

    // For numeric types, find common widened type
    if (TypeUtils.isPrimitive(t1) && TypeUtils.isPrimitive(t2)) {
      const p1 = t1 as PrimitiveType;
      const p2 = t2 as PrimitiveType;

      if (p1.isNumeric() && p2.isNumeric()) {
        return TypeUtils.widenNumericTypes(p1, p2);
      }
    }

    return null;
  }

  private static widenNumericTypes(
    t1: PrimitiveType,
    t2: PrimitiveType
  ): Type | null {
    // Both floats -> use wider float
    if (t1.isFloat() && t2.isFloat()) {
      return t1.primitiveKind === PrimitiveTypeKind.F64 ||
        t2.primitiveKind === PrimitiveTypeKind.F64
        ? BuiltinTypes.f64
        : BuiltinTypes.f32;
    }

    // One float -> use float
    if (t1.isFloat()) return t1;
    if (t2.isFloat()) return t2;

    // Both integers -> use wider integer preserving signedness
    const signed = t1.isSigned() || t2.isSigned();
    const size = Math.max(
      TypeUtils.getTypeSize(t1),
      TypeUtils.getTypeSize(t2)
    );

    if (signed) {
      if (size <= 8) return BuiltinTypes.i8;
      if (size <= 16) return BuiltinTypes.i16;
      if (size <= 32) return BuiltinTypes.i32;
      return BuiltinTypes.i64;
    } else {
      if (size <= 8) return BuiltinTypes.u8;
      if (size <= 16) return BuiltinTypes.u16;
      if (size <= 32) return BuiltinTypes.u32;
      return BuiltinTypes.u64;
    }
  }

  private static getTypeSize(type: PrimitiveType): number {
    const sizeMap: Record<PrimitiveTypeKind, number> = {
      [PrimitiveTypeKind.I8]: 8,
      [PrimitiveTypeKind.I16]: 16,
      [PrimitiveTypeKind.I32]: 32,
      [PrimitiveTypeKind.I64]: 64,
      [PrimitiveTypeKind.U8]: 8,
      [PrimitiveTypeKind.U16]: 16,
      [PrimitiveTypeKind.U32]: 32,
      [PrimitiveTypeKind.U64]: 64,
      [PrimitiveTypeKind.F32]: 32,
      [PrimitiveTypeKind.F64]: 64,
      [PrimitiveTypeKind.Bool]: 1,
      [PrimitiveTypeKind.Char]: 32,
      [PrimitiveTypeKind.Str]: 0,
    };

    return sizeMap[type.primitiveKind] ?? 0;
  }
}
