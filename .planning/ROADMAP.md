# Roadmap: DocExtractor

## Status
- **Current Phase**: Phase 2: Core Extraction
- **Progress**: 25%
- **Last Updated**: 2026-03-13

## Phases
- [x] **Phase 1: Ingestion Engine** - Recursive unpacking of EML/ZIP into standardized "Package" contexts.
- [ ] **Phase 2: Core Extraction** - Gemini 1.5 Pro integration for classification and Triplet-based extraction with Pydantic validation.
- [ ] **Phase 3: HITL UI** - Streamlit dashboard for side-by-side review, visual grounding, and manual correction.
- [ ] **Phase 4: Persistence & Export** - Hybrid SQLite/DuckDB storage and multi-tab Excel reporting via xlsxwriter.

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
**Requirements**: REQ-EXT-01, REQ-EXT-02, REQ-EXT-03, REQ-EXT-04, REQ-EXT-05
**Success Criteria**:
  1. System correctly identifies document type (Classification) before attempting extraction.
  2. Extraction returns "Triplet Objects" (Value, Confidence, BBox) for every field.
  3. Gemini's 0-1000 coordinates are successfully scaled to actual image pixel dimensions.
  4. Extracted data passes Pydantic validation against the `extraction_schema`.
**Plans**: TBD

### Phase 3: HITL UI
**Goal**: Provide a professional review interface to ensure 100% data integrity.
**Depends on**: Phase 2
**Requirements**: REQ-UI-01, REQ-UI-02, REQ-UI-03, REQ-UI-04, REQ-UI-05
**Success Criteria**:
  1. Dashboard displays real-time status of packages (`INGESTED`, `EXTRACTED`, `APPROVED`).
  2. Reviewers can see the original document and extracted fields in a side-by-side layout.
  3. Clicking a field draws a high-contrast bounding box on the source document image.
  4. Fields are color-coded (Red/Yellow/Green) based on extraction confidence.
**Plans**: TBD

### Phase 4: Persistence & Export
**Goal**: Bridge the gap between transactional AI output and structured business reporting.
**Depends on**: Phase 3
**Requirements**: REQ-DAT-01, REQ-DAT-02, REQ-EXP-01, REQ-EXP-02
**Success Criteria**:
  1. Approved extraction data is persisted in SQLite with DuckDB views for "shredded" field access.
  2. System generates multi-tab Excel files (Summary vs. Transactions) using `xlsxwriter`.
  3. Exported files are valid, sanitized (handling sheet name limits), and ready for accounting import.
**Plans**: TBD

---

## Progress Table
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ingestion Engine | 3/3 | Completed | 2026-03-13 |
| 2. Core Extraction | 0/0 | Not started | - |
| 3. HITL UI | 0/0 | Not started | - |
| 4. Persistence & Export | 0/0 | Not started | - |
