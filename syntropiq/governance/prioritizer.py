from typing import List
from syntropiq.core.models import Task


class OptimusPrioritizer:
    def __init__(self):
        self.weights = {
            "impact": 0.4,
            "urgency": 0.3,
            "risk": 0.3
        }

    def optimize(self, tasks: List[Task]) -> dict:
        def score(task: Task) -> float:
            # Score = weighted sum of impact, urgency, risk
            cost = task.impact
            time = task.urgency
            risk = task.risk
            return (
                self.weights["impact"] * cost
                + self.weights["urgency"] * time
                + self.weights["risk"] * risk
            )

        sorted_tasks = sorted(tasks, key=score, reverse=True)
        return {
            "sorted_tasks": sorted_tasks,
            "total_tasks": len(sorted_tasks),
            "input_type": "fraud_detection"
        }