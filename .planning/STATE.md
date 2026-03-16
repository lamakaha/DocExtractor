# State: DocExtractor

## Project Reference
- **Core Value**: High-integrity intake for bank documents bridging unstructured archives (EML/ZIP) to structured accounting data.
- **Current Focus**: Phase 7 planning for observability and package-context-aware classification.
- **Active Phase**: 7 (In Progress)

## Current Position
- **Phase**: 7 - Observability & Context
- **Plan**: 07-02 Observability Reporting and Failure Diagnostics (Completed)
- **Status**: In Progress
- **Progress**: [|||||-----] 50%

## Performance Metrics
- **Completion**: 6/7 Phases
- **Uptime**: N/A
- **Errors**: 0

## Accumulated Context
### Decisions
- **Stack**: Python, Gemini 1.5 Pro, Streamlit, DuckDB/SQLite.
- **Architecture**: In-memory recursive unpacking for performance.
- **Coordinate System**: Normalized 0-1000 scale remains the durable source of truth; UI scaling should happen at render time.
- **Git Automation**: Automatically commit and push to `origin` after each successful phase.
- **Structured Output**: Used Gemini's `response_schema` with Pydantic for high-fidelity extraction.
- **HITL UI**: Streamlit-based side-by-side reviewer with dynamic form and visual grounding.
- **Analytical Layer**: DuckDB views for high-performance JSON "shredding" without data duplication.
- **Export Engine**: `xlsxwriter` for professional multi-tab Excel reporting.
- **UI-Validation**: Using the built-in Playwright Server/BrowserMCP pointing to `http://localhost:8501`.
- **Pipeline Refresh**: Normalize supported source files to a canonical PDF before extraction and review.

### Todos
- [x] Initialize repository structure.
- [x] Phase 1: Ingestion Engine (Recursive unpacking)
- [x] Phase 2: Core Extraction (Gemini integration)
- [x] Phase 3: HITL UI (Streamlit Dashboard)
- [x] Phase 4: Persistence & Export (DuckDB & Excel)
- [x] Phase 5: UI-Validation (Playwright End-to-End Tests)
- [x] Phase 6: Pipeline Refresh (Canonical PDF foundation)
- [x] Runtime durability (queueing, idempotent enqueue, bounded retries)
- [x] Multi-page reconciliation
- [x] Config-driven analytical shredding
- [x] Observability metadata capture
- [x] Package-context-aware classification

### Blockers
- None.

## Session Continuity
- **Last Action**: Implemented 07-02 by surfacing structured log metadata and queue failure diagnostics in dashboard-facing helpers and views.
- **Next Step**: Define the next Phase 7 slice for aggregate observability reporting or stronger package-context selection.
