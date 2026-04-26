"""
PDF text and table extraction script — bundled with the pdf-processing skill.

Reads a PDF file and extracts text and tables, outputting structured JSON.
Tries pdfplumber first (better layout), falls back to pypdf.

Input (environment variables):
  PDF_PATH       — absolute path to the PDF file (required)
  OUTPUT_FORMAT  — "json" (default) | "text"
  MAX_PAGES      — integer, max pages to extract (default: all)

Output (stdout): JSON extraction result or plain text
"""

import json
import os
import sys


def main() -> None:
    pdf_path = os.environ.get("PDF_PATH", "")
    output_format = os.environ.get("OUTPUT_FORMAT", "json").lower()
    max_pages_raw = os.environ.get("MAX_PAGES", "")
    max_pages = int(max_pages_raw) if max_pages_raw.isdigit() else None

    if not pdf_path:
        print(json.dumps({
            "error": "PDF_PATH environment variable is required",
            "usage": "PDF_PATH=/path/to/file.pdf python extract.py",
        }, indent=2))
        sys.exit(1)

    try:
        import pdfplumber
        result = _extract_pdfplumber(pdf_path, max_pages)
    except ImportError:
        try:
            import pypdf  # noqa: F401
            result = _extract_pypdf(pdf_path, max_pages)
        except ImportError:
            print(json.dumps({
                "error": "Neither pdfplumber nor pypdf is installed.",
                "fix": "pip install pdfplumber",
            }, indent=2))
            sys.exit(1)
    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    if output_format == "text":
        for page in result["pages"]:
            print(f"\n--- Page {page['page']} ---")
            print(page["text"])
    else:
        print(json.dumps(result, indent=2))


def _extract_pdfplumber(pdf_path: str, max_pages) -> dict:
    import pdfplumber

    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for i, page in enumerate(pages, 1):
            text = page.extract_text(layout=True) or ""
            raw_tables = page.extract_tables() or []
            # Convert tables: replace None with empty string
            tables = [
                [[cell or "" for cell in row] for row in tbl]
                for tbl in raw_tables
            ]
            pages_data.append({
                "page": i,
                "text": text,
                "tables": tables,
                "word_count": len(text.split()),
            })

    return {
        "method": "pdfplumber",
        "total_pages": len(pages_data),
        "total_words": sum(p["word_count"] for p in pages_data),
        "pages": pages_data,
    }


def _extract_pypdf(pdf_path: str, max_pages) -> dict:
    import pypdf

    reader = pypdf.PdfReader(pdf_path)
    pages_to_read = reader.pages[:max_pages] if max_pages else reader.pages

    pages_data = []
    for i, page in enumerate(pages_to_read, 1):
        text = page.extract_text() or ""
        pages_data.append({
            "page": i,
            "text": text,
            "tables": [],  # pypdf doesn't extract tables
            "word_count": len(text.split()),
        })

    return {
        "method": "pypdf",
        "total_pages": len(pages_data),
        "total_words": sum(p["word_count"] for p in pages_data),
        "pages": pages_data,
        "note": "Table extraction requires pdfplumber: pip install pdfplumber",
    }


if __name__ == "__main__":
    main()
