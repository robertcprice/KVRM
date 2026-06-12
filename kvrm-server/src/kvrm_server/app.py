"""KVRM server — fail-closed action routing as an HTTP service.

Upload a domain (registry + training cases), then route features through the
same selector-ensemble → support-gate → validator → executor pipeline the
library and CLI use. Every decision is persisted to an audit log keyed by the
registry digest it ran against.

Run:
    KVRM_SERVER_DATA=./data KVRM_API_KEYS=secret1 uvicorn kvrm_server.app:app

Auth: clients send `X-API-Key`. If KVRM_API_KEYS is unset the server runs
open (development mode).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from kvrm_core import DecisionInput, DomainDirError, evaluate_domain
from kvrm_core.domain_dir import _load_jsonl
from kvrm_core.learned import save_compact_model_artifact, train_compact_model
from kvrm_core.registry import RegistryValidationError, validate_registry

from .storage import DomainStore


class DomainUpload(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    registry: dict
    train_cases: list[dict]
    cases: list[dict] | None = None
    config: dict | None = None
    overwrite: bool = False


class RouteRequest(BaseModel):
    features: dict
    case_id: str = "api_route"
    threshold: float = 0.60


class EvalRequest(BaseModel):
    cases: list[dict] | None = None
    threshold: float = 0.60


def create_app(
    data_root: str | Path | None = None,
    api_keys: set[str] | None = None,
) -> FastAPI:
    """Build a KVRM server instance. Defaults come from the environment:
    KVRM_SERVER_DATA for storage, KVRM_API_KEYS (comma-separated) for auth."""
    if data_root is None:
        data_root = os.environ.get("KVRM_SERVER_DATA", "./kvrm-server-data")
    if api_keys is None:
        api_keys = {
            k.strip() for k in os.environ.get("KVRM_API_KEYS", "").split(",") if k.strip()
        }

    store = DomainStore(data_root)
    app = FastAPI(title="KVRM Server", description=__doc__, version="0.1.0")

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if not api_keys:
            return  # development mode
        if x_api_key not in api_keys:
            raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "domains": store.list_domains(), "auth": bool(api_keys)}

    @app.get("/domains", dependencies=[Depends(require_api_key)])
    def list_domains() -> dict:
        out = []
        for name in store.list_domains():
            domain = store.load(name)
            out.append(
                {
                    "name": name,
                    "registry_name": domain.registry.registry_name,
                    "version": domain.registry.version,
                    "actions": len(domain.registry.actions),
                    "fallback_action_id": domain.config.fallback_action_id or None,
                    "trained_model": domain.default_model_path.is_file(),
                }
            )
        return {"domains": out}

    @app.post("/domains", dependencies=[Depends(require_api_key)], status_code=201)
    def create_domain(upload: DomainUpload) -> dict:
        try:
            domain = store.create_domain(
                upload.name,
                upload.registry,
                upload.train_cases,
                cases=upload.cases,
                config=upload.config,
                overwrite=upload.overwrite,
            )
            validate_registry(domain.registry)
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except (DomainDirError, RegistryValidationError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return {
            "name": upload.name,
            "registry_name": domain.registry.registry_name,
            "version": domain.registry.version,
            "actions": [a.action_id for a in domain.registry.actions],
            "fallback_action_id": domain.config.fallback_action_id or None,
        }

    @app.get("/domains/{name}", dependencies=[Depends(require_api_key)])
    def get_domain(name: str) -> dict:
        try:
            domain = store.load(name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {
            "name": name,
            "registry_name": domain.registry.registry_name,
            "version": domain.registry.version,
            "required_features": domain.registry.required_features,
            "actions": [
                {
                    "action_id": a.action_id,
                    "description": a.description,
                    "tags": a.tags,
                }
                for a in domain.registry.actions
            ],
            "fallback_action_id": domain.config.fallback_action_id or None,
            "trained_model": domain.default_model_path.is_file(),
        }

    @app.post("/domains/{name}/train", dependencies=[Depends(require_api_key)])
    def train_domain(name: str) -> dict:
        try:
            domain = store.load(name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        train_cases = _load_jsonl(domain.train_cases_path)
        artifact = train_compact_model(train_cases=train_cases, registry=domain.registry)
        save_compact_model_artifact(domain.default_model_path, artifact)
        store.invalidate(name)
        return {
            "name": name,
            "train_cases": len(train_cases),
            "train_accuracy": artifact.get("metadata", {}).get("train_accuracy"),
        }

    @app.post("/domains/{name}/route", dependencies=[Depends(require_api_key)])
    def route(name: str, request: RouteRequest) -> dict:
        try:
            runtime = store.runtime(name, threshold=request.threshold)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DomainDirError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        decision = runtime.decide_and_execute(
            DecisionInput(case_id=request.case_id, features=request.features)
        )
        payload = json.loads(decision.model_dump_json())
        payload["audit_id"] = store.record_decision(name, payload)
        return payload

    @app.post("/domains/{name}/eval", dependencies=[Depends(require_api_key)])
    def evaluate(name: str, request: EvalRequest) -> dict:
        try:
            domain = store.load(name)
            runtime = store.runtime(name, threshold=request.threshold)
            metrics = evaluate_domain(domain, runtime, request.cases)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DomainDirError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return metrics

    @app.get("/domains/{name}/audit", dependencies=[Depends(require_api_key)])
    def audit(name: str, limit: int = 50) -> dict:
        try:
            store.load(name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {
            "domain": name,
            "decisions": store.recent_decisions(name, limit=min(limit, 500)),
        }

    return app


# uvicorn kvrm_server.app:app
app = create_app()
