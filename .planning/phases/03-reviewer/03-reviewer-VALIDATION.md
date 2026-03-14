# Validation: Phase 3 - HITL UI

## Phase Goal
Implement a professional review interface (Streamlit) for human validation and correction of AI-extracted document data, ensuring 100% data integrity before approval.

## Success Criteria

### 1. Dashboard & Selection (REQ-UI-01)
- [ ] Dashboard displays a table of all packages from the SQLite database.
- [ ] Status filtering (INGESTED, EXTRACTED, APPROVED) works correctly.
- [ ] Selecting a package from the dashboard transitions the view to the Reviewer interface.

### 2. Reviewer Layout & Rendering (REQ-UI-02)
- [ ] Side-by-side layout: original document image on the left, extracted form on the right.
- [ ] Document image is rendered using `st_canvas` at the correct aspect ratio.
- [ ] Page navigation works for multi-page documents (if applicable).

### 3. Visual Grounding & Scaling (REQ-UI-03, REQ-EXT-05)
- [ ] Coordinate scaling logic correctly maps pixel-level BBoxes to the canvas display size.
- [ ] Selecting a field in the form highlights the corresponding BBox on the document image.
- [ ] BBox rendering is high-contrast and accurately matches the extracted field's location.

### 4. Dynamic Form & Color Coding (REQ-UI-04)
- [ ] The form dynamically populates based on the document's extraction schema.
- [ ] Fields are color-coded (Red/Yellow/Green) based on extraction confidence scores.
- [ ] Field values are editable by the user.

### 5. Approval Workflow & Persistence (REQ-UI-05)
- [ ] The "Approve" button correctly saves user corrections to the SQLite `extractions` table.
- [ ] The `Package` status is updated to `APPROVED` upon successful review.
- [ ] The user is redirected back to the Dashboard after approving a package.

## Verification Steps

### Automated Tests
- [ ] `pytest tests/test_ui_queries.py`: Verify DB helper functions (fetching, updating).
- [ ] `pytest tests/test_reviewer_logic.py`: Verify layout state and data fetching for the reviewer.
- [ ] `pytest tests/test_scaler.py`: Verify pixel-to-canvas scaling logic (re-verified in UI context).
- [ ] `pytest tests/test_ui_form.py`: Verify dynamic form generation and color coding logic.
- [ ] `pytest tests/test_ui_approval.py`: Verify approval workflow and data persistence.

### Manual Verification
- [ ] Run `streamlit run src/ui/app.py`.
- [ ] Confirm Dashboard loads and filters.
- [ ] Select an "EXTRACTED" package and verify side-by-side rendering.
- [ ] Edit a value, click "Approve", and verify the status change in the dashboard.
