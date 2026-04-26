---
name: supabase-integration
description: >
  Integrate Supabase into applications — PostgreSQL database queries, Row Level Security (RLS)
  policies, authentication (email/password, OAuth, magic link), real-time subscriptions, storage
  (file uploads), and Edge Functions. Covers the Supabase JavaScript/TypeScript SDK, Python client,
  type-safe queries with generated types, and local development with the Supabase CLI. Use when
  building with Supabase, setting up auth, writing RLS policies, querying a Supabase database, or
  managing file storage.
license: Apache-2.0
metadata:
  author: supabase
  version: "1.0"
  tags: [supabase, postgresql, auth, rls, realtime, storage, edge-functions, typescript]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - Supabase database
    - Supabase auth
    - Row Level Security
    - RLS policy
    - Supabase client
    - Supabase real-time
    - Supabase storage
    - Supabase Edge Functions
    - query Supabase
    - Supabase OAuth
    - set up Supabase
---

# Supabase Integration Skill

## Step 1: Setup

```bash
npm install @supabase/supabase-js

# Local development
npm install -g supabase
supabase init
supabase start  # starts local Postgres + Auth + Storage
```

### Initialize Client
```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'
import type { Database } from './database.types'  // generated types

export const supabase = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Server-side client (Next.js App Router)
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createServerSupabase() {
  const cookieStore = await cookies()
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

### Generate Types
```bash
supabase gen types typescript --local > lib/database.types.ts
# Or for remote:
supabase gen types typescript --project-id <project-id> > lib/database.types.ts
```

---

## Step 2: Database Queries

```typescript
// SELECT with filter
const { data: users, error } = await supabase
  .from('users')
  .select('id, name, email, created_at')
  .eq('active', true)
  .order('created_at', { ascending: false })
  .limit(20)

if (error) throw error

// SELECT with related data (join)
const { data: posts } = await supabase
  .from('posts')
  .select(`
    id,
    title,
    content,
    created_at,
    author:users (id, name, avatar_url),
    comments (id, body, user_id)
  `)
  .eq('published', true)

// INSERT
const { data: newPost, error } = await supabase
  .from('posts')
  .insert({
    title: 'Hello World',
    content: 'My first post',
    author_id: userId,
  })
  .select()
  .single()

// UPDATE
const { error } = await supabase
  .from('posts')
  .update({ title: 'Updated Title' })
  .eq('id', postId)
  .eq('author_id', userId)  // extra safety — only update own posts

// UPSERT
const { data } = await supabase
  .from('user_settings')
  .upsert({ user_id: userId, theme: 'dark' }, { onConflict: 'user_id' })
  .select()

// DELETE
await supabase.from('posts').delete().eq('id', postId)

// Raw SQL (complex queries)
const { data } = await supabase.rpc('get_popular_posts', { limit_count: 10 })
```

---

## Step 3: Authentication

### Email/Password
```typescript
// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123',
  options: {
    data: { full_name: 'Alice Smith' }  // stored in user_metadata
  }
})

// Sign in
const { data: { session }, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123',
})

// Sign out
await supabase.auth.signOut()

// Get current user
const { data: { user } } = await supabase.auth.getUser()
```

### OAuth (Google, GitHub, etc.)
```typescript
await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: `${window.location.origin}/auth/callback`,
    scopes: 'email profile',
  },
})
```

### Magic Link
```typescript
await supabase.auth.signInWithOtp({
  email: 'user@example.com',
  options: { emailRedirectTo: `${window.location.origin}/auth/callback` }
})
```

### Auth Callback (Next.js)
```typescript
// app/auth/callback/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabase } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')

  if (code) {
    const supabase = await createServerSupabase()
    await supabase.auth.exchangeCodeForSession(code)
  }

  return NextResponse.redirect(new URL('/dashboard', request.url))
}
```

### Listen to Auth Changes
```typescript
const { data: { subscription } } = supabase.auth.onAuthStateChange(
  (event, session) => {
    if (event === 'SIGNED_IN') router.push('/dashboard')
    if (event === 'SIGNED_OUT') router.push('/login')
  }
)

// Cleanup
return () => subscription.unsubscribe()
```

---

## Step 4: Row Level Security (RLS)

**Always enable RLS on every table.** Without it, all data is publicly accessible.

```sql
-- Enable RLS
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- Users can only read their own data
CREATE POLICY "Users can read own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = user_id);

-- Users can read published posts (public read)
CREATE POLICY "Anyone can read published posts"
  ON posts FOR SELECT
  USING (published = true);

-- Users can only insert their own posts
CREATE POLICY "Users can create own posts"
  ON posts FOR INSERT
  WITH CHECK (auth.uid() = author_id);

-- Users can only update their own posts
CREATE POLICY "Users can update own posts"
  ON posts FOR UPDATE
  USING (auth.uid() = author_id)
  WITH CHECK (auth.uid() = author_id);

-- Service role bypasses RLS (use for admin/backend)
-- Use SUPABASE_SERVICE_ROLE_KEY (not anon key) for admin operations
```

---

## Step 5: Real-Time Subscriptions

```typescript
// Subscribe to table changes
const channel = supabase
  .channel('messages')
  .on(
    'postgres_changes',
    {
      event: '*',          // INSERT | UPDATE | DELETE | *
      schema: 'public',
      table: 'messages',
      filter: `room_id=eq.${roomId}`,
    },
    (payload) => {
      if (payload.eventType === 'INSERT') {
        setMessages(prev => [...prev, payload.new as Message])
      }
      if (payload.eventType === 'DELETE') {
        setMessages(prev => prev.filter(m => m.id !== payload.old.id))
      }
    }
  )
  .subscribe()

// Cleanup
return () => { supabase.removeChannel(channel) }
```

---

## Step 6: Storage (File Uploads)

```typescript
// Upload file
const { data, error } = await supabase.storage
  .from('avatars')
  .upload(`${userId}/avatar.jpg`, file, {
    cacheControl: '3600',
    upsert: true,
    contentType: 'image/jpeg',
  })

// Get public URL
const { data: { publicUrl } } = supabase.storage
  .from('avatars')
  .getPublicUrl(`${userId}/avatar.jpg`)

// Download
const { data: blob } = await supabase.storage
  .from('documents')
  .download('report.pdf')

// Delete
await supabase.storage.from('avatars').remove([`${userId}/avatar.jpg`])
```

**Storage RLS policy:**
```sql
-- Users can manage their own avatar
CREATE POLICY "Users can upload own avatar"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'avatars' AND auth.uid()::text = (storage.foldername(name))[1]);
```

---

## Step 7: Edge Functions

```typescript
// supabase/functions/send-email/index.ts
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'

serve(async (req) => {
  const { to, subject, body } = await req.json()

  // Call external service (Resend, SendGrid, etc.)
  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${Deno.env.get('RESEND_API_KEY')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ from: 'noreply@myapp.com', to, subject, html: body }),
  })

  return new Response(JSON.stringify({ sent: response.ok }), {
    headers: { 'Content-Type': 'application/json' },
  })
})
```

```bash
supabase functions deploy send-email
supabase secrets set RESEND_API_KEY=re_xxxxx
```

---

## Common Mistakes

- **Not enabling RLS** — all unauthenticated users get full read access without RLS
- **Using service role key client-side** — `SUPABASE_SERVICE_ROLE_KEY` bypasses RLS; never expose it in the browser
- **Not handling errors** — always destructure `{ data, error }` and check `error`
- **Forgetting to generate types** — run `supabase gen types` after every schema change
- **Real-time without cleanup** — always call `supabase.removeChannel()` on component unmount
- **Storing sensitive data in `user_metadata`** — it's accessible client-side; use separate `profiles` table with RLS for private fields
