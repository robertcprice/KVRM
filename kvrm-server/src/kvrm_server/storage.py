"""Disk-backed domain store and SQLite audit log for the KVRM server.

Each uploaded domain becomes a standard KVRM domain directory under the data
root, so everything the CLI can do (`kvrm validate/train/route/eval`) works on
the server's domains too, and vice versa.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from kvrm_core import DomainDir, build_domain_runtime, load_domain_dir
from kvrm_core.domain_dir import CASES_FILENAME, CONFIG_FILENAME, REGISTRY_FILENAME, TRAIN_FILENAME
from kvrm_core.runtime import KVRMRuntime


class DomainStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._runtimes: dict[str, KVRMRuntime] = {}
        self._lock = threading.Lock()
        self._audit_db = self.root / "audit.sqlite3"
        self._init_audit()

    # -- domains -----------------------------------------------------------

    def domain_path(self, name: str) -> Path:
        safe = "".join(c for c in name if c.isalnum() or c in "-_")
        if not safe or safe != name:
            raise ValueError(f"invalid domain name: {name!r} (alphanumerics, '-', '_' only)")
        return self.root / safe

    def list_domains(self) -> list[str]:
        return sorted(
            p.name for p in self.root.iterdir()
            if p.is_dir() and (p / REGISTRY_FILENAME).is_file()
        )

    def create_domain(
        self,
        name: str,
        registry: dict,
        train_cases: list[dict],
        cases: list[dict] | None = None,
        config: dict | None = None,
        overwrite: bool = False,
    ) -> DomainDir:
        path = self.domain_path(name)
        if path.exists() and not overwrite:
            raise FileExistsError(f"domain {name!r} already exists (pass overwrite=true to replace)")
        path.mkdir(parents=True, exist_ok=True)
        (path / REGISTRY_FILENAME).write_text(json.dumps(registry, indent=2) + "\n")
        (path / TRAIN_FILENAME).write_text(
            "".join(json.dumps(case) + "\n" for case in train_cases)
        )
        if cases is not None:
            (path / CASES_FILENAME).write_text(
                "".join(json.dumps(case) + "\n" for case in cases)
            )
        if config is not None:
            (path / CONFIG_FILENAME).write_text(json.dumps(config, indent=2) + "\n")
        self.invalidate(name)
        return load_domain_dir(path)

    def load(self, name: str) -> DomainDir:
        path = self.domain_path(name)
        if not path.is_dir():
            raise FileNotFoundError(f"unknown domain: {name}")
        return load_domain_dir(path)

    def runtime(self, name: str, threshold: float = 0.60) -> KVRMRuntime:
        key = f"{name}:{threshold}"
        with self._lock:
            if key not in self._runtimes:
                self._runtimes[key] = build_domain_runtime(
                    self.load(name), threshold=threshold
                )
            return self._runtimes[key]

    def invalidate(self, name: str) -> None:
        with self._lock:
            for key in [k for k in self._runtimes if k.split(":", 1)[0] == name]:
                del self._runtimes[key]

    # -- audit log ---------------------------------------------------------

    def _init_audit(self) -> None:
        with sqlite3.connect(self._audit_db) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    case_id TEXT,
                    selected_action_id TEXT,
                    final_status TEXT,
                    registry_digest TEXT,
                    decision_json TEXT NOT NULL
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_domain ON decisions(domain, id)"
            )

    def record_decision(self, domain: str, decision_payload: dict) -> int:
        audit = decision_payload.get("audit_record") or {}
        with sqlite3.connect(self._audit_db) as conn:
            cursor = conn.execute(
                "INSERT INTO decisions (domain, recorded_at, case_id, selected_action_id,"
                " final_status, registry_digest, decision_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    domain,
                    datetime.now(timezone.utc).isoformat(),
                    decision_payload.get("case_id"),
                    decision_payload.get("selected_action_id"),
                    str(decision_payload.get("final_status")),
                    audit.get("registry_digest"),
                    json.dumps(decision_payload),
                ),
            )
            return int(cursor.lastrowid)

    def recent_decisions(self, domain: str, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self._audit_db) as conn:
            rows = conn.execute(
                "SELECT id, recorded_at, decision_json FROM decisions"
                " WHERE domain = ? ORDER BY id DESC LIMIT ?",
                (domain, limit),
            ).fetchall()
        return [
            {"audit_id": row[0], "recorded_at": row[1], **json.loads(row[2])}
            for row in rows
        ]
