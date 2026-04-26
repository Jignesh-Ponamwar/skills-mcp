# PDF Extraction Output — Standard Format

Use this template when reporting extracted PDF content to the user. Fill in each section with the actual extracted data.

---

## Document Summary

| Field | Value |
|-------|-------|
| **File** | `{filename}` |
| **Pages** | {total_pages} |
| **Total words** | {total_words} |
| **File size** | {file_size_kb} KB |
| **Extraction method** | {method} *(pdfplumber / pypdf / OCR)* |
| **Extraction quality** | {quality} *(high / medium / low — note if OCR was needed)* |

---

## Extracted Text

{extracted_text}

---

## Tables Found

*Total tables extracted: {table_count}*

### Table 1: {table_title_or_page}

{table_as_markdown}

*Add additional table sections as needed.*

---

## Data Quality Notes

- {note_1} *(e.g., "Page 3 contains a scanned image — text may contain OCR errors")*
- {note_2} *(e.g., "Table on page 5 has merged cells; values were forward-filled")*

---

## Suggested Next Steps

- [ ] Review extracted tables for merged cell artifacts
- [ ] Verify numeric values against source document
- [ ] Run `fill_form.py` if this is a form that needs to be filled
- [ ] Export to CSV: `df.to_csv("output.csv", index=False)`
