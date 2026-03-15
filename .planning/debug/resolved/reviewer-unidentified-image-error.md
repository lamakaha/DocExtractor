---
status: resolved
trigger: "UnidentifiedImageError when trying to open a document image in the reviewer."
created: 2026-03-14T22:00:00Z
updated: 2026-03-14T22:15:00Z
---

## Current Focus

Resolved.

## Symptoms

expected: The reviewer should successfully load and display the document image from the database.
actual: PIL raises `UnidentifiedImageError: cannot identify image file` when calling `Image.open(io.BytesIO(image_file.content))`.
errors: UnidentifiedImageError: cannot identify image file <_io.BytesIO object at ...> at src/ui/reviewer.py:110.
reproduction: Click "Review" on a package in the Dashboard.
started: Triggered when reviewing certain (or all) packages.

## Eliminated

## Evidence

- Checked the database files using a script. There are 39 files, many are `application/pdf`. None are `image/jpeg` or `image/png`.
- In `src/ui/reviewer.py`, `image_file` can point to a PDF file if `current_extraction.file_id` matches a PDF file.
- `Image.open(io.BytesIO(image_file.content))` will throw `UnidentifiedImageError` on PDFs.

## Resolution

root_cause: The reviewer was attempting to open PDF files using PIL's `Image.open()`, which does not support the PDF format natively.
fix: Updated `src/ui/reviewer.py` to check the file's mime type. If it's a PDF, `pdf2image` is used to convert the specific page to a PIL Image before rendering.
verification: Manual verification of code change and ensuring `pdf2image` is in requirements.
files_changed: [src/ui/reviewer.py]
