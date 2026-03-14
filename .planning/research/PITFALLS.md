# Domain Pitfalls

**Domain:** Document Extraction & Processing
**Researched:** 2025-03-24

## Critical Pitfalls

### Pitfall 1: Coordinate Scaling Mismatch
**What goes wrong:** Bounding boxes from Gemini (0-1000) don't line up with the image in Streamlit (pixels).
**Why it happens:** Gemini uses a normalized 1000x1000 grid regardless of aspect ratio.
**Consequences:** Highlights appear shifted or stretched in the dashboard.
**Prevention:** Implement a scaling utility that converts `(val / 1000) * img_width/height`.
**Detection:** Draw a test box at [0, 0, 500, 500] and ensure it covers exactly the top-left quadrant.

### Pitfall 2: Zip Slip & Zip Bomb
**What goes wrong:** A malicious ZIP file contains `../../etc/passwd` or expands to petabytes.
**Why it happens:** Blindly trusting ZIP file headers and contents.
**Consequences:** Security breach or system crash (OOM).
**Prevention:** Use `os.path.basename` on extracted names and limit total extraction size/depth.

### Pitfall 3: Multi-modal Hallucination
**What goes wrong:** Gemini "invents" a value that isn't in the document.
**Why it happens:** High temperature or lack of grounding.
**Prevention:** Use `temperature=0`, structured output (JSON mode), and require bounding boxes for every field.

## Moderate Pitfalls

### Pitfall 1: SQLite Lock Contention
**What goes wrong:** Writing extraction results while the Streamlit dashboard is reading causes "Database is locked".
**Why it happens:** SQLite's default locking in multi-threaded environments.
**Prevention:** Enable WAL (Write-Ahead Logging) mode: `PRAGMA journal_mode=WAL;`.

### Pitfall 2: PDF Page Limits
**What goes wrong:** Gemini fails on a 1001-page PDF.
**Why it happens:** Hard limit of 1000 pages for the Gemini 1.5 model.
**Prevention:** Split large PDFs into 100-page chunks before processing.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Ingestion | Nested ZIP loops | Set a `max_depth` (e.g., 5 levels). |
| Extraction | JSON schema errors | Use Pydantic to validate Gemini's output. |
| Dashboard | Heavy image reloading | Use `st.cache_data` for document images. |
| Export | Excel "Sheet Name" limits | Sanitize tab names to 31 chars and no special chars. |

## Sources

- [Snyk: Zip Slip Vulnerability](https://snyk.io/research/zip-slip-vulnerability)
- [Streamlit Performance Tips](https://docs.streamlit.io/library/advanced-features/caching)
- [Gemini API Reliability](https://ai.google.dev/gemini-api/docs/reliability)
