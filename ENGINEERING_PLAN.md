# Syntropiq: Production Engineering Plan

**Date**: 2026-02-11
**Current State**: Core governance engine complete (backend Python/FastAPI + SQLite), no frontend, no tests, no containerization
**Target State**: Full production-grade platform with modern UI, enterprise infrastructure, and demo-ready deployment

---

## Current State Summary

### What Exists Today
- **Core Governance Engine** (complete): GovernanceLoop, OptimusPrioritizer, SyntropiqTrustEngine, LearningEngine, ReflectionEngine, MutationEngine
- **3 Execution Backends**: DeterministicExecutor (testing), FunctionExecutor (Python callables), LLMExecutor (OpenAI/Anthropic)
- **Persistence Layer**: SQLite with 8-table schema (trust_scores, trust_history, suppression_state, agent_status, drift_history, execution_results, reflections, mutation_history)
- **REST API**: FastAPI with 7 endpoints under `/api/v1/`
- **Configuration**: Environment-variable-driven with Pydantic models
- **Documentation**: Comprehensive README with patent claim references

### What's Missing
- Frontend / UI
- Tests (directories exist but are empty)
- Docker / containerization
- CI/CD pipeline
- Authentication / authorization
- Production database (currently SQLite only)
- Structured logging & observability
- Rate limiting, API security
- WebSocket / real-time updates
- Multi-tenancy
- Package management (no pyproject.toml)

---

## Phase 1: Backend Hardening & Test Foundation
**Duration estimate: ~2 weeks**
**Goal**: Make the existing backend production-grade and fully tested

### 1.1 Project Packaging & Tooling
- [ ] Create `pyproject.toml` with project metadata, dependencies, build configuration
- [ ] Configure `ruff` for linting and formatting (replaces flake8/black/isort)
- [ ] Configure `mypy` for static type checking
- [ ] Add `pre-commit` hooks (ruff, mypy, trailing whitespace, YAML check)
- [ ] Add `Makefile` with common commands (`make test`, `make lint`, `make run`, `make docker`)

### 1.2 Structured Logging
- [ ] Replace all `print()` statements with Python `logging` module
- [ ] Create `syntropiq/core/logging.py` with structured JSON log formatter
- [ ] Add correlation IDs (run_id) threaded through all log messages
- [ ] Configure log levels per module (DEBUG for governance internals, INFO for API)
- [ ] Add request/response logging middleware in FastAPI

### 1.3 Configuration Hardening
- [ ] Move hardcoded constants to config (learning rates eta/gamma in learning_engine.py, prioritizer weights)
- [ ] Add configuration validation with clear error messages on startup
- [ ] Support `.env` files via `python-dotenv`
- [ ] Add configuration profiles: `development`, `testing`, `staging`, `production`
- [ ] Document all configuration options with defaults

### 1.4 Database Layer Upgrade
- [ ] Add Alembic for database migrations (schema versioning)
- [ ] Create initial migration from current SQLite schema
- [ ] Add PostgreSQL support via SQLAlchemy (keep SQLite for dev/testing)
- [ ] Add connection pooling configuration
- [ ] Add database health check endpoint
- [ ] Add indexes on frequently queried columns (agent_id + timestamp on trust_history, execution_results)

### 1.5 API Hardening
- [ ] Add API key authentication middleware
- [ ] Add rate limiting (slowapi or custom middleware)
- [ ] Add request validation with detailed error responses (RFC 7807 Problem Details)
- [ ] Add API versioning strategy (already uses /v1/, formalize it)
- [ ] Add pagination on list endpoints (agents, reflections, mutation history)
- [ ] Add filtering and sorting query parameters
- [ ] Restrict CORS origins (currently allows all)
- [ ] Add OpenAPI documentation customization (descriptions, examples, tags)
- [ ] Add request size limits

### 1.6 Async Optimization
- [ ] Convert LLMExecutor to async (aiohttp or httpx async)
- [ ] Make database operations async (aiosqlite / async SQLAlchemy)
- [ ] Add async governance cycle execution
- [ ] Add background task support for long-running governance cycles

### 1.7 Test Suite
- [ ] **Unit Tests** (target: 90%+ coverage on core modules)
  - [ ] `tests/unit/test_models.py` - Pydantic model validation, defaults, edge cases
  - [ ] `tests/unit/test_config.py` - Configuration loading, env vars, profiles
  - [ ] `tests/unit/test_prioritizer.py` - Task scoring, sorting, edge cases
  - [ ] `tests/unit/test_trust_engine.py` - Assignment, circuit breaker, suppression, drift
  - [ ] `tests/unit/test_learning_engine.py` - Asymmetric updates, boundary conditions
  - [ ] `tests/unit/test_reflection_engine.py` - Constraint scores, metadata generation
  - [ ] `tests/unit/test_mutation_engine.py` - Threshold adaptation, safety bands
  - [ ] `tests/unit/test_function_executor.py` - Callable execution, error handling
  - [ ] `tests/unit/test_deterministic_executor.py` - Deterministic outcomes
  - [ ] `tests/unit/test_llm_executor.py` - LLM routing, mocked API calls
  - [ ] `tests/unit/test_state_manager.py` - All DB operations, schema integrity
  - [ ] `tests/unit/test_agent_registry.py` - Agent lifecycle, trust sync
  - [ ] `tests/unit/test_exceptions.py` - Exception hierarchy, messages
- [ ] **Integration Tests**
  - [ ] `tests/integration/test_governance_loop.py` - Full cycle with deterministic executor
  - [ ] `tests/integration/test_api_endpoints.py` - All API endpoints via httpx TestClient
  - [ ] `tests/integration/test_persistence_cycle.py` - DB state across multiple governance cycles
  - [ ] `tests/integration/test_suppression_lifecycle.py` - Agent suppression through redemption to permanent exclusion
  - [ ] `tests/integration/test_mutation_adaptation.py` - Threshold evolution over cycles
  - [ ] `tests/integration/test_circuit_breaker.py` - Circuit breaker triggering and recovery
- [ ] **conftest.py** with fixtures: test database, sample agents, sample tasks, mock executors
- [ ] Configure `pytest.ini` / `pyproject.toml [tool.pytest]` with markers, coverage settings
- [ ] Add `pytest-cov` for coverage reporting

### 1.8 Error Handling & Resilience
- [ ] Add retry logic with exponential backoff for LLM calls
- [ ] Add circuit breaker pattern for external service calls (LLM APIs)
- [ ] Add graceful degradation when database is unavailable
- [ ] Add health check that verifies all subsystems
- [ ] Standardize error responses across all API endpoints

---

## Phase 2: Frontend - Operator Dashboard
**Duration estimate: ~3-4 weeks**
**Goal**: Build a modern, real-time operator dashboard for monitoring and controlling the governance platform

### 2.1 Technology Stack
- **Framework**: Next.js 14+ (App Router) with TypeScript
- **UI Library**: shadcn/ui (built on Radix UI primitives) + Tailwind CSS
- **Charts**: Recharts or Tremor (for analytics dashboards)
- **State Management**: TanStack Query (React Query) for server state, Zustand for client state
- **Real-time**: WebSocket via Socket.IO or native WS
- **Tables**: TanStack Table for data grids
- **Forms**: React Hook Form + Zod validation
- **Icons**: Lucide React

### 2.2 Backend Additions for Frontend Support
- [ ] **WebSocket endpoint** (`/ws/governance`) for real-time governance cycle updates
  - Trust score changes (live)
  - Execution results (live)
  - Agent status changes
  - Mutation events
  - Circuit breaker triggers
- [ ] **Session/Auth endpoints**
  - `POST /api/v1/auth/login` - API key or OAuth login
  - `GET /api/v1/auth/me` - Current user/session info
  - `POST /api/v1/auth/logout`
- [ ] **Dashboard aggregation endpoints**
  - `GET /api/v1/dashboard/overview` - High-level KPIs (active agents, success rate, avg trust, cycles today)
  - `GET /api/v1/dashboard/trust-timeline` - Trust scores over time (charting data)
  - `GET /api/v1/dashboard/execution-heatmap` - Success/failure by agent over time
  - `GET /api/v1/dashboard/mutation-timeline` - Threshold changes over time
- [ ] **Enhanced CRUD endpoints**
  - `POST /api/v1/tasks/submit-batch` - Upload CSV/JSON batch of tasks
  - `GET /api/v1/tasks/history` - Historical task execution with filtering
  - `PUT /api/v1/agents/{id}/trust` - Manual trust score override (with audit log)
  - `POST /api/v1/governance/trigger` - Manually trigger a governance cycle
  - `GET /api/v1/governance/cycles` - List past governance cycles with details
  - `GET /api/v1/governance/cycles/{id}` - Detailed cycle breakdown

### 2.3 Frontend Application Structure
```
frontend/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout (sidebar, header)
│   ├── page.tsx                  # Dashboard home (redirect to /dashboard)
│   ├── login/
│   │   └── page.tsx              # Login page
│   ├── dashboard/
│   │   └── page.tsx              # Main dashboard / overview
│   ├── agents/
│   │   ├── page.tsx              # Agent list with filters
│   │   └── [id]/
│   │       └── page.tsx          # Agent detail (trust history, execution history)
│   ├── tasks/
│   │   ├── page.tsx              # Task submission & history
│   │   └── [id]/
│   │       └── page.tsx          # Task detail (assignment, result)
│   ├── governance/
│   │   ├── page.tsx              # Governance cycles list
│   │   └── [id]/
│   │       └── page.tsx          # Cycle detail (full breakdown)
│   ├── analytics/
│   │   └── page.tsx              # Deep analytics (trust trends, mutation history, etc.)
│   ├── settings/
│   │   └── page.tsx              # Platform configuration
│   └── api/                      # Next.js API routes (BFF pattern, optional)
├── components/
│   ├── ui/                       # shadcn/ui primitives (button, card, dialog, etc.)
│   ├── layout/
│   │   ├── sidebar.tsx           # Navigation sidebar
│   │   ├── header.tsx            # Top bar with breadcrumbs, user menu
│   │   └── mobile-nav.tsx        # Responsive mobile navigation
│   ├── dashboard/
│   │   ├── kpi-cards.tsx         # Active agents, success rate, trust avg, cycle count
│   │   ├── trust-chart.tsx       # Real-time trust score line chart
│   │   ├── execution-feed.tsx    # Live feed of execution results
│   │   ├── agent-health-grid.tsx # Grid showing agent status at a glance
│   │   └── alert-banner.tsx      # Circuit breaker / drift alerts
│   ├── agents/
│   │   ├── agent-table.tsx       # Sortable, filterable agent data table
│   │   ├── agent-card.tsx        # Agent summary card
│   │   ├── trust-history-chart.tsx  # Per-agent trust history
│   │   ├── agent-status-badge.tsx   # Status indicator (active, suppressed, drifting)
│   │   └── agent-registration-form.tsx
│   ├── tasks/
│   │   ├── task-submission-form.tsx  # Submit tasks with impact/urgency/risk sliders
│   │   ├── task-table.tsx           # Task history table
│   │   └── task-detail-panel.tsx    # Assignment & result details
│   ├── governance/
│   │   ├── cycle-timeline.tsx       # Timeline visualization of governance cycles
│   │   ├── cycle-detail-view.tsx    # Step-by-step cycle breakdown
│   │   ├── mutation-chart.tsx       # Threshold mutation over time
│   │   └── reflection-viewer.tsx    # RIF metadata display
│   └── shared/
│       ├── data-table.tsx           # Reusable TanStack Table wrapper
│       ├── chart-container.tsx      # Reusable chart wrapper
│       ├── loading-skeleton.tsx     # Loading states
│       ├── empty-state.tsx          # Empty state illustrations
│       └── error-boundary.tsx       # Error handling
├── lib/
│   ├── api-client.ts               # Typed API client (fetch wrapper)
│   ├── websocket.ts                # WebSocket connection manager
│   ├── utils.ts                    # Utility functions
│   └── constants.ts                # App constants
├── hooks/
│   ├── use-agents.ts               # Agent data hooks (TanStack Query)
│   ├── use-tasks.ts                # Task data hooks
│   ├── use-governance.ts           # Governance cycle hooks
│   ├── use-dashboard.ts            # Dashboard data hooks
│   ├── use-websocket.ts            # WebSocket hook for real-time updates
│   └── use-auth.ts                 # Authentication hooks
├── stores/
│   ├── auth-store.ts               # Auth state (Zustand)
│   ├── notification-store.ts       # Toast / alert notifications
│   └── preferences-store.ts        # User preferences (theme, layout)
├── types/
│   └── index.ts                    # TypeScript types matching API schemas
├── styles/
│   └── globals.css                 # Tailwind base + custom CSS variables
├── public/
│   ├── logo.svg
│   └── favicon.ico
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 2.4 Page-by-Page UI Specification

#### 2.4.1 Dashboard (Home)
**Purpose**: At-a-glance operational overview. The first thing an operator sees.

**Layout**:
```
┌──────────────────────────────────────────────────────────┐
│ [Sidebar]  │  DASHBOARD                         [User ▾] │
│            │─────────────────────────────────────────────│
│ Dashboard  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
│ Agents     │  │ KPI │ │ KPI │ │ KPI │ │ KPI │         │
│ Tasks      │  │Card1│ │Card2│ │Card3│ │Card4│         │
│ Governance │  └─────┘ └─────┘ └─────┘ └─────┘         │
│ Analytics  │                                             │
│ Settings   │  ┌─────────────────┐ ┌────────────────┐   │
│            │  │ Trust Scores    │ │ Execution Feed │   │
│            │  │ (Line Chart)    │ │ (Live Feed)    │   │
│            │  │                 │ │                │   │
│            │  │                 │ │                │   │
│            │  └─────────────────┘ └────────────────┘   │
│            │                                             │
│            │  ┌─────────────────────────────────────┐   │
│            │  │ Agent Health Grid                    │   │
│            │  │ (Status cards for each agent)        │   │
│            │  └─────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

**KPI Cards**:
1. **Active Agents**: Count + trend arrow (vs. yesterday)
2. **Success Rate**: Percentage + sparkline (last 24h)
3. **Avg Trust Score**: Score + delta indicator
4. **Governance Cycles Today**: Count + last cycle timestamp

**Trust Score Chart**: Multi-line chart showing each agent's trust score over time. Color-coded by status. Hover shows exact values. Zoom/pan for time range selection.

**Execution Feed**: Real-time scrolling feed of execution results. Each entry shows: timestamp, task ID, agent ID, success/failure badge, latency. Auto-scrolls with new entries via WebSocket.

**Agent Health Grid**: Card grid showing each agent with: name, current trust score (color-coded gauge), status badge, last execution result. Click navigates to agent detail.

**Alert Banner**: Appears at top when critical events occur (circuit breaker triggered, agent permanently excluded, significant drift detected). Dismissible.

#### 2.4.2 Agents Page
**Purpose**: Full agent management - view, register, monitor, override

**Agent Table Columns**:
- Agent ID (linked to detail)
- Trust Score (color-coded: green >0.7, yellow 0.4-0.7, red <0.4)
- Status (Active / Suppressed / Drifting / Excluded)
- Capabilities (tag chips)
- Last Execution (timestamp + result)
- Suppression Cycle (if applicable)
- Actions (View, Edit Status, Override Trust)

**Filters**: Status dropdown, trust score range slider, capability search
**Actions**: Register New Agent button, Bulk status update

#### 2.4.3 Agent Detail Page
**Purpose**: Deep dive into a single agent's history and behavior

**Sections**:
1. **Header**: Agent ID, status badge, current trust score (large), capabilities tags
2. **Trust History Chart**: Line chart of trust score over time with annotations (suppression events, drift alerts marked)
3. **Execution History Table**: All tasks executed by this agent with success/failure, latency, task details
4. **Suppression History**: Timeline of suppression/redemption cycles
5. **Drift Events**: Table of drift detections with before/after trust scores
6. **Manual Controls**: Override trust score (with confirmation dialog), change status, force suppression/redemption

#### 2.4.4 Tasks Page
**Purpose**: Submit tasks and review execution history

**Task Submission Form**:
- Task ID (auto-generated or custom)
- Impact slider (0.0 - 1.0) with contextual labels (Low/Medium/High/Critical)
- Urgency slider (0.0 - 1.0)
- Risk slider (0.0 - 1.0)
- Metadata (JSON editor with syntax highlighting)
- Submit single or batch upload (CSV/JSON file)

**Task History Table**:
- Task ID, Impact/Urgency/Risk badges, Assigned Agent, Success/Failure, Latency, Timestamp
- Expandable row showing full execution details and reflection

#### 2.4.5 Governance Page
**Purpose**: View and analyze governance cycles

**Cycle List**: Table of past governance cycles with:
- Cycle ID / Run ID
- Timestamp
- Tasks processed count
- Success rate (bar)
- Mutation applied (yes/no with direction)
- Reflection constraint score

**Cycle Detail View** (click into a cycle):
1. **Step-by-step timeline** visualization:
   - Prioritization results (ordered task list)
   - Assignment map (which agent got which task)
   - Execution results (per-task success/failure)
   - Trust updates (before/after for each agent)
   - Mutation changes (threshold deltas)
   - Reflection output (full RIF metadata)
2. Visual flow diagram showing the governance pipeline

#### 2.4.6 Analytics Page
**Purpose**: Deep analytics for understanding platform behavior over time

**Charts/Visualizations**:
1. **Trust Score Trends**: Multi-agent line chart over configurable time range
2. **Success Rate Over Time**: Area chart with trend line
3. **Mutation History**: Dual-axis chart showing threshold values and success rates over cycles
4. **Agent Performance Heatmap**: Matrix of agents x time periods, colored by success rate
5. **Suppression Frequency**: Bar chart of suppression events by agent
6. **Drift Detection Timeline**: Scatter plot of drift events
7. **Latency Distribution**: Histogram of execution latencies
8. **Reflection Constraint Scores**: Distribution chart over time

**Filters**: Date range picker, agent filter, task impact range

#### 2.4.7 Settings Page
**Purpose**: Platform configuration management

**Sections**:
1. **Governance Parameters**: Trust threshold, suppression threshold, drift delta, learning rates (eta, gamma), mutation rate, target success rate
2. **API Configuration**: Endpoint URL, rate limits, CORS origins
3. **LLM Configuration**: API keys (masked), model selection, timeout/retry settings
4. **Notification Preferences**: Alert thresholds, email/webhook destinations
5. **User Management**: API keys, user roles (when multi-user is implemented)

### 2.5 Design System
- [ ] Dark mode primary (operators prefer dark UIs for monitoring)
- [ ] Light mode toggle available
- [ ] Color palette: Deep navy background, electric blue accents, green/amber/red for status
- [ ] Typography: Inter for UI text, JetBrains Mono for data/code
- [ ] Consistent spacing scale (4px base)
- [ ] Accessible: WCAG 2.1 AA compliance
- [ ] Responsive: Desktop-first (1440px+) with tablet support (768px+)

### 2.6 Real-Time Architecture
```
┌─────────────┐     WebSocket      ┌──────────────────┐
│   Browser    │◄──────────────────►│  FastAPI Backend  │
│  (Next.js)   │                    │                  │
│              │     REST API       │  /ws/governance   │
│              │◄──────────────────►│  /api/v1/*        │
└─────────────┘                    └──────────────────┘
```
- WebSocket pushes: trust updates, execution results, alerts, mutation events
- REST for: CRUD operations, historical data, configuration
- Optimistic updates on UI with WebSocket confirmation
- Reconnection logic with exponential backoff

---

## Phase 3: Infrastructure & DevOps
**Duration estimate: ~2 weeks**
**Goal**: Containerize, orchestrate, and set up CI/CD for reliable deployment

### 3.1 Docker
- [ ] `Dockerfile` for backend (Python 3.11+, multi-stage build, non-root user)
- [ ] `Dockerfile` for frontend (Node 20+, multi-stage build with nginx)
- [ ] `docker-compose.yml` for local development:
  ```yaml
  services:
    backend:
      build: .
      ports: ["8000:8000"]
      environment: [...]
      volumes: ["./syntropiq:/app/syntropiq"]  # hot reload
      depends_on: [postgres]
    frontend:
      build: ./frontend
      ports: ["3000:3000"]
      environment: [NEXT_PUBLIC_API_URL=http://localhost:8000]
    postgres:
      image: postgres:16-alpine
      volumes: [pgdata:/var/lib/postgresql/data]
      environment: [POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
  ```
- [ ] `docker-compose.prod.yml` with production overrides (no volume mounts, resource limits)
- [ ] `.dockerignore` files for both services

### 3.2 CI/CD Pipeline (GitHub Actions)
- [ ] `.github/workflows/ci.yml`:
  ```
  On: push to main, PR to main
  Jobs:
    lint:
      - ruff check
      - ruff format --check
      - mypy
    test:
      - pytest with coverage (fail if <85%)
      - Upload coverage to Codecov
    frontend-lint:
      - ESLint
      - TypeScript check
      - Prettier check
    frontend-test:
      - Vitest / Jest unit tests
      - Playwright E2E tests (critical paths)
    build:
      - Docker build backend
      - Docker build frontend
      - Push to container registry (on main only)
    security:
      - Dependency vulnerability scan (pip-audit, npm audit)
      - SAST scan (Bandit for Python, ESLint security plugin)
  ```
- [ ] `.github/workflows/deploy-staging.yml`:
  ```
  On: push to main
  Jobs:
    deploy:
      - Pull latest images
      - Run database migrations
      - Deploy to staging environment
      - Run smoke tests
      - Notify team
  ```
- [ ] `.github/workflows/deploy-production.yml`:
  ```
  On: manual trigger (workflow_dispatch) or tag push (v*)
  Jobs:
    deploy:
      - Require staging smoke test pass
      - Blue-green or rolling deployment
      - Run production smoke tests
      - Rollback on failure
  ```

### 3.3 Cloud Infrastructure (AWS - primary, adaptable to Azure/GCP)
```
┌─────────────────────────────────────────────────────────┐
│                        AWS VPC                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Public Subnet                       │    │
│  │  ┌──────────┐  ┌──────────────────────────┐    │    │
│  │  │ ALB/NLB  │  │ CloudFront (CDN)         │    │    │
│  │  │ (HTTPS)  │  │ (Static assets + API     │    │    │
│  │  │          │  │  caching)                 │    │    │
│  │  └─────┬────┘  └──────────────────────────┘    │    │
│  └────────┼────────────────────────────────────────┘    │
│           │                                              │
│  ┌────────┼────────────────────────────────────────┐    │
│  │        │     Private Subnet                      │    │
│  │  ┌─────▼──────┐  ┌─────────────┐               │    │
│  │  │  ECS/EKS   │  │  ECS/EKS    │               │    │
│  │  │  Backend   │  │  Frontend   │               │    │
│  │  │  (Fargate) │  │  (Fargate)  │               │    │
│  │  └─────┬──────┘  └─────────────┘               │    │
│  │        │                                         │    │
│  │  ┌─────▼──────┐  ┌─────────────┐               │    │
│  │  │ RDS        │  │ ElastiCache │               │    │
│  │  │ PostgreSQL │  │ Redis       │               │    │
│  │  │ (Multi-AZ) │  │             │               │    │
│  │  └────────────┘  └─────────────┘               │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

#### Infrastructure Components:
- [ ] **Networking**: VPC with public/private subnets across 2+ AZs
- [ ] **Compute**: ECS Fargate (or EKS if Kubernetes preferred)
  - Backend service: 2+ tasks, auto-scaling on CPU/memory
  - Frontend service: 2+ tasks, auto-scaling on requests
- [ ] **Database**: RDS PostgreSQL (Multi-AZ for production)
  - db.t3.medium for staging, db.r6g.large for production
  - Automated backups, 7-day retention
  - Read replica for analytics queries (production)
- [ ] **Caching**: ElastiCache Redis
  - Session storage
  - API response caching
  - WebSocket pub/sub (for multi-instance backend)
  - Rate limiting backing store
- [ ] **Load Balancer**: Application Load Balancer with HTTPS termination
  - Health check endpoints
  - WebSocket support (sticky sessions)
- [ ] **CDN**: CloudFront for frontend static assets
- [ ] **DNS**: Route 53 with custom domain
- [ ] **SSL**: ACM certificate (free, auto-renewed)
- [ ] **Secrets**: AWS Secrets Manager for API keys, database credentials
- [ ] **Monitoring**: CloudWatch Logs + Metrics
- [ ] **Storage**: S3 for task batch uploads, log archives

### 3.4 Infrastructure as Code
- [ ] **Terraform** modules for all AWS resources:
  ```
  infrastructure/
  ├── terraform/
  │   ├── environments/
  │   │   ├── staging/
  │   │   │   ├── main.tf
  │   │   │   ├── variables.tf
  │   │   │   └── terraform.tfvars
  │   │   └── production/
  │   │       ├── main.tf
  │   │       ├── variables.tf
  │   │       └── terraform.tfvars
  │   ├── modules/
  │   │   ├── networking/    # VPC, subnets, security groups
  │   │   ├── compute/       # ECS services, task definitions
  │   │   ├── database/      # RDS, ElastiCache
  │   │   ├── loadbalancer/  # ALB, target groups, listeners
  │   │   ├── cdn/           # CloudFront distribution
  │   │   ├── dns/           # Route 53 records
  │   │   └── monitoring/    # CloudWatch dashboards, alarms
  │   └── backend.tf         # S3 + DynamoDB for Terraform state
  ```
- [ ] Remote state in S3 with DynamoDB lock table
- [ ] Separate state files per environment

### 3.5 Environment Configuration
| Setting | Development | Staging | Production |
|---------|------------|---------|------------|
| Database | SQLite / Local PG | RDS PostgreSQL (single AZ) | RDS PostgreSQL (Multi-AZ) |
| Cache | Local Redis | ElastiCache (single node) | ElastiCache (cluster) |
| Backend instances | 1 | 2 | 2-10 (auto-scale) |
| Frontend instances | 1 | 2 | 2-6 (auto-scale) |
| SSL | Self-signed | ACM | ACM |
| Domain | localhost | staging.syntropiq.io | app.syntropiq.io |
| Logging | Console | CloudWatch | CloudWatch + S3 archive |
| LLM Keys | Dev keys | Staging keys | Production keys (rate-limited) |

---

## Phase 4: Security & Enterprise Features
**Duration estimate: ~2-3 weeks**
**Goal**: Enterprise-grade security, multi-tenancy, and audit compliance

### 4.1 Authentication & Authorization
- [ ] **JWT-based authentication** with refresh token rotation
- [ ] **Role-Based Access Control (RBAC)**:
  | Role | Permissions |
  |------|------------|
  | Viewer | Read dashboard, agents, tasks, analytics |
  | Operator | Viewer + submit tasks, register agents |
  | Admin | Operator + change config, override trust, manage users |
  | Super Admin | Admin + manage tenants, system settings |
- [ ] **OAuth 2.0 / OIDC integration** (support enterprise SSO):
  - Okta
  - Azure AD
  - Google Workspace
- [ ] **API key management**: Create, rotate, revoke API keys per service account
- [ ] **Session management**: Token expiry, concurrent session limits

### 4.2 Multi-Tenancy
- [ ] **Tenant isolation** at the database level (schema-per-tenant or row-level security)
- [ ] **Tenant-scoped API routes**: All data filtered by tenant context
- [ ] **Tenant onboarding flow**: Self-service or admin-provisioned
- [ ] **Tenant configuration**: Per-tenant governance parameters
- [ ] **Tenant usage tracking**: Governance cycles, API calls, agent counts

### 4.3 Audit & Compliance
- [ ] **Comprehensive audit log**: Every state change recorded with:
  - Who (user/service), What (action), When (timestamp), Where (resource), Why (reason/context)
- [ ] **Immutable audit trail**: Append-only table, no deletes
- [ ] **Trust score override audit**: Every manual override logged with justification
- [ ] **Configuration change audit**: Track all config changes
- [ ] **Data retention policies**: Configurable retention per data type
- [ ] **Export capabilities**: Audit logs exportable as CSV/JSON for compliance

### 4.4 Data Security
- [ ] **Encryption at rest**: Database encryption (RDS native), S3 SSE
- [ ] **Encryption in transit**: TLS 1.3 everywhere
- [ ] **Secrets management**: No secrets in code or environment variables at rest
- [ ] **Input sanitization**: Protect against injection attacks
- [ ] **PII handling**: If task metadata contains PII, support field-level encryption
- [ ] **Backup encryption**: All database backups encrypted

### 4.5 API Security
- [ ] **OWASP Top 10** protections:
  - SQL injection: Parameterized queries (already via SQLAlchemy)
  - XSS: Content-Security-Policy headers
  - CSRF: Token-based protection
  - Rate limiting: Per-user and per-IP
- [ ] **WAF rules** (AWS WAF on ALB/CloudFront)
- [ ] **IP allowlisting** option for enterprise deployments
- [ ] **Request signing** for service-to-service communication

---

## Phase 5: Observability & Operations
**Duration estimate: ~1-2 weeks**
**Goal**: Full observability stack for monitoring, alerting, and debugging in production

### 5.1 Metrics
- [ ] **Prometheus-compatible metrics** endpoint (`/metrics`)
- [ ] **Application metrics**:
  - `governance_cycles_total` (counter, labels: status)
  - `governance_cycle_duration_seconds` (histogram)
  - `task_execution_duration_seconds` (histogram, labels: agent_id, success)
  - `trust_score_current` (gauge, labels: agent_id)
  - `agents_active_total` (gauge)
  - `agents_suppressed_total` (gauge)
  - `circuit_breaker_triggers_total` (counter)
  - `mutation_events_total` (counter, labels: direction)
  - `api_request_duration_seconds` (histogram, labels: endpoint, method, status)
  - `api_requests_total` (counter, labels: endpoint, method, status)
  - `websocket_connections_active` (gauge)
- [ ] **Infrastructure metrics** via CloudWatch or Prometheus Node Exporter

### 5.2 Logging
- [ ] **Structured JSON logging** for all services
- [ ] **Log aggregation**: CloudWatch Logs or ELK/Loki stack
- [ ] **Log correlation**: Request ID / Run ID threaded through all logs
- [ ] **Log levels**: Configurable per module at runtime
- [ ] **Sensitive data masking**: API keys, tokens redacted in logs

### 5.3 Tracing
- [ ] **OpenTelemetry** integration for distributed tracing
- [ ] **Trace spans** for:
  - Full governance cycle (parent span)
  - Prioritization step
  - Agent assignment step
  - Each task execution (with agent and LLM call details)
  - Trust update calculations
  - Mutation engine evaluation
  - Database operations
- [ ] **Trace visualization**: Jaeger or AWS X-Ray

### 5.4 Alerting
- [ ] **Alert rules** (PagerDuty / Opsgenie / Slack integration):
  | Alert | Condition | Severity |
  |-------|-----------|----------|
  | Circuit breaker triggered | Any trigger | Critical |
  | Success rate drop | <70% over 5 min | Warning |
  | Success rate critical | <50% over 5 min | Critical |
  | All agents suppressed | 0 active agents | Critical |
  | Database connection failure | Health check fail | Critical |
  | API error rate spike | >5% 5xx in 5 min | Warning |
  | High latency | p95 >10s | Warning |
  | LLM API errors | >3 failures in 1 min | Warning |
  | Disk space low | >80% used | Warning |
  | Trust score anomaly | Any agent drops >0.2 in 1 cycle | Info |

### 5.5 Dashboards (Grafana or CloudWatch)
- [ ] **System Overview**: Service health, request rates, error rates, latency
- [ ] **Governance Dashboard**: Cycle throughput, success rates, trust distributions
- [ ] **Agent Performance**: Per-agent trust trends, execution stats, suppression events
- [ ] **Infrastructure**: CPU, memory, network, disk, database connections

---

## Phase 6: Advanced Features & Scale
**Duration estimate: ~3-4 weeks**
**Goal**: Features that differentiate the platform for enterprise and demo scenarios

### 6.1 Advanced Governance Features
- [ ] **Governance Policies** (configurable rules engine):
  - Define custom assignment rules (e.g., "Agent X only handles impact > 0.8 tasks")
  - Time-based policies (e.g., "Reduce trust threshold during business hours")
  - Capability-based routing (match task requirements to agent capabilities)
- [ ] **Governance Simulation Mode**:
  - "What-if" analysis: Run governance cycle without executing tasks
  - Preview assignments, predict outcomes based on historical data
  - Compare different threshold configurations
- [ ] **Agent Groups / Pools**:
  - Group agents by capability or purpose
  - Pool-level trust scoring and circuit breakers
  - Load balancing within pools
- [ ] **Task Dependencies**:
  - Define task chains (Task B depends on Task A success)
  - DAG-based execution scheduling
  - Parallel execution where dependencies allow

### 6.2 Notification & Integration
- [ ] **Webhook system**: Push events to external systems
  - Circuit breaker triggers
  - Agent suppression events
  - Governance cycle completions
  - Trust score thresholds
- [ ] **Slack integration**: Bot for alerts and quick actions
- [ ] **Email notifications**: Digest reports, critical alerts
- [ ] **API for external orchestrators**: Allow external systems to query governance state

### 6.3 Reporting & Export
- [ ] **Scheduled reports**: Daily/weekly governance summary
  - Agent performance rankings
  - Trust score trends
  - Mutation history summary
  - Success rate analytics
- [ ] **PDF export**: Generate formatted reports for stakeholders
- [ ] **CSV/JSON export**: All data tables exportable
- [ ] **Compliance reports**: Audit-ready reports for governance reviews

### 6.4 Performance & Scale
- [ ] **Horizontal scaling**: Backend stateless design verified
  - Redis for shared state (WebSocket pub/sub, rate limiting, caching)
  - Database for persistent state
  - No in-memory state that doesn't survive restart
- [ ] **Batch processing**: Handle 1000+ tasks per governance cycle
- [ ] **Async task queue**: Celery or similar for long-running cycles
  - Decouple API response from cycle completion
  - Progress tracking via WebSocket
- [ ] **Database optimization**:
  - Partitioning on execution_results by date
  - Archival strategy for old data
  - Query optimization with EXPLAIN analysis
  - Connection pool tuning
- [ ] **Caching strategy**:
  - Cache agent list (invalidate on registration/status change)
  - Cache statistics (5-second TTL)
  - Cache dashboard aggregations (configurable TTL)

### 6.5 Demo Mode
- [ ] **Built-in demo scenario**: Pre-loaded agents, tasks, and historical data
- [ ] **Demo auto-play**: Automatically run governance cycles with simulated results
  - Configurable speed (1x, 5x, 10x)
  - Shows all governance mechanisms in action:
    - Trust scores changing asymmetrically
    - Agent getting suppressed and going through redemption
    - Circuit breaker triggering and recovery
    - Mutation engine adapting thresholds
    - Drift detection firing
- [ ] **Demo reset**: One-click reset to initial state
- [ ] **Guided tour**: Step-by-step walkthrough of the UI for new users

---

## Phase 7: Production Deployment & Hardening
**Duration estimate: ~1-2 weeks**
**Goal**: Final production readiness and go-live

### 7.1 Pre-Production Checklist
- [ ] All tests passing (unit, integration, E2E)
- [ ] Security audit completed (OWASP, dependency scanning)
- [ ] Load testing completed (identify bottlenecks, set auto-scaling thresholds)
- [ ] Database migration tested (staging → production path verified)
- [ ] Backup and restore tested
- [ ] Monitoring and alerting verified
- [ ] Runbook created for common operational tasks
- [ ] Incident response plan documented

### 7.2 Production Deployment
- [ ] Blue-green deployment strategy configured
- [ ] Database migration automated in deployment pipeline
- [ ] Health checks verified at all layers (ALB, ECS, application)
- [ ] Auto-scaling policies tuned based on load test results
- [ ] CDN caching rules configured for frontend
- [ ] DNS cutover plan documented

### 7.3 Operational Documentation
- [ ] **Runbook**: Common operational procedures
  - Scale up/down
  - Database maintenance
  - Log investigation
  - Incident response
  - Agent management
  - Backup/restore
- [ ] **Architecture Decision Records (ADRs)**: Document key decisions
- [ ] **API documentation**: Auto-generated from OpenAPI spec, published
- [ ] **User guide**: Operator-facing guide for using the dashboard

### 7.4 Performance Benchmarks
| Metric | Target |
|--------|--------|
| API response time (p95) | < 200ms |
| Governance cycle (10 tasks, 5 agents) | < 2 seconds |
| Governance cycle (100 tasks, 20 agents) | < 15 seconds |
| WebSocket message latency | < 100ms |
| Dashboard initial load | < 2 seconds |
| Concurrent users supported | 50+ |
| Database query time (p95) | < 50ms |
| Uptime SLA | 99.9% |

---

## Execution Order & Dependencies

```
Phase 1 (Backend Hardening)     ════════════╗
                                             ║
Phase 2 (Frontend)              ═══════════╦═╩══════╗
  - Can start after Phase 1.5             ║        ║
  - Backend WebSocket needed for real-time ║        ║
                                           ║        ║
Phase 3 (Infrastructure)       ════════════╩═══╗    ║
  - Can start after Phase 1.1                 ║    ║
  - Docker can be done in parallel with FE    ║    ║
                                              ║    ║
Phase 4 (Security)             ═══════════════╩═══╗║
  - Requires backend + frontend + infra           ║║
                                                  ║║
Phase 5 (Observability)        ═══════════════════╩╗
  - Can start after Phase 3                       ║
  - Metrics/logging independent of FE             ║
                                                  ║
Phase 6 (Advanced Features)    ═══════════════════╩╗
  - Requires all prior phases                     ║
                                                  ║
Phase 7 (Production Deploy)    ═══════════════════╩═══
  - Final phase, requires everything complete
```

### Critical Path:
1. Phase 1 (tests + DB upgrade + async) → blocks everything
2. Phase 2 (frontend) → parallel with Phase 3 infra
3. Phase 3 (Docker + CI/CD) → blocks deployment
4. Phase 4 (auth) → blocks production
5. Phase 5 (observability) → blocks production confidence
6. Phase 6 (advanced features) → enhances demo/value
7. Phase 7 (deploy) → go-live

### Minimum Viable Demo Path (fastest to demo):
If you need a demo ASAP, the order would be:
1. Phase 1.7 (basic tests only) - 3 days
2. Phase 2.2-2.4 (frontend core pages) - 2 weeks
3. Phase 3.1 (Docker only) - 2 days
4. Phase 6.5 (Demo mode) - 3 days
**Total: ~3 weeks to a compelling demo**

### Minimum Viable Production Path:
1. Full Phase 1 - 2 weeks
2. Full Phase 2 - 3 weeks
3. Full Phase 3 - 2 weeks
4. Phase 4.1-4.2 (auth + basic multi-tenancy) - 1.5 weeks
5. Phase 5.1-5.2 (metrics + logging) - 1 week
6. Phase 7 - 1 week
**Total: ~10-11 weeks to production**

---

## Technology Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend API** | Python 3.11+ / FastAPI | Already in use, high performance async |
| **Frontend** | Next.js 14+ / TypeScript | SSR, App Router, strong ecosystem |
| **UI Components** | shadcn/ui + Tailwind CSS | Modern, accessible, customizable |
| **Charts** | Recharts or Tremor | React-native charting, good for dashboards |
| **State (Client)** | TanStack Query + Zustand | Server state + client state separation |
| **Real-time** | WebSocket (native) | Low latency, built into FastAPI |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Enterprise-grade, great tooling |
| **Cache** | Redis | Session, pub/sub, rate limiting |
| **ORM/Migrations** | SQLAlchemy + Alembic | Industry standard, migration support |
| **Container** | Docker + Docker Compose | Standard containerization |
| **Orchestration** | ECS Fargate (or EKS) | Serverless containers, low ops burden |
| **CI/CD** | GitHub Actions | Native GitHub integration |
| **IaC** | Terraform | Multi-cloud, mature, large community |
| **Monitoring** | Prometheus + Grafana (or CloudWatch) | Industry standard observability |
| **Tracing** | OpenTelemetry + Jaeger/X-Ray | Vendor-neutral distributed tracing |
| **CDN** | CloudFront | Low latency static asset delivery |
| **DNS** | Route 53 | Integrated with AWS ecosystem |
| **Secrets** | AWS Secrets Manager | Secure secrets rotation |
| **Linting** | Ruff (Python) / ESLint (TS) | Fast, comprehensive |
| **Testing** | Pytest (Python) / Vitest (TS) / Playwright (E2E) | Fast, modern test runners |

---

## Cost Estimates (AWS, Monthly)

### Staging Environment
| Resource | Spec | Est. Cost |
|----------|------|-----------|
| ECS Fargate (2 tasks) | 0.5 vCPU, 1GB each | $30 |
| RDS PostgreSQL | db.t3.micro, single AZ | $15 |
| ElastiCache Redis | cache.t3.micro | $12 |
| ALB | 1 LCU average | $20 |
| CloudFront | Minimal traffic | $5 |
| Route 53 | 1 hosted zone | $1 |
| CloudWatch | Basic logging | $10 |
| **Total** | | **~$93/month** |

### Production Environment
| Resource | Spec | Est. Cost |
|----------|------|-----------|
| ECS Fargate (4 tasks) | 1 vCPU, 2GB each | $120 |
| RDS PostgreSQL | db.r6g.large, Multi-AZ | $350 |
| ElastiCache Redis | cache.r6g.large, cluster | $200 |
| ALB | 5 LCU average | $40 |
| CloudFront | Moderate traffic | $20 |
| Route 53 | 1 hosted zone + health checks | $5 |
| CloudWatch | Full logging + metrics | $50 |
| S3 | Log archives, backups | $10 |
| Secrets Manager | 10 secrets | $5 |
| WAF | Basic rules | $10 |
| **Total** | | **~$810/month** |

---

## File Deliverables Summary

When complete, the repository structure will look like:

```
syntropiq/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy-staging.yml
│       └── deploy-production.yml
├── frontend/
│   ├── app/                    # Next.js pages
│   ├── components/             # React components
│   ├── hooks/                  # Custom hooks
│   ├── lib/                    # Utilities
│   ├── stores/                 # State management
│   ├── types/                  # TypeScript types
│   ├── public/                 # Static assets
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── syntropiq/
│   ├── core/                   # Enhanced with logging, config profiles
│   ├── governance/             # Enhanced with async, policies
│   ├── execution/              # Enhanced with async, retry logic
│   ├── persistence/            # Enhanced with PostgreSQL, migrations
│   ├── api/                    # Enhanced with auth, WebSocket, pagination
│   └── tests/
│       ├── conftest.py
│       ├── unit/               # 13+ test modules
│       └── integration/        # 6+ test modules
├── infrastructure/
│   └── terraform/
│       ├── environments/
│       │   ├── staging/
│       │   └── production/
│       └── modules/
│           ├── networking/
│           ├── compute/
│           ├── database/
│           ├── loadbalancer/
│           ├── cdn/
│           ├── dns/
│           └── monitoring/
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── .dockerignore
├── pyproject.toml
├── Makefile
├── .pre-commit-config.yaml
├── alembic.ini
├── README.md
└── ENGINEERING_PLAN.md         # This document
```
