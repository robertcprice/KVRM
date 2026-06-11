"""Command-line entry point for the KVRM compiler."""

import argparse
import sys
from src.compiler import Compiler, CompileError


def _run_compile(args: argparse.Namespace) -> int:
    compiler = Compiler(debug=args.debug)
    try:
        assembly = compiler.compile_file(args.source)
    except FileNotFoundError:
        print(f"Error: file not found: {args.source}", file=sys.stderr)
        return 1
    except CompileError as exc:
        print(f"Compilation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - unexpected failures
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            with open(args.output, "w") as output_file:
                output_file.write(assembly)
        except OSError as exc:
            print(f"Failed to write output file '{args.output}': {exc}", file=sys.stderr)
            return 1
        print(f"Wrote assembly to {args.output}")
    else:
        print(assembly)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KVRM compiler CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser(
        "compile", help="Compile a .kvrm source file to assembly"
    )
    compile_parser.add_argument(
        "source", metavar="file.kvrm", help="Path to the KVRM source file"
    )
    compile_parser.add_argument(
        "-o", "--output", metavar="output.asm", help="Write assembly output to a file"
    )
    compile_parser.add_argument(
        "--debug", action="store_true", help="Enable debug output during compilation"
    )
    compile_parser.set_defaults(func=_run_compile)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
