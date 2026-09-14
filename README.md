# AI Study Companion

An enterprise-ready, multi-tenant AI study and personalized learning platform. Built with a high-throughput **FastAPI** backend and an intuitive **React (Vite)** frontend, the application transforms static course documents (PDFs) into an interactive, grounded learning experience complete with real-time AI tutoring, adaptive quizzes, rubric-based assessments, concept mastery tracking, and administrative governance.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Quick Start & Setup Guide](#quick-start--setup-guide)
5. [Environment Variables](#environment-variables)
6. [Running the Application](#running-the-application)
7. [Running Tests & Verification](#running-tests--verification)
8. [API Documentation Summary](#api-documentation-summary)
9. [Default Test Accounts](#default-test-accounts)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## 1. Key Features

- **Hierarchical Domain Structure (Spaces & Projects)**: Organize learning into overarching academic spaces (e.g., *Computer Science*, *Physics*) and targeted course projects (e.g., *Data Structures*, *Thermodynamics*).
- **Asynchronous PDF Processing**: Non-blocking background extraction of text, page metadata, figures, tables, and formula references, followed by sliding-window chunking and vector indexing.
- **Grounded AI Study Tutor**: Conversational RAG assistant providing natural-language explanations with precise, verified page-level citations linked directly to uploaded documents.
- **Strict Anti-Hallucination & Unsupported Refusal**: Guardrailed retrieval that detects out-of-domain or unsupported queries and delivers a clear, polite refusal rather than fabricating information.
- **Adaptive Knowledge Quizzes**: Dynamic multi-choice quizzes that adapt question difficulty based on student concept mastery, scoring attempts and logging mistake counts.
- **Open-Ended Rubric Assessments**: Subjective free-response evaluations graded against a multi-criteria rubric (Accuracy, Completeness, Clarity) with detailed constructive feedback.
- **Concept Mastery Engine**: Real-time mastery calculation utilizing Exponential Moving Averages (EMA) to track proficiency trends and pinpoint critical knowledge gaps.
- **Learning Growth Analysis**: Evaluates learning velocity, categorizing concepts into *Improving*, *Stable*, or *Needs Attention*, and measuring overall progress.
- **Contextual Learning Recommendations**: Answers *"What should I do next?"* by prioritizing weak concepts, recent mistakes, and overdue review items.
- **Project & Global Analytics**: Rich aggregated analytics measuring learning sessions, quiz accuracy trends, tutor interaction counts, and activity heatmaps across individual projects and user-wide.
- **Comprehensive Activity Tracking**: Audit-logged event stream capturing every significant milestone (`SPACE_CREATED`, `MATERIAL_PROCESSED`, `TUTOR_QUESTION`, `QUIZ_COMPLETED`, etc.).
- **Admin Dashboard & RBAC**: Role-based access control (`ADMIN` vs `USER`), platform overview KPIs, user management, and activity inspection with strict multi-tenant privacy.
- **AI Usage & Evaluation Monitoring**: Tracks LLM token usage, request latency, estimated API costs, grounding fidelity rates, and citation verification percentages.
- **Lightweight System Health**: Live operational monitoring checking API status, database latency, storage disk utilization, and background worker status.

---

## 2. Architecture Overview

```
               +-------------------------------------------+
               |         React 18 + Vite Frontend          |
               | (Dashboard, Tutor, Quiz, Analytics, Admin)|
               +-------------------------------------------+
                                     |
                                REST API (JWT)
                                     v
               +-------------------------------------------+
               |           FastAPI Web Framework           |
               | (Auth, Spaces, Projects, Tutor, Admin)    |
               +-------------------------------------------+
                     /               |               \
                    /                |                \
    +-------------------+   +------------------+   +-------------------+
    | Background Tasks  |   |  RAG & AI Engine |   |  Mastery Engine   |
    | (PDF Ingestion,   |   | (Vector Search,  |   | (EMA Proficiency, |
    |  Chunking, Index) |   |  Grounded QA)    |   |  Growth, Recs)    |
    +-------------------+   +------------------+   +-------------------+
            |                        |                       |
            v                        v                       v
    +------------------------------------------------------------------+
    |           Persistence Layer: SQLite (Dev) / PostgreSQL (Prod)    |
    |           + Document Upload Storage & Vector Index               |
    +------------------------------------------------------------------+
```

For complete architectural diagrams and sequence flows, see [ARCHITECTURE.md](file:///home/rguktrkvalley/AI_campanion/ARCHITECTURE.md).

---

## 3. Prerequisites

- **Python**: Version `3.10` or higher (tested on `Python 3.12`)
- **Node.js**: Version `18.x` or higher (tested on `Node.js 20.x`)
- **Package Managers**: `pip` (Python) and `npm` (Node.js)
- **Database**: SQLite (default, zero configuration) or PostgreSQL 14+ for production

---

## 4. Quick Start & Setup Guide

### Step 1: Clone or Navigate to the Repository
```bash
cd /home/rguktrkvalley/AI_campanion
```

### Step 2: Set Up Backend Virtual Environment
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy the environment template from the root directory:
```bash
cp ../.env.example ../.env
```
*(The default settings work immediately out of the box using local SQLite and automatic offline fallback AI providers.)*

### Step 4: Initialize the Database
```bash
python -m app.database.init_db
```
*(Automatically creates all 17 schema tables and seeds the default administrator account).*

### Step 5: Set Up Frontend Dependencies
```bash
cd ../frontend
npm install
npm run build
```

---

## 5. Environment Variables

All configuration is loaded from `.env` in the repository root or system environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `AI Study Companion` | Name of the platform displayed in APIs and headers. |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin for frontend client communication. |
| `DATABASE_URL` | `sqlite:///./ai_study_companion.db` | SQLAlchemy connection string. Set to PostgreSQL in production. |
| `JWT_SECRET` | `dev_super_secret_key_...` | Cryptographic secret key for signing JWT tokens. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `1440` (24 hours) | Token validity duration before re-authentication is required. |
| `AI_PROVIDER` | `auto` | Preferred AI provider: `auto`, `openai`, or `gemini`. |
| `OPENAI_API_KEY` | `""` (optional) | OpenAI API key for production GPT-4o RAG tutoring and vision QA. |
| `OPENAI_MODEL` | `gpt-4o` | Model identifier for OpenAI calls. |
| `AI_API_KEY` | `""` (optional) | Google Gemini API key for Gemini 1.5 Flash processing. |
| `AI_MODEL` | `gemini-1.5-flash` | Model identifier for Gemini calls. |
| `EMBEDDING_MODEL` | `text-embedding-004` | Embedding model identifier. |

---

## 6. Running the Application

### Running the Backend Server
From the `backend/` directory:
```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Running the Frontend Server
From the `frontend/` directory:
```bash
npm run dev
```
- Web Application URL: `http://localhost:5173`

---

## 7. Running Tests & Verification

The test suite includes 70+ automated tests validating unit logic, integration flows, security, and error handling.

### Run All Pytest Suites
```bash
cd /home/rguktrkvalley/AI_campanion
pytest backend/tests
```

### Run Specific Test Modules
```bash
# Security & multi-tenant isolation tests
pytest backend/tests/test_security_error_handling.py

# AI Tutor grounding & anti-hallucination tests
pytest backend/tests/test_tutor_robustness.py
pytest backend/tests/test_rag_tutor.py

# Adaptive Quiz and Open-ended Assessment tests
pytest backend/tests/test_quiz.py
pytest backend/tests/test_assessment.py

# Admin RBAC & Dashboard tests
pytest backend/tests/test_admin.py
```

### Run End-to-End System Verification Script
Executes the full 12-step student lifecycle (Register -> Space -> Project -> PDF Ingest -> Tutor -> Quiz -> Assessment -> Mastery -> Growth -> Recommendations -> Analytics -> Replace/Delete):
```bash
python backend/verify_final_e2e.py
```

---

## 8. API Documentation Summary

### Authentication (`/auth`)
- `POST /auth/register` — Register a new student account.
- `POST /auth/login` — Authenticate and receive a JWT bearer token.
- `GET /auth/me` — Retrieve current authenticated user profile.

### Spaces & Projects (`/spaces`, `/projects`)
- `GET /spaces`, `POST /spaces` — List and create academic spaces.
- `GET /spaces/{id}/projects`, `POST /spaces/{id}/projects` — List and create course projects.
- `GET /projects/{id}`, `PUT /projects/{id}`, `DELETE /projects/{id}` — Manage project details.

### Materials & Ingestion (`/projects/{id}/materials`)
- `POST /projects/{id}/materials` — Upload a PDF file for background ingestion.
- `GET /projects/{id}/materials` — List uploaded materials and processing status.
- `PUT /projects/{id}/materials/{material_id}/replace` — Invalidate old chunks and re-index updated PDF.
- `DELETE /projects/{id}/materials/{material_id}` — Delete material and wipe chunks from retrieval index.

### AI Study Tutor (`/projects/{id}/tutor`)
- `POST /projects/{id}/tutor/chat` — Send a student question, returning a grounded answer with page citations or safe refusal.
- `GET /projects/{id}/tutor/conversations` — View student conversation history.

### Quizzes & Assessments (`/projects/{id}/quizzes`, `/projects/{id}/assessments`)
- `POST /projects/{id}/quizzes/generate` — Generate an adaptive knowledge quiz.
- `POST /projects/{id}/quizzes/{quiz_id}/answer` — Submit an answer for instant feedback.
- `POST /projects/{id}/assessments/generate` — Generate an open-ended assessment.
- `POST /projects/{id}/assessments/{id}/submit` — Submit free-text response for rubric grading.

### Mastery, Growth & Recommendations (`/projects/{id}/*`)
- `GET /projects/{id}/mastery` — Retrieve concept proficiencies and mastery categories.
- `GET /projects/{id}/growth` — View learning velocity and concept trend classifications.
- `GET /projects/{id}/recommendations` — Fetch actionable next steps prioritizing weak areas.
- `POST /projects/{id}/recommendations/{rec_id}/complete` — Mark a recommended action as done.

### Analytics (`/projects/{id}/analytics`, `/analytics/*`)
- `GET /projects/{id}/analytics` — Detailed project activity metrics, quiz trends, and event feed.
- `GET /analytics/global` — Cross-project aggregate analytics for the authenticated user.

### Admin Dashboard (`/admin/*`) *(Requires ADMIN role)*
- `GET /admin/dashboard/overview` — Platform-wide KPIs and recent activity streams.
- `GET /admin/users` — List platform users with learning summaries.
- `GET /admin/users/{user_id}/details` — Deep dive into a specific student's spaces, projects, and mastery.
- `GET /admin/ai-usage` — Token usage breakdown, estimated costs, and feature volume.
- `GET /admin/ai-evaluation` — Tutor grounding fidelity and citation accuracy metrics.
- `GET /admin/system-health` — Operational status, DB latency, and storage metrics.

---

## 9. Default Test Accounts

For automated verification and administrative evaluation:

| Account Type | Email | Password | Role |
| :--- | :--- | :--- | :--- |
| **Platform Administrator** | `admin@ai-study.edu` | `AdminPassword123!` | `ADMIN` |
| **Test Student A** | `alice@example.com` | `password123` | `USER` |
| **Test Student B** | `bob@example.com` | `password123` | `USER` |

---

## 10. Troubleshooting Guide

### Issue 1: SQLite Database Lock Errors during Rapid Test Runs
- **Cause**: Multiple parallel test threads attempting to write to the same SQLite database file.
- **Solution**: Run test suites sequentially using `pytest backend/tests` without `-n` parallel flags. The `conftest.py` harness uses scoped transactional rollbacks to preserve isolation.

### Issue 2: Uploaded Material Remains in `PENDING` Status
- **Cause**: Background task worker interrupted before completing ingestion.
- **Solution**: Ensure the server was not terminated during upload. Check `GET /projects/{id}/materials` to inspect the `status_message`. If the file was corrupted, upload a valid PDF file.

### Issue 3: 403 Forbidden on Admin Routes
- **Cause**: Logged-in user has the `USER` role rather than `ADMIN`.
- **Solution**: Log in with `admin@ai-study.edu` / `AdminPassword123!` or update your test user's role in the database: `UPDATE users SET role = 'ADMIN' WHERE email = '...';`.

### Issue 4: Frontend Cannot Connect to Backend
- **Cause**: Backend server is not running or CORS origin mismatch.
- **Solution**: Ensure backend is running on `http://localhost:8000`. Confirm that `FRONTEND_URL` in `.env` matches your Vite development port (default `http://localhost:5173`).
