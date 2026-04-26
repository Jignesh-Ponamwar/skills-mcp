---
name: xlsx-creator
description: >
  Create, edit, and analyze Excel spreadsheets (.xlsx, .xlsm, .csv, .tsv files). Covers building
  spreadsheets with openpyxl and pandas, writing Excel formulas, applying professional formatting
  and color conventions, creating charts, and validating formula correctness. Use when the user
  wants to create an Excel file, analyze spreadsheet data, build a financial model, generate a
  report as XLSX, or edit an existing spreadsheet.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [excel, xlsx, spreadsheet, openpyxl, pandas, formulas, financial-model, data]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - create an Excel file
    - build a spreadsheet
    - write Excel formulas
    - create an XLSX file
    - analyze spreadsheet data
    - financial model
    - generate a report in Excel
    - edit a CSV
    - openpyxl
    - pandas to Excel
    - Excel chart
---

# Excel Spreadsheet Skill (XLSX)

## Professional Standards

- **Zero formula errors** — no #REF!, #DIV/0!, #VALUE!, #N/A, or #NAME? errors allowed
- **Always use formulas** instead of calculating values in Python and hardcoding them — spreadsheets must remain dynamic
- **Consistent fonts** throughout — pick one font family (Calibri 11 or Aptos 11 for Excel defaults)
- **Document hardcoded values** with comments including source, date, and reference URL

---

## Tool Selection

| Use Case | Tool |
|----------|------|
| Data analysis, bulk operations, DataFrame export | **pandas** |
| Complex formatting, formulas, cell styling | **openpyxl** |
| Both formatting AND data manipulation | Use pandas to build data, openpyxl to format |

---

## Step 1: Setup

```bash
pip install openpyxl pandas xlsxwriter
```

---

## Step 2: Create a Spreadsheet with openpyxl

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference

wb = Workbook()
ws = wb.active
ws.title = "Revenue Model"

# ─── STYLING HELPERS ─────────────────────────────────────────────────────────
HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(fill_type="solid", fgColor="1F4E79")  # dark blue
INPUT_FILL = PatternFill(fill_type="solid", fgColor="DDEEFF")   # light blue (inputs)
FORMULA_FILL = PatternFill(fill_type="solid", fgColor="FFFFFF")  # white (formulas)
ASSUMPTION_FILL = PatternFill(fill_type="solid", fgColor="FFFF99") # yellow (key assumptions)

thin = Side(style="thin", color="000000")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

def style_header(cell):
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = BORDER

def style_input(cell):
    cell.fill = INPUT_FILL  # blue = hardcoded input (industry standard)
    cell.border = BORDER

def style_formula(cell):
    cell.fill = FORMULA_FILL  # white/black = formula
    cell.border = BORDER

# ─── HEADERS ─────────────────────────────────────────────────────────────────
headers = ["Month", "Units Sold", "Unit Price ($)", "Revenue ($)", "COGS ($)", "Gross Profit ($)"]
for col, h in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col, value=h)
    style_header(cell)
    ws.column_dimensions[get_column_letter(col)].width = max(len(h) + 2, 14)

# ─── INPUT DATA ──────────────────────────────────────────────────────────────
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
units = [1200, 1350, 1280, 1500, 1420, 1650]
price = 29.99
cogs_pct = 0.40  # key assumption — put in assumption row

for i, (month, unit) in enumerate(zip(months, units), start=2):
    row = i
    # Month
    ws.cell(row=row, column=1, value=month)
    # Units (input — blue)
    cell_units = ws.cell(row=row, column=2, value=unit)
    style_input(cell_units)
    # Unit Price (input — blue)
    cell_price = ws.cell(row=row, column=3, value=price)
    cell_price.number_format = '"$"#,##0.00'
    style_input(cell_price)
    # Revenue (formula — always use formula, not Python calculation)
    cell_rev = ws.cell(row=row, column=4, value=f"=B{row}*C{row}")
    cell_rev.number_format = '"$"#,##0.00'
    style_formula(cell_rev)
    # COGS (formula referencing assumption)
    # Assume COGS % is in cell H2
    cell_cogs = ws.cell(row=row, column=5, value=f"=D{row}*$H$2")
    cell_cogs.number_format = '"$"#,##0.00'
    style_formula(cell_cogs)
    # Gross Profit (formula)
    cell_gp = ws.cell(row=row, column=6, value=f"=D{row}-E{row}")
    cell_gp.number_format = '"$"#,##0.00'
    style_formula(cell_gp)

# ─── ASSUMPTIONS BOX ─────────────────────────────────────────────────────────
# Yellow = key assumptions
ws["G1"] = "Key Assumptions"
ws["G1"].font = Font(bold=True)
ws["G2"] = "COGS % of Revenue"
ws["H2"] = cogs_pct
ws["H2"].number_format = "0%"
ws["H2"].comment = "Source: Management estimate, April 2026"
cell_h2 = ws["H2"]
cell_h2.fill = ASSUMPTION_FILL  # yellow = key assumption

# ─── TOTALS ROW ──────────────────────────────────────────────────────────────
total_row = len(months) + 2
ws.cell(row=total_row, column=1, value="TOTAL")
ws.cell(row=total_row, column=1).font = Font(bold=True)
for col in range(2, 7):
    col_letter = get_column_letter(col)
    formula = f"=SUM({col_letter}2:{col_letter}{total_row-1})"
    cell = ws.cell(row=total_row, column=col, value=formula)
    if col >= 4:
        cell.number_format = '"$"#,##0.00'
    cell.font = Font(bold=True)
    cell.border = BORDER

# ─── CHART ───────────────────────────────────────────────────────────────────
chart = BarChart()
chart.title = "Monthly Revenue"
chart.style = 10
chart.y_axis.title = "Revenue ($)"
chart.x_axis.title = "Month"

data = Reference(ws, min_col=4, min_row=1, max_row=len(months) + 1)
categories = Reference(ws, min_col=1, min_row=2, max_row=len(months) + 1)
chart.add_data(data, titles_from_data=True)
chart.set_categories(categories)
chart.shape = 4
ws.add_chart(chart, "A10")

# ─── SAVE ────────────────────────────────────────────────────────────────────
wb.save("revenue-model.xlsx")
print("Saved: revenue-model.xlsx")
```

---

## Step 3: Read / Analyze Existing Spreadsheets with pandas

```python
import pandas as pd

# Read Excel
df = pd.read_excel("data.xlsx", sheet_name="Sheet1")

# Or CSV
df = pd.read_csv("data.csv")

# Analysis
print(df.describe())
print(df.groupby("category")["revenue"].sum())

# Write back to Excel with formatting
with pd.ExcelWriter("output.xlsx", engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Data", index=False)
    summary = df.groupby("category").agg({"revenue": ["sum", "mean", "count"]})
    summary.to_excel(writer, sheet_name="Summary")
```

---

## Financial Model Color Conventions (Industry Standard)

| Color | Meaning |
|-------|---------|
| **Blue text / blue fill** | Hardcoded input — user enters this |
| **Black text / white fill** | Formula — computed from other cells |
| **Green text** | Internal link to another cell in same workbook |
| **Red text** | External link (different workbook) |
| **Yellow background** | Key assumption — highlight for visibility |

---

## Formula Best Practices

```python
# ✅ Always write Excel formulas — NOT Python calculations
cell.value = "=B2*C2"           # revenue formula
cell.value = "=SUM(D2:D13)"     # total
cell.value = "=IFERROR(D2/E2,0)" # safe division

# ❌ Never hardcode computed values
cell.value = 35988              # static — breaks when inputs change
```

**Lock references for constants:**
```python
# $H$2 = absolute reference to assumption cell
cell.value = f"=D{row}*$H$2"   # COGS % stays fixed as formula copies down
```

---

## Common Mistakes

- **Hardcoding calculated values** — always use Excel formulas; Python is for setup only
- **Missing `number_format`** — always set `"$#,##0.00"` for currency, `"0%"` for percentages
- **Not validating formula results** — open the file and check for #REF!, #VALUE!, #DIV/0!
- **Inconsistent fonts** — pick one font and use it throughout
- **No documentation for assumptions** — add `cell.comment` with source and date for hardcoded numbers
- **Absolute vs relative references** — use `$A$1` when copying formulas that reference fixed cells
