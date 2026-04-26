---
name: react-best-practices
description: >
  Apply React best practices — hooks patterns, state management, component composition, performance
  optimization, error boundaries, accessibility, and testing. Covers React 18+, Suspense, concurrent
  features, custom hooks, Context API, and TypeScript integration. Use when writing React components,
  reviewing React code, optimizing renders, or designing component architecture.
license: Apache-2.0
metadata:
  author: vercel-labs
  version: "1.0"
  tags: [react, hooks, typescript, performance, components, state-management, accessibility]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - write React component
    - React hooks
    - React best practices
    - useState useEffect
    - React performance
    - React TypeScript
    - component architecture
    - React Context
    - React Suspense
    - optimize React renders
    - React error boundary
    - custom hooks
---

# React Best Practices Skill

## 1. Component Design

### Keep Components Small and Focused
- One component = one concern
- If it exceeds ~100 lines, consider splitting
- Name components after what they **render**, not what they **do** (e.g., `UserCard` not `RenderUser`)

### TypeScript Component Signature
```tsx
// ✅ Preferred: explicit props interface
interface UserCardProps {
  user: User
  onSelect?: (id: string) => void
  className?: string
}

export function UserCard({ user, onSelect, className }: UserCardProps) {
  return (
    <div className={cn('card', className)} onClick={() => onSelect?.(user.id)}>
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </div>
  )
}
```

---

## 2. Hooks — Rules and Patterns

### Rules of Hooks (enforce with eslint-plugin-react-hooks)
- Only call hooks at the **top level** — never inside conditions, loops, or nested functions
- Only call hooks from **React function components** or custom hooks

### useState
```tsx
// Lazy initialization for expensive default values
const [count, setCount] = useState(() => computeExpensiveDefault())

// Functional update when new state depends on old state
setCount(prev => prev + 1)  // ✅ safe with concurrent rendering
setCount(count + 1)          // ❌ stale closure risk
```

### useEffect — Common Patterns
```tsx
// Fetch data on mount + when id changes
useEffect(() => {
  let cancelled = false

  async function loadUser() {
    const user = await fetchUser(id)
    if (!cancelled) setUser(user)  // prevent state update after unmount
  }

  loadUser()
  return () => { cancelled = true }
}, [id])

// Subscribe / unsubscribe
useEffect(() => {
  const subscription = eventBus.on('update', handleUpdate)
  return () => subscription.unsubscribe()  // always cleanup subscriptions
}, [])
```

**useEffect exhaustive deps rule:** include every reactive value used inside the effect in the dependency array. Use `useCallback`/`useMemo` to stabilize references.

### useCallback and useMemo — When to Use
```tsx
// ✅ DO memoize: callback passed to a child wrapped in React.memo
const handleSubmit = useCallback(async (data: FormData) => {
  await api.submit(data)
  onSuccess?.()
}, [onSuccess])

// ✅ DO memoize: expensive computation used in render
const sortedItems = useMemo(
  () => [...items].sort(compareByDate),
  [items]
)

// ❌ DON'T memoize cheap operations — the overhead exceeds savings
const label = useMemo(() => `Hello, ${name}`, [name])  // overkill
```

---

## 3. State Management

### Local State First
Start with `useState`. Lift state up only when siblings need it. Move to global state only when the data is genuinely shared across distant components.

### useReducer for Complex State
```tsx
type Action =
  | { type: 'increment' }
  | { type: 'decrement' }
  | { type: 'reset'; payload: number }

function counterReducer(state: number, action: Action): number {
  switch (action.type) {
    case 'increment': return state + 1
    case 'decrement': return state - 1
    case 'reset': return action.payload
    default: return state
  }
}

function Counter() {
  const [count, dispatch] = useReducer(counterReducer, 0)
  return (
    <>
      <span>{count}</span>
      <button onClick={() => dispatch({ type: 'increment' })}>+</button>
    </>
  )
}
```

### Context API — Use Sparingly
```tsx
// Good for: auth state, theme, locale — NOT high-frequency updates
interface ThemeContextValue {
  theme: 'light' | 'dark'
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const toggleTheme = useCallback(() => setTheme(t => t === 'light' ? 'dark' : 'light'), [])
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

---

## 4. Performance Optimization

### React.memo — Prevent Unnecessary Re-renders
```tsx
const UserCard = React.memo(function UserCard({ user, onSelect }: UserCardProps) {
  return <div onClick={() => onSelect(user.id)}>{user.name}</div>
})
// Re-renders only when user or onSelect references change
```

### Virtualize Long Lists
```bash
npm install @tanstack/react-virtual
```
```tsx
import { useVirtualizer } from '@tanstack/react-virtual'

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  })

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(vItem => (
          <div
            key={vItem.key}
            style={{ position: 'absolute', top: vItem.start, width: '100%' }}
          >
            {items[vItem.index].name}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Code Splitting
```tsx
const HeavyComponent = lazy(() => import('./HeavyComponent'))

function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyComponent />
    </Suspense>
  )
}
```

---

## 5. Custom Hooks

Extract stateful logic into custom hooks for reuse and testability:

```tsx
// hooks/useLocalStorage.ts
function useLocalStorage<T>(key: string, defaultValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch {
      return defaultValue
    }
  })

  const setStoredValue = useCallback((newValue: T | ((prev: T) => T)) => {
    setValue(prev => {
      const resolved = typeof newValue === 'function'
        ? (newValue as (prev: T) => T)(prev)
        : newValue
      try {
        window.localStorage.setItem(key, JSON.stringify(resolved))
      } catch {}
      return resolved
    })
  }, [key])

  return [value, setStoredValue] as const
}
```

---

## 6. Error Boundaries

```tsx
'use client'  // Next.js App Router: error.tsx must be a client component

class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Caught error:', error, info)
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children
  }
}

// Usage
<ErrorBoundary fallback={<div>Something went wrong. <button onClick={() => location.reload()}>Retry</button></div>}>
  <RiskyComponent />
</ErrorBoundary>
```

---

## 7. Accessibility (a11y)

```tsx
// ✅ Buttons with icon-only content need aria-label
<button aria-label="Close dialog" onClick={onClose}>
  <XIcon aria-hidden="true" />
</button>

// ✅ Form inputs need associated labels
<label htmlFor="email">Email</label>
<input id="email" type="email" name="email" />

// ✅ Live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

// ✅ Focus management after modal opens
useEffect(() => {
  if (isOpen) firstFocusableRef.current?.focus()
}, [isOpen])
```

---

## Common Mistakes

- **Missing `key` prop in lists** — always use stable, unique keys (not array index)
- **Stale closures in effects** — add all reactive values to dependency arrays
- **Calling hooks conditionally** — hooks must run on every render in the same order
- **Mutating state directly** — always create new objects/arrays; never `state.items.push(x)`
- **Overusing useContext for high-frequency updates** — context re-renders all consumers; use Zustand/Jotai for frequently changing global state
- **Forgetting cleanup in useEffect** — return a cleanup function for subscriptions, timers, and fetch cancellations
- **Using index as key in dynamic lists** — use item.id; index keys cause incorrect re-ordering
