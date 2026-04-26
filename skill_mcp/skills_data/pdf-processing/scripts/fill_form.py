"""
PDF form filler — bundled with the pdf-processing skill.

Fills an AcroForm PDF with the provided field values and saves the result.
Does NOT support XFA forms (Adobe LiveCycle); see references/FORMS.md for details.

Input (environment variables):
  PDF_PATH     — absolute path to the source PDF form (required)
  FIELDS_JSON  — JSON object of {"field_name": "value", ...} (required)
  OUTPUT_PATH  — output file path (default: filled_<original_name>.pdf)

Output (stdout): JSON result with filled field names, missing fields, and output path
"""

import json
import os
import sys


def main() -> None:
    pdf_path = os.environ.get("PDF_PATH", "")
    fields_json = os.environ.get("FIELDS_JSON", "")
    output_path = os.environ.get("OUTPUT_PATH", "")

    if not pdf_path:
        print(json.dumps({"error": "PDF_PATH environment variable is required"}))
        sys.exit(1)

    if not fields_json:
        print(json.dumps({
            "error": "FIELDS_JSON environment variable is required",
            "example": 'FIELDS_JSON=\'{"name": "Alice", "date": "2024-01-15"}\'',
        }))
        sys.exit(1)

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"FIELDS_JSON must be valid JSON: {e}"}))
        sys.exit(1)

    if not output_path:
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(
            os.path.dirname(pdf_path) or ".", f"filled_{base}.pdf"
        )

    try:
        import pypdf
    except ImportError:
        print(json.dumps({"error": "pypdf is required: pip install pypdf"}))
        sys.exit(1)

    try:
        reader = pypdf.PdfReader(pdf_path)
    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Could not open PDF: {e}"}))
        sys.exit(1)

    # Inspect available form fields
    available_fields = {}
    raw_fields = reader.get_fields()
    if raw_fields:
        available_fields = {
            name: field.get("/V", "") for name, field in raw_fields.items()
        }

    if not available_fields:
        print(json.dumps({
            "error": "No fillable AcroForm fields found in this PDF.",
            "note": "This PDF may use XFA forms (not supported) or have no form fields.",
            "tip": "See references/FORMS.md for XFA detection guidance.",
        }))
        sys.exit(1)

    writer = pypdf.PdfWriter()
    writer.append(reader)

    # Fill all pages
    for page in writer.pages:
        writer.update_page_form_field_values(page, fields)

    # Categorise fields
    filled = [k for k in fields if k in available_fields]
    missing = [k for k in fields if k not in available_fields]

    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except OSError as e:
        print(json.dumps({"error": f"Could not write output file: {e}"}))
        sys.exit(1)

    print(json.dumps({
        "success": True,
        "output_path": output_path,
        "fields_filled": filled,
        "fields_not_found": missing,
        "all_available_fields": list(available_fields.keys()),
        "tip": (
            "If filled values are invisible, the PDF reader may need to regenerate "
            "appearance streams. Open in Adobe Reader and resave."
        ) if filled else None,
    }, indent=2))


if __name__ == "__main__":
    main()
