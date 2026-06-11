from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .types import DecisionCandidate, ExecutionResult, ExecutionStatus


@dataclass
class BaseExecutor:
    def execute(self, candidate: DecisionCandidate) -> ExecutionResult:
        raise NotImplementedError


@dataclass
class DictionaryExecutor(BaseExecutor):
    handlers: dict[str, Callable[[dict], dict]]

    def execute(self, candidate: DecisionCandidate) -> ExecutionResult:
        if candidate.action_id not in self.handlers:
            return ExecutionResult(status=ExecutionStatus.BLOCKED, action_id=candidate.action_id, reason="no_handler")
        output = self.handlers[candidate.action_id](candidate.parameters)
        status = ExecutionStatus.HANDOFF if candidate.action_id == "request_human_review" else ExecutionStatus.SUCCESS
        return ExecutionResult(status=status, action_id=candidate.action_id, output=output)
