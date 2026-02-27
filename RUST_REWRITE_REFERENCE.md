# Syntropiq Core Logic — File Reference for Rust Rewrite

---

## LAYER 1: Data Models (start here)

| File | Lines | What Gavin Needs to Know |
|------|------:|--------------------------|
| `syntropiq/core/models.py` | 35 | The entire type system. 4 structs: `Task`, `Agent`, `Assignment`, `ExecutionResult`. These become Rust structs with `serde::Serialize`/`Deserialize`. Everything else in the system operates on these. |
| `syntropiq/core/config.py` | 75 | All tunable parameters. `GovernanceConfig` holds the 7 governance knobs (`trust_threshold`, `suppression_threshold`, `drift_delta`, asymmetric η/γ, `routing_mode`, `max_redemption_cycles`). Rust: a `Config` struct loaded from env/TOML. |
| `syntropiq/core/exceptions.py` | 49 | Error types. 7 error variants — maps directly to a Rust enum: `CircuitBreakerTriggered`, `NoAgentsAvailable`, `TrustScoreInvalid`, etc. |

---

## LAYER 2: Governance Engine (the patent logic — most critical)

| File | Lines | What It Does | Key Algorithm |
|------|------:|--------------|---------------|
| `syntropiq/governance/trust_engine.py` | 237 | **The brain.** Trust-based agent assignment with circuit breaker, suppression/redemption, and drift detection. | `assign_agents()` → update history → detect drift → filter by thresholds → rank (healthy > drifting) → route tasks (reserve low-risk for probation). Lines 60–225 are the entire assignment algorithm. |
| `syntropiq/governance/learning_engine.py` | 29 | Asymmetric trust updates. Success: **+0.02**, Failure: **−0.05**. Accumulates across multiple results per cycle. | Single function `update_trust_scores()`. 29 lines total. |
| `syntropiq/governance/mutation_engine.py` | 211 | Adaptive threshold tuning (Patent Claim 5). Compares success rate to target (85%), tightens or loosens thresholds. Enforces safety band: `suppression >= trust + 0.05`. | `evaluate_and_mutate()` at line 79. Also loads persisted thresholds on init (line 64) for continuity across restarts. |
| `syntropiq/governance/reflection_engine.py` | 31 | RIF — Reflection feedback. Scores cycle outcomes on a 1–4 constraint scale. Flags grounded/recursive/contradiction. | Single function `evaluate_reflection()`. |
| `syntropiq/governance/prioritizer.py` | 29 | Task prioritization (Optimus). Weighted sum: `0.4*impact + 0.3*urgency + 0.3*risk`. Sorts high→low. | `OptimusPrioritizer.optimize()`. |
| `syntropiq/governance/loop.py` | 176 | **The orchestrator.** Wires all 5 engines above into a 7-step cycle: prioritize → assign → execute → learn → mutate → reflect → persist. | `GovernanceLoop.execute_cycle()` at line 67. This is the main entry point. |

**Total governance logic: ~713 lines of Python. That's what the entire patent rests on.**

---

## LAYER 3: Execution Abstraction (the pluggability layer)

| File | Lines | What It Does |
|------|------:|--------------|
| `syntropiq/execution/base.py` | 48 | **The trait.** `BaseExecutor` with two abstract methods: `execute(task, agent) → ExecutionResult` and `validate_agent(agent) → bool`. In Rust: `trait Executor: Send + Sync`. |
| `syntropiq/execution/deterministic_executor.py` | 42 | Test executor. `success = (trust_score - risk) >= threshold`. No randomness. Use this as the first Rust executor for validation. |
| `syntropiq/execution/function_executor.py` | 101 | Callable executor. Wraps arbitrary functions. Rust equivalent: closures or `Box<dyn Fn>`. |
| `syntropiq/execution/llm_executor.py` | 156 | LLM executor. Routes to OpenAI/Anthropic. Rust: use `reqwest` or provider SDKs. This can be ported last — not needed for governance correctness. |

---

## LAYER 4: Persistence (state continuity)

| File | Lines | What It Does |
|------|------:|--------------|
| `syntropiq/persistence/state_manager.py` | 432 | All database operations. 8 SQLite tables: `trust_scores`, `trust_history`, `suppression_state`, `agent_status`, `drift_history`, `execution_results`, `reflections`, `mutation_history`. Every write method and schema is here. Rust: `rusqlite` or `sqlx`. |
| `syntropiq/persistence/agent_registry.py` | 174 | Agent lifecycle. Registration, trust sync, status management. Sits between the governance loop and the database. |

---

## LAYER 5: API Surface (can be ported last)

| File | Lines | What It Does |
|------|------:|--------------|
| `syntropiq/api/server.py` | 225 | FastAPI server setup. Rust: `axum` or `actix-web`. |
| `syntropiq/api/routes.py` | 184 | REST endpoints. 6 routes: submit tasks, register agents, get agent status, stats, mutation history, reflections. |
| `syntropiq/api/schemas.py` | 62 | Request/response DTOs. |

---

## LAYER 6: Demos (reference implementations, not core)

| Directory | What It Demonstrates |
|-----------|----------------------|
| `syntropiq/demo/fraud/` | 3 agents, fraud detection tasks, multi-cycle with circuit breaker recovery |
| `syntropiq/demo/lending/` | Lending risk assessment variant |
| `syntropiq/demo/readmission/` | Hospital readmission prediction variant |
| `syntropiq-finance-demo/` | Market data simulation with real executor |

Each demo has `data.py` (task generation), `executor.py` (custom `BaseExecutor`), and `run.py` (multi-cycle driver with circuit breaker handling).

---

## Recommended Porting Order for Gavin

### Phase 1: Types + Core Algorithm (~150 lines)

```
 1. core/models.py          → Rust structs with serde
 2. core/config.py          → Config struct + env loader
 3. core/exceptions.py      → Error enum
```

### Phase 2: Governance Engine (~540 lines — this IS the product)

```
 4. governance/prioritizer.py        → weighted sort
 5. governance/learning_engine.py    → asymmetric update fn
 6. governance/reflection_engine.py  → constraint scoring fn
 7. governance/trust_engine.py       → THE critical file
 8. governance/mutation_engine.py    → adaptive thresholds
 9. governance/loop.py               → orchestrator
```

### Phase 3: Persistence (~600 lines)

```
10. persistence/state_manager.py    → rusqlite, same schema
11. persistence/agent_registry.py   → agent lifecycle
```

### Phase 4: Execution (~350 lines)

```
12. execution/base.py               → Executor trait
13. execution/deterministic_executor.py → first impl for testing
14. execution/function_executor.py   → closure-based
15. execution/llm_executor.py        → provider integrations
```

### Phase 5: API (~470 lines)

```
16. api/schemas.py   → request/response types
17. api/routes.py     → endpoints
18. api/server.py     → axum/actix setup
```

---

## Critical Constants Gavin Must Not Change

These are embedded in the governance logic and are part of the patent claims:

| Constant | Value | Location | Why It Matters |
|----------|------:|----------|----------------|
| Asymmetric reward (η) | 0.02 | `learning_engine.py:22` | Slow trust gain |
| Asymmetric penalty (γ) | 0.05 | `learning_engine.py:24` | Fast trust loss — 2.5x asymmetry |
| Trust threshold default | 0.7 | `config.py:14` | Minimum for assignment |
| Suppression threshold default | 0.75 | `config.py:15` | Entry into suppression |
| Drift delta | 0.1 | `config.py:16` | Sensitivity to score drops |
| Max redemption cycles | 4 | `trust_engine.py:23` | Recovery attempts before permanent exclusion |
| Probation risk ceiling | 0.4 | `trust_engine.py:24` | Max task risk for suppressed agents |
| Probation task quota | 2 | `trust_engine.py:25` | Low-risk tasks reserved per cycle |
| Mutation rate | 0.05 | `mutation_engine.py:33` | Threshold adjustment step |
| Target success rate | 0.85 | `mutation_engine.py:34` | Feedback loop target |
| Safety band | suppression >= trust + 0.05 | `mutation_engine.py:143` | Prevents unsafe threshold overlap |
| Trust history window | 10 | `trust_engine.py:88` | Entries tracked for drift |
| Priority weights | 0.4 / 0.3 / 0.3 | `prioritizer.py:8-10` | Impact / urgency / risk |

---

**Bottom line:** The entire governance brain is ~713 lines across 6 files in `syntropiq/governance/`. That's what Gavin needs to port with surgical precision. Everything else is infrastructure that wraps it.
