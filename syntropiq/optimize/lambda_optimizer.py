from __future__ import annotations

from typing import Dict, List

from syntropiq.core.models import Task
from syntropiq.optimize.schema import LambdaVector, OptimizeDecision, OptimizeInput


def compute_components(task: Task, trust_term: float) -> Dict[str, float]:
    return {
        "cost": 1.0 - float(task.impact),
        "time": 1.0 - float(task.urgency),
        "risk": float(task.risk),
        "trust": float(trust_term),
    }


def _objective(components: Dict[str, float], lam: LambdaVector) -> float:
    return (
        lam.l_cost * components["cost"]
        + lam.l_time * components["time"]
        + lam.l_risk * components["risk"]
        - lam.l_trust * components["trust"]
    )


def compute_alignment_score(tasks: List[Task], scores: Dict[str, float]) -> float:
    if not tasks:
        return 0.0

    values = [float(scores.get(task.id, 0.0)) for task in tasks]
    low = min(values)
    high = max(values)

    if abs(high - low) < 1e-12:
        normalized = [0.0 for _ in values]
    else:
        normalized = [(value - low) / (high - low) for value in values]

    mean_norm = sum(normalized) / len(normalized)
    alignment = 100.0 * (1.0 - mean_norm)
    return max(0.0, min(100.0, alignment))


def optimize_tasks(input: OptimizeInput, lambda_vector: LambdaVector, run_id: str = "OPT_RUN") -> OptimizeDecision:
    lam = LambdaVector(
        l_cost=lambda_vector.l_cost,
        l_time=lambda_vector.l_time,
        l_risk=lambda_vector.l_risk,
        l_trust=lambda_vector.l_trust,
    )
    lam.enforce_bounds().normalize()

    if input.trust_by_agent:
        trust_term = sum(float(v) for v in input.trust_by_agent.values()) / len(input.trust_by_agent)
    else:
        trust_term = 0.0

    scored = []
    score_breakdown: Dict[str, Dict[str, float]] = {}
    flat_scores: Dict[str, float] = {}

    for task in input.tasks:
        components = compute_components(task, trust_term)
        score = _objective(components, lam)
        scored.append((float(score), str(task.id), task))
        score_breakdown[str(task.id)] = {
            "score": float(score),
            **components,
        }
        flat_scores[str(task.id)] = float(score)

    scored.sort(key=lambda row: (row[0], row[1]))
    ordered_ids = [task_id for _, task_id, _ in scored]

    alignment_score = compute_alignment_score(input.tasks, flat_scores)

    context = dict(input.context or {})
    if input.request_id:
        context.setdefault("request_id", input.request_id)
    if input.actor:
        context.setdefault("actor", input.actor)

    decision = OptimizeDecision.new(
        run_id=run_id,
        lambda_vector=lam.as_dict(),
        V_prime=context,
        alignment_score=alignment_score,
        chosen_task_ids=ordered_ids,
        score_breakdown=score_breakdown,
    )
    return decision
