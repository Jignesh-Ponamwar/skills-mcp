---
name: pdf-processing
description: Extract text, tables, and metadata from PDF files. Fill PDF forms, merge multiple PDFs, split documents, and convert PDF content to structured formats. Use when the user asks to read a PDF, extract data from a PDF, fill a form, merge PDFs, or work with PDF documents.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [pdf, extraction, documents, forms, ocr]
  platforms: [claude-code, cursor, any]
  triggers:
    - read this PDF
    - extract text from PDF
    - parse PDF
    - fill this PDF form
    - merge PDFs
    - split PDF
    - convert PDF to text
    - what does this PDF say
    - extract tables from PDF
    - PDF processing
---

# PDF Processing Skill

## Overview
This skill handles all PDF operations: text extraction, table parsing, form filling, merging, splitting, and metadata extraction.

## Step-by-Step Guidance

### 1. Identify the Operation
Determine what the user needs:
- **Text extraction**: Read content from a PDF into plain text or markdown
- **Table extraction**: Pull structured tabular data into CSV/JSON
- **Form filling**: Write values into fillable PDF form fields
- **Merge**: Combine multiple PDFs into one document
- **Split**: Divide a PDF into separate pages or sections
- **Metadata**: Extract author, creation date, page count, etc.

### 2. Choose the Right Library
For Python environments:
- `pypdf` (formerly PyPDF2): text extraction, merging, splitting, metadata — pure Python, no system deps
- `pdfplumber`: best for tables and layout-aware extraction
- `pymupdf` (fitz): fastest, handles scanned PDFs with OCR via Tesseract
- `reportlab`: generate new PDFs or fill forms programmatically
- `pdfrw`: low-level PDF manipulation, ideal for form filling

### 3. Text Extraction
```python
import pypdf

reader = pypdf.PdfReader("document.pdf")
text = "\n\n".join(page.extract_text() for page in reader.pages)
print(text)
```

For layout-preserving extraction:
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        print(page.extract_text(layout=True))
```

### 4. Table Extraction
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)
```

### 5. Merging PDFs
```python
import pypdf

merger = pypdf.PdfMerger()
for path in ["file1.pdf", "file2.pdf", "file3.pdf"]:
    merger.append(path)
merger.write("merged.pdf")
merger.close()
```

### 6. Splitting a PDF
```python
import pypdf

reader = pypdf.PdfReader("document.pdf")
for i, page in enumerate(reader.pages):
    writer = pypdf.PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as f:
        writer.write(f)
```

### 7. Form Filling
```python
import pypdf

reader = pypdf.PdfReader("form.pdf")
writer = pypdf.PdfWriter()
writer.append(reader)
writer.update_page_form_field_values(
    writer.pages[0],
    {"field_name": "value", "another_field": "another_value"}
)
with open("filled_form.pdf", "wb") as f:
    writer.write(f)
```

## Edge Cases
- Scanned PDFs (image-only): use `pymupdf` + Tesseract OCR — warn the user if no text is found
- Password-protected PDFs: call `reader.decrypt("password")` before reading
- Large PDFs (>100 pages): process page by page to avoid memory issues
- Right-to-left text (Arabic, Hebrew): `pdfplumber` handles RTL better than `pypdf`

## Output Format
- Plain text extraction → return as a markdown code block
- Table extraction → return as CSV or a markdown table
- File operations (merge/split) → confirm output file path and page count
