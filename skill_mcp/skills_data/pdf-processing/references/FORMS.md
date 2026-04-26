# PDF Form Filling Reference

A complete reference for working with fillable PDF forms: field types, value formats, validation rules, and cross-library compatibility.

---

## PDF Form Field Types

### AcroForm Field Types (Standard)

| Field Type | Widget Type | Typical Value | Notes |
|-----------|------------|---------------|-------|
| Text | Single-line text | `"Alice Johnson"` | Plain string |
| Multiline text | Multi-line text | `"Line 1\nLine 2"` | Use `\n` for line breaks |
| Checkbox | Boolean | `/Yes` or `/Off` | PDF checkbox values — NOT `True`/`False` |
| Radio button | Mutually exclusive | `/Option1` | Value must match the export value |
| Dropdown (list) | Select | `"Option Text"` | Match the display text exactly |
| Digital signature | Signature field | N/A | Cannot be filled programmatically |
| Date | Text with validation | `"01/15/2024"` | Format depends on form definition |

### XFA Forms (Dynamic PDF Forms)

XFA forms (used by Adobe LiveCycle) are XML-based and behave differently:
- `pypdf` does **not** support XFA — it will silently fail or write nothing
- Use Adobe Acrobat SDK, `pdfrw`, or convert XFA → AcroForm first
- Detection: `reader.xfa` is not None if the form uses XFA

---

## Reading Available Fields

Before filling, always inspect available fields:

```python
import pypdf

reader = pypdf.PdfReader("form.pdf")
fields = reader.get_fields()

if fields is None:
    print("This PDF has no fillable form fields (or is XFA)")
else:
    for name, field in fields.items():
        field_type = field.get("/FT", "Unknown")
        current_value = field.get("/V", "")
        print(f"  {name!r}: type={field_type}, current={current_value!r}")
```

Common `/FT` values: `/Tx` (text), `/Btn` (checkbox/radio), `/Ch` (choice/dropdown)

---

## Checkbox Values

Checkboxes in PDFs use PDF name objects, not booleans:

```python
# WRONG — does not work
fields = {"agree_checkbox": True}

# CORRECT — use the PDF export value
fields = {"agree_checkbox": "/Yes"}   # when checked
fields = {"agree_checkbox": "/Off"}   # when unchecked
```

To discover the correct export value for a checkbox:
```python
field = reader.get_fields()["agree_checkbox"]
# The on-state value is in /AP/N (appearance stream) or /AS
# Or try /Yes as default — most AcroForms use this
```

---

## Filling Forms with pypdf

```python
import pypdf

reader = pypdf.PdfReader("form.pdf")
writer = pypdf.PdfWriter()
writer.append(reader)

field_values = {
    "first_name": "Alice",
    "last_name": "Johnson",
    "date_of_birth": "01/15/1990",
    "agree_terms": "/Yes",
    "gender": "/Female",
}

for page in writer.pages:
    writer.update_page_form_field_values(page, field_values)

with open("filled_form.pdf", "wb") as f:
    writer.write(f)
```

**Important:** Call `update_page_form_field_values` on every page — forms can span multiple pages.

---

## Flattening Filled Forms

"Flattening" merges the form data into the page content, making it non-editable:

```python
# With pypdf — set the read-only flag
writer.update_page_form_field_values(
    writer.pages[0],
    field_values,
    flags=1,  # 1 = ReadOnly
)
```

For true flattening (remove form structure entirely), use:
```bash
# With Ghostscript
gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dFlattenForms=true \
   -sOutputFile=flat.pdf -f filled.pdf

# With LibreOffice
libreoffice --headless --convert-to pdf filled.pdf
```

---

## Common Problems and Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Fields filled but invisible | Missing appearance stream | Set `writer.update_page_form_field_values(..., auto_regenerate=True)` in newer pypdf |
| Checkbox stays unchecked | Wrong value format | Use `/Yes` not `True` or `"Yes"` |
| Missing fields after write | XFA form | Use pdfrw or Adobe API |
| Filled form shows wrong font | Font not embedded | Open in Acrobat and re-save with embedded fonts |
| Fields appear but value is blank | Field name mismatch (case-sensitive) | Print `reader.get_fields().keys()` to inspect exact names |

---

## Field Name Discovery Script

```python
import pypdf, json

def inspect_form(pdf_path: str) -> None:
    reader = pypdf.PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        print("No AcroForm fields found")
        return
    result = {}
    for name, field in fields.items():
        result[name] = {
            "type": field.get("/FT", "?"),
            "current_value": field.get("/V", ""),
            "default_value": field.get("/DV", ""),
            "tooltip": field.get("/TU", ""),
        }
    print(json.dumps(result, indent=2, default=str))

inspect_form("your_form.pdf")
```
