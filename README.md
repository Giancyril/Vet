# 🛡️ Vet — Enterprise Multi-Agent AI Code Reviewer

**Vet** is a developer-first, production-grade automated Code Review platform powered by **Google Gemini 2.5**, async **FastAPI**, and a sleek **Next.js 15** dark-mode dashboard.

---

## 🚀 5 Advanced Features

### 1. 👥 Multi-Agent Specialized Review Committee & Health Scoring
* **4 Concurrent Personas**: Security Auditor (🛡️), Performance Architect (⚡), Clean Code Guardian (✨), and Test Coverage Specialist (🧪).
* **Weighted PR Health Score**: Aggregates findings into a composite score (0–100) with letter grades (A+ to F), dimension breakdowns, and actionable merge recommendations.

### 2. 💬 Interactive PR Chatbot & Notification Hub
* **PR Chatbot**: Inline assistant allowing developers to ask clarifying questions, explore rationale, or request refactoring examples directly on specific review reports.
* **Multi-Channel Dispatch**: Automated Slack Incoming Webhook blocks and generic HTTP webhooks with rich status cards and direct PR jump links.

### 3. 🔍 AST-Based Breaking Change & Cyclomatic Complexity Analysis
* **Public Signature Diffs**: AST engine detects deleted functions and removed parameters to flag breaking API contracts before merge.
* **Cyclomatic Complexity Tracker**: Identifies deeply nested control flow and long functions exceeding maintainability thresholds.

### 4. 🪄 Auto-Remediation Engine & Companion PR Creator
* **Unified Diff Generation**: Automatically constructs precise multi-line replacement patches from suggested code fixes.
* **1-Click Companion PR**: Automatically creates a new branch `vet/fix-pr-<id>` and opens a companion Pull Request against the developer's branch.

### 5. 🔒 Security Shield, Pre-LLM Secret Scanner & OWASP Top 10
* **Zero-Latency Secret Scanner**: Regex & Shannon entropy scanning flags AWS keys, GitHub PATs, Stripe tokens, OpenAI/Gemini credentials, and Private RSA keys in diffs.
* **OWASP Top 10 Compliance**: Maps findings to standard OWASP categories (A01: Broken Access Control through A10: SSRF) with CWE references.

---

## 🏛️ System Architecture

```mermaid
graph TD
    GH[GitHub Webhooks / PR Event] --> FastAPI[FastAPI Backend /api/v1]
    FastAPI --> Auth[GitHub App JWT / Installation Token]
    FastAPI --> Diff[Diff Fetcher & Context Builder]

    Diff --> Scanner[Security Shield & Secret Scanner]
    Diff --> AST[AST Breaking Change & Complexity Analyzer]
    Diff --> MultiAgent[Gemini 2.5 Multi-Agent Committee]

    MultiAgent --> Health[PR Health Score Calculator]
    AST --> Health
    Scanner --> Health

    Health --> DB[(SQLAlchemy / Async DB)]
    Health --> GHComment[GitHub PR Review & Inline Comments]
    Health --> Notify[Slack / Webhook Dispatcher]

    Next[Next.js 15 Dashboard] --> FastAPI
    Next --> Chat[Interactive PR Chatbot]
    Next --> Remediation[1-Click Companion PR Creator]
```

---

## 🛠️ Tech Stack

* **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Google GenAI SDK (`google-genai`), PyJWT, HTTPX, Pytest.
* **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons.
* **Database**: SQLite (local development) / PostgreSQL (production).

---

## 🧪 Test Suite

The project contains **94 automated unit and integration tests** covering all pipelines and edge cases:
```bash
cd backend
pytest -v
```

---

## ⚙️ Quick Start

### 1. Environment Setup
Create `.env` in the root folder with the following variables:
```ini
ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./reviewer.db
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_webhook_secret
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 2. Backend Server
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to access the dashboard.
