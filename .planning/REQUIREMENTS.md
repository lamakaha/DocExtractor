# Requirements: DocExtractor

## Functional Requirements

### 1. Ingestion Engine (Phase 1)
- **REQ-ING-01: Recursive Unpacking:**
  - Must recursively extract all attachments from `.eml` files.
  - Must recursively extract all files from `.zip` archives.
- **REQ-ING-02: Nested Structure Handling:**
  - Must handle nested structures (e.g., ZIP within Email within ZIP).
- **REQ-ING-03: Email Body Text Extraction:**
  - Must extract plain text from email bodies and store it.
- **REQ-ING-04: Package Context Creation:**
  - Must store extracted files as a "Package" context for downstream processing.

### 2. Core Extraction Service (Phase 2)
- **REQ-EXT-01: Gemini Integration:**
  - Use Gemini 1.5 Pro to process the merged context (Email text + Image/PDF pages).
- **REQ-EXT-02: Two-step Agentic Logic:**
  - Implement logic: Classification (using cues) -> Extraction (using schema).
- **REQ-EXT-03: Triplet Standard:**
  - For every field, return: `Value`, `Confidence`, and `Bounding Box` (`[ymin, xmin, ymax, xmax]`).
- **REQ-EXT-04: Pydantic Validation:**
  - Use Pydantic to validate extracted data against the schema.
- **REQ-EXT-05: Coordinate Scaling:**
  - Scale normalized Gemini coordinates (0-1000) to image-specific pixels.

### 3. Human-in-the-Loop Review UI (Phase 3)
- **REQ-UI-01: Dashboard:**
  - Display a table of packages with status (`INGESTED`, `EXTRACTED`, `APPROVED`).
- **REQ-UI-02: Side-by-side Review Interface:**
  - Side-by-side view: Original document (left) vs. Extracted form (right).
- **REQ-UI-03: Bounding Box Rendering:**
  - Draw bounding boxes on the document image when a field is focused.
- **REQ-UI-04: Color Coding:**
  - Red (<0.70 Confidence), Yellow (0.70-0.95), Green (>0.95).
- **REQ-UI-05: Interaction & Approval:**
  - Allow manual correction of values and confidence scores.
  - Provide an "Approve" button to move the package to `APPROVED` status.

### 4. Persistence & Export (Phase 4)
- **REQ-DAT-01: SQLite Transactional Storage:**
  - SQLite for transactional storage (raw JSON triplets, package metadata).
- **REQ-DAT-02: DuckDB Analytical Layer:**
  - DuckDB for analytical queries and "shredded" field access.
- **REQ-EXP-01: Excel Generation:**
  - Generate a multi-tab Excel file using `xlsxwriter`.
- **REQ-EXP-02: Excel Schema:**
  - Tab 1: Summary (Flat fields); Tab 2: Transactions (Itemized lists).

## Non-Functional Requirements
- **REQ-NFR-01: Reliability:** Handle corrupted ZIPs and malformed EMLs gracefully.
- **REQ-NFR-02: Performance:** Stream processing for large archives (>2GB) if needed.
- **REQ-NFR-03: Scalability:** Support multiple concurrent extraction jobs.
- **REQ-NFR-04: Security:** Ensure no PII is logged; protect API keys.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-ING-01  | Phase 1 | Pending |
| REQ-ING-02  | Phase 1 | Pending |
| REQ-ING-03  | Phase 1 | Pending |
| REQ-ING-04  | Phase 1 | Pending |
| REQ-EXT-01  | Phase 2 | Pending |
| REQ-EXT-02  | Phase 2 | Pending |
| REQ-EXT-03  | Phase 2 | Pending |
| REQ-EXT-04  | Phase 2 | Pending |
| REQ-EXT-05  | Phase 2 | Pending |
| REQ-UI-01   | Phase 3 | Pending |
| REQ-UI-02   | Phase 3 | Pending |
| REQ-UI-03   | Phase 3 | Pending |
| REQ-UI-04   | Phase 3 | Pending |
| REQ-UI-05   | Phase 3 | Pending |
| REQ-DAT-01  | Phase 4 | Pending |
| REQ-DAT-02  | Phase 4 | Pending |
| REQ-EXP-01  | Phase 4 | Pending |
| REQ-EXP-02  | Phase 4 | Pending |
| REQ-NFR-01  | Phase 1 | Pending |
| REQ-NFR-02  | Phase 1 | Pending |
| REQ-NFR-03  | Phase 2 | Pending |
| REQ-NFR-04  | Phase 1 | Pending |

## Technical Stack
- **Languages:** Python 3.10+
- **AI:** Google Gemini 1.5 Pro
- **UI:** Streamlit
- **Database:** SQLite & DuckDB
- **Libraries:** `mail-parser`, `zipfile`, `io.BytesIO`, `pydantic`, `xlsxwriter`, `Pillow`
