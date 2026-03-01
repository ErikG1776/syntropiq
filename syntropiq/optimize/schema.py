from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from syntropiq.core.models import Task


@dataclass
class LambdaVector:
    l_cost: float
    l_time: float
    l_risk: float
    l_trust: float

    def enforce_bounds(self, min_value: float = 0.0, max_value: float = 1.0, max_trust: Optional[float] = 0.3) -> "LambdaVector":
        self.l_cost = max(min_value, min(max_value, float(self.l_cost)))
        self.l_time = max(min_value, min(max_value, float(self.l_time)))
        self.l_risk = max(min_value, min(max_value, float(self.l_risk)))
        self.l_trust = max(min_value, min(max_value, float(self.l_trust)))
        if max_trust is not None:
            self.l_trust = min(self.l_trust, max_trust)
        return self

    def normalize(self) -> "LambdaVector":
        total = float(self.l_cost + self.l_time + self.l_risk + self.l_trust)
        if total <= 0.0:
            self.l_cost = 0.25
            self.l_time = 0.25
            self.l_risk = 0.25
            self.l_trust = 0.25
            return self
        self.l_cost /= total
        self.l_time /= total
        self.l_risk /= total
        self.l_trust /= total
        return self

    def as_dict(self) -> Dict[str, float]:
        return {
            "l_cost": float(self.l_cost),
            "l_time": float(self.l_time),
            "l_risk": float(self.l_risk),
            "l_trust": float(self.l_trust),
        }


@dataclass
class OptimizeInput:
    tasks: List[Task]
    trust_by_agent: Dict[str, float]
    context: Dict[str, Any] = field(default_factory=dict)
    actor: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


@dataclass
class OptimizeDecision:
    decision_id: str
    run_id: str
    timestamp: str
    lambda_vector: Dict[str, float]
    V_prime: Dict[str, Any]
    alignment_score: float
    chosen_task_ids: List[str]
    score_breakdown: Dict[str, Dict[str, float]]

    @staticmethod
    def new(
        run_id: str,
        lambda_vector: Dict[str, float],
        V_prime: Dict[str, Any],
        alignment_score: float,
        chosen_task_ids: List[str],
        score_breakdown: Dict[str, Dict[str, float]],
    ) -> "OptimizeDecision":
        return OptimizeDecision(
            decision_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            lambda_vector=lambda_vector,
            V_prime=V_prime,
            alignment_score=float(alignment_score),
            chosen_task_ids=list(chosen_task_ids),
            score_breakdown=dict(score_breakdown),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "lambda_vector": dict(self.lambda_vector),
            "V_prime": dict(self.V_prime),
            "alignment_score": float(self.alignment_score),
            "chosen_task_ids": list(self.chosen_task_ids),
            "score_breakdown": dict(self.score_breakdown),
        }
