# AI-Assisted Development Artifact (AI_DEVELOPMENT.md)

This document provides a comprehensive accounting of how Artificial Intelligence was leveraged during the conception, architecture, implementation, debugging, testing, and hardening of the **AI Study Companion** platform.

---

## 1. Development AI Tools Used

| Tool / Model | Role in Development | Primary Usage |
| :--- | :--- | :--- |
| **Antigravity (Google DeepMind)** | Autonomous Agentic Pair-Programmer | End-to-end plan generation, codebase inspection, multi-file refactoring, test writing, and continuous integration validation. |
| **Gemini 1.5 Pro / Flash** | Large Language Model | Code synthesis, prompt design, complex schema verification, and architectural tradeoff reasoning. |
| **OpenAI GPT-4o** | Multimodal Reference Model | Validating RAG grounding patterns, evaluation rubrics, and vision-assisted document QA. |
| **Pytest & Starlette TestClient** | Automated Verification Harness | Deterministic execution and verification of AI-generated backend routes, services, and models. |

---

## 2. Prompts Used by Phase

The development workflow was structured through deliberate, contextual prompts across multiple developmental phases:

### A. System Design & Architecture
- *"Design a multi-tenant hierarchical domain model supporting Spaces, Projects, Materials, and Concept Masteries with strict user isolation."*
- *"Architect an asynchronous document ingestion pipeline in FastAPI that extracts text page-by-page, generates vector embeddings, and tracks processing states (PENDING, PROCESSING, READY, FAILED) without blocking the main event loop."*

### B. Core Implementation
- *"Implement a grounded Retrieval-Augmented Generation (RAG) Tutor service that retrieves top-k chunks by similarity, attaches precise page citations, and explicitly refuses out-of-domain or unsupported queries without hallucinating."*
- *"Create an Adaptive Knowledge Quiz engine that selects questions based on concept mastery scores, updates confidence scores using exponential moving averages, and records learning activity events."*
- *"Develop an Open-ended Rubric Assessment evaluator that scores student text answers against accuracy, conceptual completeness, and clarity."*

### C. Debugging & Bug Fixing
- *"Inspect test failures in `test_rag_tutor.py` where chunk similarity threshold was filtering out borderline keywords. Adjust hybrid retrieval weighting to prioritize exact keyword matches alongside vector similarity."*
- *"Fix schema mismatch in `/projects/{project_id}/growth` endpoint where frontend expected `overall_progress` and `summary` while test harness looked for `status`."*
- *"Resolve SQLite database lock collision in `conftest.py` during concurrent test execution by standardizing test session lifecycle and database teardown."*

### D. Hardening & Testing
- *"Write an exhaustive end-to-end verification script `verify_final_e2e.py` covering registration, space/project creation, PDF upload, background ingestion, tutor chat, citation verification, unsupported question refusal, adaptive quiz, open assessment, mastery update, growth analysis, recommendations, and material replacement/deletion."*
- *"Create a dedicated security test suite `test_security_error_handling.py` verifying multi-tenant isolation, admin 403 authorization guards, unauthenticated 401 rejections, and zero stack trace leakage."*

### E. Documentation
- *"Generate comprehensive system architecture diagrams in Mermaid and document all API endpoints, environment variables, quickstart steps, and operational runbooks."*

---

## 3. AI Code vs. Human Code Analysis

### Breakdown
- **AI-Generated Code**: **~85%**
  - Boilerplate Pydantic schemas, SQLAlchemy ORM models, FastAPI route definitions, CRUD services, and automated test suites.
- **Human Guidance & Refinement**: **~15%**
  - Domain architecture definition, safety guardrails (anti-hallucination thresholds), edge case identification, security constraints, and schema synchronization.

### What Required Human Intervention
1. **RAG Refusal Threshold Calibration**:
   - Initial AI models were overly eager to answer questions from generic internal training knowledge. Human calibration introduced strict negative constraint prompts and cosine similarity minimum thresholds to ensure truthful refusals on out-of-domain topics.
2. **Database Session & Concurrency Boundaries**:
   - SQLite file locks under rapid test execution required human architectural intervention to ensure tests cleanly separated test database instances from development databases.
3. **Multi-tenant Security Hardening**:
   - Explicitly adding `user_id == current_user.id` filters to every query layer, ensuring that attempting to access another user's project returns `404 Not Found` rather than leaking existence via `403`.

### Where AI Excelled vs. Where AI Struggled
- **Where AI Excelled**:
  - Rapid scaffolding of multi-layered REST architectures.
  - Writing exhaustive, deterministic test suites covering hundreds of edge cases.
  - Generating consistent mathematical formulas (EMA mastery updates, velocity calculation).
- **Where AI Struggled**:
  - Keeping schemas in exact lockstep across disparate files when refactoring without explicit cross-referencing.
  - Handling filesystem state (e.g., PDF replacement race conditions and file descriptor cleanup) without specific platform prompts.

---

## 4. Lessons Learned in AI-Assisted Engineering

1. **Verify Early, Verify Deterministically**:
   - AI generates code rapidly; however, without a strict test suite, silent regressions compound. Running `pytest` and end-to-end verification scripts after every iteration was the single most impactful development practice.
2. **Preserve Working Code with Explicit Constraints**:
   - Framing prompts with clear negative constraints (*"Do NOT rebuild working features; preserve existing authentication and database tables"*) prevented unnecessary rewrites.
3. **Plan Before Modifying**:
   - Writing down an `implementation_plan.md` artifact before touching source code drastically reduced backtracking and circular bug-fixing.

---

## 5. Build AI vs. Runtime AI: The Critical Distinction

A foundational distinction in this project is the difference between **Build AI** and **Runtime AI**:

```
+-----------------------------------------------------------------------------+
|                                BUILD AI                                     |
|                                                                             |
|  - Tools: Google Antigravity, Gemini 1.5 Pro, Claude, GitHub Copilot        |
|  - Role: The "Software Engineer" writing and maintaining code               |
|  - Environment: Developer IDE, CLI, Code generation, Unit tests             |
|  - Output: Python scripts, React components, SQL queries, Documentation     |
+-----------------------------------------------------------------------------+
                                       |
                               Produces / Deploys
                                       v
+-----------------------------------------------------------------------------+
|                               RUNTIME AI                                    |
|                                                                             |
|  - Tools: Vector Embeddings (text-embedding-004), Gemini 1.5 / GPT-4o APIs  |
|  - Role: The "Smart Brain" inside the product delivering student features   |
|  - Environment: Live production FastAPI service executing user requests     |
|  - Capabilities:                                                            |
|      * Semantic chunk retrieval & cosine similarity ranking                 |
|      * Grounded student explanations with page-level citations              |
|      * Unsupported query refusal and hallucination mitigation               |
|      * Rubric-based assessment grading & concept mastery classification     |
+-----------------------------------------------------------------------------+
```

- **Build AI** acted as the software engineer pair-programmer that translated product requirements into robust, tested Python and React source code.
- **Runtime AI** is the runtime inference engine embedded inside the product that analyzes student PDFs, answers questions in real-time, grades assignments, and calculates concept mastery.
