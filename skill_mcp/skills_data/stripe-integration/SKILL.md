---
name: stripe-integration
description: >
  Build Stripe payment integrations — one-time payments, subscriptions, marketplaces, and Connect
  platforms. Covers API selection (Checkout Sessions vs PaymentIntents vs Setup Intents), webhooks,
  restricted API keys, Stripe Connect (Accounts v2), billing, and security best practices. Use when
  accepting payments, integrating Stripe, building subscription billing, creating connected accounts,
  or reviewing Stripe integration code.
license: Apache-2.0
metadata:
  author: stripe
  version: "1.0"
  tags: [stripe, payments, billing, subscriptions, connect, webhooks, checkout, fintech]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - integrate Stripe
    - accept payments
    - Stripe Checkout
    - Stripe PaymentIntents
    - Stripe subscriptions
    - Stripe Connect
    - Stripe webhooks
    - Stripe billing
    - payment processing
    - Stripe SDK
    - set up subscriptions
    - create connected accounts
---

# Stripe Integration Skill

## Critical Rule

**Always use the latest Stripe API version: `2026-03-25.dahlia`** unless the user explicitly requests otherwise.

---

## Step 1: Choose the Right Stripe API

| Building… | Recommended API |
|-----------|----------------|
| One-time payments with hosted UI | **Checkout Sessions** |
| Custom payment form embedded in your page | **Checkout Sessions + Payment Element** |
| Saving payment method for later | **Setup Intents** |
| Marketplace or platform | **Accounts v2** (`/v2/core/accounts`) |
| Subscriptions / recurring billing | **Billing APIs + Checkout Sessions** |
| Embedded banking / financial accounts | **Treasury v2** |

When in doubt, start with **Checkout Sessions** — it handles PCI compliance, 3D Secure, and local payment methods automatically.

---

## Step 2: Initial Setup

### Install SDK
```bash
# Python
pip install stripe

# Node.js
npm install stripe

# Go
go get github.com/stripe/stripe-go/v76
```

### Configure SDK
```python
# Python
import stripe
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]  # never hardcode
stripe.api_version = "2026-03-25.dahlia"
```

```typescript
// TypeScript / Node.js
import Stripe from 'stripe'
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2026-03-25.dahlia',
})
```

---

## Step 3: One-Time Payments (Checkout Sessions)

```typescript
// Server: Create session
const session = await stripe.checkout.sessions.create({
  payment_method_types: ['card'],
  line_items: [{
    price_data: {
      currency: 'usd',
      product_data: { name: 'Pro Plan' },
      unit_amount: 2000,  // $20.00 in cents
    },
    quantity: 1,
  }],
  mode: 'payment',
  success_url: 'https://example.com/success?session_id={CHECKOUT_SESSION_ID}',
  cancel_url: 'https://example.com/cancel',
})
return { url: session.url }  // redirect user to this URL

// After payment — verify via webhook, NOT success_url query param
```

---

## Step 4: Subscriptions (Recurring Billing)

### Step 4a: Create a Product and Price in Stripe Dashboard (or API)
```typescript
const price = await stripe.prices.create({
  currency: 'usd',
  unit_amount: 1000,  // $10/month
  recurring: { interval: 'month' },
  product_data: { name: 'Pro Subscription' },
})
```

### Step 4b: Checkout Session for Subscription
```typescript
const session = await stripe.checkout.sessions.create({
  mode: 'subscription',
  line_items: [{ price: price.id, quantity: 1 }],
  success_url: 'https://example.com/success',
  cancel_url: 'https://example.com/cancel',
  // Optionally attach to existing customer:
  customer: customerId,
})
```

### Step 4c: Customer Portal (let users manage subscriptions)
```typescript
const portalSession = await stripe.billingPortal.sessions.create({
  customer: customerId,
  return_url: 'https://example.com/account',
})
return { url: portalSession.url }
```

---

## Step 5: Webhooks (Required for Reliable Integration)

**Never** trust the `success_url` to confirm payment — always use webhooks.

```typescript
// app/api/webhooks/stripe/route.ts (Next.js App Router)
import Stripe from 'stripe'
import { headers } from 'next/headers'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!

export async function POST(request: Request) {
  const body = await request.text()
  const signature = (await headers()).get('stripe-signature')!

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret)
  } catch {
    return new Response('Invalid signature', { status: 400 })
  }

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.Checkout.Session
      await fulfillOrder(session)
      break
    }
    case 'customer.subscription.updated':
    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription
      await updateSubscriptionStatus(subscription)
      break
    }
    case 'invoice.payment_failed': {
      // Notify user, pause access, retry logic
      break
    }
  }

  return new Response(null, { status: 200 })
}
```

**Webhook setup:**
```bash
# Local development — forward events to localhost
stripe listen --forward-to localhost:3000/api/webhooks/stripe

# Copy the webhook signing secret from output ↑ to STRIPE_WEBHOOK_SECRET
```

---

## Step 6: Stripe Connect (Marketplaces & Platforms)

```typescript
// Create a connected account (v2)
const account = await stripe.v2.core.accounts.create({
  display_name: 'Acme Store',
  identity: {
    country: 'US',
    entity_type: 'company',
  },
})

// Onboard the account with Account Session
const accountSession = await stripe.accountSessions.create({
  account: account.id,
  components: {
    account_onboarding: { enabled: true },
    payments: { enabled: true },
  },
})

// Payment on behalf of connected account
const paymentIntent = await stripe.paymentIntents.create({
  amount: 2000,
  currency: 'usd',
  application_fee_amount: 200,  // platform takes $2
  transfer_data: { destination: connectedAccountId },
})
```

---

## Step 7: Security Best Practices

### API Key Management
- Use **restricted keys** in production — grant only the permissions each service needs
- Store keys in environment variables / secret managers, never in code or git
- Rotate keys immediately if compromised: `stripe.apiKeys.rotate()`

### Idempotency Keys
Always pass `idempotencyKey` for mutation requests to prevent duplicate charges:
```typescript
await stripe.paymentIntents.create(
  { amount: 2000, currency: 'usd' },
  { idempotencyKey: `pi_${orderId}` }
)
```

### Webhook Signature Verification
Always verify `stripe-signature` header using `stripe.webhooks.constructEvent()` — never skip this.

### Testing
```bash
# Test card numbers:
# 4242 4242 4242 4242  — succeeds
# 4000 0025 0000 3155  — requires 3D Secure
# 4000 0000 0000 9995  — card declined
```

---

## Step 8: Go-Live Checklist

Before switching to live keys:
- [ ] Webhooks configured for all relevant events
- [ ] All API calls use idempotency keys
- [ ] Live restricted key created (not secret key in production)
- [ ] Error handling for declined cards, webhook failures
- [ ] `STRIPE_WEBHOOK_SECRET` set from live webhook endpoint (not CLI)
- [ ] Test with live card in test mode first
- [ ] Review [go-live checklist](https://docs.stripe.com/get-started/checklist/go-live)

---

## Common Mistakes

- **Checking `success_url` to confirm payment** — always use webhooks instead
- **Using the full secret key in production** — use restricted keys
- **Hardcoding amounts client-side** — validate amount server-side to prevent manipulation
- **Storing raw card numbers** — never handle raw card data; use Stripe Elements or Checkout
- **Missing idempotency keys on retries** — always pass `idempotencyKey` for mutations
- **Not verifying webhook signatures** — always call `stripe.webhooks.constructEvent()`
- **Using deprecated APIs** — prefer `Accounts v2` for Connect; `Checkout Sessions` for payments
