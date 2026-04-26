---
name: mcp-server-builder
description: >
  Build high-quality Model Context Protocol (MCP) servers that expose tools, resources, and prompts
  to AI agents. Covers MCP architecture, tool/resource/prompt definitions, stdio and HTTP/SSE
  transports, authentication, error handling, and deployment patterns using FastMCP (Python) or the
  TypeScript MCP SDK. Use when creating an MCP server, adding tools to an existing MCP server,
  integrating an API or service as MCP tools, or debugging MCP connectivity issues.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [mcp, model-context-protocol, tools, resources, fastmcp, typescript-sdk, agents]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - build an MCP server
    - MCP tool
    - Model Context Protocol
    - FastMCP
    - MCP TypeScript SDK
    - expose tools to Claude
    - MCP resource
    - MCP prompt
    - create MCP integration
    - add MCP server
    - debug MCP server
---

# MCP Server Builder Skill

## MCP Architecture

An MCP server exposes three primitives to AI clients:

| Primitive | Purpose | When to Use |
|-----------|---------|-------------|
| **Tools** | Callable functions the agent invokes (`tools/call`) | Actions, API calls, computations |
| **Resources** | Read-only data the agent fetches (`resources/read`) | Files, database records, configuration |
| **Prompts** | Reusable prompt templates (`prompts/get`) | Guided workflows, structured interactions |

---

## Option A: Python with FastMCP (Recommended)

```bash
pip install fastmcp
```

### Minimal Server
```python
# server.py
from fastmcp import FastMCP

mcp = FastMCP("My Tools Server", version="1.0.0")

@mcp.tool(description="Add two numbers together")
def add(a: float, b: float) -> float:
    """Add two numbers and return the result."""
    return a + b

@mcp.tool(description="Fetch the current weather for a city")
async def get_weather(city: str, unit: str = "celsius") -> dict:
    """Get current weather. unit: 'celsius' or 'fahrenheit'"""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://wttr.in/{city}?format=j1")
        resp.raise_for_status()
        data = resp.json()
    return {
        "city": city,
        "temperature": data["current_condition"][0]["temp_C" if unit == "celsius" else "temp_F"],
        "condition": data["current_condition"][0]["weatherDesc"][0]["value"],
    }

if __name__ == "__main__":
    mcp.run()  # stdio mode (default)
```

### Run Modes
```bash
# stdio (for Claude Code, Cursor — recommended for local tools)
python server.py

# SSE (for browser clients and remote access)
MCP_TRANSPORT=sse python server.py           # http://localhost:8000/sse

# Streamable HTTP (modern, bidirectional)
MCP_TRANSPORT=streamable-http python server.py
```

### Resources
```python
@mcp.resource("config://app-settings")
def get_app_settings() -> str:
    """Return current application settings."""
    import json
    return json.dumps({
        "version": "1.0.0",
        "features": ["auth", "analytics"],
        "max_users": 1000,
    })

@mcp.resource("file://{path}")  # template URI with parameter
def read_file(path: str) -> str:
    """Read a file by path."""
    import pathlib
    # IMPORTANT: validate path to prevent traversal
    base = pathlib.Path("./allowed_dir").resolve()
    target = (base / path).resolve()
    if base not in target.parents and base != target:
        raise ValueError("Path outside allowed directory")
    return target.read_text()
```

### Prompts
```python
@mcp.prompt(description="Generate a code review checklist for a PR")
def code_review_prompt(language: str, pr_description: str) -> str:
    return f"""Review the following {language} pull request:

{pr_description}

Check for:
1. Correctness — does it do what it claims?
2. Security — any vulnerabilities (injection, auth issues, path traversal)?
3. Performance — any N+1 queries, unnecessary allocations?
4. Error handling — all edge cases covered?
5. Tests — adequate coverage?

Use severity tags: [CRITICAL] [HIGH] [MEDIUM] [LOW]"""
```

---

## Option B: TypeScript MCP SDK

```bash
npm install @modelcontextprotocol/sdk
```

```typescript
// server.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'

const server = new Server(
  { name: 'my-tools-server', version: '1.0.0' },
  { capabilities: { tools: {}, resources: {} } }
)

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'calculate',
      description: 'Perform arithmetic calculations',
      inputSchema: {
        type: 'object',
        properties: {
          expression: { type: 'string', description: 'Math expression, e.g. "2 + 2"' },
        },
        required: ['expression'],
      },
    },
  ],
}))

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === 'calculate') {
    const { expression } = request.params.arguments as { expression: string }
    // Safe eval — use a proper math library in production
    const result = Function(`'use strict'; return (${expression})`)()
    return { content: [{ type: 'text', text: String(result) }] }
  }
  throw new Error(`Unknown tool: ${request.params.name}`)
})

// Start
const transport = new StdioServerTransport()
await server.connect(transport)
```

---

## Tool Design Best Practices

### Write Descriptions for LLMs, Not Humans
The description is what the agent reads to decide when to call the tool:

```python
# ❌ Too vague
@mcp.tool(description="Database lookup")
def db_lookup(query: str) -> list: ...

# ✅ Tells the agent exactly when and how to use it
@mcp.tool(description="""Search the product catalog by keyword, category, or SKU.
Returns a list of matching products with id, name, price, and stock_count.
Use when the user asks about a product, wants to find items, or asks about availability.
Returns empty list if no products match. Max 20 results.""")
def search_products(query: str, category: str = "", limit: int = 20) -> list[dict]: ...
```

### Return Structured Data
```python
# ❌ String concatenation — hard for agent to parse
return f"User {user.name} has {len(orders)} orders totalling ${total}"

# ✅ Structured dict — agent can reason about individual fields
return {
    "user": {"id": user.id, "name": user.name},
    "order_count": len(orders),
    "total_spent": total,
    "currency": "USD",
}
```

### Handle Errors Explicitly
```python
@mcp.tool(description="Look up a user by email address")
async def get_user(email: str) -> dict:
    user = await db.find_user_by_email(email)
    if not user:
        # Return structured error — don't raise (let agent handle it)
        return {"found": False, "error": f"No user found with email: {email}"}
    return {"found": True, "user": {"id": user.id, "name": user.name, "email": user.email}}
```

---

## MCP Client Configuration

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/server",
      "env": {
        "DATABASE_URL": "postgresql://...",
        "API_KEY": "sk-..."
      }
    }
  }
}
```

For SSE transport:
```json
{
  "mcpServers": {
    "my-tools": {
      "transport": "sse",
      "url": "https://my-mcp-server.com/sse"
    }
  }
}
```

---

## Testing and Debugging

```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector python server.py

# Or for SSE:
npx @modelcontextprotocol/inspector sse http://localhost:8000/sse
```

The Inspector provides a web UI to list tools, call them, and view responses without needing an AI client.

---

## Security Checklist

- [ ] **Path validation** — never accept arbitrary file paths; resolve and check against a whitelist
- [ ] **Input validation** — validate all inputs, especially those used in SQL queries or shell commands
- [ ] **No secrets in tool descriptions** — descriptions are sent to the LLM; don't include credentials
- [ ] **Rate limiting** — protect expensive operations (API calls, DB queries) from being called in tight loops
- [ ] **Authentication** — for remote (SSE/HTTP) servers, require an API key or OAuth token
- [ ] **Least privilege** — tools should only have access to what they need

---

## Common Mistakes

- **Descriptions too short** — agents use descriptions to decide when to call tools; make them specific and complete
- **Raising exceptions on not-found** — return a structured `{"found": false}` response so the agent can handle it gracefully
- **Synchronous blocking I/O in async handlers** — use `httpx` (not `requests`), `asyncpg` (not `psycopg2`)
- **Not sanitizing file paths** — always resolve and validate against a base directory
- **Returning unstructured strings** — structured dicts make it easy for agents to extract relevant fields
- **No logging** — add structured logging to diagnose issues when the agent calls your tools
