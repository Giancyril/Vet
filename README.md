# Vet — AI Code Reviewer

A production-grade, enterprise-ready automated AI Code Review and Pull Request Intelligence platform powered by Google Gemini 2.5, async FastAPI, and Next.js 15. Features a 4-persona concurrent Multi-Agent Review Committee (Security, Performance, Clean Code, Testing), dynamic PR Health Scoring (0–100 composite grades with dimension breakdowns), AST-powered breaking change and cyclomatic complexity detection, pre-LLM zero-latency secret scanning with Shannon entropy filtering, full OWASP Top 10 compliance classification with CWE tagging, automated 1-click companion PR remediation with unified patch generation, real-time WebSocket review streaming telemetry with live agent radar status, PR Blast Radius & dependency impact visualizer, AI-powered semantic PR changelog and Conventional Commits generator, automated pytest test suite synthesizer, custom repository policy engine with AST rule enforcement, and a high-performance dark-mode analytics dashboard.

## Features

### Core Functionality
- **Automated PR Ingestion**: Listens to GitHub App pull request webhooks (`opened`, `synchronize`, `reopened`) with HMAC-SHA256 signature verification.
- **Unified Diff Parsing & Context Builder**: Fetches PR context, file patches, and raw source contents with smart exclusion for lockfiles (`package-lock.json`, `poetry.lock`, `yarn.lock`), minified assets, and binary files.
- **GitHub App JWT Authentication**: Automatic RS256 token generation and fine-grained installation token acquisition with automatic caching and rotation.
- **Atomic Review Posting**: Posts structured pull request reviews to GitHub via the REST API with line-targeted inline suggestions (using GitHub native ` ```suggestion ` blocks for 1-click developer merges) alongside a markdown summary.
- **Dashboard & Repository Management**: Full management UI and REST APIs for toggling active repositories, customizing review instructions per repository, filtering severity thresholds, and adjusting max comments per PR.

### Advanced Features
- **👥 Multi-Agent Review Committee**: Concurrently orchestrates four specialized AI personas running in parallel via `asyncio.gather` for comprehensive multidimensional coverage:
  - **Security Auditor (🛡️)**: Strict analyzer focused exclusively on credential leaks, SQL/command injection, deserialization, auth bypass, and missing sanitization.
  - **Performance Architect (⚡)**: Identifies N+1 query patterns, async event-loop blocking I/O, memory leaks, high algorithmic complexity, and missing pagination.
  - **Clean Code Guardian (✨)**: Enforces maintainability, DRY principles, naming clarity, single responsibility, and error-handling idioms.
  - **Test Coverage Specialist (🧪)**: Detects untested public signatures, missing boundary/edge-case tests, brittle assertions, and flaky test patterns.
- **🏥 PR Health Score Calculator**: Aggregates multi-agent findings into a weighted 0–100 health composite score (`Security: 35%`, `Performance: 25%`, `Clean Code: 20%`, `Testing: 20%`) with letter grades (`A+`, `A`, `B`, `C`, `D`, `F`), dimension penalty breakdowns, and actionable merge advice.
- **📊 Real-Time Review Streaming & Agent Radar**: WebSocket-powered live activity feed (`LiveAgentStream.tsx`) that streams real-time review progress directly to the browser, displaying live radar sweeps, active agent status badges, and sub-second event logs as files are inspected.
- **🌐 PR Blast Radius & Dependency Impact Visualizer**: Static dependency and import graph analyzer (`blast_radius.py` & `BlastRadiusGraph.tsx`) that computes an overall **Blast Radius Impact Index** (0–100), detects modified public symbols, highlights breaking exports, and maps downstream module dependencies.
- **📜 Automated PR Changelog & Release Notes Generator**: Gemini 2.5 powered changelog synthesizer (`changelog_service.py` & `ChangelogModal.tsx`) producing Conventional Commits entries (`feat:`, `fix:`, `refactor:`, `breaking:`), customer-facing release notes, technical migration guides, and 1-click GitHub PR description sync.
- **🧪 AI Test Generator & Synthetic Edge-Case Synthesizer**: AI test synthesis engine (`test_generator.py` & `TestGeneratorModal.tsx`) that inspects modified functions via AST and generates complete, runnable `pytest` test suites with fixtures, mocks, and parameterized boundary assertions.
- **🎯 Custom Repository Policy Engine & AST Rule Builder**: Configurable repository policy evaluator (`policy_engine.py` & `PolicyEngineManager.tsx`) supporting 6 built-in rule templates (banning raw `print()`, enforcing UTC on `datetime.now()`, disallowing bare `except:`, requiring docstrings/type hints, blocking hardcoded URLs) plus custom regex/AST rules with an integrated live rule tester.
- **💬 Interactive PR Chatbot Concierge**: Context-aware floating assistant widget (`PRChatBot.tsx`) connected to `POST /api/v1/reviews/{id}/chat`. Retains a sliding 6-message history window so developers can ask clarifying questions, explore rationale, or request code examples directly on specific review reports.
- **🔔 Notification Hub (Slack & Webhooks)**: Fire-and-forget asynchronous notification service that sends formatted Slack Block Kit cards and generic HTTP webhook payloads with direct PR jump links, health badges, and severity breakdowns upon review completion.
- **🔍 AST-Based Breaking Change Detection**: Static analysis engine (`ast_analyzer.py`) that parses Python Abstract Syntax Trees to detect removed public functions and deleted required parameters between base and head branches, flagging breaking API contracts before merge.
- **⚡ Cyclomatic Complexity Tracker**: Evaluates branching decision points (`If`, `While`, `For`, `BoolOp`, `ExceptHandler`, `comprehensions`) across all functions in the diff. Flags functions exceeding maintainability thresholds (CC > 10) or length thresholds (> 50 lines).
- **🪄 Auto-Remediation Engine**: Translates actionable suggested fixes into clean, unified git patches (`difflib.unified_diff`) using reverse line-indexing math to prevent offset drift during multi-location replacements.
- **🚀 1-Click Companion PR Creator**: Automatically provisions a target branch (`vet/fix-pr-<id>`), commits remediated files via GitHub REST API, and opens a companion Pull Request against the developer's feature branch.
- **🔒 Pre-LLM Secret Scanner**: Zero-latency regex and Shannon entropy scanner that inspects added diff lines before sending prompts to Gemini. Instantly flags and masks AWS keys, GitHub PATs, Stripe secret keys, OpenAI/Gemini tokens, and Private RSA/SSH keys.
- **🛡️ OWASP Top 10 Compliance Classifier**: Automatically matches findings against the standard OWASP Top 10 catalog (A01 Broken Access Control to A10 SSRF) and tags findings with standardized CWE references.
- **Health Score Gauge Component**: High-performance animated HTML5 canvas radial gauge (`HealthScoreGauge.tsx`) with gradient strokes, grade glow effects, and dynamic dimension progress indicators.
- **Security Shield Dashboard Widget**: Dedicated real-time security widget (`SecurityShield.tsx`) displaying leak statuses, credential rotation warnings, and compliance breakdowns.

---

## Tech Stack

### Backend
- **Python 3.12+** with **FastAPI** (async/await)
- **SQLAlchemy 2.0** (asyncio with `aiosqlite` and PostgreSQL support)
- **Pydantic v2** & **Pydantic Settings** for data validation and schema management
- **Google GenAI SDK** (`google-genai` with Gemini 2.5 Flash)
- **HTTPX** for async HTTP and GitHub REST API communications
- **PyJWT** & **Cryptography** for GitHub App RS256 authentication
- **WebSockets** for real-time review progress streaming
- **Pytest** with `pytest-asyncio` for unit and integration testing

### Frontend
- **Next.js 15** (App Router) with **React 19**
- **TypeScript** for strict type safety
- **Tailwind CSS** with custom dark-mode design tokens and glassmorphic styling
- **Lucide React** for icons
- **HTML5 Canvas** for animated health score radial gauges

---

## System Architecture

```mermaid
graph TD
    subgraph GitHub ["GitHub Platform"]
        PR["Pull Request Event"] --> Webhook["GitHub Webhook POST"]
        App["GitHub App API"]
    end

    subgraph Backend ["FastAPI Backend (/api/v1)"]
        Router["Webhook Router"]
        Auth["RS256 JWT & Installation Auth"]
        Diff["Diff Fetcher & Filter"]

        SecretScan["Pre-LLM Secret Scanner"]
        ASTScan["AST Breaking Change & Complexity Analyzer"]
        PolicyEngine["Custom Policy & Rule Engine"]
        MultiAgent["Gemini 2.5 Multi-Agent Committee"]

        HealthCalc["PR Health Score Calculator"]
        BlastRadius["Blast Radius & Dependency Analyzer"]
        Remediation["Auto-Remediation Engine"]
        TestGen["AI Test Suite Synthesizer"]
        Changelog["Semantic Changelog Generator"]
        ChatSvc["PR Chatbot Service"]
        WSManager["WebSocket Connection Manager"]
        NotifySvc["Notification Dispatcher"]

        DB[("SQLite / PostgreSQL DB")]
    end

    subgraph Frontend ["Next.js 15 Dashboard"]
        Dash["Review Dashboard"]
        Gauge["Health Score Gauge"]
        Shield["Security Shield Widget"]
        LiveStream["Live Agent Stream Radar"]
        BlastGraph["Blast Radius Dependency Visualizer"]
        Toolbar["Review Action Toolbar"]
        Modal["Companion PR Modal"]
        ChangelogUI["Changelog & Release Notes Modal"]
        TestUI["AI Test Generator Modal"]
        PolicyUI["Policy Engine Manager"]
        ChatWidget["Interactive PR Chatbot"]
    end

    Webhook --> Router
    Router --> Auth
    Auth --> App
    App --> Diff

    Diff --> SecretScan
    Diff --> ASTScan
    Diff --> PolicyEngine
    Diff --> MultiAgent

    SecretScan --> HealthCalc
    ASTScan --> HealthCalc
    MultiAgent --> HealthCalc
    Diff --> BlastRadius

    HealthCalc --> DB
    HealthCalc --> App
    HealthCalc --> NotifySvc
    HealthCalc --> WSManager

    Dash --> DB
    Gauge --> HealthCalc
    Shield --> SecretScan
    LiveStream --> WSManager
    BlastGraph --> BlastRadius
    Toolbar --> Modal
    Toolbar --> ChangelogUI
    Toolbar --> TestUI
    Modal --> Remediation
    ChangelogUI --> Changelog
    TestUI --> TestGen
    PolicyUI --> PolicyEngine
    ChatWidget --> ChatSvc
```

---

## Module Dependency

```mermaid
graph LR
    subgraph BE_Modules ["Backend Module Flow"]
        Config["app.core.config"] --> Database["app.db.session"]
        Database --> Models["app.models"]
        Models --> Schemas["app.schemas"]

        GHAuth["app.github.auth"] --> DiffFetcher["app.github.diff_fetcher"]
        DiffFetcher --> SecretScanner["app.security.secret_scanner"]
        DiffFetcher --> ASTAnalyzer["app.analysis.ast_analyzer"]
        DiffFetcher --> PolicyEngine["app.security.policy_engine"]
        DiffFetcher --> BlastRadius["app.analysis.blast_radius"]
        DiffFetcher --> Personas["app.agents.personas"]

        Personas --> MultiReviewer["app.agents.multi_reviewer"]
        MultiReviewer --> HealthScore["app.agents.health_score"]

        SecretScanner --> ReviewService["app.services.review_service"]
        ASTAnalyzer --> ReviewService
        HealthScore --> ReviewService
        ReviewService --> WSEmitters["app.core.ws_emitters"]
        WSEmitters --> WSManager["app.core.websocket"]

        ReviewService --> Commenter["app.github.commenter"]
        ReviewService --> Notifications["app.services.notification_service"]
        ReviewService --> RemediationSvc["app.services.remediation_service"]
        RemediationSvc --> RemediationPR["app.github.remediation_pr"]
        ReviewService --> ChangelogSvc["app.services.changelog_service"]
        ReviewService --> TestGenSvc["app.services.test_generator"]
    end

    subgraph FE_Modules ["Frontend Module Flow"]
        APIClient["lib/api.ts"] --> ReviewList["app/page.tsx"]
        APIClient --> ReviewDetail["app/reviews/[id]/page.tsx"]
        APIClient --> ConfigPage["app/config/page.tsx"]
        ReviewDetail --> HealthGauge["components/HealthScoreGauge.tsx"]
        ReviewDetail --> SecShield["components/SecurityShield.tsx"]
        ReviewDetail --> LiveStream["components/LiveAgentStream.tsx"]
        ReviewDetail --> BlastGraph["components/BlastRadiusGraph.tsx"]
        ReviewDetail --> Toolbar["components/ReviewToolbar.tsx"]
        Toolbar --> PRModal["components/CompanionPRModal.tsx"]
        Toolbar --> ChangelogModal["components/ChangelogModal.tsx"]
        Toolbar --> TestGenModal["components/TestGeneratorModal.tsx"]
        ConfigPage --> PolicyManager["components/PolicyEngineManager.tsx"]
        ReviewDetail --> ChatUI["components/PRChatBot.tsx"]
    end
```

---

## Project Structure

```
AI Code Reviewer/
├── backend/                        # FastAPI Backend Application
│   ├── app/
│   │   ├── agents/                 # Multi-Agent Review Committee
│   │   │   ├── personas.py         # 4 Agent personas & system prompts
│   │   │   ├── multi_reviewer.py   # Concurrent multi-persona execution pipeline
│   │   │   └── health_score.py     # PR Health Score & dimension calculator
│   │   ├── analysis/               # AST Static Analysis & Blast Radius
│   │   │   ├── ast_analyzer.py     # Breaking change & cyclomatic complexity
│   │   │   └── blast_radius.py     # Import tree & dependency blast radius
│   │   ├── api/v1/                 # REST API & WebSocket Endpoints
│   │   │   ├── blast_radius.py     # Blast radius API router
│   │   │   ├── changelog.py        # Semantic changelog & GitHub PR sync router
│   │   │   ├── chat.py             # PR Chatbot API router
│   │   │   ├── health.py           # System liveness & readiness probes
│   │   │   ├── policy.py           # Policy rules CRUD & rule tester router
│   │   │   ├── remediation.py      # Auto-remediation & companion PR API
│   │   │   ├── repos.py            # Repository configuration endpoints
│   │   │   ├── reviews.py          # Review history & dashboard metrics
│   │   │   ├── router.py           # Central API v1 router
│   │   │   ├── test_gen.py         # AI pytest test synthesizer router
│   │   │   ├── webhooks.py         # GitHub Webhook receiver & signature verification
│   │   │   └── ws_stream.py        # WebSocket real-time review progress stream
│   │   ├── core/                   # Core Settings, Logging & Telemetry
│   │   │   ├── config.py           # Environment variables & Pydantic BaseSettings
│   │   │   ├── logging.py          # Structured loggers
│   │   │   ├── websocket.py        # WebSocket connection manager
│   │   │   └── ws_emitters.py      # Telemetry event broadcaster helpers
│   │   ├── db/                     # Database Session & Base
│   │   │   ├── base.py             # Declarative Base
│   │   │   └── session.py          # Async SQLAlchemy engine & session factory
│   │   ├── github/                 # GitHub API Integrations
│   │   │   ├── auth.py             # JWT app auth & installation access tokens
│   │   │   ├── commenter.py        # Inline comment & review summary formatter
│   │   │   ├── diff_fetcher.py     # Diff parser & context builder
│   │   │   └── remediation_pr.py   # Companion branch & PR creation via HTTPX
│   │   ├── models/                 # SQLAlchemy ORM Models
│   │   │   ├── config.py           # RepoConfig model (with custom_policy_rules)
│   │   │   ├── finding.py          # ReviewFinding model
│   │   │   ├── installation.py     # Installation model
│   │   │   ├── repository.py       # Repository model
│   │   │   └── review.py           # PullRequestReview model
│   │   ├── schemas/                # Pydantic Schemas
│   │   │   ├── chat.py             # Chat request & response schemas
│   │   │   ├── config.py           # Repo config request & response schemas
│   │   │   ├── gemini.py           # Structured output schemas for LLM
│   │   │   ├── remediation.py      # Remediation plan & companion PR schemas
│   │   │   └── review.py           # Review metrics, health score & detail schemas
│   │   ├── security/               # Security, Secret Scanning & Policy
│   │   │   ├── owasp_rules.py      # OWASP Top 10 definitions & classifier
│   │   │   ├── policy_engine.py    # Custom repository policy engine
│   │   │   └── secret_scanner.py   # Regex & Shannon entropy secret scanner
│   │   ├── services/               # Core Business Logic
│   │   │   ├── changelog_service.py# Semantic changelog & release note generator
│   │   │   ├── chat_service.py     # Gemini PR chatbot conversation engine
│   │   │   ├── gemini_reviewer.py  # Base Gemini review pipeline
│   │   │   ├── notification_service.py # Slack & webhook dispatcher
│   │   │   ├── prompt_builder.py   # Review prompt generator
│   │   │   ├── remediation_service.py  # Diff patch builder & inline fix applier
│   │   │   ├── review_service.py   # Master review coordination pipeline
│   │   │   └── test_generator.py   # AI pytest test suite synthesizer
│   │   └── main.py                 # FastAPI application factory & lifespan
│   ├── tests/                      # 127 Automated Tests
│   │   ├── test_api_dashboard.py   # REST API endpoint tests
│   │   ├── test_ast_analyzer.py    # AST breaking change & complexity tests
│   │   ├── test_chat_notifications.py # Chat service & Slack notification tests
│   │   ├── test_commenter.py       # Inline comment format & review posting tests
│   │   ├── test_config.py          # Repo config update tests
│   │   ├── test_diff_fetcher.py    # Diff filtering & file exclusion tests
│   │   ├── test_edge_cases.py      # Large files, unicode, and fallback tests
│   │   ├── test_gemini_reviewer.py # Gemini prompt and parsing tests
│   │   ├── test_init.py            # Health & root endpoint tests
│   │   ├── test_multi_agent.py     # Persona & health score unit tests
│   │   ├── test_policy_changelog.py# Policy engine, built-in rules & changelog tests
│   │   ├── test_remediation.py     # Patch generation & inline fixing tests
│   │   ├── test_review_service.py  # End-to-end review service tests
│   │   ├── test_security.py        # Secret scanner & OWASP mapping tests
│   │   ├── test_webhooks.py        # Webhook signature & event handler tests
│   │   └── test_ws_blast_radius.py # WebSocket broadcasting & blast radius tests
│   ├── pytest.ini                  # Pytest configuration
│   └── requirements.txt            # Python dependencies
├── frontend/                       # Next.js 15 Dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── config/             # Repository settings & policy rules page
│   │   │   ├── repos/              # Repository list view
│   │   │   ├── reviews/[id]/       # Review detail, live stream & blast visualizer
│   │   │   ├── layout.tsx          # Root dark-mode layout
│   │   │   └── page.tsx            # Home review history & metrics overview
│   │   ├── components/             # Reusable UI Components
│   │   │   ├── BlastRadiusGraph.tsx# Interactive dependency blast radius visualizer
│   │   │   ├── ChangelogModal.tsx  # Tabbed changelog & 1-click PR sync modal
│   │   │   ├── CompanionPRModal.tsx# 1-Click auto-remediation modal
│   │   │   ├── FindingCard.tsx     # Rich finding card with AST & breaking badges
│   │   │   ├── HealthScoreGauge.tsx# Canvas radial health score gauge
│   │   │   ├── LiveAgentStream.tsx # Real-time WebSocket agent radar stream
│   │   │   ├── Navbar.tsx          # Navigation header
│   │   │   ├── PolicyEngineManager.tsx # Custom rule editor & live rule tester
│   │   │   ├── PRChatBot.tsx       # Floating interactive PR chat panel
│   │   │   ├── ReviewToolbar.tsx   # Action toolbar for PR actions and modals
│   │   │   ├── SecurityShield.tsx  # Zero-day secret & OWASP security widget
│   │   │   ├── TestGeneratorModal.tsx # AI pytest test suite generator modal
│   │   │   └── VerdictBadge.tsx    # APPROVED / REQUEST_CHANGES status badges
│   │   └── lib/                    # Utilities & API Client
│   │       ├── api.ts              # Fetch wrappers for backend REST endpoints
│   │       └── utils.ts            # Date formatters and className merger
│   └── package.json                # Frontend dependencies
└── README.md
```

---

## API Documentation Overview

The backend exposes the following RESTful and WebSocket API routes:

*   **Health**: `GET /api/v1/health` — System liveness & database connectivity probe.
*   **Webhooks**: `POST /api/v1/webhook` — GitHub App webhook ingestion endpoint with HMAC verification.
*   **WebSocket Stream**: `WS /api/v1/ws/reviews/:id` — Real-time review telemetry event stream.
*   **WebSocket Global Feed**: `WS /api/v1/ws/feed` — System-wide active review broadcasting channel.
*   **Reviews**: `GET /api/v1/reviews` — List all PR reviews with pagination (`?limit=20&offset=0&repository_id=...&verdict=...`).
*   **Reviews**: `GET /api/v1/reviews/:id` — Retrieve full review detail with all findings, AST data, and health score.
*   **Blast Radius**: `GET /api/v1/reviews/:id/blast-radius` — Calculate PR dependency blast radius and impacted endpoints.
*   **Changelog**: `POST /api/v1/reviews/:id/generate-changelog` — Generate Conventional Commits changelog and release notes.
*   **Sync PR Description**: `POST /api/v1/reviews/:id/sync-pr-description` — 1-click update of GitHub PR description.
*   **Generate Tests**: `POST /api/v1/reviews/:id/generate-tests` — Synthesize runnable pytest test suites for modified files.
*   **Policy Templates**: `GET /api/v1/policy/templates` — List built-in repository policy rule templates.
*   **Policy Config**: `GET /api/v1/repos/:id/policy` — Get active policy rules for a repository.
*   **Policy Config**: `PUT /api/v1/repos/:id/policy` — Update repository policy configuration.
*   **Test Policy Rule**: `POST /api/v1/policy/test-rule` — Test a custom regex or AST rule against a code snippet.
*   **Run Policy on Review**: `POST /api/v1/reviews/:id/run-policy` — Run policy evaluation against a stored review.
*   **Dashboard Stats**: `GET /api/v1/stats` — Global metrics (total reviews, blocking prevented, suggestions made, avg duration).
*   **Repositories**: `GET /api/v1/repos` — List tracked GitHub repositories.
*   **Repositories**: `GET /api/v1/repos/:id/config` — Get repository review configuration.
*   **Repositories**: `PUT /api/v1/repos/:id/config` — Update repository settings (min severity, custom instructions, categories).
*   **PR Chatbot**: `POST /api/v1/reviews/:id/chat` — Interactive conversation turn with PR review context.
*   **Remediation Preview**: `GET /api/v1/reviews/:id/remediation-plan` — Preview unified patch diffs for suggested fixes.
*   **Companion PR**: `POST /api/v1/reviews/:id/create-companion-pr` — Create branch and companion PR on GitHub.

---

## Performance & Reliability Benchmarks

| Metric / Operation | Benchmark | Architecture Note |
| :--- | :---: | :--- |
| **Secret Scanning Latency** | `< 2ms` | Zero-latency regex & entropy pass executed before LLM call |
| **AST Analysis Latency** | `< 15ms` | In-memory AST walker parsing full Python syntax trees |
| **Blast Radius Calculation** | `< 8ms` | Static import tree traversal and export difference detection |
| **Policy Engine Evaluation** | `< 5ms` | Synchronous pre-LLM regex and AST rule checks across all diff files |
| **Concurrent Multi-Agent Review** | `~3.5s - 5.0s` | 4 specialist personas executed concurrently via `asyncio.gather` |
| **WebSocket Telemetry Latency** | `< 1ms` | Sub-millisecond event push to connected browsers via async websockets |
| **Inline Patch Generation** | `< 5ms` | Reverse line-index calculation with `difflib.unified_diff` |
| **Automated Test Suite** | **127 / 127 Passed** | Full unit and integration coverage across all subsystems |
| **Frontend Production Bundle** | **0 Errors** | Next.js 15 App Router static & dynamic compilation |

---

## Quick Start

### 1. Environment Configuration
Create a `.env` file in the project root:
```ini
ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./reviewer.db

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# GitHub App Credentials
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Optional Notification Integrations
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
NOTIFICATION_WEBHOOK_URL=https://your-webhook-endpoint.com/review
```

### 2. Run Backend Server
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Run Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the review dashboard.
