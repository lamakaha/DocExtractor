# Feature Landscape

**Domain:** Document Extraction (DocExtractor)
**Researched:** 2025-03-24

## Table Stakes

Features users expect in a professional document extraction tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-format Ingestion | Users have EML, ZIP, PDF, and PNGs. | Medium | Requires recursive unpacking. |
| Layout Preservation | Extraction must respect visual structure. | High | Gemini native vision handles this. |
| Export to Excel | Standard for business workflows. | Low | Multi-tab support via `xlsxwriter`. |
| Confidence Scores | Needed to flag "uncertain" extractions. | Low | Part of the "Triplet" standard. |

## Differentiators

Features that set DocExtractor apart.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Recursive ZIP Extraction | No need for users to manually unzip. | Medium | Implemented via `zipfile` recursion. |
| Side-by-Side Review | Direct visual proof of extraction. | High | Streamlit + Canvas implementation. |
| Native Multi-modal | Better accuracy on complex tables/charts. | Medium | Avoids OCR text loss. |
| DuckDB Analytics | Near-instant querying of millions of fields. | Medium | Using DuckDB JSON shredding. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Manual OCR Engine | High maintenance, lower accuracy than LLMs. | Use Gemini's native vision. |
| Heavy Web UI | Unnecessary for internal tool. | Use Streamlit for rapid iteration. |
| Cloud Database | Complex setup and latency for local files. | Use SQLite/DuckDB for local performance. |

## Feature Dependencies

```
Recursive Unpacker → Gemini Extractor (Needs Files)
Gemini Extractor → Triplet Schema (Defines Output)
Triplet Schema → HITL Dashboard (Needs Bounding Boxes)
Triplet Schema → SQLite/DuckDB (Needs Structured Data)
SQLite/DuckDB → Excel Export (Needs Final Data)
```

## MVP Recommendation

Prioritize:
1. **Recursive Unpacker:** Handle EML/ZIP to provide raw files.
2. **Gemini Extractor:** Extract key fields with bounding boxes and confidence.
3. **Streamlit Basic Dashboard:** View extracted text next to the image.

Defer:
- **Interactive Bounding Box Editing:** Start with "Read-only" view first.
- **Advanced DuckDB Analytics:** Focus on extraction accuracy first.

## Sources

- [Gemini Multi-modal Best Practices](https://ai.google.dev/gemini-api/docs/document-processing)
- [Streamlit Component Gallery](https://streamlit.io/components)
