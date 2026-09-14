# AI Study Companion — System Architecture

## 1. System Overview

The **AI Study Companion** is an enterprise-grade, multi-tenant personalized learning platform built with a high-performance Python FastAPI backend and a responsive React (Vite) frontend. The platform structures student learning hierarchically into **Spaces** (academic domains) and **Projects** (targeted courses or topics).

Students upload course materials (PDFs), which are ingested through an asynchronous text and multimodal extraction pipeline, chunked, and embedded into a vector retrieval index. An intelligent **AI Study Tutor** utilizes grounded Retrieval-Augmented Generation (RAG) with precise page-level citations, refusing unsupported queries without hallucinating.

The platform continuously tracks student learning through **Adaptive Knowledge Quizzes**, **Open-ended Rubric Assessments**, **Concept Mastery Tracking**, **Growth Analysis**, **Contextual Learning Recommendations**, and an **Enterprise Admin Dashboard** with AI usage analytics and system health metrics.

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Frontend Layer (React 18 + Vite)"]
        UI[Modern Dashboard UI]
        Router[React Router v6]
        AuthContext[Auth & Session Store]
        TutorUI[Interactive AI Tutor]
        QuizUI[Adaptive Quiz & Assessments]
        AnalyticsUI[Growth & Analytics Charts]
        AdminUI[Admin Dashboard & Health]
    end

    subgraph API["API & Gateway Layer (FastAPI)"]
        CORS[CORS & Security Middleware]
        AuthRouter["/auth (JWT, Bcrypt)"]
        SpacesRouter["/spaces & /projects"]
        MaterialsRouter["/materials (Upload, Replace, Delete)"]
        TutorRouter["/tutor (RAG Chat, Grounding)"]
        QuizRouter["/quizzes & /assessments"]
        MasteryRouter["/mastery & /growth"]
        RecsRouter["/recommendations"]
        AnalyticsRouter["/analytics (Project & Global)"]
        AdminRouter["/admin (RBAC Guard)"]
    end

    subgraph Services["Core Application Services"]
        AuthSvc[AuthService]
        ProjectSvc[ProjectService]
        MaterialSvc[MaterialService]
        PDFProc[PDFProcessor & Ingestion]
        TutorSvc[TutorService & RAG Retriever]
        QuizSvc[QuizService & Scoring]
        AssessmentSvc[AssessmentService & Rubrics]
        MasterySvc[MasteryService & Engine]
        GrowthSvc[GrowthService]
        RecSvc[RecommendationService]
        ActivitySvc[ActivityService]
        AdminSvc[AdminService]
    end

    subgraph Data["Persistence & Vector Index"]
        DB[(Primary Relational DB: SQLite / PostgreSQL)]
        FileStore[(Local Upload Storage)]
        VectorIndex[(Embedding Vector Store)]
    end

    UI --> Router
    Router --> AuthContext
    AuthContext --> CORS
    CORS --> AuthRouter
    CORS --> SpacesRouter
    CORS --> MaterialsRouter
    CORS --> TutorRouter
    CORS --> QuizRouter
    CORS --> MasteryRouter
    CORS --> RecsRouter
    CORS --> AnalyticsRouter
    CORS --> AdminRouter

    AuthRouter --> AuthSvc
    SpacesRouter --> ProjectSvc
    MaterialsRouter --> MaterialSvc
    MaterialSvc --> PDFProc
    TutorRouter --> TutorSvc
    QuizRouter --> QuizSvc
    QuizRouter --> AssessmentSvc
    MasteryRouter --> MasterySvc
    MasteryRouter --> GrowthSvc
    RecsRouter --> RecSvc
    AnalyticsRouter --> ActivitySvc
    AdminRouter --> AdminSvc

    PDFProc --> FileStore
    PDFProc --> VectorIndex
    TutorSvc --> VectorIndex
    Services --> DB
```

---

## 3. Detailed Data Flows

### 3.1 PDF Upload, Processing, Chunking & Vector Indexing

```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant API as Materials Router
    participant BG as BackgroundTasks
    participant Proc as PDF Processor
    participant DB as Relational DB
    participant Vector as Vector Store

    Student->>API: POST /projects/{id}/materials (Upload PDF)
    API->>DB: Create Material record (status: PENDING)
    API->>API: Save raw PDF to storage disk
    API->>BG: Dispatch process_material_task(material_id)
    API-->>Student: 201 Created (status: PENDING)

    BG->>Proc: Ingest PDF file
    Proc->>Proc: Extract text by page (PyMuPDF / pdfplumber)
    Proc->>Proc: Extract figures, tables, formulas (multimodal)
    Proc->>Proc: Sliding window chunking (500 tokens, 100 overlap)
    Proc->>Proc: Compute embeddings (vector representation)
    Proc->>Vector: Store chunk embeddings + page metadata
    Proc->>DB: Store DocumentChunk records
    Proc->>DB: Update Material status to READY
    Proc->>DB: Log MATERIAL_PROCESSED ActivityEvent
```

### 3.2 Tutor RAG Retrieval, Grounding & Refusal

```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant Tutor as Tutor Router
    participant Retriever as Hybrid RAG Retriever
    participant LLM as LLM Engine (OpenAI / Gemini)
    participant Act as Activity & AI Usage

    Student->>Tutor: POST /projects/{id}/tutor/chat {"message": "..."}
    Tutor->>Tutor: Validate project access & session
    Tutor->>Retriever: Retrieve top-k chunks (hybrid semantic + lexical)
    alt No matching chunks found or below similarity threshold
        Retriever-->>Tutor: Empty or irrelevant context
        Tutor-->>Student: Grounded Refusal ("I could not find that information in the uploaded material.")
    else Relevant chunks found
        Retriever-->>Tutor: Top-k chunks with page & visual metadata
        Tutor->>LLM: Formulate grounded prompt (strict context injection)
        LLM-->>Tutor: Grounded explanation with cited pages
        Tutor->>Act: Record TUTOR_QUESTION event & AI token usage
        Tutor-->>Student: 200 OK {"answer": "...", "grounded": true, "citations": [...]}
    end
```

### 3.3 Assessment, Mastery Tracking, Growth & Recommendations

```mermaid
flowchart TD
    Start([Quiz or Open-Ended Assessment]) --> Submit[Student submits answers]
    Submit --> Eval[Automated Scoring & Rubric Evaluation]
    Eval --> LogPerf[Log Quiz/Assessment Performance Event]
    LogPerf --> Mastery[Mastery Engine: Exponential Moving Average update]
    Mastery --> Classify[Classify Concept: Mastered / Stable / Needs Attention]
    Classify --> Growth[Growth Service: Calculate velocity & progress delta]
    Growth --> Recs[Recommendation Service: Prioritize weak concepts & mistakes]
    Recs --> NextStep([Contextual Next Step: 'What Should I Do Next?'])
```

### 3.4 Activity Tracking & Analytics Aggregation

```mermaid
flowchart LR
    subgraph Events["Activity Tracking"]
        E1[SPACE_CREATED]
        E2[MATERIAL_PROCESSED]
        E3[TUTOR_QUESTION]
        E4[QUIZ_COMPLETED]
        E5[ASSESSMENT_COMPLETED]
    end

    Events --> Svc[ActivityService.log_activity]
    Svc --> Audit[(ActivityEvent Table)]

    Audit --> ProjAnalytics[Project Analytics Service]
    Audit --> GlobalAnalytics[Global User Analytics Service]
    Audit --> AdminAnalytics[Admin Platform Dashboard]

    ProjAnalytics --> PView[Project Progress, AI metrics, Event timeline]
    GlobalAnalytics --> GView[Total spaces, Quizzes, Cross-project mastery]
    AdminAnalytics --> AView[Platform KPIs, System health, AI token usage]
```

---

## 4. Security & Data Isolation Architecture

1. **Authentication (JWT & Bcrypt)**:
   - Password hashing uses salted `bcrypt` with work factor 12.
   - Stateless signed JWT access tokens containing user ID, email, and role claims.
   - Configurable expiration (default 24 hours).
2. **Multi-Tenant Ownership Isolation**:
   - Every database query for Spaces, Projects, Materials, Conversations, Quizzes, Assessments, Mastery, Growth, and Recommendations enforces `user_id == current_user.id`.
   - Access to another user's resource strictly returns `404 Not Found`, preventing resource enumeration or IDOR (Insecure Direct Object Reference) vulnerabilities.
3. **Role-Based Access Control (RBAC)**:
   - Dedicated `ADMIN` role.
   - Admin router endpoints (`/admin/*`) are protected by `get_current_admin_user` dependency.
   - Non-admin authenticated users receive `403 Forbidden` with a clean error payload.
4. **Input Validation & Sanitization**:
   - Pydantic v2 schemas enforce strict types, bounds, string length constraints, and required fields.
   - File uploads are validated for valid PDF signatures (`%PDF-`), rejecting empty, corrupted, or malicious MIME types.
   - Standardized FastAPI exception handlers ensure that no raw Python tracebacks or internal database exception details leak to the client.

---

## 5. Technology Choices & Rationale

| Component | Selected Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | High-throughput asynchronous performance, automatic OpenAPI documentation, native Pydantic v2 integration, and native `BackgroundTasks` for non-blocking file processing. |
| **ORM & Database** | **SQLAlchemy 2.0 + SQLite / PostgreSQL** | Database portability: seamless local SQLite operation with zero configuration, instantly swappable to PostgreSQL in cloud deployments via `DATABASE_URL`. |
| **PDF Extraction** | **PyMuPDF (`fitz`) / pdfplumber** | Lightning-fast page-by-page text extraction with native layout awareness, page number preservation, and tabular data extraction. |
| **Frontend Framework** | **React 18 + Vite** | Instant Hot Module Replacement (HMR), optimized production tree-shaking, predictable unidirectional component state, and rich declarative routing via React Router v6. |
| **Testing** | **Pytest + Starlette TestClient** | Standardized, blazing-fast unit and integration testing with isolated database sessions, deterministic fixture rollbacks, and reproducible E2E assertion scripts. |
