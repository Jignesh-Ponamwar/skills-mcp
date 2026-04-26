---
name: cloudflare-workers
description: >
  Build and deploy applications on the Cloudflare developer platform. Covers Workers (serverless
  edge compute), Pages (full-stack web), Durable Objects (stateful coordination), KV (key-value
  storage), D1 (SQLite edge database), R2 (object storage), Workers AI (LLM inference), Vectorize
  (vector database), Queues, and Wrangler CLI. Use when building Cloudflare Workers, deploying to
  Cloudflare Pages, or integrating any Cloudflare storage, AI, or networking product.
license: Apache-2.0
metadata:
  author: cloudflare
  version: "1.0"
  tags: [cloudflare, workers, pages, durable-objects, kv, d1, r2, wrangler, edge, serverless]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - Cloudflare Workers
    - Cloudflare Pages
    - Durable Objects
    - Cloudflare KV
    - Cloudflare D1
    - Cloudflare R2
    - Workers AI
    - Vectorize
    - Wrangler deploy
    - deploy to Cloudflare
    - edge computing
    - Cloudflare Queues
---

# Cloudflare Workers Platform Skill

Consolidated skill for building on the Cloudflare platform. Biases toward retrieval from live Cloudflare docs over pre-trained knowledge — API signatures, limits, and pricing change frequently.

---

## Step 1: Choose the Right Product

### "I need to run code"
| Need | Product |
|------|---------|
| Serverless functions at the edge | Workers |
| Full-stack web app with Git deploys | Pages |
| Stateful coordination / real-time | Durable Objects |
| Long-running multi-step jobs | Workflows |
| Scheduled tasks | Cron Triggers |
| Lightweight request transformation | Snippets |

### "I need to store data"
| Need | Product |
|------|---------|
| Key-value (config, sessions, cache) | KV |
| Relational SQL | D1 (SQLite) |
| Object/file storage (S3-compatible) | R2 |
| Message queue | Queues |
| Vector embeddings (RAG/search) | Vectorize |
| Strongly-consistent per-entity state | Durable Objects |

### "I need AI/ML"
| Need | Product |
|------|---------|
| Run LLM inference | Workers AI |
| Vector database for RAG | Vectorize |
| Stateful AI agents | Agents SDK |
| AI provider gateway | AI Gateway |

### "I need networking/security"
| Need | Product |
|------|---------|
| Expose local service to internet | Tunnel |
| Web Application Firewall | WAF |
| CAPTCHA alternative | Turnstile |
| DDoS protection | DDoS Shield |

---

## Step 2: Workers Fundamentals

### Minimal Worker (TypeScript)
```typescript
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url)

    if (url.pathname === '/health') {
      return Response.json({ status: 'ok' })
    }

    return new Response('Hello, World!', { status: 200 })
  },
} satisfies ExportedHandler<Env>

interface Env {
  MY_KV: KVNamespace
  MY_DB: D1Database
  MY_BUCKET: R2Bucket
  SECRET_KEY: string
}
```

### `wrangler.toml` Configuration
```toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2025-04-10"
compatibility_flags = ["nodejs_compat"]

[[kv_namespaces]]
binding = "MY_KV"
id = "xxxxxxxxxxxxxxxx"

[[d1_databases]]
binding = "MY_DB"
database_name = "my-database"
database_id = "xxxxxxxxxxxxxxxx"

[[r2_buckets]]
binding = "MY_BUCKET"
bucket_name = "my-bucket"

[ai]
binding = "AI"
```

### Essential Wrangler Commands
```bash
npm create cloudflare@latest   # scaffold a new project
wrangler dev                   # local dev server (http://localhost:8787)
wrangler deploy                # deploy to production
wrangler tail                  # stream real-time logs
wrangler secret put SECRET_KEY # add encrypted secret
wrangler kv key put --binding MY_KV "key" "value"
```

---

## Step 3: KV Storage

```typescript
// Write
await env.MY_KV.put('user:123', JSON.stringify({ name: 'Alice' }), {
  expirationTtl: 3600  // seconds
})

// Read
const raw = await env.MY_KV.get('user:123')
const user = raw ? JSON.parse(raw) : null

// Delete
await env.MY_KV.delete('user:123')

// List keys
const { keys } = await env.MY_KV.list({ prefix: 'user:' })
```

**KV Characteristics:**
- Eventually consistent (changes propagate in ~60s globally)
- Read-optimized (millions of reads/s, ~1 write/s per key)
- Not suitable for high-frequency writes — use Durable Objects for that

---

## Step 4: D1 Database (SQL)

```typescript
// Query
const { results } = await env.MY_DB.prepare(
  'SELECT * FROM users WHERE email = ?'
).bind('alice@example.com').all()

// Insert
await env.MY_DB.prepare(
  'INSERT INTO users (name, email) VALUES (?, ?)'
).bind('Alice', 'alice@example.com').run()

// Batch operations
await env.MY_DB.batch([
  env.MY_DB.prepare('UPDATE users SET active = 1 WHERE id = ?').bind(1),
  env.MY_DB.prepare('INSERT INTO logs (action) VALUES (?)').bind('activated'),
])
```

**Schema migrations** — use `wrangler d1 migrations`:
```bash
wrangler d1 migrations create my-database add-users-table
wrangler d1 migrations apply my-database --local   # local
wrangler d1 migrations apply my-database           # production
```

---

## Step 5: R2 Object Storage

```typescript
// Upload
await env.MY_BUCKET.put('files/photo.jpg', request.body, {
  httpMetadata: { contentType: 'image/jpeg' },
})

// Download
const object = await env.MY_BUCKET.get('files/photo.jpg')
if (!object) return new Response('Not Found', { status: 404 })
return new Response(object.body, {
  headers: { 'Content-Type': object.httpMetadata?.contentType ?? 'application/octet-stream' },
})

// Delete
await env.MY_BUCKET.delete('files/photo.jpg')

// List objects
const listed = await env.MY_BUCKET.list({ prefix: 'files/', limit: 100 })
```

---

## Step 6: Workers AI

```typescript
// Text generation
const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'Explain DNS in one paragraph.' },
  ],
})
return Response.json({ text: response.response })

// Embeddings
const embeds = await env.AI.run('@cf/baai/bge-small-en-v1.5', {
  text: ['Hello world', 'Goodbye world'],
})
// embeds.data is an array of float arrays

// Image classification
const result = await env.AI.run('@cf/microsoft/resnet-50', {
  image: [...new Uint8Array(await request.arrayBuffer())],
})
```

**Available models:** check `https://developers.cloudflare.com/workers-ai/models/`

---

## Step 7: Durable Objects

```typescript
// src/counter.ts — the Durable Object class
export class Counter implements DurableObject {
  state: DurableObjectState
  value: number = 0

  constructor(state: DurableObjectState, env: Env) {
    this.state = state
    this.state.blockConcurrencyWhile(async () => {
      this.value = (await this.state.storage.get<number>('value')) ?? 0
    })
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)
    if (url.pathname === '/increment') {
      this.value++
      await this.state.storage.put('value', this.value)
    }
    return Response.json({ value: this.value })
  }
}

// src/index.ts — Worker that uses it
export default {
  async fetch(request: Request, env: Env) {
    const id = env.COUNTER.idFromName('global')
    const stub = env.COUNTER.get(id)
    return stub.fetch(request)
  },
}

interface Env {
  COUNTER: DurableObjectNamespace
}
```

`wrangler.toml`:
```toml
[[durable_objects.bindings]]
name = "COUNTER"
class_name = "Counter"

[[migrations]]
tag = "v1"
new_classes = ["Counter"]
```

---

## Step 8: Queues (Background Processing)

```typescript
// Producer — enqueue from a Worker
await env.MY_QUEUE.send({ userId: 123, action: 'send-welcome-email' })

// Consumer — process messages
export default {
  async queue(batch: MessageBatch<{ userId: number; action: string }>, env: Env) {
    for (const msg of batch.messages) {
      await processMessage(msg.body)
      msg.ack()  // acknowledge on success
    }
  },
} satisfies ExportedHandler<Env>
```

---

## Step 9: Cloudflare Pages

Deploy full-stack apps with Git integration:
```bash
npm create cloudflare@latest my-app -- --framework=next
cd my-app
wrangler pages deploy .next   # or use the dashboard for Git integration
```

Pages Functions (serverless backend):
```typescript
// functions/api/user.ts
export async function onRequest(ctx: EventContext<Env, '/api/user', {}>) {
  return Response.json({ user: 'Alice' })
}
```

---

## Common Mistakes

- **Accessing live Cloudflare docs for exact limits** — free/paid tier limits change; check `https://developers.cloudflare.com/`
- **Using KV for high-write workloads** — KV is eventually consistent and write-limited; use Durable Objects instead
- **Missing `compatibility_date`** — always set to a recent date to get latest APIs
- **Blocking the event loop** — Workers are single-threaded; avoid CPU-heavy synchronous work
- **Storing secrets in `wrangler.toml`** — use `wrangler secret put` for sensitive values
- **Using `nodejs` APIs without `nodejs_compat` flag** — add `compatibility_flags = ["nodejs_compat"]` in `wrangler.toml`
