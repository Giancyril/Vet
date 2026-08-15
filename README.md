# 🛡️ Warden AI Code Reviewer

An autonomous, production-grade GitHub PR Code Review system powered by **Google Gemini AI**, **FastAPI**, and **Next.js**. Automatically analyzes incoming pull requests, identifies security flaws, logical bugs, and performance bottlenecks, and posts line-specific inline suggestions with 1-click commit fixes directly back to GitHub.

---

## 🌟 Key Capabilities

- **Native GitHub App Integration**: Generates short-lived installation access tokens via RS256 JWTs and verifies incoming webhook HMAC-SHA256 signatures in constant time.
- **Context-Enriched Code Analysis**: Gathers both the unified diff patches and complete surrounding file contents to prevent hallucinated feedback.
- **Gemini Structured Output**: Strictly validates review schemas via Pydantic (`blocking`, `suggestion`, `nitpick`) with automatic noise filtering (ignores lockfiles, minified assets, and binary bundles).
- **Atomic Pull Request Reviews**: Submits top-level review summaries and line-targeted inline comments with native ````suggestion```` markdown blocks in a single transaction.
- **Granular Per-Repo Configuration**: Set minimum severity thresholds (`blocking only`, `suggestions + blocking`, `all`), toggle review categories, customize maximum comments per PR, and provide project-specific prompt guidelines.
- **Developer-First Web Dashboard**: Built with Next.js 15, Tailwind CSS, and dark-mode aesthetics for reviewing past PR history and inspecting individual findings.

---

## 📐 System Architecture

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant GH as GitHub Repository
    participant App as GitHub App Webhook
    participant API as FastAPI Backend
    participant Gemini as Google Gemini AI
    participant DB as PostgreSQL / SQLite
    participant UI as Next.js Dashboard

    Dev->>GH: Open / Update Pull Request
    GH->>App: POST /api/v1/webhooks/github (HMAC-SHA256)
    App->>API: Verify Signature (X-Hub-Signature-256)
    API->>API: Mint GitHub App JWT & Installation Token
    API->>GH: GET /pulls/{number}/files & File Contents
    GH-->>API: Unified Diff Patches & Head Revisions
    API->>DB: Load Repository Configuration
    DB-->>API: Thresholds, Categories, Custom Prompt
    API->>Gemini: Send Context Prompt (Schema Enforced)
    Gemini-->>API: JSON Findings (Blocking, Suggestions, Nitpicks)
    API->>API: Filter Findings by Severity & Categories
    API->>GH: POST /pulls/{number}/reviews (Atomic Inline Comments)
    API->>DB: Persist Review Record & Finding Items
    UI->>API: GET /api/v1/reviews & GET /api/v1/stats
    API-->>UI: Real-Time Review History & Findings
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** (FastAPI backend)
- **Node.js 18+** (Next.js dashboard)
- **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))
- **GitHub Account** (to register the GitHub App)

---

### 2. GitHub App Registration

1. Go to **GitHub &rarr; Settings &rarr; Developer settings &rarr; GitHub Apps &rarr; New GitHub App**.
2. Set the following details:
   - **GitHub App name**: `Warden-AI-Reviewer` (or unique name)
   - **Homepage URL**: `http://localhost:3000`
   - **Webhook URL**: Your backend URL or ngrok / smee.io URL (e.g. `https://your-domain.ngrok.app/api/v1/webhooks/github`)
   - **Webhook Secret**: Generate a secure random string (e.g. `openssl rand -hex 20`)
3. Configure **Repository Permissions**:
   - `Pull requests`: **Read & write**
   - `Contents`: **Read-only**
   - `Metadata`: **Read-only**
4. Under **Subscribe to events**, check:
   - `[x] Pull request`
5. Click **Create GitHub App**.
6. On the app settings page:
   - Note the **App ID**.
   - Click **Generate a private key** and download the `.pem` file.
7. Click **Install App** &rarr; Install on your target repository.

---

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Configure your .env file in backend/.env
```

Fill in `backend/.env` with your credentials:
```env
ENVIRONMENT="development"
DATABASE_URL="sqlite+aiosqlite:///./reviewer.db"
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-2.5-flash"
GITHUB_APP_ID="123456"
GITHUB_WEBHOOK_SECRET="your-webhook-secret"
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

Start the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at: `http://localhost:8000/api/v1/docs`

---

### 4. Frontend Dashboard Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` to view the review dashboard.

---

### 5. Running Automated Tests

```bash
cd backend
python -m pytest -v
```

All 37 test suites cover:
- HMAC-SHA256 constant-time webhook signature verification
- GitHub App RS256 JWT minting and installation token exchanges
- Unified diff parsing and lockfile skipping
- Gemini structured output extraction & priority truncation
- GitHub Pull Request Review API payload construction with 1-click suggestion blocks
- Multi-repo settings mutation & active toggles
- Fallback handling for out-of-hunk comments and Unicode diffs

---

## 🛡️ License
MIT License. Built with ❤️ for automated developer productivity.
