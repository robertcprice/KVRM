"""Static verification of a KVRM action registry (the ``kvrm verify`` tool).

Where ``kvrm validate`` checks structure and schema, ``kvrm verify`` reasons about
*meaning*: it compiles every action's ``support_spec`` to an SMT formula over the
registry's typed context schema and uses Z3 to answer questions a registry author
cannot answer by eye, before anything is deployed:

  * DISJOINTNESS  -- are the envelopes of the primary (non-fallback) actions
    pairwise disjoint?  For each pair we check satisfiability of (phi_i AND phi_j):
    UNSAT proves the envelopes never co-fire anywhere in the typed input space;
    SAT returns a concrete witness input that lies in both (an OVERLAP region
    where preference, not the gate, decides -- see KVRM's admissibility/preference
    split). Overlaps are reported as INFO, not errors: they are expected and are
    where the calibrated/conformal disambiguation layer applies.

  * FAIL-CLOSURE GAPS -- envelopes that use negation (not / neq / not_in /
    not_exists) or existence (exists / not_exists) operators can be satisfied by
    out-of-schema or missing values, so malformed inputs are NOT guaranteed to
    fail closed by the support-spec validator alone. These are WARNINGs. (The
    unknown-extra-feature case is reported separately: a spec ignores features it
    does not name, so schema validation must run in the validator to close it.)

  * DEAD ACTIONS -- an envelope that is UNSAT under the schema bounds can never be
    selected (a specification bug). ERROR.

  * UNDECLARED FEATURES -- a spec references a feature absent from
    ``context_schema``. ERROR.

  * ORDINAL-ON-ENUM -- a numeric comparison (gt/lt/...) applied to an enum/string
    feature (almost always a modeling mistake). WARNING.

  * COVERAGE (optional, --coverage) -- whether schema-valid inputs exist that
    satisfy no envelope (an abstention region). For a fail-closed system this is
    expected, so it is reported as INFO.

The verifier reads ``registry.json`` directly and depends only on the standard
library and ``z3-solver``; it does not import the rest of ``kvrm_core``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

try:
    import z3
except ImportError:  # z3-solver is an optional extra: pip install 'kvrm-core[verify]'
    z3 = None  # type: ignore[assignment]

__all__ = [
    "Finding",
    "VerificationReport",
    "verify_registry_dict",
    "verify_registry_file",
    "render_report_text",
    "main",
]

NEGATION_OPS = {"neq", "not_in", "not_exists", "not"}
EXISTENCE_OPS = {"exists", "not_exists"}
NUMERIC_OPS = {"gt", "gte", "lt", "lte"}
DEFAULT_FALLBACK_TAGS = frozenset({"fallback", "handoff"})

SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


# --------------------------------------------------------------------------
# Report types
# --------------------------------------------------------------------------

@dataclasses.dataclass
class Finding:
    severity: str          # ERROR | WARNING | INFO
    code: str              # machine-readable, e.g. "overlap", "dead_action"
    message: str           # human-readable one-liner
    detail: dict = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class VerificationReport:
    registry_name: str | None
    version: str | None
    n_actions: int
    primary_actions: list[str]
    fallback_actions: list[str]
    actions_without_spec: list[str]
    findings: list[Finding]

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARNING")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "INFO")

    def passed(self, *, strict: bool = False) -> bool:
        if self.error_count:
            return False
        if strict and self.warning_count:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "registry_name": self.registry_name,
            "version": self.version,
            "n_actions": self.n_actions,
            "primary_actions": self.primary_actions,
            "fallback_actions": self.fallback_actions,
            "actions_without_spec": self.actions_without_spec,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "findings": [f.to_dict() for f in self.findings],
        }


# --------------------------------------------------------------------------
# Spec scanning
# --------------------------------------------------------------------------

def _walk(node: Any, ops: set, leaves: list) -> None:
    if not isinstance(node, dict):
        return
    if "feature" in node:
        ops.add(node.get("op"))
        leaves.append(node)
        return
    for key in ("all", "any"):
        if key in node:
            ops.add(key)
            for child in node[key]:
                _walk(child, ops, leaves)
            return
    if "not" in node:
        ops.add("not")
        _walk(node["not"], ops, leaves)


def _scan(spec: Any) -> tuple[set, list]:
    ops: set = set()
    leaves: list = []
    _walk(spec, ops, leaves)
    return ops, leaves


def _is_fallback(action: dict, fallback_tags: frozenset) -> bool:
    return bool({str(t).lower() for t in action.get("tags", [])} & fallback_tags)


# --------------------------------------------------------------------------
# Z3 compilation
# --------------------------------------------------------------------------

class _Compiler:
    """Compile support-spec trees to Z3 constraints under a typed schema."""

    def __init__(self, schema: dict):
        self.schema = schema or {}
        self.vars: dict[str, Any] = {}
        self.enum_index: dict[str, dict] = {}
        self.kind: dict[str, str] = {}
        self.bounds: list = []
        self.undeclared: set = set()
        self.ordinal_on_enum: set = set()

    def var(self, feature: str):
        if feature in self.vars:
            return self.vars[feature]
        spec = self.schema.get(feature)
        if spec is None:
            v = z3.Int(f"u_{feature}")
            self.kind[feature] = "unknown"
            self.undeclared.add(feature)
        elif spec.get("enum"):
            enum = spec["enum"]
            v = z3.Int(f"e_{feature}")
            self.enum_index[feature] = {val: i for i, val in enumerate(enum)}
            self.bounds.append(z3.And(v >= 0, v < len(enum)))
            self.kind[feature] = "enum"
        elif spec.get("type") == "boolean":
            v = z3.Bool(f"b_{feature}")
            self.kind[feature] = "bool"
        elif spec.get("type") in ("number", "integer"):
            v = z3.Int(f"n_{feature}") if spec.get("type") == "integer" else z3.Real(f"n_{feature}")
            if "minimum" in spec:
                self.bounds.append(v >= spec["minimum"])
            if "maximum" in spec:
                self.bounds.append(v <= spec["maximum"])
            self.kind[feature] = "num"
        else:
            v = z3.Int(f"x_{feature}")
            self.kind[feature] = "unknown"
        self.vars[feature] = v
        return v

    def _mapped(self, feature: str, value: Any):
        if self.kind.get(feature) == "enum":
            return self.enum_index[feature].get(value)  # may be None (out-of-enum)
        return value

    def leaf(self, node: dict):
        feature, op = node["feature"], node["op"]
        v = self.var(feature)
        kind = self.kind[feature]
        if op == "exists":
            return z3.BoolVal(True)
        if op == "not_exists":
            return z3.BoolVal(False)
        if op in NUMERIC_OPS and kind == "enum":
            self.ordinal_on_enum.add((feature, op))
        if op == "eq":
            m = self._mapped(feature, node.get("value"))
            if kind == "enum" and m is None:
                return z3.BoolVal(False)
            if kind == "bool":
                return v if node.get("value") else z3.Not(v)
            return v == m
        if op == "neq":
            m = self._mapped(feature, node.get("value"))
            if kind == "enum" and m is None:
                return z3.BoolVal(True)
            if kind == "bool":
                return z3.Not(v) if node.get("value") else v
            return v != m
        if op == "in":
            vals = [self._mapped(feature, x) for x in node.get("value", [])]
            vals = [x for x in vals if x is not None]
            return z3.Or(*[v == x for x in vals]) if vals else z3.BoolVal(False)
        if op == "not_in":
            vals = [self._mapped(feature, x) for x in node.get("value", [])]
            vals = [x for x in vals if x is not None]
            return z3.And(*[v != x for x in vals]) if vals else z3.BoolVal(True)
        if op == "gt":
            return v > self._mapped(feature, node.get("value"))
        if op == "gte":
            return v >= self._mapped(feature, node.get("value"))
        if op == "lt":
            return v < self._mapped(feature, node.get("value"))
        if op == "lte":
            return v <= self._mapped(feature, node.get("value"))
        raise ValueError(f"unknown op: {op!r}")

    def build(self, node: Any):
        if node is None:
            return z3.BoolVal(True)
        if not isinstance(node, dict):
            raise ValueError(f"malformed support_spec node: {node!r}")
        if "feature" in node:
            return self.leaf(node)
        if "all" in node:
            return z3.And(*[self.build(c) for c in node["all"]])
        if "any" in node:
            return z3.Or(*[self.build(c) for c in node["any"]])
        if "not" in node:
            return z3.Not(self.build(node["not"]))
        raise ValueError(f"malformed support_spec node: {node!r}")

    def decode(self, model) -> dict:
        out = {}
        for feature, v in self.vars.items():
            try:
                val = model.eval(v, model_completion=True)
            except z3.Z3Exception:
                continue
            if self.kind.get(feature) == "enum":
                inv = {i: k for k, i in self.enum_index[feature].items()}
                try:
                    out[feature] = inv.get(val.as_long(), str(val))
                except Exception:
                    out[feature] = str(val)
            elif self.kind.get(feature) == "bool":
                out[feature] = bool(z3.is_true(val))
            else:
                out[feature] = str(val)
        return out


def _sat(constraints: list, bounds: list):
    s = z3.Solver()
    for b in bounds:
        s.add(b)
    for c in constraints:
        s.add(c)
    return s.check()


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------

def verify_registry_dict(
    registry: dict,
    *,
    coverage: bool = False,
    fallback_tags: frozenset = DEFAULT_FALLBACK_TAGS,
) -> VerificationReport:
    if z3 is None:
        raise RuntimeError(
            "kvrm verify requires the optional 'z3-solver' dependency: "
            "pip install 'kvrm-core[verify]'"
        )
    schema = registry.get("context_schema", {}) or {}
    all_actions = registry.get("actions", []) or []
    with_spec = [a for a in all_actions if a.get("support_spec") is not None]
    without_spec = [a["action_id"] for a in all_actions if a.get("support_spec") is None]

    fallback_ids = sorted(a["action_id"] for a in all_actions if _is_fallback(a, fallback_tags))
    fb_set = set(fallback_ids)
    primaries = [a for a in with_spec if a["action_id"] not in fb_set]
    primary_ids = sorted(a["action_id"] for a in primaries)

    findings: list[Finding] = []

    # ---- per-action operator scan + dead-action + structural checks ----
    negation_actions: list[str] = []
    existence_actions: list[str] = []
    for a in with_spec:
        aid = a["action_id"]
        ops, leaves = _scan(a["support_spec"])
        if ops & NEGATION_OPS:
            negation_actions.append(aid)
        if ops & EXISTENCE_OPS:
            existence_actions.append(aid)

        comp = _Compiler(schema)
        try:
            phi = comp.build(a["support_spec"])
        except ValueError as exc:
            findings.append(Finding("ERROR", "malformed_spec",
                                    f"action {aid!r}: {exc}", {"action": aid}))
            continue

        if comp.undeclared:
            findings.append(Finding(
                "ERROR", "undeclared_feature",
                f"action {aid!r} references features not in context_schema: "
                f"{sorted(comp.undeclared)}",
                {"action": aid, "features": sorted(comp.undeclared)}))
        if comp.ordinal_on_enum:
            findings.append(Finding(
                "WARNING", "ordinal_on_enum",
                f"action {aid!r} applies a numeric comparison to an enum feature: "
                f"{sorted(comp.ordinal_on_enum)}",
                {"action": aid, "pairs": sorted(list(comp.ordinal_on_enum))}))

        if _sat([phi], comp.bounds) == z3.unsat:
            findings.append(Finding(
                "ERROR", "dead_action",
                f"action {aid!r} has an unsatisfiable envelope (can never be selected)",
                {"action": aid}))

    # ---- actions without a support_spec ----
    for aid in without_spec:
        if aid in fb_set:
            findings.append(Finding(
                "INFO", "catch_all_fallback",
                f"fallback action {aid!r} has no support_spec (matches every input by design)",
                {"action": aid}))
        else:
            findings.append(Finding(
                "ERROR", "primary_without_spec",
                f"primary action {aid!r} has no support_spec (would accept any input)",
                {"action": aid}))

    # ---- fail-closure caveats ----
    if negation_actions:
        findings.append(Finding(
            "WARNING", "negation_failclosure",
            "negation operators (not/neq/not_in/not_exists) can be satisfied by "
            "out-of-schema or missing values; malformed inputs are not guaranteed "
            "to fail closed by the support-spec validator alone in: "
            f"{sorted(negation_actions)}. Enforce the context schema in the validator.",
            {"actions": sorted(negation_actions)}))
    if existence_actions:
        findings.append(Finding(
            "WARNING", "existence_failclosure",
            "existence operators (exists/not_exists) interact with missing features; "
            f"verify fail-closure behavior for: {sorted(existence_actions)}",
            {"actions": sorted(existence_actions)}))
    # The unknown-extra-feature gap is architectural, not per-spec: always surface it.
    findings.append(Finding(
        "INFO", "schema_enforcement_note",
        "support specs ignore features they do not name; an input carrying an "
        "unknown extra feature can satisfy an envelope. Context-schema validation "
        "(enum/type/required/unknown) must run in the validator to guarantee "
        "fail-closure for any selector.",
        {}))

    # ---- pairwise disjointness among primaries ----
    n_overlap = 0
    for i in range(len(primaries)):
        for j in range(i + 1, len(primaries)):
            ai, aj = primaries[i], primaries[j]
            comp = _Compiler(schema)
            try:
                ci = comp.build(ai["support_spec"])
                cj = comp.build(aj["support_spec"])
            except ValueError:
                continue  # malformed spec already reported above
            res = _sat([ci, cj], comp.bounds)
            if res == z3.sat:
                n_overlap += 1
                witness = comp.decode(
                    _solver_model([ci, cj], comp.bounds))
                findings.append(Finding(
                    "INFO", "overlap",
                    f"envelopes of {ai['action_id']!r} and {aj['action_id']!r} overlap "
                    "(both admissible for some input -> disambiguation region)",
                    {"pair": [ai["action_id"], aj["action_id"]], "witness": witness}))
            elif res == z3.unknown:
                findings.append(Finding(
                    "WARNING", "overlap_unknown",
                    f"Z3 could not decide disjointness of {ai['action_id']!r} and "
                    f"{aj['action_id']!r}",
                    {"pair": [ai["action_id"], aj["action_id"]]}))

    findings.append(Finding(
        "INFO", "disjointness_summary",
        f"{len(primary_ids)} primary actions; "
        f"{'pairwise disjoint' if n_overlap == 0 else str(n_overlap) + ' overlapping pair(s)'}",
        {"n_primary": len(primary_ids), "n_overlap": n_overlap}))

    # ---- optional coverage / abstention region ----
    if coverage and with_spec:
        comp = _Compiler(schema)
        try:
            disj = z3.Or(*[comp.build(a["support_spec"]) for a in with_spec])
            res = _sat([z3.Not(disj)], comp.bounds)
            if res == z3.sat:
                witness = comp.decode(_solver_model([z3.Not(disj)], comp.bounds))
                findings.append(Finding(
                    "INFO", "abstention_region",
                    "schema-valid inputs exist that satisfy no envelope (these abstain "
                    "-- expected for a fail-closed system)",
                    {"witness": witness}))
            elif res == z3.unsat:
                findings.append(Finding(
                    "INFO", "full_coverage",
                    "every schema-valid input satisfies at least one envelope "
                    "(no abstention region)", {}))
        except ValueError:
            pass

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.code))
    return VerificationReport(
        registry_name=registry.get("registry_name"),
        version=registry.get("version"),
        n_actions=len(all_actions),
        primary_actions=primary_ids,
        fallback_actions=fallback_ids,
        actions_without_spec=without_spec,
        findings=findings,
    )


def _solver_model(constraints: list, bounds: list):
    s = z3.Solver()
    for b in bounds:
        s.add(b)
    for c in constraints:
        s.add(c)
    s.check()
    return s.model()


def verify_registry_file(path: str | Path, **kwargs) -> VerificationReport:
    """Verify a registry given a path to ``registry.json`` or a domain directory."""
    p = Path(path)
    if p.is_dir():
        p = p / "registry.json"
    if not p.is_file():
        raise FileNotFoundError(f"no registry.json at {p}")
    registry = json.loads(p.read_text(encoding="utf-8"))
    return verify_registry_dict(registry, **kwargs)


# --------------------------------------------------------------------------
# Rendering + CLI
# --------------------------------------------------------------------------

_SEVERITY_TAG = {"ERROR": "ERROR  ", "WARNING": "WARN   ", "INFO": "info   "}


def render_report_text(report: VerificationReport) -> str:
    lines = [
        f"registry   : {report.registry_name} v{report.version}",
        f"actions    : {report.n_actions} "
        f"({len(report.primary_actions)} primary, {len(report.fallback_actions)} fallback)",
        f"summary    : {report.error_count} error(s), "
        f"{report.warning_count} warning(s), {report.info_count} info",
        "",
    ]
    for f in report.findings:
        lines.append(f"{_SEVERITY_TAG[f.severity]} [{f.code}] {f.message}")
        if f.code == "overlap":
            lines.append(f"           witness: {json.dumps(f.detail['witness'])}")
    verdict = "PASS" if report.passed() else "FAIL"
    lines.append("")
    lines.append(f"verdict    : {verdict}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kvrm verify",
        description="SMT verification of a KVRM action registry "
                    "(disjointness, fail-closure gaps, dead actions).",
    )
    parser.add_argument("domain_dir", help="domain directory or path to registry.json")
    parser.add_argument("--json", action="store_true", help="emit the JSON report")
    parser.add_argument("--strict", action="store_true",
                        help="exit nonzero on warnings as well as errors")
    parser.add_argument("--coverage", action="store_true",
                        help="also check for an abstention region (schema-valid, no envelope)")
    args = parser.parse_args(argv)

    try:
        report = verify_registry_file(args.domain_dir, coverage=args.coverage)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_report_text(report))
    return 0 if report.passed(strict=args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
