from __future__ import annotations

import curses
import os
import queue
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent

from kvrm_bench.dashboard import load_dashboard_snapshot
from kvrm_bench.demo import (
    DRAFT_FILTERS,
    DRAFT_SORTS,
    DOMAIN_CONFIG,
    append_case_draft,
    available_demo_case_files,
    build_case_review_queue,
    clear_demo_caches,
    export_selected_draft_cases,
    find_adjacent_draft_group_index,
    load_domain_action_ids,
    load_domain_artifact_summary,
    load_domain_training_artifact_summary,
    promote_ready_draft_cases,
    promote_draft_case,
    run_draft_case_matrix,
    run_demo_case_matrix,
    run_incident_replay_episode_matrix,
    update_draft_case,
    update_selected_draft_cases,
    write_draft_export_manifest,
)


TRAINED_MODEL_PATHS = {
    "soc": REPO_ROOT / "kvrm-models" / "soc_compact_selector_v1.joblib",
    "sre": REPO_ROOT / "kvrm-models" / "sre_compact_selector_v1.joblib",
    "drone": REPO_ROOT / "kvrm-models" / "drone_compact_selector_v1.joblib",
    "grid": REPO_ROOT / "kvrm-models" / "grid_compact_selector_v1.joblib",
    "finance": REPO_ROOT / "kvrm-models" / "finance_compact_selector_v1.joblib",
    "medical": REPO_ROOT / "kvrm-models" / "medical_compact_selector_v1.joblib",
    "iam": REPO_ROOT / "kvrm-models" / "iam_compact_selector_v1.joblib",
}

DEMO_DOMAINS = ["soc", "sre", "drone", "grid", "finance", "medical", "iam"]


def _domain_data_dir(domain: str) -> Path:
    return Path(DOMAIN_CONFIG[domain]["data_dir"])


def _domain_root(domain: str) -> Path:
    return _domain_data_dir(domain).parent


def _benchmark_command(domain: str) -> list[str]:
    return ["python3", str(_domain_root(domain) / "scripts" / "run_benchmark.py")]


def _train_command(domain: str) -> list[str]:
    data_dir = _domain_data_dir(domain)
    return [
        "python3",
        "train_kvrm_model.py",
        "--domain",
        domain,
        "--registry",
        str(data_dir / "registry.json"),
        "--train-cases",
        str(data_dir / "train_cases.jsonl"),
        "--eval-cases",
        str(data_dir / "cases.jsonl"),
        "--output-model",
        str(TRAINED_MODEL_PATHS[domain]),
        "--output-report",
        f"kvrm-bench/results/{domain}_compact_training_report_v1.json",
    ]


def _focused_refresh_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_operator_refresh.py", "--domains", domain]


def _stale_refresh_command() -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_operator_refresh.py", "--stale-only"]


def _domain_test_command(domain: str) -> list[str]:
    return ["pytest", f"kvrm-demos/tests/{domain}", "-q"]


def _stress_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_support_gate_stress.py", "--domains", domain]


def _counterfactual_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_counterfactual_boundary_benchmark.py", "--domains", domain]


def _ambiguity_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_ambiguity_regret_benchmark.py", "--domains", domain]


def _temporal_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_temporal_transition_benchmark.py", "--domains", domain]


def _coordination_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_coordination_chain_benchmark.py", "--domains", domain]


def _registry_evolution_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_registry_evolution_benchmark.py", "--domains", domain]


def _incident_replay_command(domain: str) -> list[str]:
    return ["python3", "kvrm-bench/scripts/run_incident_replay_benchmark.py", "--domains", domain]


def _fallback_feasibility_command(domain: str) -> list[str]:
    command = ["python3", "kvrm-bench/scripts/run_fallback_feasibility_benchmark.py"]
    if domain in {"sre", "drone"}:
        command.extend(["--domains", domain])
    return command


@dataclass(frozen=True)
class TaskDefinition:
    key: str
    label: str
    command: list[str]


@dataclass
class DemoState:
    enabled: bool = False
    training_mode: bool = False
    domain_index: int = 0
    case_index: int = 0
    case_file_index: int = 0
    review_only: bool = False
    review_index: int = 0
    replay_mode: bool = False
    replay_episode_index: int = 0
    replay_step_index: int = 0
    draft_target: str | None = None
    draft_filter: str = "all"
    draft_sort: str = "queue"
    draft_index: int = 0
    payload: dict | None = None
    error: str | None = None

    @property
    def current_domain(self) -> str:
        return DEMO_DOMAINS[self.domain_index]

def _build_tasks(domain: str) -> list[TaskDefinition]:
    return [
        TaskDefinition(
            "1",
            "Targeted test suite",
            [
                "pytest",
                "tests/kvrm_core",
                "tests/kvrm_bench",
                "kvrm-demos/tests/soc",
                "kvrm-demos/tests/sre",
                "kvrm-demos/tests/drone",
                "kvrm-demos/tests/grid",
                "kvrm-demos/tests/finance",
                "kvrm-demos/tests/medical",
                "kvrm-demos/tests/iam",
                "-q",
            ],
        ),
        TaskDefinition("2", f"Test {domain.upper()} domain", _domain_test_command(domain)),
        TaskDefinition("3", f"Benchmark {domain.upper()} demo", _benchmark_command(domain)),
        TaskDefinition("4", f"Train {domain.upper()} compact model", _train_command(domain)),
        TaskDefinition("a", f"Refresh {domain.upper()} train+benchmark+report", _focused_refresh_command(domain)),
        TaskDefinition("b", "Refresh stale domains + demo report", _stale_refresh_command()),
        TaskDefinition("5", "Refresh demo comparison report", ["python3", "kvrm-demos/compare_demos.py"]),
        TaskDefinition("6", f"Stress-test {domain.upper()} support gate", _stress_command(domain)),
        TaskDefinition("7", f"Boundary-test {domain.upper()} counterfactuals", _counterfactual_command(domain)),
        TaskDefinition("8", f"Frontier-test {domain.upper()} ambiguity/regret", _ambiguity_command(domain)),
        TaskDefinition("9", f"Temporal-test {domain.upper()} transitions", _temporal_command(domain)),
        TaskDefinition("0", f"Coordination-test {domain.upper()} chains", _coordination_command(domain)),
        TaskDefinition("e", f"Evolution-test {domain.upper()} registry changes", _registry_evolution_command(domain)),
        TaskDefinition("f", "Fallback-feasibility benchmark", _fallback_feasibility_command(domain)),
        TaskDefinition("p", f"Replay-test {domain.upper()} incident logs", _incident_replay_command(domain)),
    ]


class TaskRunner:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.process: subprocess.Popen[str] | None = None
        self.output = deque(maxlen=260)
        self._queue: queue.Queue[str] = queue.Queue()
        self._reader: threading.Thread | None = None
        self.current_task: TaskDefinition | None = None
        self.last_exit_code: int | None = None
        self.last_finished_label: str | None = None
        self.completed_count: int = 0

    def start(self, task: TaskDefinition) -> bool:
        if self.process and self.process.poll() is None:
            return False
        self.output.clear()
        self.last_exit_code = None
        self.current_task = task
        env = os.environ.copy()
        pythonpath = [
            str(self.repo_root / "kvrm-core" / "src"),
            str(self.repo_root / "kvrm-bench" / "src"),
            str(self.repo_root / "kvrm-demos" / "soc-playbook-router" / "src"),
            str(self.repo_root / "kvrm-demos" / "sre-policy-router" / "src"),
            str(self.repo_root / "kvrm-demos" / "drone-mission-router" / "src"),
            str(self.repo_root / "kvrm-demos" / "grid-ops-router" / "src"),
            str(self.repo_root / "kvrm-demos" / "finance-risk-router" / "src"),
            str(self.repo_root / "kvrm-demos" / "medical-workflow-router" / "src"),
            str(self.repo_root / "kvrm-demos" / "iam-access-router" / "src"),
        ]
        existing = env.get("PYTHONPATH")
        if existing:
            pythonpath.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(pythonpath)
        self.process = subprocess.Popen(
            task.command,
            cwd=self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        self._reader = threading.Thread(target=self._pump_output, daemon=True)
        self._reader.start()
        self.output.append(f"$ {' '.join(task.command)}")
        return True

    def _pump_output(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._queue.put(line.rstrip())

    def poll(self) -> None:
        while True:
            try:
                self.output.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if self.process and self.process.poll() is not None and self.last_exit_code is None:
            self.last_exit_code = self.process.returncode
            self.last_finished_label = self.current_task.label if self.current_task else None
            self.completed_count += 1
            self.output.append(f"[exit {self.last_exit_code}] {self.last_finished_label or 'task'}")

    def terminate(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.process.kill()

    @property
    def running(self) -> bool:
        return bool(self.process and self.process.poll() is None)


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.3f}"


def _fmt_latency(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.1f}ms"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "--"
    return "yes" if value else "no"


def _fmt_size(value: int | None) -> str:
    if value is None:
        return "--"
    if value < 1024:
        return f"{value}B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f}KB"
    return f"{value / (1024 * 1024):.1f}MB"


def _fmt_timestamp(value: float | None) -> str:
    if value is None:
        return "--"
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def _relpath(path: str | Path | None) -> str:
    if path is None:
        return "--"
    path = Path(path)
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _strategy_label(strategy: str) -> str:
    return {
        "rule": "rule",
        "retrieval": "retrieval",
        "prototype": "prototype",
        "semantic": "semantic",
        "learned": "learned",
        "hybrid": "hybrid",
    }.get(strategy, strategy)


def _fmt_count_rows(rows: list[dict] | None, limit: int = 3) -> str:
    if not rows:
        return "--"
    return "  ".join(
        f"{row.get('label')}={row.get('count')}"
        for row in rows[:limit]
    )


def _draw_box(win, y: int, x: int, h: int, w: int, title: str) -> None:
    if h < 3 or w < 4:
        return
    win.addstr(y, x + 2, f"[{title}]"[: max(0, w - 4)])
    for cx in range(x, x + w):
        win.addch(y, cx, curses.ACS_HLINE)
        win.addch(y + h - 1, cx, curses.ACS_HLINE)
    for cy in range(y, y + h):
        win.addch(cy, x, curses.ACS_VLINE)
        win.addch(cy, x + w - 1, curses.ACS_VLINE)
    win.addch(y, x, curses.ACS_ULCORNER)
    win.addch(y, x + w - 1, curses.ACS_URCORNER)
    win.addch(y + h - 1, x, curses.ACS_LLCORNER)
    win.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)


def _safe_addstr(win, y: int, x: int, text: str, width: int | None = None, attr: int = 0) -> None:
    if width is not None:
        text = text[: max(0, width)]
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def _preferred_case_file_index(case_files: list[str]) -> int:
    return 0


def _learned_model_path(domain: str) -> str | None:
    candidate_model_path = TRAINED_MODEL_PATHS.get(domain)
    if candidate_model_path is not None and candidate_model_path.exists():
        return str(candidate_model_path)
    return None


def _refresh_demo(demo: DemoState) -> None:
    case_files = available_demo_case_files(REPO_ROOT, demo.current_domain)
    if not case_files:
        demo.payload = None
        demo.error = f"no demo datasets for {demo.current_domain}"
        return
    demo.case_file_index %= len(case_files)
    eval_filename = case_files[demo.case_file_index]
    learned_model_path = _learned_model_path(demo.current_domain)
    try:
        if demo.draft_target is not None:
            demo.payload = run_draft_case_matrix(
                repo_root=REPO_ROOT,
                domain=demo.current_domain,
                target=demo.draft_target,
                draft_index=demo.draft_index,
                draft_filter=demo.draft_filter,
                draft_sort=demo.draft_sort,
                learned_model_path=learned_model_path,
            )
            demo.draft_index = int(demo.payload["draft_index"])
            demo.error = None
            return
        if demo.replay_mode:
            demo.payload = run_incident_replay_episode_matrix(
                repo_root=REPO_ROOT,
                domain=demo.current_domain,
                episode_index=demo.replay_episode_index,
                step_index=demo.replay_step_index,
                learned_model_path=learned_model_path,
            )
            replay_entry = demo.payload.get("replay_entry") or {}
            demo.replay_episode_index = int(replay_entry.get("episode_index", 0))
            demo.replay_step_index = int(replay_entry.get("step_index", 0))
            demo.error = None
            return
        review_entry = None
        if demo.review_only:
            review_queue = build_case_review_queue(
                repo_root=REPO_ROOT,
                domain=demo.current_domain,
                eval_filename=eval_filename,
                learned_model_path=learned_model_path,
            )
            if not review_queue:
                demo.payload = None
                demo.error = f"no boundary-review cases for {demo.current_domain}"
                return
            demo.review_index %= len(review_queue)
            review_entry = review_queue[demo.review_index]
            demo.case_index = int(review_entry["case_index"])
        demo.payload = run_demo_case_matrix(
            repo_root=REPO_ROOT,
            domain=demo.current_domain,
            eval_filename=eval_filename,
            case_index=demo.case_index,
            learned_model_path=learned_model_path,
        )
        demo.case_index = int(demo.payload["case_index"])
        if review_entry is not None:
            demo.payload["review_entry"] = review_entry
            demo.payload["review_count"] = len(review_queue)
        demo.error = None
    except Exception as exc:
        demo.payload = None
        demo.error = str(exc)


def _cycle_demo_domain(demo: DemoState, step: int) -> None:
    demo.domain_index = (demo.domain_index + step) % len(DEMO_DOMAINS)
    case_files = available_demo_case_files(REPO_ROOT, demo.current_domain)
    demo.case_file_index = _preferred_case_file_index(case_files) if case_files else 0
    demo.case_index = 0
    demo.review_index = 0
    demo.replay_episode_index = 0
    demo.replay_step_index = 0
    demo.draft_filter = "all"
    demo.draft_sort = "queue"
    demo.draft_index = 0
    _refresh_demo(demo)


def _cycle_demo_case(demo: DemoState, step: int) -> None:
    if demo.draft_target is not None:
        demo.draft_index += step
    elif demo.replay_mode:
        demo.replay_episode_index += step
    elif demo.review_only:
        demo.review_index += step
    else:
        demo.case_index += step
    _refresh_demo(demo)


def _toggle_review_mode(demo: DemoState) -> None:
    demo.training_mode = False
    demo.draft_target = None
    demo.replay_mode = False
    demo.replay_episode_index = 0
    demo.replay_step_index = 0
    demo.review_only = not demo.review_only
    demo.review_index = 0
    _refresh_demo(demo)


def _toggle_draft_mode(demo: DemoState) -> None:
    if demo.draft_target is None:
        demo.training_mode = False
        demo.review_only = False
        demo.replay_mode = False
        demo.draft_target = "review"
        demo.draft_filter = "all"
        demo.draft_sort = "queue"
        demo.draft_index = 0
    else:
        demo.draft_target = None
        demo.draft_filter = "all"
        demo.draft_sort = "queue"
    _refresh_demo(demo)


def _cycle_draft_target(demo: DemoState, step: int) -> None:
    targets = ["review", "train", "eval"]
    current = demo.draft_target or "review"
    index = targets.index(current)
    demo.draft_target = targets[(index + step) % len(targets)]
    demo.draft_filter = "all"
    demo.draft_sort = "queue"
    demo.draft_index = 0
    _refresh_demo(demo)


def _cycle_demo_case_file(demo: DemoState) -> None:
    case_files = available_demo_case_files(REPO_ROOT, demo.current_domain)
    if not case_files:
        demo.error = f"no demo datasets for {demo.current_domain}"
        demo.payload = None
        return
    demo.case_file_index = (demo.case_file_index + 1) % len(case_files)
    demo.case_index = 0
    demo.review_index = 0
    _refresh_demo(demo)


def _toggle_replay_mode(demo: DemoState) -> None:
    if demo.replay_mode:
        demo.replay_mode = False
    else:
        demo.training_mode = False
        demo.review_only = False
        demo.draft_target = None
        demo.replay_mode = True
        demo.replay_episode_index = 0
        demo.replay_step_index = 0
    _refresh_demo(demo)


def _toggle_training_mode(demo: DemoState) -> None:
    demo.training_mode = not demo.training_mode
    if demo.training_mode:
        demo.enabled = False
        demo.review_only = False
        demo.replay_mode = False
        demo.draft_target = None


def _cycle_replay_step(demo: DemoState, step: int) -> None:
    if not demo.replay_mode:
        raise ValueError("replay mode is not active")
    demo.replay_step_index += step
    _refresh_demo(demo)


def _save_current_case_draft(demo: DemoState, target: str) -> str:
    if demo.payload is None:
        raise ValueError("no active case to save")
    review_flags = []
    if demo.payload.get("review_entry"):
        review_flags = list(demo.payload["review_entry"].get("review_flags", []))
    result = append_case_draft(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        eval_filename=demo.payload["eval_filename"],
        case=demo.payload["case"],
        decision=demo.payload["decision"],
        strategy_results=demo.payload.get("strategy_results", []),
        target=target,
        review_flags=review_flags,
    )
    return _relpath(result["path"])


def _current_draft_original_index(demo: DemoState) -> int:
    if demo.payload is None:
        raise ValueError("draft mode is not active")
    return int(demo.payload.get("draft_original_index", demo.draft_index))


def _cycle_draft_filter(demo: DemoState, step: int) -> None:
    if demo.draft_target is None:
        raise ValueError("draft mode is not active")
    index = DRAFT_FILTERS.index(demo.draft_filter)
    demo.draft_filter = DRAFT_FILTERS[(index + step) % len(DRAFT_FILTERS)]
    demo.draft_index = 0
    _refresh_demo(demo)


def _cycle_draft_sort(demo: DemoState, step: int) -> None:
    if demo.draft_target is None:
        raise ValueError("draft mode is not active")
    index = DRAFT_SORTS.index(demo.draft_sort)
    demo.draft_sort = DRAFT_SORTS[(index + step) % len(DRAFT_SORTS)]
    demo.draft_index = 0
    _refresh_demo(demo)


def _cycle_draft_group(demo: DemoState, step: int) -> None:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    result = find_adjacent_draft_group_index(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_index=demo.draft_index,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        step=step,
    )
    demo.draft_index = int(result["draft_index"])
    _refresh_demo(demo)


def _cycle_current_draft_expected_action(demo: DemoState, step: int) -> str:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    action_ids = [None] + load_domain_action_ids(REPO_ROOT, demo.current_domain)
    case = demo.payload["case"]
    current_action = case.get("expected_action_id")
    if current_action not in action_ids:
        action_ids.append(current_action)
    current_index = action_ids.index(current_action)
    new_action = action_ids[(current_index + step) % len(action_ids)]
    result = update_draft_case(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_index=_current_draft_original_index(demo),
        expected_action_id=new_action,
    )
    _refresh_demo(demo)
    return str(result["draft_case"].get("expected_action_id"))


def _toggle_current_draft_flag(demo: DemoState, field_name: str) -> bool:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    current = bool(demo.payload["case"].get(field_name, False))
    result = update_draft_case(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_index=_current_draft_original_index(demo),
        **{field_name: not current},
    )
    _refresh_demo(demo)
    return bool(result["draft_case"].get(field_name))


def _promote_current_draft(demo: DemoState) -> tuple[str, str]:
    if demo.draft_target is None:
        raise ValueError("draft mode is not active")
    result = promote_draft_case(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_index=_current_draft_original_index(demo),
    )
    clear_demo_caches()
    _refresh_demo(demo)
    return (_relpath(result["destination_path"]), result["promoted_case"]["case_id"])


def _promote_ready_drafts(demo: DemoState) -> dict:
    if demo.draft_target is None:
        raise ValueError("draft mode is not active")
    result = promote_ready_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
    )
    clear_demo_caches()
    _refresh_demo(demo)
    return result


def _promote_current_draft_group(demo: DemoState) -> dict:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    group_label = demo.payload.get("draft_group_label")
    if group_label is None:
        raise ValueError("current draft sort mode does not define a promotable group")
    result = promote_ready_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        group_label=str(group_label),
    )
    clear_demo_caches()
    _refresh_demo(demo)
    return result


def _set_current_draft_group_review_status(demo: DemoState, review_status: str) -> dict:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    group_label = demo.payload.get("draft_group_label")
    if group_label is None:
        raise ValueError("current draft sort mode does not define an editable group")
    result = update_selected_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        group_label=str(group_label),
        review_status=review_status,
    )
    _refresh_demo(demo)
    return result


def _apply_current_draft_group_flag(demo: DemoState, field_name: str) -> dict:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    group_label = demo.payload.get("draft_group_label")
    if group_label is None:
        raise ValueError("current draft sort mode does not define an editable group")
    current_value = bool((demo.payload.get("case") or {}).get(field_name, False))
    result = update_selected_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        group_label=str(group_label),
        **{field_name: current_value},
    )
    _refresh_demo(demo)
    return result


def _apply_visible_draft_slice_flag(demo: DemoState, field_name: str) -> dict:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    current_value = bool((demo.payload.get("case") or {}).get(field_name, False))
    result = update_selected_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        **{field_name: current_value},
    )
    _refresh_demo(demo)
    return result


def _export_visible_draft_slice(demo: DemoState) -> dict:
    if demo.draft_target is None:
        raise ValueError("draft mode is not active")
    return export_selected_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
    )


def _export_current_draft_group(demo: DemoState) -> dict:
    if demo.draft_target is None or demo.payload is None:
        raise ValueError("draft mode is not active")
    group_label = demo.payload.get("draft_group_label")
    if group_label is None:
        raise ValueError("current draft sort mode does not define an exportable group")
    return export_selected_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        group_label=str(group_label),
    )


def _write_draft_export_manifest() -> dict:
    return write_draft_export_manifest(REPO_ROOT)


def _set_visible_draft_slice_review_status(demo: DemoState, review_status: str) -> dict:
    if demo.draft_target is None:
        raise ValueError("draft mode is not active")
    result = update_selected_draft_cases(
        repo_root=REPO_ROOT,
        domain=demo.current_domain,
        target=demo.draft_target,
        draft_filter=demo.draft_filter,
        draft_sort=demo.draft_sort,
        review_status=review_status,
    )
    _refresh_demo(demo)
    return result


def _draw_artifacts_panel(stdscr, focused_domain: str, left_w: int, right_w: int, top_h: int) -> None:
    snapshot = load_dashboard_snapshot(REPO_ROOT)
    artifact = load_domain_artifact_summary(REPO_ROOT, focused_domain)
    focused_summary = next(domain for domain in snapshot.domains if domain.domain == focused_domain)
    line_y = 5
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"FOCUS {focused_domain.upper()}  {artifact['registry_name']}@{artifact['registry_version']}",
        right_w - 6,
        curses.A_BOLD,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"digest {str(artifact['registry_digest'])[:12]}  actions {artifact['action_count']}  req {artifact['required_feature_count']}  schema {artifact['context_field_count']}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"train {artifact['train_case_count']}  eval {artifact['eval_case_count']}  supported {artifact['supported_case_count']}  unsupported {artifact['unsupported_case_count']}  ood-supported {artifact['ood_supported_case_count']}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"demo acc {_fmt_rate(focused_summary.demo_hybrid.semantic_correctness_rate)}  fa {_fmt_rate(focused_summary.demo_hybrid.false_accept_rate)}  rej {_fmt_rate(focused_summary.demo_hybrid.unsupported_case_rejection_rate)}  cost {_fmt_rate(focused_summary.demo_hybrid.mean_decision_cost)}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"train sel {_fmt_rate(focused_summary.training.selector_only_accuracy)}  hybrid+learn {_fmt_rate(focused_summary.training.hybrid_augmented_accuracy)}  cost {_fmt_rate(focused_summary.training.hybrid_augmented_mean_decision_cost)}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"registry {_relpath(artifact['registry_path'])}", right_w - 6)
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"train    {_relpath(artifact['train_cases_path'])}", right_w - 6)
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"eval     {_relpath(artifact['eval_cases_path'])}", right_w - 6)
    line_y += 2
    draft_counts = artifact.get("draft_counts", {})
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"drafts review {draft_counts.get('review', 0)}  train {draft_counts.get('train', 0)}  eval {draft_counts.get('eval', 0)}",
        right_w - 6,
    )
    line_y += 2
    _safe_addstr(stdscr, line_y, left_w + 4, "suite", right_w - 6, curses.A_BOLD)
    line_y += 1
    for domain in snapshot.domains:
        train_acc = domain.training.hybrid_augmented_accuracy
        row = (
            f"{domain.domain.upper():8} "
            f"demo {_fmt_rate(domain.demo_hybrid.semantic_correctness_rate)} "
            f"fa {_fmt_rate(domain.demo_hybrid.false_accept_rate)} "
            f"rej {_fmt_rate(domain.demo_hybrid.unsupported_case_rejection_rate)} "
            f"train {_fmt_rate(train_acc)}"
        )
        _safe_addstr(stdscr, line_y, left_w + 4, row, right_w - 6)
        line_y += 1
        if line_y >= top_h - 2:
            break


def _draw_training_panel(stdscr, focused_domain: str, left_w: int, right_w: int, top_h: int) -> None:
    line_y = 5
    try:
        summary = load_domain_training_artifact_summary(REPO_ROOT, focused_domain)
    except Exception as exc:
        _safe_addstr(stdscr, line_y, left_w + 4, f"error: {exc}", right_w - 6, curses.A_BOLD)
        return

    metadata = summary.get("metadata") or {}
    selector_only = summary.get("selector_only") or {}
    hybrid_augmented = summary.get("hybrid_augmented") or {}

    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"TRAIN {focused_domain.upper()}  {summary.get('registry_name')}@{summary.get('registry_version')}  status {summary.get('status')}",
        right_w - 6,
        curses.A_BOLD,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"model {_fmt_bool(summary.get('model_exists'))} fresh {_fmt_bool(summary.get('model_fresh'))}  report {_fmt_bool(summary.get('report_exists'))} fresh {_fmt_bool(summary.get('report_fresh'))}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"digest match {_fmt_bool(summary.get('registry_digest_matches'))}  train rows {summary.get('train_case_count')}/{summary.get('reported_train_case_count')}  eval {summary.get('eval_case_count')}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"model size {_fmt_size(summary.get('model_size_bytes'))}  trees {metadata.get('n_estimators')}  seed {metadata.get('random_state')}  train acc {_fmt_rate(metadata.get('train_accuracy'))}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"model mtime {_fmt_timestamp(summary.get('model_mtime'))}  report mtime {_fmt_timestamp(summary.get('report_mtime'))}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"registry mtime {_fmt_timestamp(summary.get('registry_mtime'))}  train mtime {_fmt_timestamp(summary.get('train_cases_mtime'))}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"eval mtime {_fmt_timestamp(summary.get('eval_cases_mtime'))}  newer->model {_fmt_bool(summary.get('sources_newer_than_model'))}  newer->report {_fmt_bool(summary.get('sources_newer_than_report'))}",
        right_w - 6,
    )
    line_y += 2
    if summary.get("recommended_action"):
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            "action rerun task [a] for this domain or task [b] for stale-domain batch refresh",
            right_w - 6,
        )
        line_y += 2
    _safe_addstr(stdscr, line_y, left_w + 4, "selector-only", right_w - 6, curses.A_BOLD)
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"acc {_fmt_rate(selector_only.get('semantic_correctness_rate'))}  fa {_fmt_rate(selector_only.get('false_accept_rate'))}  rej {_fmt_rate(selector_only.get('unsupported_case_rejection_rate'))}  cost {_fmt_rate(selector_only.get('mean_decision_cost'))}  ece {_fmt_rate(selector_only.get('calibration_ece'))}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"lat p50 {_fmt_latency(selector_only.get('latency_p50_ms'))}  p95 {_fmt_latency(selector_only.get('latency_p95_ms'))}  abst {_fmt_rate(selector_only.get('abstention_rate'))}  fallback {_fmt_rate(selector_only.get('fallback_rate'))}",
        right_w - 6,
    )
    line_y += 2
    _safe_addstr(stdscr, line_y, left_w + 4, "hybrid-augmented", right_w - 6, curses.A_BOLD)
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"acc {_fmt_rate(hybrid_augmented.get('semantic_correctness_rate'))}  fa {_fmt_rate(hybrid_augmented.get('false_accept_rate'))}  rej {_fmt_rate(hybrid_augmented.get('unsupported_case_rejection_rate'))}  cost {_fmt_rate(hybrid_augmented.get('mean_decision_cost'))}  ece {_fmt_rate(hybrid_augmented.get('calibration_ece'))}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"lat p50 {_fmt_latency(hybrid_augmented.get('latency_p50_ms'))}  p95 {_fmt_latency(hybrid_augmented.get('latency_p95_ms'))}  gate {_fmt_rate(hybrid_augmented.get('support_gate_trigger_rate'))}  short {_fmt_rate(hybrid_augmented.get('unsupported_support_gate_short_circuit_rate'))}",
        right_w - 6,
    )
    line_y += 2
    _safe_addstr(stdscr, line_y, left_w + 4, f"model  {_relpath(summary.get('model_path'))}", right_w - 6)
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"report {_relpath(summary.get('report_path'))}", right_w - 6)
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"train  {_relpath(summary.get('train_cases_path'))}", right_w - 6)
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"eval   {_relpath(summary.get('eval_cases_path'))}", right_w - 6)


def _draw_demo_panel(stdscr, demo: DemoState, left_w: int, right_w: int, top_h: int) -> None:
    line_y = 5
    case_files = available_demo_case_files(REPO_ROOT, demo.current_domain)
    if demo.error:
        _safe_addstr(stdscr, line_y, left_w + 4, f"error: {demo.error}", right_w - 6, curses.A_BOLD)
        return
    if demo.payload is None:
        _safe_addstr(stdscr, line_y, left_w + 4, "demo unavailable", right_w - 6)
        return

    case = demo.payload["case"]
    decision = demo.payload["decision"]
    audit = decision.get("audit_record", {})
    execution_result = decision.get("execution_result") or {}
    review_entry = demo.payload.get("review_entry")
    draft_entry = demo.payload.get("draft_entry")
    draft_readiness = demo.payload.get("draft_readiness") or {}
    draft_primary_diagnostic = demo.payload.get("draft_primary_diagnostic") or {}
    replay_entry = demo.payload.get("replay_entry") or {}
    case_label = case_files[demo.case_file_index] if case_files else demo.payload["eval_filename"]

    if replay_entry:
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"{demo.current_domain.upper()}  replay {replay_entry.get('episode_index', 0) + 1}/{replay_entry.get('episode_count', 0)}  step {replay_entry.get('step_index', 0) + 1}/{replay_entry.get('step_count', 0)}",
            right_w - 6,
            curses.A_BOLD,
        )
        line_y += 1
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"episode {replay_entry.get('episode_id')}  source {replay_entry.get('episode_source') or '--'}  type {replay_entry.get('episode_type') or '--'}",
            right_w - 6,
        )
        line_y += 1
        step_meta = replay_entry.get("step") or {}
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"event {step_meta.get('event_kind') or '--'}  minute {step_meta.get('minute_offset')}  base {replay_entry.get('base_case_id') or '--'}  switch {replay_entry.get('switch_case_id') or '--'}",
            right_w - 6,
        )
        line_y += 1
        if step_meta.get("event_note"):
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"note {step_meta.get('event_note')}",
                right_w - 6,
            )
            line_y += 1
    else:
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"{demo.current_domain.upper()}  {case_label}  case {demo.payload['case_index'] + 1}/{demo.payload['case_count']}",
            right_w - 6,
            curses.A_BOLD,
        )
        line_y += 1
    if draft_entry is not None:
        draft_meta = draft_entry.get("draft_meta") or {}
        draft_summary = demo.payload.get("draft_summary") or {}
        draft_filter = str(demo.payload.get("draft_filter") or "all")
        draft_sort = str(demo.payload.get("draft_sort") or "queue")
        draft_filtered_count = int(demo.payload.get("draft_filtered_count", demo.payload.get("draft_count", 0)))
        draft_original_index = int(demo.payload.get("draft_original_index", demo.draft_index))
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"draft {demo.payload.get('draft_target')} filter {draft_filter} sort {draft_sort} {demo.draft_index + 1}/{draft_filtered_count}",
            right_w - 6,
        )
        line_y += 1
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"original {draft_original_index + 1}/{demo.payload.get('draft_count', 0)}  status {draft_meta.get('review_status')}  proposed {draft_meta.get('proposed_expected_action_id')}",
            right_w - 6,
        )
        line_y += 1
        draft_group_label = demo.payload.get("draft_group_label")
        draft_group_position = demo.payload.get("draft_group_position")
        draft_group_count = demo.payload.get("draft_group_count")
        draft_group_summary = demo.payload.get("draft_group_summary") or {}
        if draft_group_label is not None and draft_group_position is not None and draft_group_count is not None:
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"group {draft_group_label} {draft_group_position}/{draft_group_count}",
                right_w - 6,
            )
            line_y += 1
        if draft_group_summary:
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                (
                    f"group supported {draft_group_summary.get('supported_count', 0)}  "
                    f"unsupported {draft_group_summary.get('unsupported_count', 0)}  "
                    f"ood {draft_group_summary.get('ood_count', 0)}"
                ),
                right_w - 6,
            )
            line_y += 1
            if draft_sort == "diagnostic":
                feature_text = _fmt_count_rows(draft_group_summary.get("diagnostic_feature_counts"))
                if feature_text != "--":
                    _safe_addstr(
                        stdscr,
                        line_y,
                        left_w + 4,
                        f"group features {feature_text}",
                        right_w - 6,
                    )
                    line_y += 1
                _safe_addstr(
                    stdscr,
                    line_y,
                    left_w + 4,
                    f"group expected {_fmt_count_rows(draft_group_summary.get('expected_action_counts'))}",
                    right_w - 6,
                )
                line_y += 1
                _safe_addstr(
                    stdscr,
                    line_y,
                    left_w + 4,
                    f"group proposed {_fmt_count_rows(draft_group_summary.get('proposed_action_counts'))}",
                    right_w - 6,
                )
                line_y += 1
            elif draft_sort == "status":
                _safe_addstr(
                    stdscr,
                    line_y,
                    left_w + 4,
                    f"group targets {_fmt_count_rows(draft_group_summary.get('recommended_target_counts'))}",
                    right_w - 6,
                )
                line_y += 1
                _safe_addstr(
                    stdscr,
                    line_y,
                    left_w + 4,
                    f"group diags {_fmt_count_rows(draft_group_summary.get('diagnostic_counts'))}",
                    right_w - 6,
                )
                line_y += 1
            elif draft_sort == "target":
                _safe_addstr(
                    stdscr,
                    line_y,
                    left_w + 4,
                    f"group status {_fmt_count_rows(draft_group_summary.get('review_status_counts'))}",
                    right_w - 6,
                )
                line_y += 1
                _safe_addstr(
                    stdscr,
                    line_y,
                    left_w + 4,
                    f"group diags {_fmt_count_rows(draft_group_summary.get('diagnostic_counts'))}",
                    right_w - 6,
                )
                line_y += 1
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"ready train {_fmt_bool(draft_readiness.get('train_ready'))}  eval {_fmt_bool(draft_readiness.get('eval_ready'))}  rec {draft_readiness.get('recommended_target') or '--'}",
            right_w - 6,
        )
        line_y += 1
        action_state = "--"
        if draft_readiness.get("expected_action_known") is False:
            action_state = "unknown"
        elif draft_readiness.get("expected_action_supported") is not None:
            action_state = "ok" if draft_readiness.get("expected_action_supported") else "xx"
        action_reason = draft_readiness.get("expected_action_reason")
        if action_reason is None and draft_readiness.get("expected_action_known") is False:
            action_reason = "unknown_action_id"
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"schema {_fmt_bool(draft_readiness.get('context_valid'))}:{draft_readiness.get('context_reason') or '--'}  action {action_state}:{action_reason or '--'}",
            right_w - 6,
        )
        line_y += 1
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"queue total {draft_summary.get('total_count', 0)}  pending {draft_summary.get('pending_count', 0)}  reviewed {draft_summary.get('reviewed_count', 0)}  promoted {draft_summary.get('promoted_count', 0)}",
            right_w - 6,
        )
        line_y += 1
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"queue ready train {draft_summary.get('train_ready_count', 0)}  eval {draft_summary.get('eval_ready_count', 0)}  blocked {draft_summary.get('blocked_count', 0)}  promotable {draft_summary.get('promotable_count', 0)}",
            right_w - 6,
        )
        line_y += 1
        if draft_primary_diagnostic:
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"diag {draft_primary_diagnostic.get('message')}",
                right_w - 6,
            )
            line_y += 1
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"hint {draft_primary_diagnostic.get('detail')}",
                right_w - 6,
            )
            line_y += 1
        blocked_counts = draft_summary.get("blocked_diagnostic_counts") or []
        if blocked_counts:
            blocked_text = "  ".join(
                f"{item.get('code')}={item.get('count')}"
                for item in blocked_counts[:3]
            )
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"blocked reasons {blocked_text}",
                right_w - 6,
            )
            line_y += 1
        group_counts = demo.payload.get("draft_group_counts") or []
        if group_counts and draft_sort != "queue":
            group_text = "  ".join(
                f"{item.get('label')}={item.get('count')}"
                for item in group_counts[:3]
            )
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"sort groups {group_text}",
                right_w - 6,
            )
            line_y += 1
    if review_entry is not None:
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"review {demo.review_index + 1}/{demo.payload.get('review_count', 0)}  flags {','.join(review_entry.get('review_flags', []))}",
            right_w - 6,
        )
        line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, f"id {case['case_id']}", right_w - 6)
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"expected {case.get('expected_action_id')}  selected {decision.get('selected_action_id')}  final {decision.get('final_status')}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"conf {_fmt_rate(decision.get('confidence'))}  exec {execution_result.get('status')}  correct {decision.get('correct')}  valid {decision.get('valid')}",
        right_w - 6,
    )
    line_y += 1
    _safe_addstr(
        stdscr,
        line_y,
        left_w + 4,
        f"supported {case.get('supported')}  ood {case.get('ood')}  fallback {decision.get('fallback_used')}  latency {_fmt_latency(decision.get('latency_ms'))}  digest {str(audit.get('registry_digest', ''))[:12]}",
        right_w - 6,
    )
    line_y += 2
    _safe_addstr(stdscr, line_y, left_w + 4, "strategies", right_w - 6, curses.A_BOLD)
    line_y += 1
    strategy_results = demo.payload.get("strategy_results", [])
    for row in strategy_results:
        strategy = _strategy_label(row.get("strategy", ""))
        strategy_decision = row.get("decision", {})
        selected_action = strategy_decision.get("selected_action_id") or "--"
        correct_marker = "ok" if strategy_decision.get("correct") else "xx"
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"{strategy:<9} {selected_action:<28} {_fmt_rate(strategy_decision.get('confidence'))} {strategy_decision.get('final_status')} {correct_marker}",
            right_w - 6,
        )
        line_y += 1
        if line_y >= top_h - 8:
            break
    line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, "audit", right_w - 6, curses.A_BOLD)
    line_y += 1
    selected_evidence = audit.get("selected_evidence", {})
    if selected_evidence:
        nearest_case_id = selected_evidence.get("nearest_case_id")
        if nearest_case_id:
            _safe_addstr(stdscr, line_y, left_w + 4, f"nearest {nearest_case_id}", right_w - 6)
            line_y += 1
        fused_families = selected_evidence.get("fused_source_families") or []
        if fused_families:
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"fused {'/'.join(str(item) for item in fused_families)}  candidates {selected_evidence.get('fused_candidate_count')}",
                right_w - 6,
            )
            line_y += 1
        if selected_evidence.get("confidence_distance") is not None:
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"prototype distance {selected_evidence.get('confidence_distance')}  masked {selected_evidence.get('masked_distance')}",
                right_w - 6,
            )
            line_y += 1
    candidate_scores = audit.get("candidate_scores", [])
    for candidate in candidate_scores[:3]:
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"{candidate.get('action_id')}  eff {_fmt_rate(candidate.get('effective_confidence'))}  src {candidate.get('source')}",
            right_w - 6,
        )
        line_y += 1
        if line_y >= top_h - 5:
            break
    line_y += 1
    if draft_entry is not None:
        draft_meta = draft_entry.get("draft_meta") or {}
        review_flags = draft_meta.get("review_flags") or []
        _safe_addstr(
            stdscr,
            line_y,
            left_w + 4,
            f"draft flags {','.join(review_flags) if review_flags else '--'}",
            right_w - 6,
        )
        line_y += 1
        strategy_snapshot = draft_meta.get("strategy_snapshot") or []
        if strategy_snapshot:
            first_snapshot = strategy_snapshot[0]
            _safe_addstr(
                stdscr,
                line_y,
                left_w + 4,
                f"captured {len(strategy_snapshot)} strategies  first {first_snapshot.get('strategy')}->{first_snapshot.get('selected_action_id')}",
                right_w - 6,
            )
            line_y += 1
        line_y += 1
    _safe_addstr(stdscr, line_y, left_w + 4, "features", right_w - 6, curses.A_BOLD)
    line_y += 1
    for key, value in sorted(case.get("input_features", {}).items()):
        _safe_addstr(stdscr, line_y, left_w + 4, f"{key}: {value}", right_w - 6)
        line_y += 1
        if line_y >= top_h - 3:
            break


def draw(stdscr, runner: TaskRunner, demo: DemoState, status: str, selected_index: int) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    tasks = _build_tasks(demo.current_domain)
    selected_index = min(selected_index, len(tasks) - 1)

    _safe_addstr(stdscr, 0, 2, "KVRM Operator Console", width - 4, curses.A_BOLD)
    _safe_addstr(stdscr, 1, 2, status, width - 4)

    top_h = max(12, height // 2 - 1)
    left_w = max(38, width // 3)
    right_w = width - left_w - 3
    bottom_y = top_h + 1
    bottom_h = height - bottom_y - 1

    right_title = "Focused Domain"
    if demo.training_mode:
        right_title = "Training Audit"
    elif demo.enabled:
        if demo.draft_target is not None:
            right_title = "Draft Browser"
        elif demo.replay_mode:
            right_title = "Replay Audit"
        elif demo.review_only:
            right_title = "Boundary Review"
        else:
            right_title = "Interactive Audit"
    _draw_box(stdscr, 3, 1, top_h - 2, left_w, "Actions")
    _draw_box(stdscr, 3, left_w + 2, top_h - 2, right_w, right_title)
    _draw_box(stdscr, bottom_y, 1, bottom_h, width - 2, "Task Output")

    for index, task in enumerate(tasks):
        marker = ">" if index == selected_index else " "
        disabled = runner.running and index != selected_index
        label = f"{marker} [{task.key}] {task.label}"
        attr = curses.A_REVERSE if index == selected_index else 0
        if disabled:
            attr |= curses.A_DIM
        _safe_addstr(stdscr, 5 + index, 3, label, left_w - 6, attr)

    controls_y = 5 + len(tasks) + 1
    _safe_addstr(stdscr, controls_y, 3, "[enter] run selected  [1-9,0] quick run", left_w - 6)
    _safe_addstr(stdscr, controls_y + 1, 3, "[j/k] move task  [r] refresh  [q] quit", left_w - 6)
    _safe_addstr(stdscr, controls_y + 2, 3, "[d] audit on/off  [v] review queue  [g] draft browser  [i] replay browser", left_w - 6)
    _safe_addstr(stdscr, controls_y + 3, 3, "[h/l or <-/->] focus domain  [up/down] case/review/draft/replay  [c] dataset", left_w - 6)
    _safe_addstr(stdscr, controls_y + 4, 3, "[x] training audit  [w/t/y] save draft  draft: [n] queue [F] filter [s] sort [[/]] action", left_w - 6)
    _safe_addstr(stdscr, controls_y + 5, 3, "draft: [{] prev-group [}] next-group [R] grp-reviewed [P] grp-pending", left_w - 6)
    _safe_addstr(stdscr, controls_y + 6, 3, "draft: [U] grp-supported=current [O] grp-ood=current [V] slice-reviewed [B] slice-pending", left_w - 6)
    _safe_addstr(stdscr, controls_y + 7, 3, "draft: [S] slice-supported=current [D] slice-ood=current [u] supported [o] ood", left_w - 6)
    _safe_addstr(stdscr, controls_y + 8, 3, "draft: [E] export-slice [H] export-group [J] refresh-export-manifest [m] promote", left_w - 6)
    _safe_addstr(stdscr, controls_y + 9, 3, "draft: [M] batch-slice [G] batch-group  replay: [[/]] step", left_w - 6)
    status_y = controls_y + 11
    if runner.running and runner.current_task:
        _safe_addstr(stdscr, status_y, 3, f"running: {runner.current_task.label}", left_w - 6, curses.A_BOLD)
    elif runner.last_finished_label:
        _safe_addstr(stdscr, status_y, 3, f"last: {runner.last_finished_label} (exit {runner.last_exit_code})", left_w - 6)

    if demo.training_mode:
        _draw_training_panel(stdscr, demo.current_domain, left_w, right_w, top_h)
    elif demo.enabled:
        _draw_demo_panel(stdscr, demo, left_w, right_w, top_h)
    else:
        _draw_artifacts_panel(stdscr, demo.current_domain, left_w, right_w, top_h)

    output_y = bottom_y + 2
    output_h = bottom_h - 3
    lines = list(runner.output)[-max(1, output_h):]
    for idx, line in enumerate(lines):
        _safe_addstr(stdscr, output_y + idx, 3, line, width - 6)

    stdscr.refresh()


def main(stdscr) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    runner = TaskRunner(REPO_ROOT)
    demo = DemoState()
    selected_index = 0
    seen_completed_count = 0
    status = f"repo={REPO_ROOT}  focus domain={demo.current_domain}  keys=1-9,0 run tasks, d audit, v review, g drafts, i replay, x training, h/l domain, q quit"

    try:
        while True:
            runner.poll()
            if runner.completed_count != seen_completed_count:
                seen_completed_count = runner.completed_count
                clear_demo_caches()
            draw(stdscr, runner, demo, status, selected_index)
            key = stdscr.getch()
            if key == -1:
                time.sleep(0.08)
                continue
            if key in (ord("q"), 27):
                break
            tasks = _build_tasks(demo.current_domain)
            if key == ord("j"):
                selected_index = min(len(tasks) - 1, selected_index + 1)
                continue
            if key == ord("k"):
                selected_index = max(0, selected_index - 1)
                continue
            if key == ord("d"):
                demo.training_mode = False
                demo.enabled = not demo.enabled
                if demo.enabled:
                    case_files = available_demo_case_files(REPO_ROOT, demo.current_domain)
                    demo.case_file_index = _preferred_case_file_index(case_files) if case_files else 0
                    demo.case_index = 0
                    _refresh_demo(demo)
                status = f"audit {'enabled' if demo.enabled else 'disabled'} domain={demo.current_domain}"
                continue
            if key == ord("x"):
                _toggle_training_mode(demo)
                status = f"training audit {'enabled' if demo.training_mode else 'disabled'} domain={demo.current_domain}"
                continue
            if key == ord("v"):
                demo.enabled = True
                _toggle_review_mode(demo)
                status = f"review queue {'enabled' if demo.review_only else 'disabled'} domain={demo.current_domain}"
                continue
            if key == ord("g"):
                demo.enabled = True
                _toggle_draft_mode(demo)
                status = f"draft browser {'enabled' if demo.draft_target is not None else 'disabled'} domain={demo.current_domain}"
                continue
            if key == ord("i"):
                demo.enabled = True
                _toggle_replay_mode(demo)
                status = f"replay browser {'enabled' if demo.replay_mode else 'disabled'} domain={demo.current_domain}"
                continue
            if key == ord("r"):
                clear_demo_caches()
                if demo.enabled:
                    _refresh_demo(demo)
                status = f"refreshed {time.strftime('%H:%M:%S')} domain={demo.current_domain}"
                continue
            if key in (curses.KEY_LEFT, ord("h")):
                _cycle_demo_domain(demo, -1)
                status = f"focus domain={demo.current_domain}"
                continue
            if key in (curses.KEY_RIGHT, ord("l")):
                _cycle_demo_domain(demo, 1)
                status = f"focus domain={demo.current_domain}"
                continue
            if demo.enabled and key == curses.KEY_UP:
                _cycle_demo_case(demo, -1)
                if demo.draft_target is not None and demo.payload is not None:
                    status = (
                        f"draft {demo.payload.get('draft_filter', 'all')}/{demo.payload.get('draft_sort', 'queue')}="
                        f"{demo.payload.get('draft_index', 0) + 1}/{demo.payload.get('draft_filtered_count', 0)}"
                    )
                elif demo.replay_mode and demo.payload is not None:
                    replay_entry = demo.payload.get("replay_entry") or {}
                    status = f"replay episode={replay_entry.get('episode_index', 0) + 1}/{replay_entry.get('episode_count', 0)}"
                else:
                    status = f"demo case={demo.case_index + 1 if demo.payload else 0}"
                continue
            if demo.enabled and key == curses.KEY_DOWN:
                _cycle_demo_case(demo, 1)
                if demo.draft_target is not None and demo.payload is not None:
                    status = (
                        f"draft {demo.payload.get('draft_filter', 'all')}/{demo.payload.get('draft_sort', 'queue')}="
                        f"{demo.payload.get('draft_index', 0) + 1}/{demo.payload.get('draft_filtered_count', 0)}"
                    )
                elif demo.replay_mode and demo.payload is not None:
                    replay_entry = demo.payload.get("replay_entry") or {}
                    status = f"replay episode={replay_entry.get('episode_index', 0) + 1}/{replay_entry.get('episode_count', 0)}"
                else:
                    status = f"demo case={demo.case_index + 1 if demo.payload else 0}"
                continue
            if demo.enabled and key == ord("c"):
                if demo.replay_mode:
                    status = "dataset selection is disabled in replay browser"
                    continue
                if demo.draft_target is not None:
                    status = "dataset selection is disabled in draft browser"
                    continue
                _cycle_demo_case_file(demo)
                status = f"dataset={demo.payload['eval_filename'] if demo.payload else 'unavailable'}"
                continue
            if demo.enabled and demo.replay_mode and key == ord("["):
                try:
                    _cycle_replay_step(demo, -1)
                    replay_entry = (demo.payload or {}).get("replay_entry") or {}
                    status = f"replay step={replay_entry.get('step_index', 0) + 1}/{replay_entry.get('step_count', 0)}"
                except Exception as exc:
                    status = f"replay step failed: {exc}"
                continue
            if demo.enabled and demo.replay_mode and key == ord("]"):
                try:
                    _cycle_replay_step(demo, 1)
                    replay_entry = (demo.payload or {}).get("replay_entry") or {}
                    status = f"replay step={replay_entry.get('step_index', 0) + 1}/{replay_entry.get('step_count', 0)}"
                except Exception as exc:
                    status = f"replay step failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("n"):
                _cycle_draft_target(demo, 1)
                status = f"draft queue={demo.draft_target} filter={demo.draft_filter} sort={demo.draft_sort}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("F"):
                _cycle_draft_filter(demo, 1)
                status = f"draft filter={demo.draft_filter}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("s"):
                _cycle_draft_sort(demo, 1)
                status = f"draft sort={demo.draft_sort}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("{"):
                try:
                    _cycle_draft_group(demo, -1)
                    status = (
                        f"draft group={demo.payload.get('draft_group_label', '--')} "
                        f"{demo.payload.get('draft_group_position', 0)}/{demo.payload.get('draft_group_count', 0)}"
                    )
                except Exception as exc:
                    status = f"draft group jump failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("}"):
                try:
                    _cycle_draft_group(demo, 1)
                    status = (
                        f"draft group={demo.payload.get('draft_group_label', '--')} "
                        f"{demo.payload.get('draft_group_position', 0)}/{demo.payload.get('draft_group_count', 0)}"
                    )
                except Exception as exc:
                    status = f"draft group jump failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("["):
                try:
                    new_action = _cycle_current_draft_expected_action(demo, -1)
                    status = f"draft expected_action_id={new_action}"
                except Exception as exc:
                    status = f"draft edit failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("]"):
                try:
                    new_action = _cycle_current_draft_expected_action(demo, 1)
                    status = f"draft expected_action_id={new_action}"
                except Exception as exc:
                    status = f"draft edit failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("R"):
                try:
                    result = _set_current_draft_group_review_status(demo, "reviewed")
                    status = (
                        f"group {result['group_label']} review_status=reviewed "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"group review update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("P"):
                try:
                    result = _set_current_draft_group_review_status(demo, "pending")
                    status = (
                        f"group {result['group_label']} review_status=pending "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"group review update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("V"):
                try:
                    result = _set_visible_draft_slice_review_status(demo, "reviewed")
                    status = (
                        f"slice {result['draft_filter']}/{result['draft_sort']} review_status=reviewed "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"slice review update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("B"):
                try:
                    result = _set_visible_draft_slice_review_status(demo, "pending")
                    status = (
                        f"slice {result['draft_filter']}/{result['draft_sort']} review_status=pending "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"slice review update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("E"):
                try:
                    result = _export_visible_draft_slice(demo)
                    status = f"exported slice -> {_relpath(result['json_path'])}"
                except Exception as exc:
                    status = f"slice export failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("H"):
                try:
                    result = _export_current_draft_group(demo)
                    status = f"exported group -> {_relpath(result['json_path'])}"
                except Exception as exc:
                    status = f"group export failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("J"):
                try:
                    result = _write_draft_export_manifest()
                    status = (
                        f"export manifest refreshed -> {_relpath(result['path'])} "
                        f"exports={result['export_count']}"
                    )
                except Exception as exc:
                    status = f"export manifest failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("S"):
                try:
                    result = _apply_visible_draft_slice_flag(demo, "supported")
                    status = (
                        f"slice {result['draft_filter']}/{result['draft_sort']} supported="
                        f"{bool((demo.payload or {}).get('case', {}).get('supported', False))} "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"slice flag update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("D"):
                try:
                    result = _apply_visible_draft_slice_flag(demo, "ood")
                    status = (
                        f"slice {result['draft_filter']}/{result['draft_sort']} ood="
                        f"{bool((demo.payload or {}).get('case', {}).get('ood', False))} "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"slice flag update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("U"):
                try:
                    result = _apply_current_draft_group_flag(demo, "supported")
                    status = (
                        f"group {result['group_label']} supported={bool((demo.payload or {}).get('case', {}).get('supported', False))} "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"group flag update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("O"):
                try:
                    result = _apply_current_draft_group_flag(demo, "ood")
                    status = (
                        f"group {result['group_label']} ood={bool((demo.payload or {}).get('case', {}).get('ood', False))} "
                        f"updated={result['updated_count']} skipped_promoted={result['skipped_promoted_count']}"
                    )
                except Exception as exc:
                    status = f"group flag update failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("u"):
                try:
                    new_value = _toggle_current_draft_flag(demo, "supported")
                    status = f"draft supported={new_value}"
                except Exception as exc:
                    status = f"draft edit failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("o"):
                try:
                    new_value = _toggle_current_draft_flag(demo, "ood")
                    status = f"draft ood={new_value}"
                except Exception as exc:
                    status = f"draft edit failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("m"):
                try:
                    destination_path, promoted_case_id = _promote_current_draft(demo)
                    status = f"promoted {promoted_case_id} -> {destination_path}"
                except Exception as exc:
                    status = f"promotion failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("M"):
                try:
                    result = _promote_ready_drafts(demo)
                    status = (
                        f"slice promoted {result['promoted_count']}/{result['eligible_count']} ready drafts "
                        f"in {result['draft_filter']} "
                        f"(train={result['destination_counts']['train']} eval={result['destination_counts']['eval']})"
                    )
                except Exception as exc:
                    status = f"batch promotion failed: {exc}"
                continue
            if demo.enabled and demo.draft_target is not None and key == ord("G"):
                try:
                    result = _promote_current_draft_group(demo)
                    status = (
                        f"group {result['group_label']} promoted {result['promoted_count']}/{result['eligible_count']} ready drafts "
                        f"(train={result['destination_counts']['train']} eval={result['destination_counts']['eval']})"
                    )
                except Exception as exc:
                    status = f"group promotion failed: {exc}"
                continue
            if demo.enabled and key in (ord("w"), ord("t"), ord("y")):
                target = {
                    ord("w"): "review",
                    ord("t"): "train",
                    ord("y"): "eval",
                }[key]
                try:
                    saved_path = _save_current_case_draft(demo, target)
                    status = f"saved {target} draft -> {saved_path}"
                except Exception as exc:
                    status = f"draft save failed: {exc}"
                continue

            selected_index = min(selected_index, len(tasks) - 1)
            task = next((task for task in tasks if ord(task.key) == key), None)
            if task is None and key in (10, 13):
                task = tasks[selected_index]
            if task is not None:
                if runner.start(task):
                    status = f"started: {task.label}"
                else:
                    status = f"task already running: {runner.current_task.label if runner.current_task else 'unknown'}"
                continue
    finally:
        runner.terminate()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    curses.wrapper(main)
