# Research Summary: DocExtractor

**Project:** DocExtractor
**Researched:** 2025-03-24

## Executive Summary

DocExtractor is a professional-grade document extraction tool designed to handle complex, nested ingestion formats (EML, ZIP, PDF) and produce high-fidelity structured data using **Gemini 1.5 Pro**. The core value proposition lies in its "Native Multi-modal" approach, which bypasses traditional OCR-first pipelines to preserve spatial context, and its "Human-in-the-Loop" (HITL) review dashboard built with **Streamlit**.

The recommended technical path utilizes a **Hybrid Storage Pattern**: **SQLite** serves as the transactional source of truth for raw documents and extraction "triplets" (Value, Confidence, Bounding Box), while **DuckDB** is used to "shred" JSON triplets into analytical tables for near-instant querying and Excel export. To mitigate common pitfalls like LLM hallucinations and coordinate shifting, the system enforces a strict normalization of bounding boxes (0-1000 scale) and utilizes `temperature=0` with structured Pydantic validation.

## Key Findings

### 1. Ingestion & Recursive Unpacking
- **Strategy:** Use `mail-parser` for EML and the standard `zipfile` library for archives.
- **Pattern:** Implement **In-Memory Recursive Unpacking** using `io.BytesIO` to avoid unnecessary disk I/O, but include a `max_depth` (e.g., 5 levels) and `max_size` limit to prevent "Zip Bomb" attacks.
- **Dependency:** Ingestor → Metadata stored in SQLite.

### 2. Gemini 1.5 Pro & Visual Grounding
- **Mechanism:** Leverage Gemini's native vision capabilities. Instead of passing OCR text, pass the full image/PDF page.
- **Output:** Extract "Triplet Objects" consisting of `Value`, `Confidence`, and `Bounding Box` (normalized to `[ymin, xmin, ymax, xmax]` on a 1000x1000 grid).
- **Prompting:** Use `temperature=0` and structured JSON mode (or Pydantic) to ensure schema adherence and minimize hallucinations.

### 3. Streamlit Dashboard (HITL)
- **Design:** A side-by-side layout using `streamlit-drawable-canvas` to render the original document with highlighted bounding boxes.
- **Critical Note:** A scaling utility is required to map Gemini's 0-1000 coordinates to the actual pixel dimensions of the image displayed in the browser.
- **State Management:** Use `st.cache_data` for heavy images and SQLite WAL mode to prevent lock contention between the background extractor and the UI.

### 4. Hybrid Storage & Analytics
- **SQLite:** Handles transactional writes, raw file blobs (for small files), and the `extractions` table.
- **DuckDB:** Uses its `sqlite` extension to `ATTACH` the SQLite database. It performs high-speed "shredding" of the `bbox_json` and `field_value` columns into structured columnar formats.
- **Rationale:** SQLite provides robustness and local simplicity; DuckDB provides the analytical power needed for large-scale reporting.

### 5. Multi-tab Excel Export
- **Tool:** `xlsxwriter` is preferred over `openpyxl` for its performance in creating large, multi-tab files.
- **Sanitization:** Tab names must be limited to 31 characters and stripped of special characters (e.g., `[]:*?/`).

---

## Implications for Roadmap

### Suggested Phase Structure

1. **Phase 1: Ingestion Engine**
   - **Rationale:** Foundation for all other tasks. Must handle messy EML/ZIP structures before extraction can begin.
   - **Delivers:** Recursive unpacker, SQLite schema, file metadata storage.
   - **Pitfall Avoidance:** Implement "Zip Slip" protection (using `os.path.basename`) immediately.

2. **Phase 2: Core Extraction (Gemini)**
   - **Rationale:** The most complex logic. Requires prompt engineering for visual grounding.
   - **Delivers:** Extraction service, Pydantic validation, Triplet JSON generation.
   - **Research Flag:** Needs `/gsd:research-phase` for prompt optimization and coordinate scaling logic.

3. **Phase 3: HITL Reviewer (Streamlit)**
   - **Rationale:** Connects the AI output to human validation.
   - **Delivers:** Side-by-side dashboard, Bounding Box rendering, "Mark as Reviewed" workflow.
   - **Research Flag:** Standard patterns exist for Streamlit, but "Canvas Scaling" needs careful implementation.

4. **Phase 4: Analytics & Export**
   - **Rationale:** Aggregates reviewed data for business use.
   - **Delivers:** DuckDB views, Excel reporting service.
   - **Pitfall Avoidance:** Handle "Excel Sheet Name" limits during tab generation.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python/Gemini/Streamlit/DuckDB is a proven, modern stack for this domain. |
| Features | HIGH | Clear alignment between user needs (Excel, Review) and technology capabilities. |
| Architecture | MEDIUM | Hybrid storage is powerful but adds minor complexity to the data sync. |
| Pitfalls | HIGH | Critical issues (Scaling, Zip Slip, Hallucinations) are well-identified. |

### Gaps to Address
- **Large File Handling:** If ZIPs/PDFs exceed 1GB or 1000 pages, the current "In-Memory" and "Single Prompt" strategies will need to pivot to streaming and chunking.
- **Coordinate Precision:** Gemini's 0-1000 grid may be coarse for tiny text; validation against real-world complex forms is needed.

## Sources
- [Gemini API Vision Grounding Guide](https://ai.google.dev/gemini-api/docs/vision)
- [DuckDB SQLite Integration](https://duckdb.org/docs/extensions/sqlite)
- [Snyk: Zip Slip Vulnerability Research](https://snyk.io/research/zip-slip-vulnerability)
- [Streamlit Drawable Canvas Docs](https://github.com/andfanilo/streamlit-drawable-canvas)
