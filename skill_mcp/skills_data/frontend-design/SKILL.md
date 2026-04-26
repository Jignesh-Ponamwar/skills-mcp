---
name: frontend-design
description: >
  Design and implement distinctive, production-grade web interfaces that avoid generic AI aesthetics.
  Covers establishing an aesthetic direction, typography selection, color system design, layout
  composition, micro-animations, responsive design, and design-to-code workflow. Use when designing
  a website, landing page, dashboard, or UI component from scratch, or when existing UI feels generic
  and needs a distinctive visual identity.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [design, ui-ux, css, tailwind, typography, color, animation, responsive, landing-page]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - design a website
    - create a landing page
    - improve UI design
    - make it look better
    - design a dashboard
    - web design best practices
    - distinctive UI
    - design a component
    - UI looks generic
    - design a hero section
    - create a beautiful interface
    - frontend design
---

# Frontend Design Skill

## Step 1: Establish Aesthetic Direction Before Writing Code

Before touching a line of CSS, decide:

1. **Purpose** — What is this interface for? Who uses it? What emotion should it evoke?
2. **Tone** — Serious/clinical? Playful/energetic? Minimal/confident? Bold/expressive?
3. **Differentiator** — What one thing will make this memorable? (Unusual typography? Unexpected layout? Strong color contrast?)
4. **Constraint** — What can you NOT use? (Overused styles to avoid)

**Choose an extreme and execute with intentionality.** Mediocre design lives in the middle. Either go brutally minimal or richly layered — both work; the generic middle does not.

---

## Step 2: Typography (The Most Impactful Decision)

### Font Pairing Formula
- **Display/Heading:** Distinctive, character-rich (serif, slab, condensed, or geometric sans)
- **Body:** Highly legible neutral (Inter, Geist, Outfit, DM Sans)

### Pairings that Work
| Heading | Body | Mood |
|---------|------|------|
| Playfair Display | Inter | Editorial, premium |
| Space Grotesk | DM Sans | Tech, modern |
| Syne | Outfit | Bold, design-forward |
| Fraunces | Source Serif | Literary, warm |
| Cabinet Grotesk | Inter | Startup, clean |

### Font Scale (Never Use Default Browser Sizes)
```css
:root {
  --text-xs:   0.75rem;   /* 12px — captions */
  --text-sm:   0.875rem;  /* 14px — secondary text */
  --text-base: 1rem;      /* 16px — body */
  --text-lg:   1.125rem;  /* 18px — lead text */
  --text-xl:   1.25rem;   /* 20px — small headings */
  --text-2xl:  1.5rem;    /* 24px */
  --text-3xl:  1.875rem;  /* 30px */
  --text-4xl:  2.25rem;   /* 36px */
  --text-5xl:  3rem;      /* 48px */
  --text-6xl:  clamp(3rem, 8vw, 5rem); /* Responsive hero */
}
```

### Typography Rules
- Heading line-height: 1.1–1.2
- Body line-height: 1.6–1.8
- Max line length: 65–75 characters (add `max-width: 65ch` to body text)
- Never: all-caps body text, three different font weights at the same size, Arial/Times New Roman

---

## Step 3: Color System

### 4-Layer System
```css
:root {
  /* Base — backgrounds, surfaces */
  --color-bg:       #09090b;   /* dark: near-black */
  --color-surface:  #18181b;   /* dark: card background */
  --color-border:   #27272a;   /* subtle borders */

  /* Content — text */
  --color-text:     #fafafa;   /* primary text */
  --color-muted:    #a1a1aa;   /* secondary text, labels */

  /* Accent — one dominant brand color */
  --color-accent:   #8b5cf6;   /* violet */
  --color-accent-h: #7c3aed;   /* hover state */
  --color-accent-l: #8b5cf620; /* 12% opacity for backgrounds */

  /* Semantic */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error:   #ef4444;
}
```

### Color Rules
- **60-30-10 rule:** 60% background/neutral, 30% surface/secondary, 10% accent
- One primary accent color — never two competing brand colors at equal weight
- Use opacity variants instead of additional colors: `hsl(262 80% 60% / 0.15)`
- Dark mode default is increasingly expected — design it from the start

### Avoid
- Purple gradients on white backgrounds
- Rainbow color palettes with no hierarchy
- Low-contrast text (WCAG AA: ≥4.5:1 for body, ≥3:1 for large text)
- Pure black (`#000000`) on pure white — use `#09090b` and `#fafafa`

---

## Step 4: Layout and Composition

### Spatial Rhythm
Use a consistent spacing scale based on 4px or 8px:
```css
:root {
  --space-1:  0.25rem;  /* 4px */
  --space-2:  0.5rem;   /* 8px */
  --space-3:  0.75rem;  /* 12px */
  --space-4:  1rem;     /* 16px */
  --space-6:  1.5rem;   /* 24px */
  --space-8:  2rem;     /* 32px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-24: 6rem;     /* 96px */
}
```

### Breaking the Grid (Strategic)
Generic designs stay strictly on-grid. Distinctive designs intentionally break it:
```css
/* Offset element creates tension and visual interest */
.hero-image {
  position: absolute;
  right: -4rem;          /* intentionally overflows */
  top: -2rem;
  transform: rotate(3deg);
}

/* Overlapping elements create depth */
.card-badge {
  position: absolute;
  top: -0.75rem;
  left: 1.5rem;
}
```

### Responsive Strategy
Mobile-first, always:
```css
/* Mobile base */
.container {
  padding: 1rem;
  max-width: 100%;
}

/* Tablet */
@media (min-width: 768px) {
  .container { padding: 2rem; }
}

/* Desktop */
@media (min-width: 1280px) {
  .container {
    max-width: 1200px;
    margin: 0 auto;
  }
}
```

---

## Step 5: Micro-Animations

**Animate for meaning, not decoration.** Every animation should communicate something.

```css
/* Entrance — elements appear with purpose */
@keyframes slide-up {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

.card { animation: slide-up 0.3s ease-out; }

/* Interactive feedback — confirm the user's action */
button {
  transition: transform 0.1s ease, box-shadow 0.2s ease;
}
button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
button:active { transform: translateY(0); box-shadow: none; }

/* Loading state — communicates progress */
.skeleton {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**Rules:**
- Duration: 150-300ms for interactions, 300-500ms for page transitions
- Easing: `ease-out` for entrances (fast start, slow end), `ease-in` for exits
- Never animate more than 3 things simultaneously
- Respect `prefers-reduced-motion`:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; }
  }
  ```

---

## Step 6: Production-Grade Component Example

```html
<!-- Hero section: minimal, typographic, with strong vertical rhythm -->
<section class="hero">
  <span class="eyebrow">Introducing v2.0</span>
  <h1 class="headline">Design that<br><em>speaks</em> for itself.</h1>
  <p class="subheading">Build interfaces that users remember — and come back to.</p>
  <div class="cta-group">
    <a href="#" class="btn btn-primary">Get started free</a>
    <a href="#" class="btn btn-ghost">See examples →</a>
  </div>
</section>

<style>
.hero {
  max-width: 800px;
  margin: 0 auto;
  padding: clamp(4rem, 10vw, 8rem) 2rem;
}

.eyebrow {
  display: inline-block;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-accent);
  border: 1px solid var(--color-accent-l);
  background: var(--color-accent-l);
  padding: 0.25rem 0.75rem;
  border-radius: 2rem;
  margin-bottom: 1.5rem;
}

.headline {
  font-family: 'Playfair Display', serif;
  font-size: clamp(2.5rem, 7vw, 5rem);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--color-text);
  margin-bottom: 1.5rem;
}

.headline em {
  font-style: italic;
  color: var(--color-accent);
}

.subheading {
  font-size: clamp(1.1rem, 2.5vw, 1.35rem);
  color: var(--color-muted);
  line-height: 1.7;
  max-width: 540px;
  margin-bottom: 2.5rem;
}

.cta-group { display: flex; gap: 1rem; flex-wrap: wrap; }

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 1rem;
  text-decoration: none;
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-primary {
  background: var(--color-accent);
  color: white;
}
.btn-primary:hover {
  background: var(--color-accent-h);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px var(--color-accent-l);
}

.btn-ghost {
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.btn-ghost:hover {
  border-color: var(--color-muted);
  background: var(--color-surface);
}
</style>
```

---

## Design Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Purple gradient on white | Overused, signals "AI-generated" | Choose an unusual color or texture |
| Centered body text on wide screens | Hard to read, looks amateur | Left-align body; center only short headings |
| Three different sans-serif fonts | Visual noise, no hierarchy | Max two font families |
| Blue/gray corporate palette | Forgettable, interchangeable | Pick a distinctive accent hue |
| Equal visual weight everywhere | No focus, no hierarchy | Create 3-4 clear visual tiers |
| Thin gray text on white | Low contrast, inaccessible | Test with WebAIM contrast checker |
| Rounded everything uniformly | Looks like a Bootstrap template | Mix border-radius values deliberately |
