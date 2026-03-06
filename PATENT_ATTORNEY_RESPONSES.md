# Patent Attorney Questions — Technical Responses
**Based on source code review of syntropiq and syngentik-os repositories**
**Date: 2026-03-06**

---

## 1. For the optimization engine: does the formula pick agents, or are agents pre-assigned?

**The formula ranks tasks, not agents. Agents are selected separately by the trust engine.**

The system has two distinct operations that operate sequentially:

1. **Task prioritization/scoring** — `lambda_optimizer.py`: `optimize_tasks()` scores every task using the four-factor formula and returns them in ranked order. It does not select or evaluate agents.
2. **Agent assignment** — `trust_engine.py`: `SyntropiqTrustEngine.assign_agents()` takes the ranked task list and assigns agents to tasks based on trust score alone.

The formula operates on tasks; the trust engine operates on agents. They are separate modules called in sequence inside `governance/loop.py`.

---

## 2. Does the system choose which agent handles each task using the four-factor formula? Or are agents assigned to domains up front?

**Agents are not domain-assigned up front. The trust engine dynamically selects agents per cycle based on trust score.**

In `trust_engine.py`, agents are filtered into `active_agents` (trust ≥ trust_threshold) and `probation_agents` (suppressed but within redemption window). The trust engine then assigns tasks to agents using one of two routing modes:

- **Deterministic** (default): always picks the highest-trust eligible agent — `candidates[0]` after descending sort.
- **Competitive**: trust-weighted probabilistic selection — `random.choices(candidates, weights=[a.trust_score for a in candidates])`.

The four-factor formula's trust term (`T_r`) is a **system-wide average trust score** used to score tasks for ordering, not for selecting individual agents. Trust influences the task ordering; the trust engine then independently selects which agent executes each task.

---

## 3. After the system runs a task, how do you score how well it did on each of the four factors?

The four components are **pre-computed from task attributes before execution**, not scored post-execution on all four dimensions:

```
cost  = 1.0 − task.impact     # lower-impact task = higher cost weight
time  = 1.0 − task.urgency    # lower-urgency task = higher time weight
risk  = task.risk              # direct pass-through
trust = mean(τᵢ for all agents)  # system-wide average trust score
```

**Post-execution**, only the trust dimension is updated:
- `learning_engine.py`: If `result.success == True` → `trust_score += 0.02` (capped at 1.0)
- `learning_engine.py`: If `result.success == False` → `trust_score -= 0.05` (floored at 0.0)

Cost, time, and risk components are **not re-scored post-execution** — they are task-level properties set before the task runs. The four-factor formula is a task-selection/ordering tool; the trust update is the performance feedback mechanism.

---

## 4. Example of a full run-through with real numbers

**Setup:**
- 3 agents: RuleModel (τ=0.82), MLModel (τ=0.84), VendorAPI (τ=0.80)
- Lambda vector (default): λ_cost=0.25, λ_time=0.25, λ_risk=0.25, λ_trust=0.25
- Trust term: T_r = (0.82 + 0.84 + 0.80) / 3 = **0.82**

**3 tasks:**

| Task | impact | urgency | risk |
|------|--------|---------|------|
| T1   | 0.90   | 0.80    | 0.10 |
| T2   | 0.50   | 0.50    | 0.30 |
| T3   | 0.30   | 0.90    | 0.20 |

**Step 1 — Compute components for each task:**

| Task | cost (1−impact) | time (1−urgency) | risk | trust |
|------|-----------------|-----------------|------|-------|
| T1   | 0.10            | 0.20            | 0.10 | 0.82  |
| T2   | 0.50            | 0.50            | 0.30 | 0.82  |
| T3   | 0.70            | 0.10            | 0.20 | 0.82  |

**Step 2 — Apply objective function:** `Score = λ_cost·C + λ_time·T + λ_risk·R − λ_trust·T_r`

| Task | Score calculation                                         | Score  |
|------|----------------------------------------------------------|--------|
| T1   | 0.25(0.10) + 0.25(0.20) + 0.25(0.10) − 0.25(0.82)      | **−0.105** |
| T2   | 0.25(0.50) + 0.25(0.50) + 0.25(0.30) − 0.25(0.82)      | **+0.120** |
| T3   | 0.25(0.70) + 0.25(0.10) + 0.25(0.20) − 0.25(0.82)      | **+0.045** |

**Step 3 — Rank tasks ascending (lower score = higher priority):** T1 → T3 → T2

**Step 4 — Agent assignment (deterministic mode):**
MLModel (trust=0.84) is highest-trust active agent → assigned to all tasks.

**Step 5 — Execution and trust update:**
- T1 succeeds → MLModel trust: 0.84 + 0.02 = **0.86**
- T3 fails → MLModel trust: 0.86 − 0.05 = **0.81**
- T2 succeeds → MLModel trust: 0.81 + 0.02 = **0.83**

**Final state:** MLModel trust=0.83, all tasks executed.

---

## 5. When you say higher-trust agents get bigger optimization steps, what's the actual relationship?

**This relationship is not in the lambda optimizer.** The lambda formula applies the same λ weights to all tasks regardless of which agent will execute them.

What IS trust-proportional in the code:
- In **competitive routing mode** (`trust_engine.py`): `P(agent_i selected) = τᵢ / Σ(τⱼ)` — higher-trust agents are proportionally more likely to be selected.
- In the **healing reflex** (`loop.py`): the rehabilitation step size (`HEALING_TRUST_STEP`, default 0.02) is uniform regardless of trust level — it is not trust-proportional.

The "20% corrective step on each dimension of the state vector" described in the provisionals does not appear in either repository's current implementation. This may require clarification about what document section introduced that framing.

---

## 6. The objective function and the solver/optimization method appear to operate on different things

**Correct — these are two separate operations that should be described distinctly.**

From the code:

- **The objective function** (`lambda_optimizer.py`) operates on **tasks**: it scores each task and returns an ordered list. The formula is: `Score(task) = λ_cost·C(task) + λ_time·T(task) + λ_risk·R(task) − λ_trust·T_r`. This is a **task ranker**.

- **The state vector corrective step** ("S₀[k] = S₀[k] − (S₀[k] − S₁[k]) × 0.20") does not appear in the current codebase. If this was intended to describe the mutation engine's threshold adjustments, those are computed as: `new_threshold = old_threshold ± (mutation_rate × 0.2)` — but they operate on governance thresholds, not a state vector.

**The correct description of the flow is:**
1. Task objective function ranks tasks → sorted task list
2. Trust engine assigns agents to ranked tasks
3. Executors run tasks
4. Learning engine updates trust scores (+0.02 / −0.05)
5. Mutation engine adjusts governance thresholds based on overall success rate

No candidate agent is "evaluated by running the state optimizer." Agent selection is trust-score-based only.

---

## 7. T_r in the objective function appears undefined

**T_r is the mean trust score across all active agents in the current cycle.**

From `lambda_optimizer.py`:
```python
if input.trust_by_agent:
    trust_term = sum(float(v) for v in input.trust_by_agent.values()) / len(input.trust_by_agent)
else:
    trust_term = 0.0
```

`trust_by_agent` is a dict of `{agent_id: τᵢ}` passed in at cycle start. T_r is therefore:

**T_r = (1/N) · Σ τᵢ**   where τᵢ is each agent's current `trust_score` and N is the number of active agents.

It is **not** the individual agent trust score τᵢ, and it is **not** the Bayesian posterior E[p]. It is a system-level scalar that represents the collective trust state of the agent pool.

---

## 8. In the optimization formula, what number actually goes in as T_r?

The number is the **arithmetic mean of all active agents' trust scores** at the start of the cycle.

Example: If RuleModel=0.82, MLModel=0.84, VendorAPI=0.80:
**T_r = (0.82 + 0.84 + 0.80) / 3 = 0.82**

This single scalar is used identically for all tasks in the same cycle. T_r does not vary per task within a cycle.

---

## 9. When you showed the Bayesian example with Agent_A getting 0.69 and Agent_B getting 0.31 after normalization, are those the T_r values?

**No.** Those normalized Bayesian probabilities are not T_r values and do not feed into the four-factor formula.

In the codebase, the Bayesian module (`bayes_posterior.py`) produces a `posterior_mean` for each agent based on their historical success/failure count using a Beta distribution with Laplace (uniform) prior (α₀=1, β₀=1):

```
posterior_mean = (α₀ + successes) / (α₀ + β₀ + successes + failures)
```

This `posterior_mean` is used for two things:
1. **Healing reflex gate** (`loop.py`): determines whether a suppressed agent is eligible for rehabilitation (`posterior_mean ≥ HEALING_POSTERIOR_MEAN_MIN`, default 0.80).
2. **Risk adjustment**: `suggested_risk_multiplier` increases if `posterior_mean < 0.6` or uncertainty is high.

The normalized probabilities (0.69/0.31 style) may describe the competitive routing weights: `P(agent_i) = τᵢ / Σ(τⱼ)`. These are routing selection probabilities, **not inputs to the four-factor formula**.

---

## 10. When a new agent joins with no track record, how does the optimization engine handle it for the first few cycles?

**New agents receive a Laplace (uniform) prior; the trust engine uses their initial trust_score directly.**

For the **Bayesian module** (`bayes_posterior.py`): with 0 successes and 0 failures, α₀=1, β₀=1:
- `posterior_mean = 1 / (1+1) = 0.50` (neutral prior, maximum uncertainty)
- `posterior_uncertainty = 1 / (1+1) = 0.50`
- `suggested_risk_multiplier = 1.30` (both mean < 0.6 and high uncertainty penalties apply)

For the **trust engine** (`trust_engine.py`): new agents carry their initial `trust_score` set at registration (default agents start at 0.80–0.84). If their initial score ≥ `trust_threshold` (default 0.70), they immediately enter the active pool.

For the **healing reflex** (`loop.py`): the posterior_mean minimum gate (0.80) means a new agent with no history (posterior_mean=0.50) would **not** be eligible for rehabilitation if suppressed, until it builds a sufficient success track record.

There is no warm-up isolation period — new agents are eligible for task assignment from cycle 1 if their initial trust_score clears the threshold.

---

## 11. What counts as "Success" or "Failure" for non-text production task types?

**Success is a boolean field set by the executor, not by the governance system.**

`ExecutionResult` in `core/models.py`:
```python
class ExecutionResult(BaseModel):
    task_id: str
    agent_id: str
    success: bool       # ← set by the executor
    latency: float
    metadata: Optional[dict] = {}
```

The governance system (trust engine, learning engine, Bayesian module) treats `success` as an opaque boolean. The definition of success is entirely determined by the **executor implementation** for each domain. In the demo executors (fraud, lending, readmission), success criteria are domain-specific. For non-text tasks, the executor author defines what constitutes a pass or fail and sets `success=True/False` accordingly.

**This is a gap in the provisionals that needs to be addressed.** The patent should describe the executor interface contract (the `success` boolean) and give examples of how different domain executors implement it (threshold breach = failure for fraud; prediction accuracy = failure for ML models; etc.).

---

## 12. What does the system actually check to decide whether a task was done well or poorly?

**The system uses the binary `success` boolean from the executor. There is no multi-dimensional task quality evaluation in the current implementation.**

From `reflection_engine.py`, the `constraint_score` is a 4-tier value derived purely from counting successes:

```python
constraint_score = 3                          # default
if successes == 0:
    constraint_score = 1                      # all failed
elif successes == len(execution_results):
    constraint_score = 4                      # all succeeded
```

Scores 2 and 3 are partially populated (3 is the default for mixed results; 2 is not currently emitted). The reflection engine does not examine task output content, latency quality bands, or other dimensions — it counts binary success/failure outcomes.

**Text quality score**: not applicable as a concept in the current codebase. All task types use the binary success boolean.

---

## 13. When the Bayesian ranker counts successes and failures, is it using the same definition of success as the trust update?

**Yes — both use the same binary `result.success` boolean from `ExecutionResult`.**

Trust update (`learning_engine.py`):
```python
if success:   # result.success
    updated = min(1.0, current_score + 0.02)
else:
    updated = max(0.0, current_score - 0.05)
```

Bayesian input (`loop.py` → telemetry cycle record):
```python
"successes": sum(1 for r in results if r.success),
"failures":  sum(1 for r in results if not r.success),
```

Both count from `result.success`. They are consistent.

**The 4-tier quality score** (`constraint_score` in `reflection_engine.py`) is a **separate, parallel output** used for reflection metadata only — it does not feed back into trust updates or Bayesian counts. This distinction should be made explicit in the provisionals to avoid confusion.

---

## 14. For the grounding check: how does the system decide whether a proposed action is based on real information?

**The grounding check is currently a stub — it always returns `True`.**

From `reflection_engine.py`:
```python
reflection = {
    ...
    "grounded": True,   # always True — not evaluated
    ...
}
```

There is no knowledge base lookup, citation check, or model-based grounding verification in the current codebase. The grounding flag is a placeholder field in the reflection record.

**For the patent**: This should either (a) be described as a planned/future mechanism with an architectural description of how it would work, or (b) the claim should be narrowed to exclude the grounding check until it is implemented. Describing it as "the system checks grounding" when the implementation always returns True could create prosecution problems.

---

## 15. For the recursive validity check: how does the system know if a proposed action would undo a previous improvement?

**The recursive validity check is currently a stub — it always returns `True`.**

From `reflection_engine.py`:
```python
"recursive": True,   # always True — not evaluated
```

The mutation engine does maintain history (`mutation_history`) and enforces monotonicity rules (e.g., warmup blocks loosening, suppression dampening blocks loosening while an agent is suppressed), which is the closest functional analog. However, the `recursive` field in the reflection record is not connected to any of that logic.

---

## 16. For the performative check: how does the system catch an agent making statements it shouldn't?

**The performative check is currently a stub — it always returns `False` (no flag).**

From `reflection_engine.py`:
```python
"performative_flag": False,   # always False — not evaluated
```

There is no phrase detection, NLP filter, or output scanner for unauthorized statements. This is a placeholder.

---

## 17. Are the consistency check in the quality evaluator and the contradiction check in the constraint evaluation the same operation, or different ones?

**They are architecturally different operations, though both are currently stubs.**

- **`contradiction` in the reflection engine** (`reflection_engine.py`): intended to detect logical contradictions in agent outputs. Currently always `False`.

- **Constraint evaluation** (`constraint_kernel.py`): checks five system-state metrics (trust_floor, suppression_rate, drift_limit, instability, reproducibility) against numerical thresholds. This is a quantitative system health check, not a semantic consistency check.

They are different operations: reflection checks agent output semantics (stub); constraint evaluation checks system state numerics (implemented). They should be named distinctly in the patent — e.g., "output contradiction check" vs. "system constraint evaluation."

---

## 18. What are the "aspiration levels" (A_i) in the formula for the foresight score?

**In the code, the variable `A` at each horizon step is a risk-adjusted average trust level, not a goal target in the classical satisficing sense.**

From `fs_score.py`:
```python
drift_proxy = clamp(drift_delta / 0.2, 0.0, 1.0)
risk_proxy   = max(drift_proxy, clamp(failure_rate, 0.0, 1.0))

# Per horizon step:
avg_trust = mean(trust values projected for this step)
A = clamp(avg_trust − risk_proxy, 0.0, 1.0)
```

`A` = projected average trust for a future horizon step, penalized by the current risk level (which combines the drift rate and the recent failure rate). It represents "how much usable trust does the system expect to have available, net of risk, at time step i?"

`D` (disruption) at each step is:
```python
delta = |avg_trust_this_step − avg_trust_previous_step|
suppression_indicator = 0.2 if suppression_active else 0.0
D = clamp(delta + suppression_indicator, 0.0, 1.0)
```

The foresight score per step = `w_i × (A − D)`, summed over horizon.

---

## 19. Example walkthrough of a foresight score calculation with actual numbers

**Setup:**
- 2 agents: trust = [0.80, 0.75], avg = 0.775
- drift_delta = 0.10, failure_rate = 0.20
- horizon_steps = 3, decay = 0.85, suppression_active = False
- expected_delta (recent per-agent trust change) = +0.005

**Step 1 — Compute weights** (geometric decay, normalized):
- raw: [1.0, 0.85, 0.7225], total = 2.5725
- w₀ = 0.389, w₁ = 0.330, w₂ = 0.281

**Step 2 — Project trust forward** (`foresight.py`):
- Step 0: both agents += 0.005 → [0.805, 0.755], avg = 0.780
- Step 1: both agents += 0.005 → [0.810, 0.760], avg = 0.785
- Step 2: both agents += 0.005 → [0.815, 0.765], avg = 0.790

**Step 3 — Compute risk_proxy:**
- drift_proxy = clamp(0.10 / 0.20, 0, 1) = **0.50**
- risk_proxy = max(0.50, 0.20) = **0.50**

**Step 4 — Compute A and D per step:**

| Step | avg_trust | A = avg−risk_proxy | delta from prev | D  | w     | w×(A−D)  |
|------|-----------|--------------------|-----------------|----|-------|----------|
| 0    | 0.780     | 0.280              | 0 (first)       | 0.0| 0.389 | +0.109   |
| 1    | 0.785     | 0.285              | 0.005           | 0.005| 0.330 | +0.092 |
| 2    | 0.790     | 0.290              | 0.005           | 0.005| 0.281 | +0.079 |

**Step 5 — Raw Fs** = 0.109 + 0.092 + 0.079 = **0.280**

**Step 6 — Apply constraint penalties** (from `constraint_kernel.py`):
Assume min_trust=0.75 ≥ trust_threshold=0.70, suppression_count=0, instability=0 → total_penalty ≈ 0.0

**Final Fs** = clamp(0.280 − 0.0, −1, 1) = **0.280**

θ = 0.10 → Fs (0.280) ≥ θ → **classification: "stable", action: "hold"**

---

## 20. When the foresight score drops below the threshold, what specifically changes?

**The reflect engine issues an advisory only. The mutation engine implements the actual threshold changes.**

From `reflect/engine.py`:
```python
theta = 0.10    # default Fs threshold
margin = 0.10

if Fs >= theta:                   → "stable" / action = "hold"
elif Fs >= (theta - margin):      → "degrading" / action = "tighten"
else:                             → "crisis" / action = "tighten"

advisory = {
    "recommended_deltas": {
        "trust_threshold":        +0.01 if tighten else 0.0,
        "suppression_threshold":  +0.01 if tighten else 0.0,
        "drift_delta":            0.0,
    },
    "non_binding": True,          # ← advisory only
}
```

The advisory is stored in the reflect decision record but is marked `non_binding`. The actual threshold changes are applied by the **mutation engine** (`mutation_engine.py`) which responds to the cycle's observed success rate, not directly to the Fs score. The reflect and mutation engines operate in parallel with no direct dependency between them in the current implementation.

---

## 21. When the circuit breaker fires, what happens to tasks that are coming in?

**Tasks are rejected — no queueing mechanism exists in the current implementation.**

From `trust_engine.py`:
```python
if not active_agents and not probation_agents:
    raise RuntimeError("No trusted agents available — system halted to avoid unsafe execution.")
```

From `loop.py`:
```python
try:
    assignments = self.trust_engine.assign_agents(sorted_tasks, agents)
except RuntimeError as e:
    raise CircuitBreakerTriggered(str(e))
```

`CircuitBreakerTriggered` propagates to the caller of `execute_cycle()`. The caller receives an exception; tasks in that cycle are dropped. There is no queue, no retry buffer, and no graceful degradation path beyond probation agents (who can still take low-risk tasks). If even probation agents are exhausted, all tasks in that cycle are lost.

---

## 22. When a suspended agent passes all 4 redemption cycles and comes back, what trust score does it come back with? If a suspended agent has 3 good cycles but fails on the 4th, does the counter reset?

**Recovery is trust-score-based, not cycle-count-based. The counter does not reset.**

From `trust_engine.py`:
```python
MAX_REDEMPTION_CYCLES = 4

if agent.trust_score >= self.suppression_threshold:
    # Recovered → moved to active_agents
    del self.suppressed_agents[agent_id]
elif cycles <= self.MAX_REDEMPTION_CYCLES:
    self.suppressed_agents[agent_id] += 1   # increment cycle count
    probation_agents.append(agent)
else:
    # Permanently excluded — removed from pool entirely
    continue
```

- An agent **recovers** when its `trust_score` rises back above `suppression_threshold` (default 0.75), regardless of how many cycles it's been in suppression.
- It comes back with **whatever trust_score it has accumulated through probation work**. Probation agents receive up to 2 low-risk tasks per cycle (PROBATION_TASK_QUOTA=2, risk ≤ 0.4), earning +0.02 per success.
- The cycle counter **monotonically increments each cycle** — it does not reset if cycle 4 fails. An agent suppressed at cycle 1 that reaches cycle 4 without its trust recovering is permanently excluded regardless of individual cycle outcomes.
- After 4 cycles without trust recovery → permanent exclusion. No reset, no second chance.

---

## 23. While an agent is suspended, how does it get the chance to demonstrate stability?

**Suspended agents receive real low-risk production tasks, up to 2 per cycle.**

From `trust_engine.py`:
```python
PROBATION_RISK_CEILING = 0.4   # only tasks with risk ≤ 0.4
PROBATION_TASK_QUOTA = 2       # max 2 per cycle

if (ranked_probation
        and task.risk <= self.PROBATION_RISK_CEILING
        and probation_assigned < self.PROBATION_TASK_QUOTA):
    agent = self._select_agent(ranked_probation)
    assignments.append(Assignment(task_id=task.id, agent_id=agent.id))
```

These are **not simulated test tasks** — they are real tasks from the incoming queue that happen to have risk ≤ 0.4. Successful execution earns +0.02 per task per `learning_engine.py`. At maximum (2 successes/cycle), it takes approximately 3 cycles to recover from a single failure (which deducted −0.05) and reach recovery threshold.

---

## 24. The asymmetrical reward/penalty system: can you clarify?

**The current code uses magnitude-asymmetric binary updates. The tiered lookup with equal extremes is not implemented.**

From `learning_engine.py` (the implemented system):
```python
if success:
    updated = min(1.0, current_score + 0.02)   # reward
else:
    updated = max(0.0, current_score - 0.05)   # penalty
```

This is **magnitude-asymmetric**: penalty (0.05) is 2.5× the reward (0.02). A single failure requires 3 successes to offset (`3 × 0.02 = 0.06 > 0.05`).

The "tiered lookup with +0.05/−0.05 equal extremes" described in the provisionals is **not in the codebase**. The "alternative formula (η=0.02, γ=0.05)" matches the implemented code exactly.

**Recommendation for the patent:** Describe the implemented system (binary asymmetric updates: +η on success, −γ on failure, where γ > η) as the primary mechanism. If tiered quality scoring is intended, it should be implemented and tested before being included in claims.

---

## 25. The word "confidence" is used for three different concepts. Are they the same measurement?

**No — they are three distinct concepts that happen to share a label. Each should have a distinct name.**

| Use | Location | What it measures | Suggested distinct name |
|-----|----------|-----------------|------------------------|
| (1) Certainty about a specific output | Reflection engine (`reflection_engine.py`) | Currently a stub — always True/False | **Output certainty** |
| (2) Reliability of a knowledge graph edge | Not found in current codebase | N/A — may be from provisionals description | **Edge reliability** |
| (3) Agent voting weight in multi-agent selection | Trust engine competitive mode (`trust_engine.py`) | `τᵢ / Σ(τⱼ)` — normalized trust score | **Selection weight** or **routing authority** |

In `fs_score.py`, there is a `confidence_factor(mean, uncertainty)` function:
```python
def confidence_factor(mean: float, uncertainty: float) -> float:
    return mean * (1.0 - uncertainty)    # = posterior_mean × (1 − posterior_uncertainty)
```
This is used in the healing reflex pathway and represents a **Bayesian confidence** in an agent's historical performance. This is a fourth distinct concept that also currently carries the "confidence" label.

**Recommendation:** Define four distinct terms in the patent claims: (1) output certainty, (2) edge reliability, (3) routing authority (normalized trust weight), and (4) Bayesian performance confidence (posterior_mean × (1 − uncertainty)).

---

## Attachment: Requested Source Files

The patent attorney requested `trust_engine.py` and `constraint_kernel.py`. Both files are located at:

- **trust_engine.py**: `syntropiq/governance/trust_engine.py`
- **constraint_kernel.py**: `syntropiq/reflect/constraint_kernel.py`

Copies are included as attachments to this response.

---

## Summary of Gaps Identified

The following items in the provisionals describe things that are **not yet implemented** in the current codebase and need clarification for patent strategy:

| Item | Status |
|------|--------|
| Grounding check | Stub — always returns True |
| Recursive validity check | Stub — always returns True |
| Performative statement check | Stub — always returns False |
| State vector corrective step (20%) | Not found in codebase |
| Tiered quality score lookup (±0.05 equal extremes) | Not found in codebase |
| Knowledge graph edge confidence | Not found in codebase |
| Task queuing on circuit breaker | Not implemented — tasks are dropped |
