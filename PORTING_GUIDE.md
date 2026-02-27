# Syntropiq Codebase — Porting Guide

> Complete inventory of every file, its purpose, key classes/functions, internal dependencies, and dependents.
> Use this to trace any change's impact across the system.

---

## Dependency Graph (Quick Reference)

```
governance/loop.py  (orchestrator)
├── prioritizer.py          (task scoring)
├── trust_engine.py         (agent assignment, suppression, drift)
├── learning_engine.py      (trust score updates)
├── mutation_engine.py      (adaptive threshold tuning)
├── reflection_engine.py    (RIF constraint scoring)
├── persistence/state_manager.py  (SQLite state)
└── core/models.py          (Task, Agent, ExecutionResult)

execution/base.py  (ABC)
├── deterministic_executor.py  (testing)
├── function_executor.py       (custom callables)
└── llm_executor.py            (OpenAI / Anthropic)

api/server.py  (FastAPI + global state)
├── routes.py   (8 REST endpoints)
└── schemas.py  (request/response validation)

persistence/
├── state_manager.py   (SQLite, 8-table schema)
└── agent_registry.py  (agent lifecycle, trust sync)
```

---

## 1. Core Governance (6 files)

### `syntropiq/governance/loop.py` — Orchestrator

Coordinates all governance components in a synchronous 7-step cycle:
prioritization → assignment → execution → trust update → mutation → reflection → persistence.

| Item | Detail |
|------|--------|
| **Class** | `GovernanceLoop` |
| **Key methods** | `execute_cycle()`, `get_agent_status()`, `get_system_statistics()` |
| **Imports** | `core.models`, `core.exceptions`, `governance.prioritizer`, `governance.trust_engine`, `governance.learning_engine`, `governance.reflection_engine`, `governance.mutation_engine`, `persistence.state_manager` |
| **Used by** | API routes, demo scripts, tests |

---

### `syntropiq/governance/trust_engine.py` — Trust-Based Assignment

Core decision engine. Implements circuit breaker, suppression/redemption cycles, and preemptive drift detection.

| Item | Detail |
|------|--------|
| **Class** | `SyntropiqTrustEngine` |
| **Key methods** | `assign_agents()`, `_filter_agents()`, `_create_assignments()`, `_detect_drift()`, `_select_agent()` |
| **Routing modes** | Deterministic vs. competitive |
| **Imports** | `core.models` (Task, Agent, Assignment), `persistence.state_manager` (optional) |
| **Used by** | `governance.loop` |
| **Syncs with** | `governance.mutation_engine` (threshold values) |

---

### `syntropiq/governance/mutation_engine.py` — Adaptive Threshold Tuning

Adjusts `trust_threshold`, `suppression_threshold`, and `drift_delta` to balance safety vs. throughput (Patent Claim 5).

| Item | Detail |
|------|--------|
| **Class** | `MutationEngine` |
| **Key methods** | `evaluate_and_mutate()`, `_load_persisted_state()`, `get_mutation_history()`, `get_performance_trend()` |
| **Imports** | `core.models` (ExecutionResult), `persistence.state_manager` (optional) |
| **Used by** | `governance.loop` |
| **Syncs with** | `governance.trust_engine` (thresholds synced back) |

---

### `syntropiq/governance/learning_engine.py` — Asymmetric Trust Updates

Updates agent trust scores from execution results. Success: **+0.02**, Failure: **−0.05** (asymmetric reward/penalty).

| Item | Detail |
|------|--------|
| **Function** | `update_trust_scores()` |
| **Imports** | `core.models` (ExecutionResult, Agent) |
| **Used by** | `governance.loop` |

---

### `syntropiq/governance/reflection_engine.py` — RIF (Reflexive Integration Framework)

Generates reflection on governance cycle outcomes. Evaluates constraint scores (1–4) based on success/failure distribution.

| Item | Detail |
|------|--------|
| **Function** | `evaluate_reflection()` |
| **Imports** | `core.models` (ExecutionResult) |
| **Used by** | `governance.loop` |

---

### `syntropiq/governance/prioritizer.py` — Task Prioritization

Weighted scoring on impact, urgency, and risk.

| Item | Detail |
|------|--------|
| **Class** | `OptimusPrioritizer` |
| **Key methods** | `optimize()` — sort tasks by composite score |
| **Imports** | `core.models` (Task) |
| **Used by** | `governance.loop` |

---

## 2. Data Models (3 files)

### `syntropiq/core/models.py` — Domain Objects

| Class | Fields |
|-------|--------|
| `Task` | id, impact, urgency, risk, metadata |
| `Agent` | id, trust_score, capabilities, status |
| `Assignment` | task_id, agent_id |
| `ExecutionResult` | task_id, agent_id, success, latency, metadata |
| `default_agents()` | Factory for baseline agent pool |

Dependencies: `pydantic` only. Used everywhere.

---

### `syntropiq/core/config.py` — Configuration

| Class | Purpose |
|-------|---------|
| `GovernanceConfig` | Governance parameters (thresholds, mutation_rate) |
| `DatabaseConfig` | DB setup (db_path, pool_size, WAL) |
| `ExecutorConfig` | Executor timeouts, API keys |
| `APIConfig` | FastAPI server settings |
| `SyntropiqConfig` | Master config with `from_env()` class method |

---

### `syntropiq/core/exceptions.py` — Custom Exceptions

| Exception | Trigger |
|-----------|---------|
| `SyntropiqError` | Base |
| `CircuitBreakerTriggered` | No agents meet trust threshold (Patent Claim 2) |
| `NoAgentsAvailable` | Registry empty |
| `AgentExecutionError` | Execution failure |
| `InvalidConfiguration` | Config validation failure |
| `DatabaseError` | DB operation failure |
| `TrustScoreInvalid` | Trust score outside [0, 1] |
| `SuppressionError` | Suppression/redemption failure |

---

## 3. Execution Layer (4 files)

### `syntropiq/execution/base.py` — Abstract Base

ABC with `execute()` and `validate_agent()` methods. All executors subclass this.

---

### `syntropiq/execution/deterministic_executor.py` — Testing Executor

Decision: `(trust_score − risk) >= decision_threshold`. Reproducible, no randomness. Used by all tests and the default API server.

---

### `syntropiq/execution/function_executor.py` — Custom Callable Executor

Register arbitrary Python functions via `register_function()`. Execute and interpret result as success/failure.

---

### `syntropiq/execution/llm_executor.py` — LLM Executor

Routes to OpenAI or Anthropic. Lazy-loads clients. Used when `ExecutorConfig` has API keys set.

| Method | Provider |
|--------|----------|
| `_execute_openai()` | OpenAI |
| `_execute_anthropic()` | Anthropic |

---

## 4. Persistence (2 files)

### `syntropiq/persistence/state_manager.py` — SQLite State

8-table schema:

| Table | Purpose |
|-------|---------|
| `trust_scores` | Current trust scores |
| `trust_history` | Trust score timeline |
| `suppression_state` | Suppressed agent tracking |
| `agent_status` | Agent lifecycle state |
| `drift_history` | Detected drift events |
| `execution_results` | All execution outcomes |
| `reflections` | RIF reflection records |
| `mutation_history` | Threshold change timeline |

Key methods: `update_trust_scores()`, `record_execution_results()`, `record_reflection()`, `record_mutation_event()`, `get_statistics()`

---

### `syntropiq/persistence/agent_registry.py` — Agent Lifecycle

| Method | Purpose |
|--------|---------|
| `register_agent()` | Create or update agent |
| `get_agents_dict()` | Return agents as dict (required by governance loop) |
| `sync_trust_scores()` | Pull latest scores from DB |
| `get_agent_statistics()` | Registry metrics |

---

## 5. API Layer (3 files)

### `syntropiq/api/server.py` — FastAPI App

Global state initialization, CORS middleware, lifespan context manager. Includes `synthetic_demo_stream()` for LIVE mode.

---

### `syntropiq/api/routes.py` — REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/tasks/submit` | Submit tasks for governance cycle |
| POST | `/api/v1/agents/register` | Register new agent |
| GET | `/api/v1/agents` | List all agents |
| GET | `/api/v1/agents/{agent_id}` | Agent status |
| PUT | `/api/v1/agents/{agent_id}/status` | Update agent status |
| GET | `/api/v1/statistics` | System-wide metrics |
| GET | `/api/v1/reflections` | RIF reflection history |
| GET | `/api/v1/mutation/history` | Mutation timeline |

---

### `syntropiq/api/schemas.py` — Request/Response Models

`TaskSchema`, `TaskSubmissionRequest`, `GovernanceCycleResponse`, `AgentRegistrationRequest`, `AgentResponse`, `SystemStatisticsResponse`

---

## 6. Demo Domains (12 files, 3 domains)

Each domain follows the same structure:

| File | Purpose |
|------|---------|
| `run.py` | Orchestration — creates agents, streams tasks, outputs JSON timeline |
| `executor.py` | Domain-specific simulation with configurable drift |
| `data.py` | Synthetic data generation + optional real CSV loading |
| `prepare_data.py` | Utility to curate real-world CSVs for demos |

### Fraud Detection (`syntropiq/demo/fraud/`)
- 3 agents, one drifts by raising `fraud_threshold` (passes riskier transactions)
- Data: IEEE-CIS transaction distributions

### Lending (`syntropiq/demo/lending/`)
- 3 underwriting agents, one drifts on risk tolerance
- Data: Lending Club loan application distributions

### Hospital Readmission (`syntropiq/demo/readmission/`)
- 3 discharge planning agents, one drifts
- Data: UCI Diabetes 130 patient encounter distributions
- Includes `READMISSION_PENALTY` constant (Medicare penalty modeling)

---

## 7. Tests (3 files)

### `syntropiq/tests/integration/test_governance_stress.py`
50-cycle validation with phased risks. Checks invariants INV-1 through INV-6, POST-1 through POST-6.

### `syntropiq/tests/integration/test_fifty_cycle_stress.py`
v1 architecture validation gate. Invariants:
- Trust scores bounded [0, 1]
- Suppression >= trust threshold
- Suppressed agents don't execute high-risk tasks
- Mutation thresholds bounded
- Circuit breaker fires correctly
- System resilience (>= 40/50 cycles executed)

### `syntropiq/tests/integration/test_routing_simulation.py`
Validates deterministic and competitive routing modes. Tests circuit breaker and suppression enforcement.

---

## Key Architectural Patterns

| Pattern | Where | Detail |
|---------|-------|--------|
| Circuit Breaker | `trust_engine` | Triggers `CircuitBreakerTriggered` when no agents meet threshold |
| Suppression / Redemption | `trust_engine` | Agents below suppression threshold are blocked; redemption quota allows controlled re-entry |
| Preemptive Drift Detection | `trust_engine` | Compares consecutive trust scores to flag degrading agents |
| Asymmetric Learning | `learning_engine` | Penalizes failure 2.5× more than it rewards success |
| Adaptive Mutation | `mutation_engine` | Thresholds auto-adjust based on rolling success rate |
| Reflexive Integration (RIF) | `reflection_engine` | Constraint score 1–4 based on cycle outcome distribution |
| Pluggable Execution | `execution/base.py` | Swap executor without changing governance logic |
