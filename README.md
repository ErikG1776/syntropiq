# Syntropiq

**Self-Governing Pre-Execution Plane for Autonomous AI**

Syntropiq is a patent-protected governance framework that provides trust-based agent orchestration, asymmetric learning, and adaptive threshold management for autonomous AI systems.

## 🎯 What is Syntropiq?

Syntropiq operates as a **pre-execution governance layer** that:

- **Prioritizes** tasks based on impact, urgency, and risk
- **Assigns** agents based on trust scores (stigmergic coordination)
- **Learns** asymmetrically from successes and failures
- **Suppresses** underperforming agents with redemption cycles
- **Detects** performance drift preemptively
- **Adapts** governance thresholds automatically

All governance decisions happen **before execution**, ensuring safe, autonomous AI operation.

## 🔬 Patent Claims Implemented

- **Claim 1**: Asymmetric Learning (η=0.02, γ=0.05)
- **Claim 2**: Circuit Breaker Pattern
- **Claim 3**: Suppression with Redemption Cycles
- **Claim 4**: Drift Detection & Preemptive Routing
- **Claim 5**: Trust Mutation (Adaptive Thresholds)
- **Claim 6**: RIF (Reflection-In-Flow)

## 🏗️ Architecture


syntropiq/
├── core/ # Data models, config, exceptions
├── governance/ # Trust engine, learning, prioritization, mutation
├── execution/ # Pluggable executors (LLM, function, custom)
├── persistence/ # Database, agent registry
└── api/ # REST API (FastAPI)


## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd syntropiq-clean

# Install dependencies
pip install -r requirements.txt

Basic Usage (Python)
from syntropiq.core.models import Task, Agent
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.execution.function_executor import FunctionExecutor

# Initialize components
state_manager = PersistentStateManager("governance.db")
agent_registry = AgentRegistry(state_manager)
governance_loop = GovernanceLoop(state_manager)
executor = FunctionExecutor()

# Register agents
agent_registry.register_agent(
    agent_id="fraud_detector",
    capabilities=["fraud_detection"],
    initial_trust_score=0.6
)

# Create tasks
tasks = [
    Task(id="task_1", impact=0.8, urgency=0.9, risk=0.3, metadata={})
]

# Execute governance cycle
agents = agent_registry.get_agents_dict()
result = governance_loop.execute_cycle(tasks, agents, executor, run_id="CYCLE_1")

print(f"Executed {result['statistics']['tasks_executed']} tasks")
print(f"Trust updates: {result['trust_updates']}")

Running as API Server
# Start server
uvicorn syntropiq.api.server:app --host 0.0.0.0 --port 8000

# Access API docs
open http://localhost:8000/docs

API Usage
# Register an agent
curl -X POST http://localhost:8000/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "gpt-4",
    "capabilities": ["text_generation"],
    "initial_trust_score": 0.7
  }'

# Submit tasks
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "id": "task_1",
        "impact": 0.8,
        "urgency": 0.9,
        "risk": 0.3,
        "metadata": {"prompt": "Analyze this transaction"}
      }
    ]
  }'

# Get statistics
curl http://localhost:8000/api/v1/statistics

🔧 Configuration
Environment variables:

# Governance parameters
export TRUST_THRESHOLD=0.7
export SUPPRESSION_THRESHOLD=0.75
export MAX_REDEMPTION_CYCLES=4
export DRIFT_DETECTION_DELTA=0.1

# Database
export DB_PATH=governance_state.db

# API
export API_HOST=0.0.0.0
export API_PORT=8000

# LLM executors (optional)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

📊 Governance Parameters
Parameter	Default	Description
trust_threshold	0.7	Minimum trust for agent assignment
suppression_threshold	0.75	Agents below this are suppressed
max_redemption_cycles	4	Cycles for suppressed agents to recover
drift_detection_delta	0.1	Threshold for drift detection
asymmetric_reward	0.02	Trust increase on success (η)
asymmetric_penalty	0.05	Trust decrease on failure (γ)
🔌 Extensibility
Custom Executors
from syntropiq.execution.base import BaseExecutor

class CustomExecutor(BaseExecutor):
    def execute(self, task, agent):
        # Your execution logic
        return ExecutionResult(...)
    
    def validate_agent(self, agent):
        return True

Custom Agents
Syntropiq is agent-agnostic. Register any agent type:

LLMs (GPT-4, Claude)
ML models (XGBoost, TensorFlow)
Rule-based systems
External APIs
Robotic systems
Human-in-the-loop
📈 Monitoring
Track system performance:

# Get system statistics
stats = state_manager.get_statistics()

# Get agent status
agent_status = governance_loop.get_agent_status("agent_id")

# Get mutation history
mutation_history = mutation_engine.get_mutation_history()

🧪 Testing
# Run tests (when implemented)
pytest syntropiq/tests/

📄 License
Proprietary - Patent Protected

🤝 Support
For questions or support, contact:erik@syntropiq.ai

## Invariants Mode

Set `INVARIANTS_MODE` to control read-only invariant checks:

- `off`: disable invariant checks and alerts
- `log`: emit `system_alert` telemetry events for violations (default)
- `enforce`: reserved for a future blocking mode (currently non-blocking)


## Audit Chain Mode

Set `AUDIT_CHAIN_MODE` to control tamper-evident ledger hashing for telemetry persistence:

- `off`: disable hash-chain computation/storage
- `log`: compute and store `chain_id`, `prev_hash`, `hash`, and `hash_algo` for events/cycles (default)

This mode is non-blocking in Phase 2 and does not change governance decisions.

## Mutation Envelope Controls

Set bounded adaptive mutation controls with environment variables:

- `MUTATION_WARMUP_CYCLES=5`: cycles before any loosening is allowed
- `MUTATION_MAX_STEP=0.02`: maximum per-cycle mutation step size
- `MUTATION_DAMPEN_ON_SUPPRESSION=true`: block loosening while suppression is active

## Replay Validation and Reproducibility

Replay validation checks deterministic reproducibility using persisted telemetry cycles/events.

Signals compared per cycle:

- selected agents (exact match)
- trust trajectory by agent (normalized MAE agreement)
- mutation thresholds (normalized MAE agreement)
- suppression set (exact match)

Reproducibility score:

- `r = 0.35*selection_match + 0.35*trust_corr + 0.2*threshold_corr + 0.1*suppression_match`
- each component is in `[0, 1]`

Replay modes:

- `light`: validates deterministic agreement from persisted governance signals only
- `full`: attempts full-fidelity replay; if required artifacts are missing, falls back to `light` with explanation

Validate over API:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/replay/validate \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "LIVE_STREAM",
    "threshold": 0.99,
    "seed": 123,
    "mode": "light"
  }'
```

CI-friendly local check:

```bash
python -m syntropiq.tools.replay_check --run-id LIVE_STREAM --threshold 0.99 --mode light
```

## Optimize Layer (Lambda Objective)

Feature flag:

- `OPTIMIZE_MODE=off|score|integrate` (default: `off`)
  - `off`: no optimize behavior change
  - `score`: enable optimize scoring API only
  - `integrate`: apply optimize ordering inside governance loop (non-invasive, flag-gated)

Lambda defaults:

- `OPTIMIZE_LAMBDA_DEFAULTS='{\"l_cost\":0.25,\"l_time\":0.25,\"l_risk\":0.25,\"l_trust\":0.25}'`
- or individual env vars:
  - `OPT_L_COST`, `OPT_L_TIME`, `OPT_L_RISK`, `OPT_L_TRUST`

Objective:

- components:
  - `cost = 1 - impact`
  - `time = 1 - urgency`
  - `risk = risk`
  - `trust = avg_trust_term`
- score:
  - `score = λ1*cost + λ2*time + λ3*risk - λ4*trust`
- ordering:
  - deterministic `sort(score asc, task.id asc)`
- normalization:
  - `Σλ = 1`

Optimize audit endpoints:

- `POST /api/v1/optimize/score`
- `GET /api/v1/optimize/events?run_id=...&limit=...`
- `GET /api/v1/optimize/verify?run_id=...`

All optimize decisions are persisted in an audit-chain ledger (`optimization_events`) for tamper-evident verification.

## Reflect Layer (Fs + Foresight + Constraints)

Feature flag:

- `REFLECT_MODE=off|score|integrate` (default: `off`)
  - `off`: reflect endpoints/integration disabled
  - `score`: enable explicit reflect scoring endpoints
  - `integrate`: additionally write a reflect insight after each governance cycle (advisory-only)

Fs equation:

- `Fs = Σ w_i * (A_i - D_i) - total_penalty`
- `w_i` uses geometric decay (`decay^i`) and is normalized so `Σw=1`
- `Fs` is clamped to `[-1, 1]`

Horizon model:

- deterministic N-step projection:
  - `trust(t+1) = clamp(trust(t) + expected_delta, 0, 1)`
  - expected delta estimated from recent `trust_delta_total`
  - suppression-active runs apply an additional `-0.01` per step

Constraint kernel penalties (`p_i`):

- trust floor (min trust vs trust_threshold)
- suppression rate bound
- drift delta limit
- instability bound (threshold movement)
- replay reproducibility floor (`r >= 0.99` when available)

Insight ledger endpoints:

- `POST /api/v1/reflect/run`
- `GET /api/v1/reflect/decisions?run_id=...&limit=...`
- `GET /api/v1/reflect/verify?run_id=...`

Reflect decisions are persisted in `insight_ledger` with audit-chain hashing for tamper-evident verification.

## Adaptive Lambda Recalibration (Phase 6)

Feature flag:

- `OPTIMIZE_LAMBDA_ADAPT_MODE=off|log|apply` (default `off`)
  - `off`: no lambda recalibration
  - `log`: compute and persist recommended lambda only
  - `apply`: persist and apply recommended lambda for future optimize calls

Adaptive signals:

- `avg_trust`, `suppression_active`, `drift_delta`, `r_score_latest`, `A_score`, `failure_rate`
- bounded per-step changes (`|delta| <= 0.02`)
- post-update clamp + normalization (`Σλ=1`, each `λ∈[0,1]`, trust cap supported)

Endpoints:

- `POST /api/v1/optimize/lambda/recommend`
- `POST /api/v1/optimize/lambda/apply`
- `GET /api/v1/optimize/lambda/history?run_id=...`
- `GET /api/v1/optimize/lambda/verify?run_id=...`

## Bayesian Risk Posterior (Phase 7)

Feature flag:

- `OPTIMIZE_BAYES_MODE=off|log|apply` (default `off`)

Posterior model:

- Beta posterior with deterministic update:
  - `alpha = alpha0 + successes`
  - `beta = beta0 + failures`
  - `mean = alpha / (alpha + beta)`
  - `uncertainty = 1 / (alpha + beta)`
- posterior can conservatively increase risk weight recommendation.

Endpoints:

- `GET /api/v1/optimize/bayes?run_id=...&window=...`
- `GET /api/v1/optimize/bayes/verify?run_id=...`

## Consensus Foresight (Phase 8)

Feature flag:

- `REFLECT_CONSENSUS_MODE=off|log|integrate` (default `off`)

Consensus method:

- deterministic profile set (`safety`, `efficiency`, `balanced`)
- per-profile reflect Fs computed on same inputs
- consensus Fs = median(profile Fs)
- disagreement = median absolute deviation
- deterministic outlier flagging around median.

Endpoints:

- `POST /api/v1/reflect/consensus`
- `GET /api/v1/reflect/consensus/decisions?run_id=...`
- `GET /api/v1/reflect/consensus/verify?run_id=...`
