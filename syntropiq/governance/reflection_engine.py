from syntropiq.core.models import ExecutionResult
from typing import List, Dict

def evaluate_reflection(
    execution_results: List[ExecutionResult],
    trust_updates: Dict[str, float],
    prior_memory,
    run_id: str
) -> dict:
    successes = sum(1 for r in execution_results if r.success)
    failures = len(execution_results) - successes

    constraint_score = 3
    if successes == 0:
        constraint_score = 1
    elif successes == len(execution_results):
        constraint_score = 4

    reflection = {
        "timestamp": run_id.replace("RUN_", ""),
        "run_id": run_id,
        "reflection": f"Agent(s) executed {len(execution_results)} tasks with {successes} success(es) and {failures} failure(s).\n"
                      f"Trust updates: {trust_updates}.\n"
                      f"Feedback loop shows changes in routing based on agent trust.",
        "grounded": True,
        "recursive": True,
        "performative_flag": False,
        "contradiction": False,
        "constraint_score": constraint_score
    }

    return reflection