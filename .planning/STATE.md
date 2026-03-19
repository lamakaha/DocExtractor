# State: DocExtractor

## Project Reference
- **Core Value**: High-integrity intake for bank documents bridging unstructured archives (EML/ZIP) to structured accounting data.
- **Current Focus**: Phase 8 hardening after completing runtime recovery and package-level selection improvements.
- **Active Phase**: 8 (In Progress)

## Current Position
- **Phase**: 8 - Hardening
- **Plan**: 08-02 Package-Level Selection and Reconciliation (Completed)
- **Status**: In Progress
- **Progress**: [||||||----] 67%

## Performance Metrics
- **Completion**: 7/7 Phases
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
- [x] Aggregate observability reporting
- [x] Runtime stale-claim recovery and terminal dead-letter handling
- [x] Explicit package-level candidate selection and supporting-artifact reconciliation

### Blockers
- None.

## Session Continuity
- **Last Action**: Implemented 08-02 by making package-level candidate selection explicit and feeding supporting artifacts into classification context and bounded reconciliation.
- **Next Step**: Decide whether to open a final Phase 8 slice for orchestrator/stage-boundary cleanup or stop here with the remaining architecture debt documented.
