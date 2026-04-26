---
name: typescript-patterns
description: >
  Apply advanced TypeScript patterns — strict type safety, utility types, generics, discriminated
  unions, branded types, conditional types, template literal types, and declaration merging. Covers
  tsconfig best practices, type-safe API design, narrowing, and eliminating any/unknown. Use when
  writing TypeScript, reviewing TypeScript types, designing type-safe APIs, debugging type errors,
  or improving type coverage in a codebase.
license: Apache-2.0
metadata:
  author: community
  version: "1.0"
  tags: [typescript, types, generics, utility-types, strict, type-safety, interfaces]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - TypeScript types
    - TypeScript generics
    - TypeScript utility types
    - fix TypeScript error
    - type-safe API
    - discriminated union
    - TypeScript best practices
    - branded types
    - conditional types
    - narrow TypeScript types
    - improve TypeScript coverage
    - TypeScript any
---

# TypeScript Patterns Skill

## 1. Strict tsconfig (Always Start Here)

```json
{
  "compilerOptions": {
    "strict": true,               // enables all strict checks
    "noUncheckedIndexedAccess": true,  // arr[0] returns T | undefined
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true,
    "useUnknownInCatchVariables": true,
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

---

## 2. Utility Types — Essential Reference

```typescript
interface User {
  id: number
  name: string
  email: string
  age?: number
}

// Partial — all properties optional
type UpdateUser = Partial<User>

// Required — all properties required
type StrictUser = Required<User>

// Pick — select specific properties
type UserSummary = Pick<User, 'id' | 'name'>

// Omit — exclude specific properties
type PublicUser = Omit<User, 'email'>

// Readonly — prevent mutation
type ImmutableUser = Readonly<User>

// Record — typed object with known key shape
type UserById = Record<number, User>
type RolePermissions = Record<'admin' | 'editor' | 'viewer', string[]>

// Extract / Exclude
type StringOrNumber = string | number | boolean
type OnlyStrNum = Extract<StringOrNumber, string | number>   // string | number
type NoString = Exclude<StringOrNumber, string>               // number | boolean

// ReturnType / Parameters
function getUser(id: number): Promise<User> { ... }
type GetUserReturn = Awaited<ReturnType<typeof getUser>>      // User
type GetUserParams = Parameters<typeof getUser>               // [id: number]

// NonNullable
type MaybeUser = User | null | undefined
type DefiniteUser = NonNullable<MaybeUser>                   // User
```

---

## 3. Generics — Patterns

```typescript
// Generic function
function first<T>(arr: readonly T[]): T | undefined {
  return arr[0]
}

// Generic with constraint
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]
}

// Generic interface with default
interface ApiResponse<T = unknown> {
  data: T
  status: number
  message: string
}

// Multiple type parameters
function merge<A, B>(a: A, b: B): A & B {
  return { ...a, ...b }
}

// Generic class
class Repository<T extends { id: number }> {
  private items = new Map<number, T>()

  save(item: T): void {
    this.items.set(item.id, item)
  }

  findById(id: number): T | undefined {
    return this.items.get(id)
  }

  findAll(): T[] {
    return [...this.items.values()]
  }
}
```

---

## 4. Discriminated Unions — Type-Safe State Machines

```typescript
// Instead of flags (error-prone):
// type Result = { loading: boolean; data?: User; error?: Error }

// Use discriminated union:
type Result<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }

// TypeScript narrows correctly in each branch:
function renderUser(result: Result<User>) {
  switch (result.status) {
    case 'idle':    return <Placeholder />
    case 'loading': return <Spinner />
    case 'success': return <UserCard user={result.data} />   // data is User here
    case 'error':   return <ErrorMessage error={result.error} />
  }
}

// API response pattern
type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; statusCode: number }

async function fetchUser(id: number): Promise<ApiResult<User>> {
  const response = await fetch(`/api/users/${id}`)
  if (!response.ok) {
    return { ok: false, error: await response.text(), statusCode: response.status }
  }
  return { ok: true, data: await response.json() }
}

// Consuming:
const result = await fetchUser(1)
if (result.ok) {
  console.log(result.data.name)  // TypeScript knows data is User
} else {
  console.error(result.error)    // TypeScript knows error is string
}
```

---

## 5. Branded Types (Nominal Typing)

Prevent mixing up primitive values that have the same underlying type:

```typescript
// Without brands — easy to mix up IDs:
function getUser(id: number) { ... }
function getOrder(id: number) { ... }
getUser(orderId)  // TypeScript allows this — wrong!

// With brands — type-safe:
type UserId = number & { readonly _brand: 'UserId' }
type OrderId = number & { readonly _brand: 'OrderId' }

function createUserId(id: number): UserId {
  return id as UserId
}

function getUser(id: UserId) { ... }
function getOrder(id: OrderId) { ... }

const userId = createUserId(123)
const orderId = 456 as OrderId
getUser(userId)    // ✅
getUser(orderId)   // ❌ TypeScript error — OrderId is not UserId
```

---

## 6. Conditional Types

```typescript
// Basic conditional type
type IsArray<T> = T extends any[] ? true : false
type Test1 = IsArray<string[]>  // true
type Test2 = IsArray<string>    // false

// Infer — extract inner types
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T
type User = UnwrapPromise<Promise<{ name: string }>>  // { name: string }

type ElementType<T> = T extends (infer U)[] ? U : never
type Elem = ElementType<string[]>  // string

// Distributive conditional types
type ToArray<T> = T extends any ? T[] : never
type StringOrNumberArray = ToArray<string | number>  // string[] | number[]

// Non-distributive (wrap in tuple)
type IsUnion<T> = [T] extends [any] ? ([any] extends [T] ? false : true) : false
```

---

## 7. Template Literal Types

```typescript
type EventName = 'click' | 'focus' | 'blur'
type Handler = `on${Capitalize<EventName>}`  // 'onClick' | 'onFocus' | 'onBlur'

type CSSUnit = 'px' | 'em' | 'rem' | 'vh' | 'vw'
type CSSValue = `${number}${CSSUnit}`  // e.g. '16px', '1.5rem'

// Route types
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'
type ApiRoute = `/api/${string}`

// Extract path parameters
type ExtractParams<Path extends string> =
  Path extends `${string}:${infer Param}/${infer Rest}`
    ? Param | ExtractParams<`/${Rest}`>
    : Path extends `${string}:${infer Param}`
    ? Param
    : never

type Params = ExtractParams<'/users/:id/posts/:postId'>  // 'id' | 'postId'
```

---

## 8. Type Narrowing

```typescript
// typeof
function process(value: string | number) {
  if (typeof value === 'string') {
    return value.toUpperCase()  // string here
  }
  return value * 2  // number here
}

// instanceof
function handleError(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'string') return err
  return 'Unknown error'
}

// User-defined type guard
interface Cat { meow(): void }
interface Dog { bark(): void }

function isCat(animal: Cat | Dog): animal is Cat {
  return 'meow' in animal
}

// Assertion function
function assertDefined<T>(value: T, name: string): asserts value is NonNullable<T> {
  if (value === null || value === undefined) {
    throw new Error(`Expected ${name} to be defined`)
  }
}
```

---

## 9. Eliminating `any`

```typescript
// ❌ any — unsafe
function parseData(raw: any) {
  return raw.user.name  // runtime error if shape wrong
}

// ✅ unknown + narrowing — safe
function parseData(raw: unknown): string {
  if (
    typeof raw === 'object' && raw !== null &&
    'user' in raw && typeof (raw as any).user === 'object' &&
    'name' in (raw as any).user
  ) {
    return String((raw as any).user.name)
  }
  throw new Error('Unexpected data shape')
}

// ✅ Zod — best for runtime validation of external data
import { z } from 'zod'

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
})
type User = z.infer<typeof UserSchema>

const user = UserSchema.parse(rawData)  // throws on invalid, returns User
```

---

## Common Mistakes

- **Using `any` instead of `unknown`** — `unknown` forces narrowing before use
- **`as` everywhere** — `as SomeType` suppresses errors; use type guards instead
- **`!` non-null assertion without checking** — assert only when you've verified the value exists
- **Loose `tsconfig`** — always start with `"strict": true`
- **Interface vs type for objects** — prefer `interface` for public APIs (extensible), `type` for unions and computed types
- **Forgetting `readonly`** — immutable arrays should use `readonly T[]` not `T[]`
- **Implicit `any` in catch** — use `catch (err: unknown)` and narrow to `Error` before accessing `.message`
