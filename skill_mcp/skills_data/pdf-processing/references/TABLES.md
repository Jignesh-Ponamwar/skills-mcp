# PDF Table Extraction Reference

Strategies for extracting tables from PDFs, handling merged cells, multi-page tables, and inconsistent formatting.

---

## Why PDF Table Extraction Is Hard

PDFs store content as positioned text elements — there is no "table" concept in the file format. Table extraction means inferring rows and columns from the spatial relationships between text boxes. This is inherently heuristic and imperfect.

**Reliability spectrum (best to worst):**
1. Native text PDF with clear borders → `pdfplumber` works well
2. Native text PDF without borders (whitespace-separated) → `pdfplumber` with explicit settings
3. Scanned PDF (image-based) → OCR required first (Tesseract / AWS Textract)
4. Complex layouts (merged cells, rotated headers, spanning rows) → manual post-processing required

---

## pdfplumber — Recommended for Most Cases

```python
import pdfplumber
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        for table_num, table in enumerate(tables, 1):
            print(f"Page {page_num}, Table {table_num}:")
            df = pd.DataFrame(table[1:], columns=table[0])  # assume first row = header
            print(df.to_string(index=False))
            print()
```

### Tuning Table Settings

When default extraction misses columns or merges wrong cells:

```python
table_settings = {
    "vertical_strategy": "lines",      # "lines" | "text" | "explicit"
    "horizontal_strategy": "lines",    # "lines" | "text" | "explicit"
    "explicit_vertical_lines": [],     # provide x-coordinates if strategy="explicit"
    "explicit_horizontal_lines": [],   # provide y-coordinates if strategy="explicit"
    "snap_tolerance": 3,               # pixels to snap nearby lines together
    "join_tolerance": 3,               # pixels to join nearly-touching lines
    "edge_min_length": 3,              # minimum length to count as a table border line
    "min_words_vertical": 3,           # min words for a text-based vertical rule
    "min_words_horizontal": 1,         # min words for a text-based horizontal rule
    "intersection_tolerance": 3,       # pixels when intersecting lines
    "text_tolerance": 3,               # pixels for grouping text into cells
    "text_x_tolerance": 3,
    "text_y_tolerance": 3,
}

tables = page.extract_tables(table_settings=table_settings)
```

**Key setting combinations:**

| PDF type | `vertical_strategy` | `horizontal_strategy` |
|----------|--------------------|-----------------------|
| Has visible grid lines | `"lines"` | `"lines"` |
| Column-separated by whitespace | `"text"` | `"text"` |
| Has row lines only | `"text"` | `"lines"` |
| Known column positions | `"explicit"` | `"lines"` |

---

## Handling Merged Cells

`pdfplumber` returns `None` for cells that are part of a merged region:

```python
import pdfplumber
import pandas as pd

def fill_merged_cells(table: list[list]) -> list[list]:
    """Forward-fill None values to handle horizontally merged cells."""
    result = []
    for row in table:
        new_row = []
        last_value = None
        for cell in row:
            if cell is None:
                new_row.append(last_value)  # propagate previous cell
            else:
                last_value = cell
                new_row.append(cell)
        result.append(new_row)
    return result

with pdfplumber.open("merged.pdf") as pdf:
    raw_tables = pdf.pages[0].extract_tables()
    for table in raw_tables:
        filled = fill_merged_cells(table)
        df = pd.DataFrame(filled[1:], columns=filled[0])
        print(df)
```

---

## Multi-Page Tables

Tables that continue across pages need special handling:

```python
import pdfplumber
import pandas as pd

all_rows = []
header = None

with pdfplumber.open("multi_page_table.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            if header is None:
                # First table — assume first row is header
                header = table[0]
                all_rows.extend(table[1:])
            else:
                # Subsequent pages — check if first row repeats the header
                if table[0] == header:
                    all_rows.extend(table[1:])  # skip repeated header
                else:
                    all_rows.extend(table)

df = pd.DataFrame(all_rows, columns=header)
print(df)
```

---

## Cleaning Extracted Data

Raw table data needs cleaning before use:

```python
import pandas as pd
import re

def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    # Remove completely empty rows and columns
    df = df.dropna(how="all").dropna(axis=1, how="all")
    
    # Strip whitespace from string cells
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Replace empty strings with NaN
    df = df.replace("", pd.NA)
    
    # Remove newlines inside cells (common in PDF extraction)
    df = df.map(lambda x: re.sub(r"\s+", " ", x) if isinstance(x, str) else x)
    
    return df
```

---

## When pdfplumber Fails: pypdf + Manual Parsing

For PDFs where `pdfplumber` returns no tables or garbled results:

```python
import pypdf
import re

def extract_table_from_text(pdf_path: str, page_num: int = 0) -> list[list[str]]:
    """Extract tabular data from raw text using column alignment heuristics."""
    reader = pypdf.PdfReader(pdf_path)
    text = reader.pages[page_num].extract_text()
    
    lines = [l for l in text.splitlines() if l.strip()]
    rows = []
    for line in lines:
        # Split on 2+ consecutive spaces (column separator in aligned text)
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) > 1:
            rows.append(cols)
    return rows
```

---

## Using Camelot for Complex Tables

`camelot-py` is specifically designed for table extraction and handles complex layouts:

```bash
pip install camelot-py[cv]
```

```python
import camelot

# For PDFs with clear borders
tables = camelot.read_pdf("document.pdf", flavor="lattice", pages="1-3")

# For PDFs without borders (whitespace-separated)
tables = camelot.read_pdf("document.pdf", flavor="stream", pages="1-3")

for i, table in enumerate(tables):
    print(f"Table {i}: accuracy={table.accuracy:.1f}%")
    df = table.df
    print(df)
```
