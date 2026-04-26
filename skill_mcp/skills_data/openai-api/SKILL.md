---
name: openai-api
description: >
  Build applications using the OpenAI API — chat completions, function calling, streaming,
  embeddings, image generation (DALL-E), vision (GPT-4 Vision), audio (Whisper, TTS), assistants,
  and structured outputs. Covers Python and TypeScript OpenAI SDK, model selection (GPT-4o, o3,
  o4-mini), cost optimization with prompt caching, and batch processing. Use when integrating OpenAI
  models, building GPT-powered features, working with the openai Python package or openai npm package.
license: Apache-2.0
metadata:
  author: openai
  version: "1.0"
  tags: [openai, gpt, llm, chatgpt, function-calling, embeddings, dall-e, whisper, assistants]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - use OpenAI API
    - GPT-4 integration
    - OpenAI function calling
    - ChatGPT API
    - OpenAI embeddings
    - DALL-E image generation
    - Whisper transcription
    - OpenAI streaming
    - OpenAI Assistants API
    - GPT-4o
    - openai Python package
    - "@openai/openai npm"
---

# OpenAI API Skill

## Step 1: Choose the Right Model

| Model | Best For | Context |
|-------|---------|---------|
| `gpt-4o` | Multimodal (text + vision), balanced | 128K tokens |
| `gpt-4o-mini` | Fast, cheap, most tasks | 128K tokens |
| `o3` | Complex multi-step reasoning | 200K tokens |
| `o4-mini` | Efficient reasoning at low cost | 200K tokens |
| `text-embedding-3-large` | High-quality embeddings (3072-dim) | — |
| `text-embedding-3-small` | Affordable embeddings (1536-dim) | — |
| `dall-e-3` | High-quality image generation | — |
| `whisper-1` | Audio transcription | — |
| `tts-1-hd` | High-quality text-to-speech | — |

---

## Step 2: Setup

```bash
pip install openai         # Python
npm install openai          # Node.js / TypeScript
```

```python
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # never hardcode
```

```typescript
import OpenAI from 'openai'

const client = new OpenAI()  // reads OPENAI_API_KEY from env automatically
```

---

## Step 3: Chat Completions

```python
# Python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain recursion with an example."},
    ],
    temperature=0.7,
    max_tokens=1024,
)
print(response.choices[0].message.content)
```

```typescript
// TypeScript
const response = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'Explain recursion with an example.' },
  ],
  temperature: 0.7,
  max_tokens: 1024,
})
console.log(response.choices[0].message.content)
```

---

## Step 4: Streaming

```python
# Python
with client.chat.completions.stream(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Write a poem about the sea"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

```typescript
// TypeScript — Server-Sent Events for Next.js
const stream = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Write a poem about the sea' }],
  stream: true,
})

for await (const chunk of stream) {
  const delta = chunk.choices[0]?.delta?.content ?? ''
  process.stdout.write(delta)
}
```

---

## Step 5: Function Calling (Tool Use)

```python
import json

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City, e.g. 'London, UK'"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

def get_weather(location: str, unit: str = "celsius") -> str:
    return json.dumps({"location": location, "temperature": 22, "unit": unit})

messages = [{"role": "user", "content": "What's the weather in Tokyo?"}]

while True:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    msg = response.choices[0].message
    messages.append(msg)

    if response.choices[0].finish_reason == "stop":
        print(msg.content)
        break

    # Execute tool calls
    for tool_call in (msg.tool_calls or []):
        args = json.loads(tool_call.function.arguments)
        result = get_weather(**args)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })
```

---

## Step 6: Structured Output (Guaranteed JSON)

```python
from pydantic import BaseModel

class MovieReview(BaseModel):
    title: str
    rating: float
    summary: str
    pros: list[str]
    cons: list[str]

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Review the movie Inception"}],
    response_format=MovieReview,
)
review = response.choices[0].message.parsed
print(f"{review.title}: {review.rating}/10")
print("Pros:", review.pros)
```

---

## Step 7: Vision (Multimodal)

```python
import base64

# From URL
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "https://example.com/chart.png"}},
            {"type": "text", "text": "What trend does this chart show?"},
        ],
    }]
)

# From local file
with open("diagram.png", "rb") as f:
    b64 = base64.standard_b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": "Describe this architecture diagram."},
        ],
    }]
)
```

---

## Step 8: Embeddings

```python
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=["The quick brown fox", "Semantic search is powerful"]
)

vectors = [e.embedding for e in response.data]
# Each vector: 1536 floats

# Cosine similarity
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

similarity = cosine_similarity(vectors[0], vectors[1])
```

---

## Step 9: Audio (Whisper + TTS)

```python
# Transcription (Whisper)
with open("recording.mp3", "rb") as audio:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio,
        language="en",
    )
print(transcript.text)

# Text-to-speech
response = client.audio.speech.create(
    model="tts-1-hd",
    voice="nova",   # alloy | echo | fable | onyx | nova | shimmer
    input="Hello, how can I help you today?",
)
response.stream_to_file("speech.mp3")
```

---

## Step 10: Image Generation (DALL-E 3)

```python
response = client.images.generate(
    model="dall-e-3",
    prompt="A serene mountain lake at sunset, photorealistic, 4K",
    size="1792x1024",   # 1024x1024 | 1024x1792 | 1792x1024
    quality="hd",
    n=1,
)
image_url = response.data[0].url
```

---

## Step 11: Batch Processing (50% Cost Reduction)

```python
import jsonlines

# Create batch file
with jsonlines.open("batch_requests.jsonl", "w") as writer:
    for i, text in enumerate(texts):
        writer.write({
            "custom_id": f"task-{i}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": text}],
                "max_tokens": 500,
            }
        })

# Submit batch
with open("batch_requests.jsonl", "rb") as f:
    batch_file = client.files.create(file=f, purpose="batch")

batch = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
)

# Check status and retrieve
import time
while True:
    batch = client.batches.retrieve(batch.id)
    if batch.status == "completed": break
    time.sleep(30)

results = client.files.content(batch.output_file_id)
```

---

## Common Mistakes

- **Hardcoding API keys** — always use environment variables
- **Not handling rate limits** — implement exponential backoff with `openai.RateLimitError`
- **Ignoring token limits** — count tokens with `tiktoken` before sending long inputs
- **Not streaming for long outputs** — use streaming for responses > 500 tokens
- **Skipping error handling** — always catch `openai.APIError` and its subclasses
- **Using deprecated `gpt-4-turbo`** — prefer `gpt-4o` for better performance and lower cost
- **Missing tool_call loop exit condition** — the agent loop must check `finish_reason == "stop"` to exit
