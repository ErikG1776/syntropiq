from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, Optional


@dataclass
class InvariantViolation:
    name: str
    severity: str
    expected: str
    actual: str
    context: Mapping[str, Any]


class Invariants:
    @staticmethod
    def check_tau_range(tau: Optional[float], min: float = 0.5, max: float = 0.95) -> List[InvariantViolation]:
        if tau is None:
            return []
        if min <= tau <= max:
            return []
        return [
            InvariantViolation(
                name="tau_range",
                severity="warn",
                expected=f"{min} <= tau <= {max}",
                actual=str(tau),
                context={"tau": tau, "min": min, "max": max},
            )
        ]

    @staticmethod
    def check_delta_bound(delta: Optional[float], max_abs: float = 0.05) -> List[InvariantViolation]:
        if delta is None:
            return []
        if abs(delta) <= max_abs:
            return []
        return [
            InvariantViolation(
                name="delta_bound",
                severity="warn",
                expected=f"|delta| <= {max_abs}",
                actual=str(delta),
                context={"delta": delta, "max_abs": max_abs},
            )
        ]

    @staticmethod
    def check_gamma_eta(gamma: Optional[float], eta: Optional[float]) -> List[InvariantViolation]:
        if gamma is None or eta is None:
            return []
        if gamma > eta:
            return []
        return [
            InvariantViolation(
                name="gamma_eta",
                severity="warn",
                expected="gamma > eta",
                actual=f"gamma={gamma}, eta={eta}",
                context={"gamma": gamma, "eta": eta},
            )
        ]

    @staticmethod
    def check_lambda_simple(lambda_vec: Optional[Iterable[float]]) -> List[InvariantViolation]:
        # Stub for future Optimize enforcement: keep non-blocking and conservative.
        if lambda_vec is None:
            return []
        values = list(lambda_vec)
        if not values:
            return []
        violations: List[InvariantViolation] = []
        total = sum(values)
        if abs(total - 1.0) > 1e-6:
            violations.append(
                InvariantViolation(
                    name="lambda_sum",
                    severity="warn",
                    expected="sum(lambda_i) == 1.0",
                    actual=str(total),
                    context={"lambda": values, "sum": total},
                )
            )
        if any(v < 0.0 or v > 1.0 for v in values):
            violations.append(
                InvariantViolation(
                    name="lambda_bounds",
                    severity="warn",
                    expected="0.0 <= lambda_i <= 1.0",
                    actual=str(values),
                    context={"lambda": values},
                )
            )
        return violations

    @staticmethod
    def check_cooldown_bound(cooldown_cycles: Optional[int], max_cycles: int = 3) -> List[InvariantViolation]:
        if cooldown_cycles is None:
            return []
        if cooldown_cycles <= max_cycles:
            return []
        return [
            InvariantViolation(
                name="cooldown_bound",
                severity="warn",
                expected=f"cooldown_cycles <= {max_cycles}",
                actual=str(cooldown_cycles),
                context={"cooldown_cycles": cooldown_cycles, "max_cycles": max_cycles},
            )
        ]

    @staticmethod
    def check_request_id_present(request_id: Optional[str]) -> List[InvariantViolation]:
        if request_id and request_id.strip():
            return []
        return [
            InvariantViolation(
                name="request_id_present",
                severity="warn",
                expected="non-empty request_id",
                actual=str(request_id),
                context={"request_id": request_id},
            )
        ]


def mode_from_env() -> str:
    mode = (os.getenv("INVARIANTS_MODE") or "log").strip().lower()
    if mode in {"off", "log", "enforce"}:
        return mode
    return "log"


def emit_violations(
    telemetry_hub: Any,
    violations: Iterable[InvariantViolation],
    base_metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    mode = mode_from_env()
    if mode == "off" or telemetry_hub is None:
        return

    metadata_base = dict(base_metadata or {})
    for violation in violations:
        metadata = {
            **metadata_base,
            "invariant": violation.name,
            "expected": violation.expected,
            "actual": violation.actual,
            "context": dict(violation.context),
            "invariants_mode": mode,
        }
        event = {
            "run_id": str(metadata_base.get("run_id") or "INVARIANTS"),
            "cycle_id": str(metadata_base.get("cycle_id") or "INVARIANTS"),
            "timestamp": str(metadata_base.get("timestamp") or ""),
            "type": "system_alert",
            "agent_id": None,
            "trust_before": 0.0,
            "trust_after": 0.0,
            "authority_before": 0.0,
            "authority_after": 0.0,
            "metadata": metadata,
        }
        if hasattr(telemetry_hub, "publish_event"):
            telemetry_hub.publish_event(event)
        elif hasattr(telemetry_hub, "publish_events"):
            telemetry_hub.publish_events([event])

        # Phase 1 behavior: enforce is reserved; keep non-blocking.
        if mode == "enforce":
            # TODO(phase-2): raise blocking errors for high-severity violations.
            pass
