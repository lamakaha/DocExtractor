# Architecture Patterns

**Domain:** Document Extraction & Processing
**Researched:** 2025-03-24

## Recommended Architecture

DocExtractor follows a **Pipeline Architecture** with a **Hybrid Storage Pattern**.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Ingestor** | Recursive unpacking of EML/ZIP; PDF to Image conversion. | Gemini Extractor, SQLite |
| **Extractor** | Gemini API calls; Triplet generation (Value, Conf, Bbox). | Ingestor, SQLite |
| **Reviewer (UI)** | Side-by-side HITL dashboard; Bbox correction. | SQLite, Extractor (for re-runs) |
| **Storage Engine** | Managing SQLite (Raw) and DuckDB (Analytical). | Extractor, Reviewer, Exporter |
| **Exporter** | Multi-tab Excel generation. | Storage Engine |

### Data Flow

1. `Raw File` → **Ingestor** → `Extracted Files` + `Metadata` stored in **SQLite**.
2. `Extracted File` → **Extractor** → `JSON Triplets` stored in **SQLite**.
3. **Reviewer** reads `JSON Triplets` + `Image` → `Human Corrections` stored in **SQLite**.
4. **DuckDB** `ATTACH`es SQLite → `Shreds JSON` → `Structured Tables`.
5. **Exporter** queries **DuckDB** → `Multi-tab Excel`.

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

### Pattern 2: Visual Grounding (Gemini 1.5)
Request bounding boxes in prompts to enable visual proof in the UI.
**Format:** `[ymin, xmin, ymax, xmax]` normalized to `1000`.

### Pattern 3: The "Triplet" Schema
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

## Scalability Considerations

| Concern | At 100 docs | At 10K docs | At 1M docs |
|---------|--------------|--------------|-------------|
| Extraction Latency | Sequential calls. | Use `asyncio` or Threading. | Distributed workers (Celery). |
| Query Speed | Simple SQLite SELECT. | DuckDB Columnar Scan. | DuckDB Parquet partitioning. |
| RAM Usage | In-memory extraction ok. | Switch to `tempfile` for ZIPs. | Streaming extraction. |

## Sources

- [DuckDB + SQLite Pattern](https://duckdb.org/2022/11/08/sqlite-extension.html)
- [Gemini Vision Prompting Guide](https://ai.google.dev/gemini-api/docs/vision)
