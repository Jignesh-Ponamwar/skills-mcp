---
name: graphql-api
description: >
  Design and implement GraphQL APIs — schema definition, resolvers, mutations, subscriptions,
  authentication, DataLoader for N+1 prevention, pagination (cursor and offset), error handling,
  and testing. Covers both server-side (GraphQL Yoga, Apollo Server, Strawberry for Python) and
  client-side (Apollo Client, urql, TanStack Query). Use when building a GraphQL API, adding
  GraphQL to an existing service, writing GraphQL queries/mutations/subscriptions, or optimizing
  GraphQL performance.
license: Apache-2.0
metadata:
  author: community
  version: "1.0"
  tags: [graphql, api, schema, resolvers, apollo, dataloader, subscriptions, typescript]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - build a GraphQL API
    - GraphQL schema
    - GraphQL resolver
    - GraphQL mutation
    - GraphQL subscription
    - Apollo Server
    - Strawberry GraphQL
    - GraphQL query
    - DataLoader N+1
    - GraphQL pagination
    - GraphQL authentication
    - GraphQL client
---

# GraphQL API Skill

## Step 1: Choose Your Stack

| Use Case | Recommendation |
|----------|---------------|
| TypeScript server | **GraphQL Yoga** + `graphql` |
| Python server | **Strawberry** (code-first) |
| React client | **Apollo Client** or **urql** |
| Next.js API | **GraphQL Yoga** in Route Handler |
| Schema-first TypeScript | **GraphQL Code Generator** |

---

## Step 2: Schema Design Principles

```graphql
# ✅ Good schema design
type User {
  id: ID!
  name: String!
  email: String!
  posts(first: Int = 10, after: String): PostConnection!
  createdAt: DateTime!
}

type Post {
  id: ID!
  title: String!
  content: String!
  author: User!
  publishedAt: DateTime
  status: PostStatus!
}

enum PostStatus {
  DRAFT
  PUBLISHED
  ARCHIVED
}

# Relay-style cursor pagination (preferred for large datasets)
type PostConnection {
  edges: [PostEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type PostEdge {
  node: Post!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

# Input types for mutations (keep separate from output types)
input CreatePostInput {
  title: String!
  content: String!
}

input UpdatePostInput {
  id: ID!
  title: String
  content: String
}

# Mutation return types — always return the mutated object
type CreatePostPayload {
  post: Post
  errors: [UserError!]!
}

type UserError {
  field: String
  message: String!
}

type Query {
  me: User
  user(id: ID!): User
  post(id: ID!): Post
  posts(first: Int, after: String, status: PostStatus): PostConnection!
}

type Mutation {
  createPost(input: CreatePostInput!): CreatePostPayload!
  updatePost(input: UpdatePostInput!): CreatePostPayload!
  deletePost(id: ID!): Boolean!
}

type Subscription {
  postCreated: Post!
  postUpdated(id: ID!): Post!
}
```

---

## Step 3: Server Setup (TypeScript + GraphQL Yoga)

```bash
npm install graphql graphql-yoga
```

```typescript
// app/api/graphql/route.ts (Next.js App Router)
import { createYoga, createSchema } from 'graphql-yoga'
import { typeDefs } from './schema'
import { resolvers } from './resolvers'
import { createContext } from './context'

const yoga = createYoga({
  schema: createSchema({ typeDefs, resolvers }),
  context: createContext,
  graphqlEndpoint: '/api/graphql',
  fetchAPI: { Response, Request, ReadableStream },
})

export { yoga as GET, yoga as POST }

// context.ts
import { NextRequest } from 'next/server'

export async function createContext({ request }: { request: NextRequest }) {
  const token = request.headers.get('authorization')?.replace('Bearer ', '')
  const user = token ? await verifyToken(token) : null
  return { user, db }
}
```

---

## Step 4: Resolvers

```typescript
// resolvers.ts
import { Resolvers } from './generated/types'

export const resolvers: Resolvers = {
  Query: {
    me: (_, __, { user }) => {
      if (!user) throw new GraphQLError('Not authenticated', {
        extensions: { code: 'UNAUTHENTICATED' }
      })
      return user
    },

    user: async (_, { id }, { db }) => {
      return db.users.findUnique({ where: { id } })
    },

    posts: async (_, { first = 10, after, status }, { db }) => {
      const cursor = after ? Buffer.from(after, 'base64').toString() : undefined
      const posts = await db.posts.findMany({
        take: first + 1,  // fetch one extra to determine hasNextPage
        cursor: cursor ? { id: cursor } : undefined,
        skip: cursor ? 1 : 0,
        where: status ? { status } : undefined,
        orderBy: { createdAt: 'desc' },
      })

      const hasNextPage = posts.length > first
      const edges = posts.slice(0, first).map(post => ({
        node: post,
        cursor: Buffer.from(post.id).toString('base64'),
      }))

      return {
        edges,
        pageInfo: {
          hasNextPage,
          hasPreviousPage: !!after,
          startCursor: edges[0]?.cursor,
          endCursor: edges[edges.length - 1]?.cursor,
        },
        totalCount: await db.posts.count(),
      }
    },
  },

  Mutation: {
    createPost: async (_, { input }, { user, db }) => {
      if (!user) return { post: null, errors: [{ message: 'Not authenticated' }] }

      try {
        const post = await db.posts.create({
          data: { ...input, authorId: user.id, status: 'DRAFT' }
        })
        return { post, errors: [] }
      } catch (err) {
        return { post: null, errors: [{ field: 'general', message: String(err) }] }
      }
    },
  },

  // Field resolvers for relationships
  User: {
    posts: async (user, { first = 10, after }, { loaders }) => {
      // Use DataLoader to prevent N+1
      return loaders.postsByUserId.load({ userId: user.id, first, after })
    },
  },

  Post: {
    author: async (post, _, { loaders }) => {
      return loaders.userById.load(post.authorId)
    },
  },

  Subscription: {
    postCreated: {
      subscribe: (_, __, { pubsub }) => pubsub.subscribe('POST_CREATED'),
    },
  },
}
```

---

## Step 5: DataLoader (Prevent N+1)

The N+1 problem: fetching 10 posts then making 10 separate DB calls for each author.

```typescript
// loaders.ts
import DataLoader from 'dataloader'
import { db } from './database'

// Batch: one DB call fetches all requested users
export function createUserLoader() {
  return new DataLoader<string, User | null>(async (userIds) => {
    const users = await db.users.findMany({
      where: { id: { in: [...userIds] } }
    })
    const byId = new Map(users.map(u => [u.id, u]))
    return userIds.map(id => byId.get(id) ?? null)
  })
}

// Add to context so loaders are per-request (not shared globally)
export function createLoaders() {
  return {
    userById: createUserLoader(),
    // Add more loaders here
  }
}

// context.ts
export function createContext({ request }) {
  return {
    user: ...,
    db,
    loaders: createLoaders(),  // fresh per request
  }
}
```

```bash
npm install dataloader
```

---

## Step 6: Authentication Pattern

```typescript
// Helper: protect resolvers
function requireAuth<T>(
  resolver: (parent: unknown, args: T, context: Context) => unknown
) {
  return (parent: unknown, args: T, context: Context) => {
    if (!context.user) {
      throw new GraphQLError('Authentication required', {
        extensions: { code: 'UNAUTHENTICATED', http: { status: 401 } }
      })
    }
    return resolver(parent, args, context)
  }
}

// Usage
const resolvers = {
  Mutation: {
    createPost: requireAuth(async (_, { input }, { user, db }) => {
      return db.posts.create({ data: { ...input, authorId: user.id } })
    }),
  },
}
```

---

## Step 7: Python Server (Strawberry)

```python
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import Optional

@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str

@strawberry.type
class Post:
    id: strawberry.ID
    title: str
    author_id: strawberry.ID

    @strawberry.field
    async def author(self, info: strawberry.types.Info) -> User:
        return await info.context.loaders.user_by_id.load(self.author_id)

@strawberry.input
class CreatePostInput:
    title: str
    content: str

@strawberry.type
class Query:
    @strawberry.field
    async def me(self, info: strawberry.types.Info) -> Optional[User]:
        return info.context.user

    @strawberry.field
    async def post(self, id: strawberry.ID, info: strawberry.types.Info) -> Optional[Post]:
        return await info.context.db.get_post(id)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_post(self, input: CreatePostInput, info: strawberry.types.Info) -> Post:
        if not info.context.user:
            raise Exception("Not authenticated")
        return await info.context.db.create_post(input, info.context.user.id)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
```

---

## Step 8: Client (Apollo Client + React)

```typescript
// Apollo setup
import { ApolloClient, InMemoryCache, ApolloProvider, gql, useQuery } from '@apollo/client'

const client = new ApolloClient({
  uri: '/api/graphql',
  cache: new InMemoryCache({
    typePolicies: {
      Query: {
        fields: {
          posts: { keyArgs: ['status'], merge: true }  // cursor pagination merge
        }
      }
    }
  }),
  headers: { Authorization: `Bearer ${token}` },
})

// Query
const GET_POSTS = gql`
  query GetPosts($first: Int, $after: String) {
    posts(first: $first, after: $after) {
      edges {
        node {
          id
          title
          author { id name }
        }
        cursor
      }
      pageInfo { hasNextPage endCursor }
    }
  }
`

function PostList() {
  const { data, loading, error, fetchMore } = useQuery(GET_POSTS, {
    variables: { first: 10 }
  })

  if (loading) return <Spinner />
  if (error) return <Error message={error.message} />

  return (
    <>
      {data.posts.edges.map(({ node }) => (
        <PostCard key={node.id} post={node} />
      ))}
      {data.posts.pageInfo.hasNextPage && (
        <button onClick={() => fetchMore({
          variables: { after: data.posts.pageInfo.endCursor }
        })}>
          Load More
        </button>
      )}
    </>
  )
}
```

---

## Common Mistakes

- **N+1 queries** — always use DataLoader for relationship resolvers
- **Overfetching in resolvers** — fetch only the fields requested using projection/select
- **Resolving errors with exceptions** — for business errors (validation), return `UserError` in payload; use exceptions only for system errors
- **Forgetting to authenticate field resolvers** — apply `requireAuth` at the resolver level, not just the schema
- **Global DataLoader instances** — DataLoaders must be created per-request to prevent cross-request data leaks
- **No input validation** — validate IDs, string lengths, enums before DB calls
- **Schema introspection in production** — disable `introspection: false` in production GraphQL servers to prevent schema leakage
