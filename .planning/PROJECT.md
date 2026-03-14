# Project: DocExtractor

## Vision
A high-integrity intake system for bank loan documents that bridges the gap between unstructured communication (Email/PDF/Zip) and structured accounting data.

## Core Pillars

### 1. Container Ingestion
- **Package Rule:** Treat every input (Email with attachments or a ZIP file) as a single document package.
- **Recursive Unpacking:** Use standard Python libraries (`zipfile`, `mail-parser`) to extract all text from email bodies and all images/pages from attachments.
- **Context Merging:** Combine email body text and PDF pages into a single vision/text context for Gemini.

### 2. Two-Step Agentic Logic
- **Classification:** Read the "Package" and match it against `classification_cues` in `/configs/`.
- **Extraction:** Use associated `extraction_schema` to pull data once document type is known (e.g., "Bank Paydown").

### 3. Triplet Extraction Standard
Every extracted field must be returned as a Triplet Object:
- **Value:** Normalized data (e.g., 15000.00).
- **Confidence:** A 0.0–1.0 score.
- **Bounding Box:** `[ymin, xmin, ymax, xmax]` coordinates on the source document image.

### 4. Human-in-the-Loop UI (Streamlit)
- **Dashboard:** Status board (INGESTED, EXTRACTED, APPROVED).
- **Review Interface:** Side-by-side view (Original PDF/Email image vs. Extracted form).
- **Color Schema:**
  - Red (<0.70): Critical focus required.
  - Yellow (0.70-0.95): Needs verification.
  - Green (>0.95): Likely correct.
- **Interaction:** Clicking a field draws the bounding box on the document image.

### 5. Persistence & Export
- **Database:** DuckDB or SQLite storing the full JSON triplet.
- **Excel Service:** Multi-tab Excel file via `openpyxl` or `xlsxwriter`.
  - Tab 1: Summary (Date, Lender, Total).
  - Tab 2: Transactions (Itemized list from transactions JSON).

## Technical Stack
- **Languages:** Python
- **AI/LLM:** Gemini (Vision/Text)
- **UI:** Streamlit
- **Database:** DuckDB / SQLite
- **Libraries:** `zipfile`, `mail-parser`, `openpyxl`, `xlsxwriter`
