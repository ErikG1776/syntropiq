from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
import uuid


Direction = Literal["max", "min"]
Classification = Literal["stable", "degrading", "crisis"]
Mode = Literal["score", "integrate"]


@dataclass
class ConstraintSpec:
    name: str
    weight: float
    threshold: float
    direction: Direction
    penalty_scale: float = 1.0


@dataclass
class ConstraintPenalty:
    name: str
    value: float
    threshold: float
    penalty: float
    weight: float


@dataclass
class ForesightStep:
    horizon_index: int
    A: float
    D: float
    weighted: float
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectDecision:
    id: str
    run_id: str
    cycle_id: str
    timestamp: str
    mode: Mode
    horizon_steps: int
    weights: Dict[str, float]
    Fs: float
    Fs_threshold: float
    classification: Classification
    penalties: List[ConstraintPenalty]
    foresight: List[ForesightStep]
    advisory: Dict[str, Any]
    metadata: Dict[str, Any]

    @staticmethod
    def new(
        run_id: str,
        cycle_id: str,
        mode: Mode,
        horizon_steps: int,
        weights: Dict[str, float],
        Fs: float,
        Fs_threshold: float,
        classification: Classification,
        penalties: List[ConstraintPenalty],
        foresight: List[ForesightStep],
        advisory: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ReflectDecision":
        return ReflectDecision(
            id=str(uuid.uuid4()),
            run_id=run_id,
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=mode,
            horizon_steps=horizon_steps,
            weights={k: float(v) for k, v in (weights or {}).items()},
            Fs=max(-1.0, min(1.0, float(Fs))),
            Fs_threshold=float(Fs_threshold),
            classification=classification,
            penalties=list(penalties),
            foresight=list(foresight),
            advisory=dict(advisory),
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "mode": self.mode,
            "horizon_steps": int(self.horizon_steps),
            "weights": dict(self.weights),
            "Fs": float(self.Fs),
            "Fs_threshold": float(self.Fs_threshold),
            "classification": self.classification,
            "penalties": [
                {
                    "name": p.name,
                    "value": float(p.value),
                    "threshold": float(p.threshold),
                    "penalty": float(p.penalty),
                    "weight": float(p.weight),
                }
                for p in self.penalties
            ],
            "foresight": [
                {
                    "horizon_index": int(step.horizon_index),
                    "A": float(step.A),
                    "D": float(step.D),
                    "weighted": float(step.weighted),
                    "notes": dict(step.notes),
                }
                for step in self.foresight
            ],
            "advisory": dict(self.advisory),
            "metadata": dict(self.metadata),
        }
