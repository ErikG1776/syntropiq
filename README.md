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