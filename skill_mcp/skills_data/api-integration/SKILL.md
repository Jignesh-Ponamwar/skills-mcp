---
name: api-integration
description: Integrate with REST APIs, handle authentication (API keys, OAuth 2.0, JWT), manage pagination, rate limiting, retries, and error handling. Use when the user needs to call an external API, integrate a third-party service, handle webhooks, or build an API client.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [api, rest, oauth, http, integration, webhooks, http-client]
  platforms: [claude-code, cursor, any]
  triggers:
    - integrate this API
    - call this API
    - connect to this service
    - REST API integration
    - OAuth authentication
    - handle API pagination
    - API client
    - webhook handler
    - handle rate limiting
    - API error handling
---

# API Integration Skill

## Overview
Build reliable integrations with REST APIs: authentication, pagination, rate limiting, retries, and error handling. Covers the full lifecycle from first call to production-ready client.

## Step-by-Step Process

### Step 1: Read the API Docs
Before writing any code, identify:
- **Base URL** and API version (`https://api.example.com/v2`)
- **Authentication method** (API key header, Bearer token, OAuth 2.0, Basic auth)
- **Rate limits** (requests per minute/hour, burst limits)
- **Pagination style** (offset/limit, cursor, page number, Link header)
- **Error response format** (status codes, error body schema)

### Step 2: Set Up Authentication

**API Key (header)**
```python
import httpx

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
client = httpx.Client(base_url="https://api.example.com/v2", headers=headers)
```

**OAuth 2.0 Client Credentials**
```python
import httpx

def get_access_token(client_id: str, client_secret: str, token_url: str) -> str:
    response = httpx.post(token_url, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    })
    response.raise_for_status()
    return response.json()["access_token"]
```

**Basic Auth**
```python
client = httpx.Client(auth=(username, password))
```

### Step 3: Make Requests with Retry Logic

```python
import httpx
import time
from typing import Any

def api_request(
    client: httpx.Client,
    method: str,
    path: str,
    max_retries: int = 3,
    **kwargs: Any,
) -> dict:
    for attempt in range(max_retries):
        try:
            response = client.request(method, path, timeout=30, **kwargs)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # exponential backoff
                continue
            raise

    raise RuntimeError(f"Failed after {max_retries} attempts")
```

### Step 4: Handle Pagination

**Offset/limit pagination**
```python
def paginate_offset(client, path: str, page_size: int = 100):
    offset = 0
    while True:
        data = api_request(client, "GET", path, params={"limit": page_size, "offset": offset})
        items = data.get("items", data.get("data", []))
        if not items:
            break
        yield from items
        if len(items) < page_size:
            break
        offset += page_size
```

**Cursor pagination**
```python
def paginate_cursor(client, path: str):
    cursor = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        data = api_request(client, "GET", path, params=params)
        yield from data["items"]
        cursor = data.get("next_cursor")
        if not cursor:
            break
```

**Link header (GitHub-style)**
```python
import re

def paginate_link_header(client, url: str):
    while url:
        response = client.get(url)
        response.raise_for_status()
        yield from response.json()
        link_header = response.headers.get("Link", "")
        next_url = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
        url = next_url.group(1) if next_url else None
```

### Step 5: Handle Errors

```python
def handle_api_error(response: httpx.Response) -> None:
    try:
        error_body = response.json()
    except Exception:
        error_body = {"message": response.text}

    status = response.status_code
    if status == 400:
        raise ValueError(f"Bad request: {error_body}")
    elif status == 401:
        raise PermissionError("Authentication failed — check API key")
    elif status == 403:
        raise PermissionError(f"Forbidden: {error_body}")
    elif status == 404:
        raise KeyError(f"Resource not found: {response.url}")
    elif status == 422:
        raise ValueError(f"Validation error: {error_body}")
    elif status == 429:
        raise RuntimeError("Rate limit exceeded")
    elif status >= 500:
        raise RuntimeError(f"Server error {status}: {error_body}")
```

### Step 6: Webhook Handling

```python
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.post("/webhooks/example")
async def handle_webhook(request: Request):
    # Verify signature
    signature = request.headers.get("X-Webhook-Signature")
    body = await request.body()
    expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = payload.get("type")
    # Route to handler...
    return {"status": "ok"}
```

## Production Checklist
- [ ] Secrets in environment variables, never in code
- [ ] Retry with exponential backoff on 5xx and 429
- [ ] Timeout set on every request (default: 30s)
- [ ] Rate limit tracking to avoid hitting limits proactively
- [ ] Structured logging with request ID for debugging
- [ ] Webhook signature verification before processing
