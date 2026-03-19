# 09-01 Summary: BBox Grounding Hardening

## Outcome
- Tightened the extraction prompt to ask for exact value-only grounding and explicit zero-box fallback when the model cannot localize a field precisely.
- Raised extraction page rendering to a configurable higher-DPI path so the model receives sharper page inputs during extraction.
- Added bbox-audit heuristics to extraction metadata and elevated extraction log severity when suspicious bbox patterns are detected.

## Why This Matters
- Recent paydown testing showed that some models return usable values but poor grounding; this slice improves input quality and gives the logs enough structure to flag suspect boxes without hiding them.
- The extraction prompt now makes the expected grounding behavior much less ambiguous for multimodal models.
- Operators can inspect `bbox_audit` details to see whether duplicate, zeroed, tiny, or oversized boxes were detected on a page.

## Validation
- `python -m pytest tests/test_extraction_pipeline.py tests/test_extraction_service.py tests/test_ui_form.py -q --basetemp=C:\Users\sarka\OneDrive\Papa\DocExtractor\.pytest-lite-09-01`

## Remaining Work
- Grounding quality is improved, but model choice still materially affects bbox quality.
- If poor grounding persists on specific documents, the next step is targeted model comparison or document-specific preprocessing rather than more generic UI debugging.
