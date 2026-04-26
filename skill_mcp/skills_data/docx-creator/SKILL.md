---
name: docx-creator
description: Create, read, and edit Microsoft Word (.docx) documents. Generate reports, contracts, letters, and structured documents with headings, tables, images, lists, and formatting. Use when the user needs to create a Word document, edit a .docx file, generate a report, or export content to Word format.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [docx, word, documents, reports, office]
  platforms: [claude-code, cursor, any]
  triggers:
    - create a Word document
    - make a .docx file
    - generate a report in Word
    - write a Word doc
    - create docx
    - edit this Word document
    - export to Word
    - create a contract
    - generate a letter
---

# DOCX Creator Skill

## Overview
Create and edit Microsoft Word (.docx) documents programmatically using `python-docx`. Handles documents from simple letters to complex reports with tables, headers, footers, and styles.

## Library Setup

```bash
pip install python-docx
```

For reading complex `.docx` files: `python-docx` handles most cases. For advanced conversion (docx → PDF, docx → HTML), add `libreoffice` (CLI) or `pandoc`.

## Step-by-Step Process

### Step 1: Understand the Document Structure
Ask or infer:
- Document type (letter, report, contract, resume, technical doc)
- Sections and headings needed
- Whether it needs tables, images, or lists
- Target audience (formal vs. informal tone)
- Page setup (orientation, margins, headers/footers)

### Step 2: Create a New Document

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
```

### Step 3: Set Document Styles and Page Setup

```python
from docx.oxml.ns import qn
import docx

# Set margins
sections = doc.sections
for section in sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.25)
    section.right_margin = Inches(1.25)
```

### Step 4: Add Headings

```python
doc.add_heading("Document Title", level=0)   # Title style
doc.add_heading("Section 1", level=1)          # Heading 1
doc.add_heading("Subsection 1.1", level=2)     # Heading 2
```

### Step 5: Add Paragraphs with Formatting

```python
para = doc.add_paragraph("This is a paragraph with ")
run = para.add_run("bold text")
run.bold = True
para.add_run(" and normal text.")

# Alignment
para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# Custom font
run.font.name = "Calibri"
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
```

### Step 6: Add Tables

```python
table = doc.add_table(rows=1, cols=3)
table.style = "Table Grid"

# Header row
header_cells = table.rows[0].cells
header_cells[0].text = "Name"
header_cells[1].text = "Role"
header_cells[2].text = "Department"

# Data rows
data = [("Alice", "Engineer", "Platform"), ("Bob", "Designer", "Product")]
for name, role, dept in data:
    row_cells = table.add_row().cells
    row_cells[0].text = name
    row_cells[1].text = role
    row_cells[2].text = dept
```

### Step 7: Add Lists

```python
# Bullet list
doc.add_paragraph("First item", style="List Bullet")
doc.add_paragraph("Second item", style="List Bullet")

# Numbered list
doc.add_paragraph("Step one", style="List Number")
doc.add_paragraph("Step two", style="List Number")
```

### Step 8: Add Images

```python
doc.add_picture("chart.png", width=Inches(5.0))
# Add caption
doc.add_paragraph("Figure 1: Quarterly Revenue", style="Caption")
```

### Step 9: Add Headers and Footers

```python
section = doc.sections[0]
header = section.header
header_para = header.paragraphs[0]
header_para.text = "Confidential — Company Name"
header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
```

### Step 10: Save

```python
doc.save("output.docx")
```

## Reading Existing .docx Files

```python
doc = Document("existing.docx")

# Extract all text
for para in doc.paragraphs:
    print(para.style.name, ":", para.text)

# Extract tables
for table in doc.tables:
    for row in table.rows:
        print([cell.text for cell in row.cells])
```

## Edge Cases
- **Template-based generation**: Load an existing .docx as a template with `Document("template.docx")` to inherit styles
- **Large documents**: Add a page break with `doc.add_page_break()` between major sections
- **Complex formatting**: Use `doc.styles` to list available styles before applying custom ones
- **Track changes / comments**: `python-docx` does not support these — use LibreOffice CLI for conversion instead
