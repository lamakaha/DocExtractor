# Roadmap: DocExtractor

## Status
- **Current Phase**: None active
- **Progress**: 9 phases complete; current planned roadmap delivered
- **Last Updated**: 2026-03-19

## Phases
- [x] **Phase 1: Ingestion Engine** - Recursive unpacking of EML/ZIP into standardized "Package" contexts.
- [x] **Phase 2: Core Extraction** - Gemini 1.5 Pro integration for classification and Triplet-based extraction with Pydantic validation.
- [x] **Phase 3: HITL UI** - Streamlit dashboard for side-by-side review, visual grounding, and manual correction.
- [x] **Phase 4: Persistence & Export** - Hybrid SQLite/DuckDB storage and multi-tab Excel reporting via xlsxwriter.
- [x] **Phase 5: UI-Validation** - Automated E2E testing using Playwright to interact with Streamlit UI (http://localhost:8501) and verify "Reviewer" and "Export" features.
- [x] **Phase 6: Pipeline Refresh** - Canonical PDF normalization, normalized bbox persistence, and staged durability improvements for the extraction pipeline.
- [x] **Phase 7: Observability & Context** - Structured runtime metadata, richer package-context classification, and improved debugging/operational traceability.
- [x] **Phase 8: Hardening** - Runtime recovery semantics, stronger package-level decision rules, and reviewer/debugging hardening for bbox auditability.
- [x] **Phase 9: Grounding Quality** - Prompt, rendering, and audit improvements for better bbox localization quality.

---

## Phase Details

### Phase 1: Ingestion Engine
**Goal**: Transform messy input archives into a clean, searchable "Package" structure.
**Depends on**: Nothing
**Requirements**: REQ-ING-01, REQ-ING-02, REQ-ING-03, REQ-ING-04
**Success Criteria**:
  1. User can upload a `.eml` containing a nested `.zip` and see all files extracted.
  2. System extracts and stores plain text from email bodies for LLM context.
  3. All extracted files are correctly grouped under a single "Package ID" in storage.
**Plans**: 3 plans
- [x] 01-01-PLAN.md — Project Foundation & Data Model
- [x] 01-02-PLAN.md — Core Ingestion Logic (TDD)
- [x] 01-03-PLAN.md — Resilience & Verification

### Phase 2: Core Extraction
**Goal**: Leverage Gemini 1.5 Pro to produce high-fidelity, visually grounded structured data.
**Depends on**: Phase 1
**Requirements**: REQ-EXT-01, REQ-EXT-02, REQ-EXT-03, REQ-EXT-04, REQ-EXT-05, REQ-NFR-03
**Success Criteria**:
  1. System correctly identifies document type (Classification) before attempting extraction.
  2. Extraction returns "Triplet Objects" (Value, Confidence, BBox) for every field.
  3. Gemini's normalized `0-1000` coordinates remain the persisted source of truth and are scaled only at render time.
  4. Extracted data passes Pydantic validation against the `extraction_schema`.
  5. System supports concurrent processing of multiple extraction jobs.
**Plans**: 3 plans
- [x] 02-01-PLAN.md — Extraction Foundation & Scaling
- [x] 02-02-PLAN.md — Classification & Extraction Services
- [x] 02-03-PLAN.md — Extraction Pipeline & Concurrency

### Phase 3: HITL UI
**Goal**: Provide a professional review interface to ensure 100% data integrity.
**Depends on**: Phase 2
**Requirements**: REQ-UI-01, REQ-UI-02, REQ-UI-03, REQ-UI-04, REQ-UI-05
**Success Criteria**:
  1. Dashboard displays real-time status of packages (`INGESTED`, `EXTRACTED`, `APPROVED`).
  2. Reviewers can see the original document and extracted fields in a side-by-side layout.
  3. Clicking a field draws a high-contrast bounding box on the source document image.
  4. Fields are color-coded (Red/Yellow/Green) based on extraction confidence.
**Plans**: 3 plans
- [x] 03-01-PLAN.md — Dashboard & Layout
- [x] 03-02-PLAN.md — Reviewer Layout & Rendering
- [x] 03-03-PLAN.md — Dynamic Form & Approval

### Phase 4: Persistence & Export
**Goal**: Bridge the gap between transactional AI output and structured business reporting.
**Depends on**: Phase 3
**Requirements**: REQ-DAT-01, REQ-DAT-02, REQ-EXP-01, REQ-EXP-02
**Success Criteria**:
  1. Approved extraction data is persisted in SQLite with DuckDB views for "shredded" field access.
  2. System generates multi-tab Excel files (Summary vs. Transactions) using `xlsxwriter`.
  3. Exported files are valid, sanitized (handling sheet name limits), and ready for accounting import.
**Plans**: 3 plans
- [x] 04-01-PLAN.md — DuckDB Analytical Layer
- [x] 04-02-PLAN.md — Excel Export Service
- [x] 04-03-PLAN.md — UI Integration & Resilience

### Phase 5: UI-Validation
**Goal**: Automated End-to-End Testing of the Streamlit UI to catch JS errors and regressions.
**Depends on**: Phase 4
**Requirements**: REQ-UI-01, REQ-UI-02
**Success Criteria**:
  1. Playwright tests navigate to `http://localhost:8501`.
  2. Tests interact with the "Reviewer" and "Export" features automatically.
  3. Validates no JavaScript errors or Streamlit exception dialogs appear during operation.
**Plans**: 3 plans
- [x] 05-01-PLAN.md — Setup E2E Testing Infrastructure (Playwright)
- [x] 05-02-PLAN.md — Validate Dashboard & Export Features
- [x] 05-03-PLAN.md — Validate Reviewer Interface

### Phase 6: Pipeline Refresh
**Goal**: Re-center the pipeline around a canonical PDF review contract while addressing the highest-value architecture gaps from the first review.
**Depends on**: Phase 5
**Requirements**: REQ-EXT-01, REQ-EXT-03, REQ-EXT-05, REQ-UI-02, REQ-UI-03, REQ-NFR-03
**Success Criteria**:
  1. Supported source files are normalized to a canonical PDF before extraction/review.
  2. Extractions reference canonical PDFs and persist normalized bbox coordinates.
  3. The reviewer remains page + bbox based with one consistent contract.
  4. Follow-on plans are defined for runtime durability, reconciliation, and analytics generalization.
**Plans**: 4 completed plans
- [x] 06-01-PLAN.md — Canonical PDF Foundation
- [x] 06-02-PLAN.md — Durable Extraction Job Handoff
- [x] 06-03-PLAN.md — Multi-Page Reconciliation
- [x] 06-04-PLAN.md — Config-Driven Analytical Shredding

### Phase 7: Observability & Context
**Goal**: Reduce first-page classification bias and make pipeline execution metadata queryable and operationally useful.
**Depends on**: Phase 6
**Requirements**: REQ-EXT-01, REQ-EXT-02, REQ-NFR-03, REQ-NFR-04
**Success Criteria**:
  1. Classification can use bounded package context instead of only the first page.
  2. Pipeline logs or metadata capture model/version/prompt/schema/latency details in a structured form.
  3. Retry and failure causes are easier to diagnose than the current free-text-only flow.
**Plans**: 3 completed plans
- [x] 07-01-PLAN.md — Observability and Package Context
- [x] 07-02-PLAN.md — Observability Reporting and Failure Diagnostics
- [x] 07-03-PLAN.md — Observability Analytics and Trend Reporting

### Post-Phase Note
Phase 8 is now open for the remaining architectural hardening work that was intentionally deferred after the Phase 1-7 delivery path.

### Phase 8: Hardening
**Goal**: Close the highest-value remaining architecture gaps in runtime recovery behavior and package-level decision semantics without reopening already-sufficient observability or deferred redaction policy work.
**Depends on**: Phase 7
**Requirements**: REQ-NFR-01, REQ-NFR-03, REQ-DAT-01
**Success Criteria**:
  1. Extraction jobs recover cleanly from stale claims or worker interruption.
  2. Retry exhaustion results in explicit terminal queue states rather than ambiguous failures.
  3. Package-level candidate selection and supporting-artifact handling are explicit and reproducible.
  4. Follow-on plans are defined for orchestrator/stage-boundary cleanup if still justified after hardening.
**Plans**: 3 completed plans
- [x] 08-01-PLAN.md — Runtime Hardening
- [x] 08-02-PLAN.md — Package-Level Selection and Reconciliation
- [x] 08-03-PLAN.md — Reviewer BBox Debugging and Raw Response Audit

### Phase 9: Grounding Quality
**Goal**: Improve bbox localization quality without changing the canonical-PDF review contract by tightening prompt guidance, increasing extraction render quality, and adding grounding audits.
**Depends on**: Phase 8
**Requirements**: REQ-EXT-03, REQ-EXT-05, REQ-NFR-01, REQ-UI-03
**Success Criteria**:
  1. Extraction prompts explicitly request tight value-only grounding and clear fallback behavior.
  2. Extraction page rendering uses a configurable higher-quality input path.
  3. Extraction audit logs flag suspicious bbox patterns for review.
**Plans**: 1 completed plan
- [x] 09-01-PLAN.md — BBox Grounding Hardening

---

## Progress Table
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ingestion Engine | 3/3 | Completed | 2026-03-13 |
| 2. Core Extraction | 3/3 | Completed | 2026-03-13 |
| 3. HITL UI | 3/3 | Completed | 2026-03-14 |
| 4. Persistence & Export | 3/3 | Completed | 2026-03-14 |
| 5. UI-Validation | 3/3 | Completed | 2026-03-14 |
| 6. Pipeline Refresh | 4/4 | Completed | 2026-03-16 |
| 7. Observability & Context | 3/3 | Completed | 2026-03-16 |
| 8. Hardening | 3/3 | Completed | 2026-03-19 |
| 9. Grounding Quality | 1/1 | Completed | 2026-03-19 |
