---
name: web-artifacts-builder
description: >
  Build complex, self-contained interactive web artifacts — rich HTML/CSS/JavaScript applications,
  React components with Tailwind CSS and shadcn/ui, data visualizations with D3.js or Chart.js,
  interactive tools, and games — all bundled into a single portable HTML file. Use when the user
  wants to create an interactive demo, a data visualization, a UI prototype, a mini web app, or
  any rich browser-rendered artifact that can be embedded or shared as a single file.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [html, react, tailwind, shadcn, d3, charts, visualization, interactive, artifacts]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - create an interactive web app
    - build a data visualization
    - make a React component
    - create a demo
    - build a dashboard
    - interactive HTML artifact
    - web artifact with React
    - Tailwind CSS component
    - shadcn component
    - D3 chart
    - Chart.js visualization
    - build a game
    - create a tool
---

# Web Artifacts Builder Skill

## Two Approaches

| Approach | When to Use | Complexity |
|---------|-------------|-----------|
| **Pure HTML/CSS/JS** | Simple interactions, no framework needed | Low |
| **React + Tailwind (CDN)** | Rich UI, components, state management | Medium |
| **React + Vite + Bundle** | Production app, many dependencies | High |

---

## Approach A: Self-Contained HTML (No Build Step)

Best for: calculators, visualizations, simple tools, games.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Budget Calculator</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }

    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 1rem;
      padding: 2rem;
      width: 100%;
      max-width: 480px;
    }

    h1 {
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 1.5rem;
      color: #f8fafc;
    }

    .field {
      margin-bottom: 1rem;
    }

    label {
      display: block;
      font-size: 0.875rem;
      color: #94a3b8;
      margin-bottom: 0.4rem;
    }

    input {
      width: 100%;
      padding: 0.6rem 0.8rem;
      background: #0f172a;
      border: 1px solid #475569;
      border-radius: 0.5rem;
      color: #f8fafc;
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s;
    }

    input:focus { border-color: #6366f1; }

    button {
      width: 100%;
      padding: 0.75rem;
      background: #6366f1;
      color: white;
      border: none;
      border-radius: 0.5rem;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      margin-top: 1rem;
      transition: background 0.2s;
    }

    button:hover { background: #4f46e5; }

    .result {
      margin-top: 1.5rem;
      padding: 1rem;
      background: #0f172a;
      border-radius: 0.5rem;
      border-left: 4px solid #6366f1;
      display: none;
    }

    .result.show { display: block; }
    .result-label { color: #94a3b8; font-size: 0.875rem; }
    .result-value { color: #f8fafc; font-size: 1.5rem; font-weight: 700; }
  </style>
</head>
<body>
  <div class="card">
    <h1>💰 Budget Calculator</h1>

    <div class="field">
      <label>Monthly Income ($)</label>
      <input type="number" id="income" placeholder="5000">
    </div>

    <div class="field">
      <label>Monthly Expenses ($)</label>
      <input type="number" id="expenses" placeholder="3500">
    </div>

    <button onclick="calculate()">Calculate Savings</button>

    <div class="result" id="result">
      <div class="result-label">Monthly Savings</div>
      <div class="result-value" id="savings-value"></div>
      <div class="result-label" style="margin-top: 0.5rem" id="savings-pct"></div>
    </div>
  </div>

  <script>
    function calculate() {
      const income = parseFloat(document.getElementById('income').value) || 0
      const expenses = parseFloat(document.getElementById('expenses').value) || 0
      const savings = income - expenses
      const pct = income > 0 ? ((savings / income) * 100).toFixed(1) : 0

      const result = document.getElementById('result')
      document.getElementById('savings-value').textContent = `$${savings.toLocaleString()}`
      document.getElementById('savings-pct').textContent = `${pct}% of income`
      result.classList.add('show')
    }
  </script>
</body>
</html>
```

---

## Approach B: React + Tailwind via CDN

Best for: interactive dashboards, component demos, data visualization with state.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard</title>
  <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/recharts@2.12.0/umd/Recharts.js"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            brand: { 500: '#6366f1', 600: '#4f46e5' }
          }
        }
      }
    }
  </script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
<div id="root"></div>

<script type="text/babel">
const { useState, useEffect, useCallback } = React
const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } = Recharts

const data = [
  { month: 'Jan', revenue: 4200, users: 1200 },
  { month: 'Feb', revenue: 5800, users: 1450 },
  { month: 'Mar', revenue: 5100, users: 1380 },
  { month: 'Apr', revenue: 7200, users: 1820 },
  { month: 'May', revenue: 6800, users: 1750 },
  { month: 'Jun', revenue: 9100, users: 2100 },
]

function MetricCard({ label, value, change }) {
  const isPositive = change >= 0
  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
      <div className="text-sm text-slate-400 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className={`text-sm mt-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
        {isPositive ? '↑' : '↓'} {Math.abs(change)}% vs last month
      </div>
    </div>
  )
}

function Dashboard() {
  const [activeMetric, setActiveMetric] = useState('revenue')

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Analytics Dashboard</h1>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <MetricCard label="Revenue" value="$9,100" change={33.8} />
        <MetricCard label="Active Users" value="2,100" change={20.0} />
        <MetricCard label="Conversion" value="3.4%" change={-0.2} />
      </div>

      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <div className="flex gap-4 mb-4">
          {['revenue', 'users'].map(metric => (
            <button
              key={metric}
              onClick={() => setActiveMetric(metric)}
              className={`px-3 py-1 rounded-full text-sm capitalize ${
                activeMetric === metric
                  ? 'bg-brand-500 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {metric}
            </button>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="month" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
            />
            <Line
              type="monotone"
              dataKey={activeMetric}
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ fill: '#6366f1' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<Dashboard />)
</script>
</body>
</html>
```

---

## Design Guidelines

### Palette Approach
- Dark theme: `#0f172a` background, `#1e293b` card, `#6366f1` accent
- Light theme: `#f8fafc` background, `#ffffff` card, `#6366f1` accent
- Pick one dominant color; use 60-30-10 rule (background: 60%, surface: 30%, accent: 10%)

### Typography
- Headings: `font-size: clamp(1.5rem, 4vw, 2.5rem)` — scales on mobile
- Body: 16px minimum; never below 14px for readable content
- Avoid default system fonts for anything beyond demos — use `Inter` or `Geist` via Google Fonts

### Layout Principles
- Use CSS Grid for page layout, Flexbox for component layout
- Always set `max-width` on content containers (800-1200px)
- Add meaningful micro-interactions: `transition: all 0.2s`, hover states, focus rings

### What to Avoid
- Purple gradients on white — too generic
- Centered body text on wide screens
- Missing loading/empty states
- No hover states on interactive elements
- Placeholder-only content (Lorem ipsum everywhere)

---

## Common Mistakes

- **CDN versions mismatched** — check exact version numbers for React, Recharts, etc.
- **Babel `type="text/babel"` missing** — JSX won't parse without it when using CDN Babel
- **No responsive design** — always add `meta viewport` and test at 375px width
- **Missing accessibility** — buttons need `type="button"`, form inputs need labels
- **Forgetting error states** — always handle empty data, loading, and error conditions visually
- **Inline CSS overriding Tailwind** — be consistent; pick one approach per project
