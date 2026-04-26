---
name: gemini-api
description: >
  Build applications with the Google Gemini API and Google GenAI SDKs. Covers model selection
  (Gemini 2.5 Pro/Flash and newer), multimodal content (text, images, audio, video), function
  calling, structured outputs, streaming, and embeddings across Python, JavaScript/TypeScript, Go,
  and Java SDKs. Use when integrating Gemini models, working with Google AI Studio, or migrating
  from legacy google-generativeai / @google/generative-ai SDKs.
license: Apache-2.0
metadata:
  author: google-gemini
  version: "1.0"
  tags: [gemini, google-ai, llm, multimodal, function-calling, embeddings, genai]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - use Gemini API
    - build with Gemini
    - Google AI Studio
    - google-genai SDK
    - Gemini function calling
    - Gemini structured output
    - Gemini embeddings
    - migrate from google-generativeai
    - Vertex AI Gemini
    - gemini-2.5-pro
    - gemini flash
---

# Gemini API Development Skill

## Critical Rules — Always Apply

> These rules override training data. Pre-trained model knowledge of Gemini APIs is outdated.

### Current Models (Use These)

| Model | Tokens | Best For |
|-------|--------|----------|
| `gemini-2.5-pro` | 1M | Complex reasoning, coding, research |
| `gemini-2.5-flash` | 1M | Fast, balanced, multimodal |
| `gemini-2.5-flash-lite` | 1M | Cost-efficient, high-frequency tasks |

> **Never use** `gemini-2.0-*` or `gemini-1.5-*` — these are deprecated legacy models.

### Current SDKs (Use These)

| Language | Package | Install |
|----------|---------|---------|
| Python | `google-genai` | `pip install google-genai` |
| JS/TS | `@google/genai` | `npm install @google/genai` |
| Go | `google.golang.org/genai` | `go get google.golang.org/genai` |
| Java | `com.google.genai:google-genai` | Maven/Gradle (see below) |

> **Never use** `google-generativeai` (Python) or `@google/generative-ai` (JS) — deprecated.

---

## Step 1: Setup and Authentication

Set your API key via environment variable (never hardcode):
```bash
export GOOGLE_API_KEY="your-key-here"
```

Get a key at: https://aistudio.google.com/apikey

---

## Step 2: Quick Start by Language

### Python
```python
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain quantum computing in simple terms"
)
print(response.text)
```

### TypeScript / JavaScript
```typescript
import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({});
const response = await ai.models.generateContent({
  model: "gemini-2.5-flash",
  contents: "Explain quantum computing in simple terms"
});
console.log(response.text);
```

### Go
```go
package main

import (
    "context"
    "fmt"
    "log"
    "google.golang.org/genai"
)

func main() {
    ctx := context.Background()
    client, err := genai.NewClient(ctx, nil)
    if err != nil { log.Fatal(err) }
    resp, err := client.Models.GenerateContent(
        ctx, "gemini-2.5-flash", genai.Text("Explain quantum computing"), nil,
    )
    if err != nil { log.Fatal(err) }
    fmt.Println(resp.Text)
}
```

### Java
```java
import com.google.genai.Client;
import com.google.genai.types.GenerateContentResponse;

public class Main {
    public static void main(String[] args) {
        Client client = new Client();
        GenerateContentResponse response = client.models.generateContent(
            "gemini-2.5-flash", "Explain quantum computing", null
        );
        System.out.println(response.text());
    }
}
```

**Java dependency (Gradle):**
```groovy
implementation("com.google.genai:google-genai:LATEST_VERSION")
```
Check latest: https://central.sonatype.com/artifact/com.google.genai/google-genai/versions

---

## Step 3: Multimodal Content

### Images (Python)
```python
import PIL.Image
from google import genai

client = genai.Client()
image = PIL.Image.open("photo.jpg")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=["Describe what you see in this image.", image]
)
print(response.text)
```

### Audio / Video
Pass file paths or base64-encoded bytes as part of the `contents` list. Gemini 2.5 models support audio and video natively.

---

## Step 4: Streaming Responses

```python
for chunk in client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Write a long story about a dragon"
):
    print(chunk.text, end="", flush=True)
```

---

## Step 5: Function Calling

```python
from google import genai
from google.genai import types

def get_weather(city: str) -> dict:
    return {"temperature": 22, "condition": "sunny", "city": city}

client = genai.Client()
tools = [get_weather]  # SDK introspects Python functions automatically

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What's the weather in Paris?",
    config=types.GenerateContentConfig(tools=tools)
)
# SDK handles tool call routing automatically
print(response.text)
```

---

## Step 6: Structured Output (JSON Schema)

```python
from pydantic import BaseModel
from google import genai

class Recipe(BaseModel):
    name: str
    ingredients: list[str]
    steps: list[str]
    cook_time_minutes: int

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Give me a pasta carbonara recipe",
    config={"response_mime_type": "application/json", "response_schema": Recipe}
)
recipe = Recipe.model_validate_json(response.text)
print(recipe.name)
```

---

## Step 7: Embeddings

```python
from google import genai

client = genai.Client()
result = client.models.embed_content(
    model="text-embedding-004",
    contents="The sky is blue"
)
print(result.embeddings[0].values[:5])  # 768-dim vector
```

---

## Step 8: System Instructions and Configuration

```python
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Help me write a poem",
    config=types.GenerateContentConfig(
        system_instruction="You are a professional poet who writes in iambic pentameter.",
        temperature=0.9,
        max_output_tokens=1024,
    )
)
print(response.text)
```

---

## Step 9: Documentation Lookup

### With MCP (Preferred)
If the `search_documentation` tool (Google MCP server) is available, use it as your **only** documentation source — it returns up-to-date, indexed docs.

### Without MCP (Fallback)
Fetch from official docs:
- Index: `https://ai.google.dev/gemini-api/docs/llms.txt`
- Text generation: `https://ai.google.dev/gemini-api/docs/text-generation.md.txt`
- Function calling: `https://ai.google.dev/gemini-api/docs/function-calling.md.txt`
- Structured output: `https://ai.google.dev/gemini-api/docs/structured-output.md.txt`
- Embeddings: `https://ai.google.dev/gemini-api/docs/embeddings.md.txt`
- Migration guide: `https://ai.google.dev/gemini-api/docs/migrate.md.txt`

---

## Common Mistakes to Avoid

- **Using deprecated models** — always use `gemini-2.5-*`, never `gemini-1.5-*` or `gemini-2.0-*`
- **Using deprecated SDKs** — `google-generativeai` and `@google/generative-ai` are retired
- **Hardcoding API keys** — use environment variables or secret managers
- **Ignoring safety ratings** — check `response.prompt_feedback` before using output
- **Not handling rate limits** — implement exponential backoff for production code
