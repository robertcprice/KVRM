from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .demo import DOMAIN_CONFIG, load_domain_training_artifact_summary


PIPELINE_DOMAINS = tuple(DOMAIN_CONFIG.keys())


@dataclass(frozen=True)
class OperatorRefreshStep:
    key: str
    label: str
    command: list[str]
    domain: str | None = None


def resolve_operator_pipeline_domains(
    repo_root: str | Path,
    *,
    domains: list[str] | tuple[str, ...] | None = None,
    stale_only: bool = False,
) -> list[str]:
    selected_domains = list(domains) if domains else list(PIPELINE_DOMAINS)
    invalid_domains = [domain for domain in selected_domains if domain not in DOMAIN_CONFIG]
    if invalid_domains:
        raise ValueError(f"unsupported domains: {', '.join(invalid_domains)}")
    if not stale_only:
        return selected_domains
    return [
        domain
        for domain in selected_domains
        if load_domain_training_artifact_summary(repo_root, domain).get("status") != "ready"
    ]


def build_operator_refresh_plan(
    repo_root: str | Path,
    *,
    domains: list[str] | tuple[str, ...] | None = None,
    stale_only: bool = False,
    include_benchmark: bool = True,
    include_report_refresh: bool = True,
) -> list[OperatorRefreshStep]:
    root = Path(repo_root)
    resolved_domains = resolve_operator_pipeline_domains(
        root,
        domains=domains,
        stale_only=stale_only,
    )
    steps: list[OperatorRefreshStep] = []
    for domain in resolved_domains:
        steps.append(
            OperatorRefreshStep(
                key=f"train:{domain}",
                label=f"Train {domain.upper()} compact model",
                command=_train_command(root, domain),
                domain=domain,
            )
        )
        if include_benchmark:
            steps.append(
                OperatorRefreshStep(
                    key=f"benchmark:{domain}",
                    label=f"Benchmark {domain.upper()} demo",
                    command=_benchmark_command(root, domain),
                    domain=domain,
                )
            )
    if include_report_refresh and resolved_domains:
        steps.append(
            OperatorRefreshStep(
                key="compare",
                label="Refresh demo comparison report",
                command=["python3", "kvrm-demos/compare_demos.py"],
            )
        )
    return steps


def build_operator_environment(
    repo_root: str | Path,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    root = Path(repo_root)
    env = dict(base_env or os.environ)
    existing = env.get("PYTHONPATH")
    if existing:
        env["PYTHONPATH"] = existing
    return env


def run_operator_refresh_plan(
    repo_root: str | Path,
    steps: list[OperatorRefreshStep],
    *,
    env: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    root = Path(repo_root)
    run_env = build_operator_environment(root, env)
    completed: list[dict[str, object]] = []
    for index, step in enumerate(steps, start=1):
        print(f"==> [{index}/{len(steps)}] {step.label}")
        print(f"$ {' '.join(step.command)}")
        result = subprocess.run(step.command, cwd=root, env=run_env)
        completed.append(
            {
                "key": step.key,
                "label": step.label,
                "domain": step.domain,
                "command": step.command,
                "returncode": result.returncode,
            }
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, step.command)
    return completed


def _domain_root(repo_root: Path, domain: str) -> Path:
    return (repo_root / DOMAIN_CONFIG[domain]["data_dir"]).parent


def _benchmark_command(repo_root: Path, domain: str) -> list[str]:
    return ["python3", str(_domain_root(repo_root, domain) / "scripts" / "run_benchmark.py")]


def _train_command(repo_root: Path, domain: str) -> list[str]:
    data_dir = repo_root / DOMAIN_CONFIG[domain]["data_dir"]
    return [
        "python3",
        "scripts/train_kvrm_model.py",
        "--domain",
        domain,
        "--registry",
        str(data_dir / "registry.json"),
        "--train-cases",
        str(data_dir / "train_cases.jsonl"),
        "--eval-cases",
        str(data_dir / "cases.jsonl"),
        "--output-model",
        str(repo_root / "kvrm-models" / f"{domain}_compact_selector_v1.joblib"),
        "--output-report",
        str(repo_root / "kvrm-bench" / "results" / f"{domain}_compact_training_report_v1.json"),
    ]
