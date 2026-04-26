---
name: claude-api
description: >
  Build, debug, and optimize applications using the Anthropic Claude API and official SDKs. Covers
  single API calls, tool use, streaming, prompt caching, vision/multimodal, extended thinking,
  batch processing, and managed agents. Use when writing code that imports the anthropic SDK, working
  with Claude models (Opus, Sonnet, Haiku), building agentic pipelines, or migrating between Claude
  model versions.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [claude, anthropic, llm, tool-use, streaming, prompt-caching, agents, multimodal]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - use Claude API
    - Anthropic SDK
    - build with Claude
    - Claude tool use
    - Claude streaming
    - prompt caching
    - Claude vision
    - extended thinking
    - Claude Opus
    - Claude Sonnet
    - Claude Haiku
    - anthropic Python SDK
    - "@anthropic-ai/sdk"
    - claude model
    - build an AI agent with Claude
---

# Claude API Skill (Anthropic SDK)

## Step 1: Detect Language and Install SDK

Scan the project for `package.json`, `requirements.txt`, `pyproject.toml`, `build.gradle`, or `go.mod` to identify the language.

```bash
# Python
pip install anthropic

# Node.js / TypeScript
npm install @anthropic-ai/sdk

# Go
go get github.com/anthropics/anthropic-sdk-go
```

---

## Step 2: Choose the Right Model

| Model | Best For | Speed | Cost |
|-------|---------|-------|------|
| `claude-opus-4-5` | Complex reasoning, coding, research | Slower | Higher |
| `claude-sonnet-4-5` | Balanced — most tasks | Medium | Medium |
| `claude-haiku-3-5` | Fast, lightweight tasks, classification | Fast | Lower |

**Default to `claude-opus-4-5`** for new implementations unless the user specifies otherwise or speed/cost is a constraint.

---

## Step 3: Basic API Call

### Python
```python
import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Explain the CAP theorem in simple terms."}
    ]
)
print(message.content[0].text)
```

### TypeScript / Node.js
```typescript
import Anthropic from '@anthropic-ai/sdk'

const client = new Anthropic()  // reads ANTHROPIC_API_KEY from env

const message = await client.messages.create({
  model: 'claude-opus-4-5',
  max_tokens: 1024,
  messages: [
    { role: 'user', content: 'Explain the CAP theorem in simple terms.' }
  ],
})
console.log(message.content[0].text)
```

---

## Step 4: System Prompts and Multi-Turn Conversations

```python
conversation_history = []

def chat(user_message: str) -> str:
    conversation_history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system="You are a senior software engineer. Be concise and precise.",
        messages=conversation_history
    )

    assistant_message = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_message})
    return assistant_message
```

---

## Step 5: Streaming

Use streaming for long outputs to reduce perceived latency:

```python
# Python — streaming
with client.messages.stream(
    model="claude-opus-4-5",
    max_tokens=4096,
    messages=[{"role": "user", "content": "Write a detailed explanation of neural networks"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

```typescript
// TypeScript — streaming
const stream = client.messages.stream({
  model: 'claude-opus-4-5',
  max_tokens: 4096,
  messages: [{ role: 'user', content: 'Write a detailed explanation of neural networks' }],
})

for await (const chunk of stream) {
  if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
    process.stdout.write(chunk.delta.text)
  }
}
```

---

## Step 6: Tool Use (Function Calling)

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name, e.g. 'London'"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    }
]

def get_weather(location: str, unit: str = "celsius") -> dict:
    # Your actual implementation
    return {"temperature": 15, "condition": "cloudy", "location": location}

# Agentic loop
messages = [{"role": "user", "content": "What's the weather in Tokyo?"}]

while True:
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        # Final text response — done
        for block in response.content:
            if hasattr(block, "text"):
                print(block.text)
        break

    # Process tool calls
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            if block.name == "get_weather":
                result = get_weather(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })

    messages.append({"role": "user", "content": tool_results})
```

---

## Step 7: Vision (Multimodal)

```python
import base64

# From URL
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "url", "url": "https://example.com/chart.png"},
            },
            {"type": "text", "text": "What does this chart show?"},
        ],
    }]
)

# From file (base64)
with open("diagram.png", "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": image_data},
            },
            {"type": "text", "text": "Describe this diagram."},
        ],
    }]
)
```

---

## Step 8: Prompt Caching (Cost Optimization)

Cache large system prompts or repeated context to reduce costs by up to 90%:

```python
# Mark cacheable content with cache_control
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are an expert in our codebase. " + very_long_codebase_context,
            "cache_control": {"type": "ephemeral"}  # cache this block
        }
    ],
    messages=[{"role": "user", "content": user_question}]
)

# Check cache usage in response
print(response.usage.cache_creation_input_tokens)  # tokens written to cache
print(response.usage.cache_read_input_tokens)       # tokens read from cache
```

**Caching rules:**
- Cache TTL: 5 minutes (refreshed on each cache hit)
- Minimum cacheable block: 1024 tokens (Haiku: 2048)
- Mark the largest, most stable prefix with `cache_control`

---

## Step 9: Extended Thinking

For complex reasoning tasks (math, coding, analysis):

```python
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000  # allow up to 10k tokens of internal thinking
    },
    messages=[{"role": "user", "content": "Prove that there are infinitely many primes."}]
)

for block in response.content:
    if block.type == "thinking":
        print("Thinking:", block.thinking[:200], "...")  # internal reasoning
    elif block.type == "text":
        print("Answer:", block.text)
```

---

## Step 10: Batch Processing

For large-scale offline processing (50% cost reduction):

```python
# Create batch
batch = client.messages.batches.create(requests=[
    {
        "custom_id": f"task-{i}",
        "params": {
            "model": "claude-haiku-3-5",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": text}]
        }
    }
    for i, text in enumerate(texts)
])

# Poll until complete
import time
while True:
    batch = client.messages.batches.retrieve(batch.id)
    if batch.processing_status == "ended":
        break
    time.sleep(60)

# Retrieve results
for result in client.messages.batches.results(batch.id):
    print(result.custom_id, result.result.message.content[0].text)
```

---

## Application Tiers

| Tier | Pattern | When to Use |
|------|---------|-------------|
| 1 | Single API call | Classification, extraction, summarization |
| 2 | Multi-turn + tools | Research assistant, coding helper |
| 3 | Managed Agents | Long-running autonomous tasks |

---

## Common Mistakes

- **Hardcoding API keys** — always use `ANTHROPIC_API_KEY` environment variable
- **Not streaming long outputs** — add streaming to reduce latency for responses > 500 tokens
- **Ignoring stop_reason** — check `response.stop_reason`; `"tool_use"` means loop continues
- **Skipping prompt caching** — add `cache_control` to large system prompts to cut costs
- **Using non-serializable tool results** — always stringify tool results before returning
- **Forgetting to append assistant + tool_result to messages** — the agentic loop requires both
