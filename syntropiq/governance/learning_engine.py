from typing import List, Dict
from syntropiq.core.models import ExecutionResult, Agent

def update_trust_scores(
    results: List[ExecutionResult],
    agents: Dict[str, Agent]
) -> Dict[str, float]:
    new_scores = {}

    for result in results:
        agent_id = result.agent_id
        success = result.success

        if agent_id not in agents:
            continue

        current_score = agents[agent_id].trust_score

        if success:
            updated = min(1.0, current_score + 0.02)
        else:
            updated = max(0.0, current_score - 0.05)

        new_scores[agent_id] = round(updated, 3)

    return new_scores

