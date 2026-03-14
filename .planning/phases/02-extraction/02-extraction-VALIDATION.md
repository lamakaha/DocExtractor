# Validation: Phase 2 - Core Extraction

## Phase Goal
Implement a robust, Gemini-powered extraction service that converts multi-modal package contexts into structured "Triplet" data with high spatial accuracy and validated schema adherence.

## Success Criteria

### 1. Gemini 1.5 Pro Integration
- [ ] System successfully initializes the `google-genai` SDK and communicates with the Gemini API.
- [ ] Extraction uses `response_schema` (JSON mode) to ensure structured output.
- [ ] Extraction prompts utilize the document's multi-modal context (images and text).

### 2. Agentic Extraction Logic
- [ ] Classification service correctly identifies document types using cues from `configs/`.
- [ ] Extraction service applies the correct schema based on the classified document type.

### 3. Triplet Data Standard
- [ ] All extracted fields are returned as Pydantic-validated `Triplet` objects.
- [ ] Every triplet contains a `value`, a `confidence` score (0.0-1.0), and a `bbox` [ymin, xmin, ymax, xmax].

### 4. Coordinate Scaling (Visual Grounding)
- [ ] Gemini's normalized [0, 1000] coordinates are accurately scaled to image pixels.
- [ ] Verification script confirms that scaled BBoxes align with the actual content on the document images.

### 5. Extraction Pipeline & Concurrency
- [ ] Pipeline handles PDF-to-image conversion for multi-page documents.
- [ ] Pipeline processes multiple packages concurrently using asynchronous workers.
- [ ] Final extraction results are persisted in the SQLite database and linked to the original package.

## Verification Steps

### Automated Tests
- [ ] `pytest tests/test_scaler.py`: Verify coordinate mapping accuracy.
- [ ] `pytest tests/test_extraction.py`: Verify Pydantic validation and structured output parsing.

### Manual Verification
- [ ] Run `scripts/verify_extraction.py` with a sample bank paydown PDF.
- [ ] Check the CLI output for correctly classified type and extracted values.
- [ ] Inspect the `extractions` table in SQLite to confirm record persistence and scaled BBox values.
