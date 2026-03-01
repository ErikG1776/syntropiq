import pytest

from syntropiq.core.models import Task
from syntropiq.optimize.lambda_optimizer import compute_alignment_score, optimize_tasks
from syntropiq.optimize.schema import LambdaVector, OptimizeInput


def test_lambda_normalization_sums_to_one():
    lam = LambdaVector(l_cost=2.0, l_time=1.0, l_risk=1.0, l_trust=0.5)
    lam.enforce_bounds(max_trust=None).normalize()

    total = lam.l_cost + lam.l_time + lam.l_risk + lam.l_trust
    assert total == pytest.approx(1.0)


def test_higher_trust_reduces_objective_score():
    task = Task(id="t1", impact=0.7, urgency=0.6, risk=0.2, metadata={})
    lam = LambdaVector(l_cost=0.25, l_time=0.25, l_risk=0.25, l_trust=0.25).enforce_bounds(max_trust=None).normalize()

    low_trust = optimize_tasks(
        OptimizeInput(tasks=[task], trust_by_agent={"a": 0.2}, context={}),
        lam,
        run_id="RUN_LOW",
    )
    high_trust = optimize_tasks(
        OptimizeInput(tasks=[task], trust_by_agent={"a": 0.9}, context={}),
        lam,
        run_id="RUN_HIGH",
    )

    assert high_trust.score_breakdown["t1"]["score"] < low_trust.score_breakdown["t1"]["score"]


def test_deterministic_tie_breaker_by_task_id():
    tasks = [
        Task(id="b-task", impact=0.5, urgency=0.5, risk=0.5, metadata={}),
        Task(id="a-task", impact=0.5, urgency=0.5, risk=0.5, metadata={}),
    ]
    lam = LambdaVector(l_cost=0.25, l_time=0.25, l_risk=0.25, l_trust=0.25).enforce_bounds(max_trust=None).normalize()

    decision = optimize_tasks(
        OptimizeInput(tasks=tasks, trust_by_agent={"a": 0.5}, context={}),
        lam,
        run_id="RUN_TIE",
    )

    assert decision.chosen_task_ids == ["a-task", "b-task"]


def test_alignment_score_bounds():
    tasks = [
        Task(id="t1", impact=0.9, urgency=0.9, risk=0.1, metadata={}),
        Task(id="t2", impact=0.2, urgency=0.3, risk=0.8, metadata={}),
    ]
    scores = {"t1": 0.1, "t2": 0.8}

    alignment = compute_alignment_score(tasks, scores)
    assert 0.0 <= alignment <= 100.0
