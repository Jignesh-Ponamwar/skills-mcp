---
name: pptx-creator
description: >
  Create, edit, and analyze PowerPoint presentations (.pptx files). Covers building slides from
  scratch with pptxgenjs, reading and extracting text with markitdown, editing existing presentations
  by unpacking and modifying XML, and converting slides to images for review. Use when the user
  wants to create a presentation, add slides, modify an existing PPTX file, or generate a slide
  deck programmatically.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [pptx, powerpoint, presentations, slides, pptxgenjs, office, documents]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - create a PowerPoint presentation
    - make slides
    - create a PPTX file
    - edit a presentation
    - generate slide deck
    - read a PowerPoint file
    - extract text from PPTX
    - add slides to presentation
    - build a pitch deck
    - create slides
---

# PowerPoint Presentation Skill (PPTX)

## Three Workflows

| Workflow | When to Use |
|---------|-------------|
| **Read** | Extract text, generate thumbnails from an existing PPTX |
| **Create** | Build a new presentation from scratch using pptxgenjs |
| **Edit** | Unpack XML, modify content, repack existing PPTX |

---

## Workflow 1: Reading an Existing PPTX

### Extract Text (requires markitdown)
```bash
pip install markitdown
```
```python
from markitdown import MarkItDown

converter = MarkItDown()
result = converter.convert("presentation.pptx")
print(result.text_content)  # all slides as markdown
```

### Generate Slide Thumbnails
```bash
# Requires LibreOffice
libreoffice --headless --convert-to png presentation.pptx
# Generates: Slide1.png, Slide2.png, ...
```

---

## Workflow 2: Create a New Presentation with pptxgenjs

### Setup
```bash
npm install pptxgenjs
```

### Complete Example
```javascript
const PptxGenJS = require('pptxgenjs')
const pptx = new PptxGenJS()

// Set presentation properties
pptx.layout = 'LAYOUT_WIDE'  // 16:9
pptx.author = 'Claude'

// ─── SLIDE 1: Title Slide ───────────────────────────────────────────────────
const slide1 = pptx.addSlide()
slide1.background = { color: '1a1a2e' }  // dark navy

slide1.addText('Quarterly Review', {
  x: 1, y: 1.5, w: 8, h: 1.5,
  fontSize: 48, bold: true, color: 'ffffff',
  align: 'center', fontFace: 'Georgia',
})

slide1.addText('Q1 2026 Results', {
  x: 1, y: 3.2, w: 8, h: 0.8,
  fontSize: 24, color: 'e0e0e0',
  align: 'center',
})

// ─── SLIDE 2: Content Slide ─────────────────────────────────────────────────
const slide2 = pptx.addSlide()

// Title
slide2.addText('Key Metrics', {
  x: 0.5, y: 0.3, w: 9, h: 0.8,
  fontSize: 32, bold: true, color: '1a1a2e',
})

// Divider line (using shape)
slide2.addShape(pptx.ShapeType.rect, {
  x: 0.5, y: 1.15, w: 9, h: 0.05,
  fill: { color: '4a90e2' }, line: { color: '4a90e2' },
})

// Bullet points
slide2.addText([
  { text: 'Revenue: ', options: { bold: true } },
  { text: '$2.4M (+18% YoY)' },
], { x: 0.7, y: 1.5, w: 8.3, h: 0.5, fontSize: 18, color: '333333' })

slide2.addText([
  { text: 'Users: ', options: { bold: true } },
  { text: '142,000 active (+32%)' },
], { x: 0.7, y: 2.1, w: 8.3, h: 0.5, fontSize: 18, color: '333333' })

// ─── SLIDE 3: Chart Slide ───────────────────────────────────────────────────
const slide3 = pptx.addSlide()
slide3.addText('Monthly Revenue', {
  x: 0.5, y: 0.3, w: 9, h: 0.8,
  fontSize: 28, bold: true, color: '1a1a2e',
})

slide3.addChart(pptx.ChartType.bar, [
  {
    name: 'Revenue ($K)',
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    values: [180, 210, 195, 240, 225, 280],
  }
], {
  x: 0.5, y: 1.2, w: 9, h: 4.5,
  chartColors: ['4a90e2'],
  showLegend: false,
  valAxisLabelFontSize: 12,
  catAxisLabelFontSize: 12,
})

// Save
await pptx.writeFile({ fileName: 'quarterly-review.pptx' })
console.log('Presentation saved.')
```

---

## Workflow 3: Editing an Existing PPTX

PPTX files are ZIP archives containing XML. Edit in three steps:

### Step 3a: Unpack
```bash
mkdir unpacked
unzip presentation.pptx -d unpacked/
# Slides are in: unpacked/ppt/slides/slide1.xml, slide2.xml, ...
```

### Step 3b: Edit the XML
Slides are in `unpacked/ppt/slides/slideN.xml`. Text runs are in `<a:t>` elements:

```xml
<!-- Find and update text like this -->
<a:t>Old Title Text</a:t>
<!-- Change to: -->
<a:t>New Title Text</a:t>
```

Use smart quotes in professional documents: `&#x201C;` (") and `&#x201D;` (").

### Step 3c: Repack
```bash
cd unpacked/
zip -r ../output.pptx . -x "*.DS_Store"
cd ..
```

---

## Design Principles

### Color Strategy
- **One dominant color** (60-70% visual weight) + 1-2 supporting tones + one sharp accent
- Avoid: all-white slides with thin gray text, purple gradients, blue-on-blue

### Typography
- Headings: 32-44pt, bold, distinctive typeface (Georgia, Playfair Display)
- Body: 16-20pt, clean sans-serif (Calibri, Inter)
- Never: Wall-of-text slides, font sizes below 14pt

### Layout Rules
- Every slide needs at least one visual element (image, chart, icon, or bold shape)
- Text-only slides are boring — add a supporting graphic
- Use consistent alignment and margins (0.5in minimum from edges)
- One key message per slide — if you have three points, consider three slides

### What to Avoid
- Centered body text on every slide
- Generic blue/gray corporate palettes
- Bullet point lists with 8+ items
- Placeholder text left over (`Click to add text`)
- Low-contrast text (dark gray on dark background)

---

## Quality Verification

After creating slides:
1. Convert to images: `libreoffice --headless --convert-to png output.pptx`
2. Visually inspect: check for text overflow, overlapping elements, low contrast
3. Verify all slides have visual elements — no text-only slides
4. Check font sizes are readable (≥14pt body, ≥24pt titles)
5. Confirm color consistency across all slides

---

## Dependencies

| Tool | Purpose | Install |
|------|---------|---------|
| `pptxgenjs` | Create new presentations | `npm install pptxgenjs` |
| `markitdown` | Extract text from PPTX | `pip install markitdown` |
| LibreOffice | Convert to images / PDF | System package |
| `unzip` / `zip` | Unpack/repack for XML editing | System package |
