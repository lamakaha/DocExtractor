# Architecture Patterns

**Domain:** Document Extraction & Processing
**Researched:** 2025-03-24

## Recommended Architecture

DocExtractor follows a **Pipeline Architecture** with a **Hybrid Storage Pattern** centered on a
**Canonical PDF Review Contract**.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Ingestor** | Recursive unpacking of EML/ZIP and persistence of raw package files. | Canonicalizer, SQLite |
| **Job Orchestrator** | Persists extraction jobs, claims queued work, and manages retry state between ingestion and extraction. | Ingestor, Extractor, SQLite |
| **Canonicalizer** | Convert supported source files into a canonical PDF used for extraction and review. | Ingestor, Extractor, SQLite |
| **Extractor** | Gemini API calls over canonical PDF pages; Triplet generation (Value, Conf, Bbox). | Canonicalizer, SQLite |
| **Reviewer (UI)** | Side-by-side HITL dashboard over canonical PDF pages. | SQLite, Extractor (for re-runs) |
| **Storage Engine** | Managing SQLite (Raw) and DuckDB (Analytical). | Extractor, Reviewer, Exporter |
| **Exporter** | Multi-tab Excel generation. | Storage Engine |

### Data Flow

1. `Raw File` → **Ingestor** → `Extracted Files` + `Metadata` stored in **SQLite**.
2. **Job Orchestrator** creates an `ExtractionJob` handoff in **SQLite** for the package.
3. `Primary Source File` → **Canonicalizer** → `Canonical PDF` stored in **SQLite**.
4. `Canonical PDF` → **Extractor** → `JSON Triplets` stored in **SQLite** with normalized boxes.
5. **Reviewer** reads `JSON Triplets` + `Canonical PDF` → `Human Corrections` stored in **SQLite**.
6. **DuckDB** `ATTACH`es SQLite → `Shreds JSON` → `Structured Tables`.
7. **Exporter** queries **DuckDB** → `Multi-tab Excel`.

## Patterns to Follow

### Pattern 1: Recursive In-Memory Unpacking
Avoid writing temporary files to disk for nested archives.
```python
def extract_recursive(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.endswith('.zip'):
                extract_recursive(z.read(name)) # Recurse
            else:
                process(z.read(name))
```

### Pattern 2: Canonical PDF First
Convert supported source files into a canonical PDF before extraction and review.
This preserves a single viewer contract for the UI while keeping extraction vision-first.

### Pattern 3: Visual Grounding (Gemini)
Request bounding boxes in prompts to enable visual proof in the UI.
Persist **normalized** coordinates in `[ymin, xmin, ymax, xmax]` on a `0-1000` scale.

### Pattern 4: The "Triplet" Schema
```sql
-- SQLite Table
CREATE TABLE extractions (
    doc_id TEXT,
    field_name TEXT,
    field_value TEXT,
    confidence REAL,
    bbox_json TEXT, -- [ymin, xmin, ymax, xmax]
    is_reviewed BOOLEAN DEFAULT 0
);
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: OCR-First Text Passing
**What:** Running Tesseract/OCR and passing only the text to Gemini.
**Why bad:** Loses spatial context (layout, tables, font weight) which Gemini can use for better accuracy.
**Instead:** Pass the document directly as an image/PDF to Gemini's multi-modal endpoint.

### Anti-Pattern 2: Mixed Reviewer Contracts
**What:** Letting some packages review against images, others against raw text, and others against PDFs.
**Why bad:** Forces the UI and provenance model to branch by file type.
**Instead:** Normalize to a canonical PDF and use page + bbox as the review contract.

## Scalability Considerations

| Concern | At 100 docs | At 10K docs | At 1M docs |
|---------|--------------|--------------|-------------|
| Extraction Latency | Sequential calls. | Use `asyncio` or Threading. | Distributed workers (Celery). |
| Query Speed | Simple SQLite SELECT. | DuckDB Columnar Scan. | DuckDB Parquet partitioning. |
| RAM Usage | In-memory extraction ok. | Switch to `tempfile` for ZIPs/PDF conversion. | Streaming extraction. |
| Runtime Durability | SQLite-backed job handoff ok. | Add stronger queue leasing and dead-letter handling. | Distributed workers with leases. |

## Sources

- [DuckDB + SQLite Pattern](https://duckdb.org/2022/11/08/sqlite-extension.html)
- [Gemini Vision Prompting Guide](https://ai.google.dev/gemini-api/docs/vision)
