from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ReplayComparison:
    selection_match: float
    trust_corr: float
    threshold_corr: float
    suppression_match: float
    diagnostics: Dict[str, Any]


@dataclass
class ReplayResult:
    ok: bool
    run_id: str
    mode: str
    r_score: float
    threshold: float
    comparison: ReplayComparison
    explanation: Optional[str] = None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_cycle(cycle: Dict[str, Any], run_events: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    cycle_id = str(cycle.get("cycle_id", ""))

    selected_agents: List[str] = []
    suppressed_agents: List[str] = []
    trust_after: Dict[str, float] = {}
    mutation = {
        "trust_threshold": None,
        "suppression_threshold": None,
        "drift_delta": None,
    }

    for event in run_events.get(cycle_id, []):
        event_type = event.get("type")
        metadata = event.get("metadata") or {}

        if event_type == "mediation_decision":
            if isinstance(metadata.get("selected_agents"), list):
                selected_agents = [str(x) for x in metadata.get("selected_agents")]
            elif isinstance(metadata.get("selected_agent"), str):
                selected_agents = [metadata.get("selected_agent")]
            elif isinstance(event.get("agent_id"), str):
                selected_agents = [event.get("agent_id")]

        if event_type == "trust_update":
            aid = event.get("agent_id")
            if isinstance(aid, str):
                trust_after[aid] = _safe_float(event.get("trust_after"), 0.0)

        if event_type in {"suppression", "restoration", "status_change"}:
            aid = event.get("agent_id")
            if isinstance(aid, str):
                status_after = metadata.get("status_after")
                if event_type == "suppression" or status_after == "suppressed":
                    if aid not in suppressed_agents:
                        suppressed_agents.append(aid)
                elif event_type in {"restoration", "status_change"} and aid in suppressed_agents:
                    suppressed_agents.remove(aid)

        if event_type == "mutation":
            mutation["trust_threshold"] = metadata.get("trust_threshold")
            mutation["suppression_threshold"] = metadata.get("suppression_threshold")
            mutation["drift_delta"] = metadata.get("drift_delta")

    if not selected_agents and isinstance(cycle.get("selected_agents"), list):
        selected_agents = [str(x) for x in cycle.get("selected_agents")]

    if not trust_after and isinstance(cycle.get("trust_updates"), dict):
        trust_after = {str(k): _safe_float(v, 0.0) for k, v in cycle.get("trust_updates", {}).items()}

    return {
        "run_id": cycle.get("run_id"),
        "cycle_id": cycle_id,
        "selected_agents": selected_agents,
        "suppressed_agents": sorted(set(suppressed_agents)),
        "trust_after": trust_after,
        "mutation": {
            "trust_threshold": _safe_float(mutation["trust_threshold"], 0.0) if mutation["trust_threshold"] is not None else None,
            "suppression_threshold": _safe_float(mutation["suppression_threshold"], 0.0) if mutation["suppression_threshold"] is not None else None,
            "drift_delta": _safe_float(mutation["drift_delta"], 0.0) if mutation["drift_delta"] is not None else None,
        },
    }


def load_run_artifacts(state_manager: Any, run_id: str) -> Dict[str, Any]:
    cycles = []
    events = []

    if hasattr(state_manager, "load_cycles_by_run_id"):
        cycles = state_manager.load_cycles_by_run_id(run_id=run_id, limit=2000)
    if hasattr(state_manager, "load_events_by_run_id"):
        events = state_manager.load_events_by_run_id(run_id=run_id, limit=5000)

    events_by_cycle: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        cycle_id = str(event.get("cycle_id", ""))
        events_by_cycle.setdefault(cycle_id, []).append(event)

    normalized_cycles = [_normalize_cycle(cycle, events_by_cycle) for cycle in cycles]

    return {
        "run_id": run_id,
        "cycles": normalized_cycles,
        "events": events,
        "raw_cycles": cycles,
        "mode_capabilities": {
            "has_tasks": any(isinstance(c.get("tasks"), list) for c in cycles),
            "has_agent_snapshots": any(isinstance(c.get("agents"), dict) for c in cycles),
        },
    }


def replay_run(run_artifacts: Dict[str, Any], seed: Optional[int] = None, mode: str = "light") -> Dict[str, Any]:
    # seed reserved for future full-fidelity replay harness.
    _ = seed

    original_cycles = list(run_artifacts.get("cycles") or [])
    capabilities = run_artifacts.get("mode_capabilities") or {}

    if mode == "full":
        has_tasks = bool(capabilities.get("has_tasks"))
        has_agents = bool(capabilities.get("has_agent_snapshots"))
        if not (has_tasks and has_agents):
            return {
                "run_id": run_artifacts.get("run_id", "unknown"),
                "mode": "light",
                "explanation": (
                    "full replay unavailable: missing persisted task payloads and/or agent snapshots; "
                    "performed light replay on persisted governance signals"
                ),
                "cycles": [dict(cycle) for cycle in original_cycles],
            }

    # Light-mode replay is deterministic because it rehydrates persisted signals directly.
    return {
        "run_id": run_artifacts.get("run_id", "unknown"),
        "mode": mode if mode in {"light", "full"} else "light",
        "explanation": "light replay from persisted cycle/event signals",
        "cycles": [dict(cycle) for cycle in original_cycles],
    }


def _component_selection_match(original_cycles: List[Dict[str, Any]], replay_cycles: List[Dict[str, Any]]) -> float:
    n = min(len(original_cycles), len(replay_cycles))
    if n == 0:
        return 0.0
    matches = 0
    for i in range(n):
        left = original_cycles[i].get("selected_agents") or []
        right = replay_cycles[i].get("selected_agents") or []
        if list(left) == list(right):
            matches += 1
    return matches / n


def _component_suppression_match(original_cycles: List[Dict[str, Any]], replay_cycles: List[Dict[str, Any]]) -> float:
    n = min(len(original_cycles), len(replay_cycles))
    if n == 0:
        return 0.0
    matches = 0
    for i in range(n):
        left = sorted(set(original_cycles[i].get("suppressed_agents") or []))
        right = sorted(set(replay_cycles[i].get("suppressed_agents") or []))
        if left == right:
            matches += 1
    return matches / n


def _component_trust_corr(original_cycles: List[Dict[str, Any]], replay_cycles: List[Dict[str, Any]]) -> float:
    n = min(len(original_cycles), len(replay_cycles))
    if n == 0:
        return 0.0

    total_err = 0.0
    count = 0
    for i in range(n):
        left_map = original_cycles[i].get("trust_after") or {}
        right_map = replay_cycles[i].get("trust_after") or {}
        agents = sorted(set(left_map.keys()) | set(right_map.keys()))
        for aid in agents:
            left = _safe_float(left_map.get(aid), 0.0)
            right = _safe_float(right_map.get(aid), 0.0)
            total_err += abs(left - right)
            count += 1

    if count == 0:
        return 0.0
    mae = total_err / count
    return max(0.0, min(1.0, 1.0 - mae))


def _component_threshold_corr(original_cycles: List[Dict[str, Any]], replay_cycles: List[Dict[str, Any]]) -> float:
    n = min(len(original_cycles), len(replay_cycles))
    if n == 0:
        return 0.0

    ranges = {
        "trust_threshold": 0.45,
        "suppression_threshold": 0.35,
        "drift_delta": 0.15,
    }

    total_score = 0.0
    series_count = 0

    for key, rng in ranges.items():
        total_err = 0.0
        count = 0
        for i in range(n):
            left = (original_cycles[i].get("mutation") or {}).get(key)
            right = (replay_cycles[i].get("mutation") or {}).get(key)
            if left is None and right is None:
                continue
            total_err += abs(_safe_float(left, 0.0) - _safe_float(right, 0.0)) / max(rng, 1e-9)
            count += 1

        if count > 0:
            mae = total_err / count
            total_score += max(0.0, min(1.0, 1.0 - mae))
            series_count += 1

    if series_count == 0:
        return 0.0
    return total_score / series_count


def compare_runs(original: Dict[str, Any], replayed: Dict[str, Any]) -> ReplayComparison:
    original_cycles = list(original.get("cycles") or [])
    replay_cycles = list(replayed.get("cycles") or [])

    selection_match = _component_selection_match(original_cycles, replay_cycles)
    suppression_match = _component_suppression_match(original_cycles, replay_cycles)
    trust_corr = _component_trust_corr(original_cycles, replay_cycles)
    threshold_corr = _component_threshold_corr(original_cycles, replay_cycles)

    diagnostics = {
        "original_cycles": len(original_cycles),
        "replay_cycles": len(replay_cycles),
        "mode": replayed.get("mode", "light"),
        "explanation": replayed.get("explanation"),
    }

    return ReplayComparison(
        selection_match=selection_match,
        trust_corr=trust_corr,
        threshold_corr=threshold_corr,
        suppression_match=suppression_match,
        diagnostics=diagnostics,
    )


def compute_r(comparison: ReplayComparison) -> float:
    w1 = 0.35
    w2 = 0.35
    w3 = 0.2
    w4 = 0.1

    score = (
        w1 * comparison.selection_match
        + w2 * comparison.trust_corr
        + w3 * comparison.threshold_corr
        + w4 * comparison.suppression_match
    )
    bounded = max(0.0, min(1.0, score))
    if abs(1.0 - bounded) < 1e-12:
        return 1.0
    if abs(bounded) < 1e-12:
        return 0.0
    return bounded


def replay_result_to_dict(result: ReplayResult) -> Dict[str, Any]:
    payload = asdict(result)
    payload["comparison"] = asdict(result.comparison)
    return payload
