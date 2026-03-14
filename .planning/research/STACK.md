# Technology Stack

**Project:** DocExtractor
**Researched:** 2025-03-24

## Recommended Stack

### Core Framework & AI
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.10+ | Core Language | Robust ecosystem for AI and data processing. |
| Gemini 1.5 Pro | Latest | Multi-modal Extraction | Native vision/text support; 1M+ token window. |
| google-generativeai| Latest | API Client | Official SDK for Gemini integration. |

### Data Processing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| mail-parser | 3.15+ | Email Parsing | Handles EML decoding and attachments automatically. |
| zipfile | Stdlib | Archive Extraction | Built-in, reliable support for ZIP files. |
| io / BytesIO | Stdlib | In-memory Streams | Essential for recursive unpacking without disk I/O. |

### Dashboard (HITL)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Streamlit | 1.30+ | Dashboard UI | Rapid development of data apps. |
| streamlit-drawable-canvas | Latest | Bounding Box Drawing | Best-in-class for interactive image annotation. |
| Pillow (PIL) | Latest | Image Handling | Required for canvas background and processing. |

### Storage & Export
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite | Stdlib | Transactional Store | Low-latency storage for raw documents and metadata. |
| DuckDB | 1.0+ | Analytical Store | Fast "shredding" of JSON triplets and aggregation. |
| xlsxwriter | Latest | Excel Export | High performance for large multi-tab reports. |
| Pandas | 2.0+ | Data Wrangling | Industry standard for table manipulation. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Email | `mail-parser` | `email` (stdlib) | `mail-parser` is easier for messy/malformed EMLs. |
| Excel | `xlsxwriter` | `openpyxl` | `xlsxwriter` is faster for *creating* new files. |
| Storage | SQLite + DuckDB | PostgreSQL | Local file-based DBs are easier for this project scope. |

## Installation

```bash
# Core Dependencies
pip install google-generativeai streamlit streamlit-drawable-canvas mail-parser duckdb xlsxwriter pandas pillow

# Optimization
pip install lxml  # Speeds up openpyxl if used for templates
```

## Sources

- [Gemini Documentation](https://ai.google.dev/docs)
- [Streamlit Drawable Canvas](https://github.com/andfanilo/streamlit-drawable-canvas)
- [DuckDB SQLite Integration](https://duckdb.org/docs/extensions/sqlite)
