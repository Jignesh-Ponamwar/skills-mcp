---
name: nextjs-best-practices
description: >
  Apply Next.js App Router best practices — file conventions, React Server Components, async APIs
  (Next.js 15+), data fetching patterns, metadata, image/font optimization, error handling, route
  handlers, bundling, and self-hosting. Use when writing or reviewing Next.js code, building
  full-stack React apps, or migrating from the Pages Router.
license: Apache-2.0
metadata:
  author: vercel-labs
  version: "1.0"
  tags: [nextjs, react, app-router, server-components, typescript, vercel, full-stack]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - write Next.js code
    - Next.js App Router
    - React Server Components
    - Next.js best practices
    - next/image
    - next/font
    - Server Actions
    - Route Handlers
    - Next.js data fetching
    - Next.js 15 async params
    - build a Next.js app
    - migrate to App Router
---

# Next.js Best Practices Skill

Apply these rules when writing or reviewing Next.js code. Covers App Router (Next.js 13+).

---

## 1. File Conventions

### Project Structure
```
app/
├── layout.tsx           # Root layout (required)
├── page.tsx             # Home page
├── loading.tsx          # Loading UI (Suspense boundary)
├── error.tsx            # Error boundary
├── not-found.tsx        # 404 page
├── global-error.tsx     # Root-level error boundary
├── (auth)/              # Route group (no URL segment)
│   ├── login/page.tsx
│   └── register/page.tsx
├── [id]/                # Dynamic segment
│   └── page.tsx
├── [...slug]/           # Catch-all segment
└── api/
    └── route.ts         # Route Handler
```

### Special Files
| File | Purpose |
|------|---------|
| `layout.tsx` | Shared UI, persists across navigations |
| `page.tsx` | Unique page UI, makes route publicly accessible |
| `loading.tsx` | Auto-wraps page in `<Suspense>` |
| `error.tsx` | Error boundary for segment (client component) |
| `not-found.tsx` | Rendered when `notFound()` is thrown |
| `route.ts` | API endpoint (no co-located `page.tsx` allowed) |
| `middleware.ts` | Runs before request, at edge |

---

## 2. React Server Components (RSC) Boundaries

### Server Components (default) — do:
- `async/await` data fetching directly in component
- Access databases, file system, environment variables
- Import server-only packages

### Client Components (`'use client'`) — required when:
- Using `useState`, `useEffect`, `useReducer`, `useContext`
- Using browser APIs (`window`, `document`, `localStorage`)
- Using event handlers (`onClick`, `onChange`)
- Using third-party client libraries

### Rules
- **Never** make a Client Component `async` — it's invalid
- **Never** pass non-serializable props (functions, class instances) from Server → Client
- Server Components can import Client Components, not the reverse
- Use `'use server'` only for Server Actions, not to mark Server Components

---

## 3. Async APIs — Next.js 15+

In Next.js 15, `params`, `searchParams`, `cookies()`, `headers()`, and `draftMode()` are now **async**. Always await them:

```tsx
// ✅ Correct — Next.js 15+
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ q: string }>
}) {
  const { id } = await params
  const { q } = await searchParams
  const cookieStore = await cookies()
  const token = cookieStore.get('token')
  // ...
}
```

```tsx
// ❌ Wrong — old synchronous pattern
export default function Page({ params }: { params: { id: string } }) {
  const { id } = params  // broken in Next.js 15
}
```

---

## 4. Data Fetching Patterns

### Server Components — preferred for most fetching
```tsx
async function ProductList() {
  const products = await db.products.findMany() // Direct DB access, no API needed
  return <ul>{products.map(p => <li key={p.id}>{p.name}</li>)}</ul>
}
```

### Avoid waterfalls — use `Promise.all`
```tsx
// ❌ Sequential waterfall — slow
const user = await getUser(id)
const posts = await getPosts(user.id)

// ✅ Parallel — fast
const [user, posts] = await Promise.all([getUser(id), getPosts(id)])
```

### Server Actions — for mutations
```tsx
// app/actions.ts
'use server'

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string
  await db.posts.create({ data: { title } })
  revalidatePath('/posts')
}

// app/page.tsx
import { createPost } from './actions'

export default function Page() {
  return (
    <form action={createPost}>
      <input name="title" />
      <button type="submit">Create</button>
    </form>
  )
}
```

### Route Handlers — for API endpoints needed by external clients
```ts
// app/api/products/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const products = await db.products.findMany()
  return NextResponse.json(products)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const product = await db.products.create({ data: body })
  return NextResponse.json(product, { status: 201 })
}
```

---

## 5. Image Optimization

**Always** use `next/image` instead of `<img>`:
```tsx
import Image from 'next/image'

// Local image — size known automatically
import photo from './photo.jpg'
<Image src={photo} alt="Description" />

// Remote image — must configure domain in next.config.ts
<Image
  src="https://example.com/photo.jpg"
  alt="Description"
  width={800}
  height={600}
  sizes="(max-width: 768px) 100vw, 50vw"
  priority  // Add for LCP images above the fold
/>
```

Configure remote domains:
```ts
// next.config.ts
const config: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'example.com' },
    ],
  },
}
```

---

## 6. Font Optimization

**Always** use `next/font` instead of `<link>` tags — it prevents layout shift and self-hosts fonts:
```tsx
// app/layout.tsx
import { Inter, Roboto_Mono } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
})

export default function RootLayout({ children }) {
  return (
    <html className={`${inter.variable}`}>
      <body>{children}</body>
    </html>
  )
}
```

---

## 7. Error Handling

```tsx
// app/error.tsx — must be a Client Component
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```

Trigger programmatically:
```tsx
import { notFound, redirect } from 'next/navigation'

// In any Server Component or Server Action:
if (!user) notFound()                          // renders not-found.tsx
if (!session) redirect('/login')               // HTTP 307 redirect
```

---

## 8. Metadata

```tsx
// app/layout.tsx — static
export const metadata = {
  title: { template: '%s | My App', default: 'My App' },
  description: 'My application description',
}

// app/products/[id]/page.tsx — dynamic
export async function generateMetadata({ params }) {
  const { id } = await params
  const product = await getProduct(id)
  return {
    title: product.name,
    openGraph: { images: [product.imageUrl] },
  }
}
```

---

## 9. Suspense Boundaries

Wrap anything that uses `useSearchParams()` or `usePathname()` in a Client Component with `<Suspense>` to avoid CSR bailout:

```tsx
import { Suspense } from 'react'
import SearchBar from './SearchBar'  // contains useSearchParams

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SearchBar />
    </Suspense>
  )
}
```

---

## 10. Self-Hosting with Docker

```ts
// next.config.ts
const config: NextConfig = {
  output: 'standalone',
}
```

```dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static
COPY --from=base /app/public ./public
CMD ["node", "server.js"]
```

---

## Common Mistakes

- Async Client Components — **invalid**, move `async` to a parent Server Component
- `params` access without `await` in Next.js 15+ — add `await params`
- `<img>` instead of `next/image` — always use `next/image` for optimization
- `<link>` tags for fonts — always use `next/font`
- Fetching in Client Components when a Server Component would work — default to Server
- Route Handler + `page.tsx` in the same folder — causes a conflict, use different paths
- `export const dynamic = 'force-dynamic'` everywhere — use it only when truly needed
