---
name: llm-prompt-engineering
description: >
  Design effective prompts for large language models — chain-of-thought reasoning, few-shot
  examples, role assignment, XML structure, output format control, temperature tuning, and
  prompt chaining for multi-step tasks. Covers both general LLM prompting and model-specific
  best practices for Claude, GPT-4o, and Gemini. Use when writing system prompts, designing
  AI agent instructions, improving LLM output quality, reducing hallucinations, or engineering
  prompts for production AI applications.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [prompting, llm, chain-of-thought, few-shot, system-prompt, ai-engineering, claude, gpt]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - write a system prompt
    - improve prompt quality
    - chain of thought prompting
    - few-shot examples
    - prompt engineering
    - reduce hallucinations
    - design AI agent instructions
    - LLM prompt best practices
    - prompt chaining
    - structured output prompting
    - prompt for Claude
    - prompt for GPT
---

# LLM Prompt Engineering Skill

## Principle 1: Be Specific and Unambiguous

Vague prompts produce vague outputs. Every ambiguity in a prompt becomes variance in the output.

```
❌ "Summarize this article."

✅ "Summarize this article in 3 bullet points, each 1-2 sentences. Focus on:
   - The main problem being solved
   - The proposed solution or finding
   - The practical implication for developers
   Do not include background context that isn't mentioned in the article."
```

---

## Principle 2: Assign a Role / Persona

Role assignment primes the model's knowledge domain and response style:

```
"You are a senior security engineer conducting a code audit. Your role is to:
- Identify vulnerabilities with severity ratings (Critical/High/Medium/Low)
- Explain the attack vector for each finding
- Provide concrete remediation code
- Be precise — only flag real issues, not style preferences"
```

---

## Principle 3: Structured Prompts with XML Tags (Claude / GPT-4)

XML tags make prompt sections unambiguous and allow easy programmatic parsing:

```xml
<system_prompt>
You are a technical writer specializing in API documentation.

<rules>
- Write in second person ("you can", "use the", not "the developer should")
- Show complete code examples with working imports
- Include error handling in every example
- Format: Overview → Parameters table → Example → Common errors
</rules>
</system_prompt>

<user_request>
Document the following Python function:
<function>
{code_here}
</function>
</user_request>
```

---

## Principle 4: Chain-of-Thought Reasoning

For complex tasks, instruct the model to reason step by step before answering:

```
"Before giving your final answer, think through this step by step:
1. What information is given?
2. What is being asked?
3. What approach should I take?
4. Work through the solution
5. Verify the answer
Then provide your final answer."
```

Or simply: **"Think step by step."** — this alone improves accuracy on reasoning tasks.

**Zero-shot CoT:**
```
Q: A bat and a ball cost $1.10 total. The bat costs $1.00 more than the ball. How much does the ball cost?

Let's think step by step.
```

**Extended thinking (Claude):**
```python
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 8000},
    messages=[{"role": "user", "content": complex_problem}]
)
```

---

## Principle 5: Few-Shot Examples

Show the model the desired input/output pattern (3-5 examples is usually sufficient):

```
Convert product descriptions to SEO-optimized titles following these examples:

Input: "Blue running shoe with memory foam insole, available in sizes 7-12"
Output: "Memory Foam Running Shoes - Comfortable Athletic Footwear (Sizes 7-12)"

Input: "Stainless steel coffee mug, 16oz, keeps drinks hot for 8 hours"
Output: "16oz Insulated Stainless Steel Coffee Mug - 8-Hour Heat Retention"

Input: "Leather wallet, slim design, 6 card slots, RFID blocking"
Output: "Slim RFID Blocking Leather Wallet - 6 Card Slots"

Now convert:
Input: "{product_description}"
Output:
```

---

## Principle 6: Output Format Control

Specify exact output structure to make parsing reliable:

```
Return your analysis as JSON with exactly this structure:
{
  "sentiment": "positive" | "negative" | "neutral",
  "confidence": 0.0 to 1.0,
  "key_topics": ["topic1", "topic2"],
  "summary": "1-2 sentence summary"
}

Return only the JSON object, no explanation before or after.
```

Use Pydantic/structured output for guaranteed compliance:
```python
# Claude
client.messages.create(
    model="claude-opus-4-5",
    messages=[...],
    tools=[{
        "name": "extract_sentiment",
        "input_schema": SentimentResult.model_json_schema()
    }],
    tool_choice={"type": "tool", "name": "extract_sentiment"}
)

# OpenAI
client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[...],
    response_format=SentimentResult
)
```

---

## Principle 7: Provide Context and Constraints

```
Context:
- You are helping a team of 5 engineers
- The codebase uses Python 3.12, FastAPI, and PostgreSQL
- We have a 2-week deadline
- Code must pass our existing mypy strict configuration

Constraints:
- Do not introduce new dependencies without flagging the tradeoff
- Use async/await throughout (no sync I/O)
- All functions must have complete type annotations

Task: {task_description}
```

---

## Principle 8: Prompt Chaining for Complex Tasks

Break complex tasks into sequential prompts where each output feeds the next:

```python
# Step 1: Research
research_prompt = f"Research the key challenges in {topic}. Return 5 specific technical challenges."
challenges = llm.call(research_prompt)

# Step 2: Solutions (uses Step 1 output)
solutions_prompt = f"For each of these challenges:\n{challenges}\n\nPropose a concrete technical solution."
solutions = llm.call(solutions_prompt)

# Step 3: Synthesis
synthesis_prompt = f"Synthesize this research into a structured report:\nChallenges: {challenges}\nSolutions: {solutions}"
final_report = llm.call(synthesis_prompt)
```

---

## Principle 9: Reducing Hallucinations

```
Grounding rules:
1. Only use information explicitly provided in the <documents> below
2. If the answer is not in the documents, say "I don't have information about that"
3. When citing a fact, quote the relevant passage exactly
4. Do not extrapolate beyond what the documents state

<documents>
{retrieved_context}
</documents>

Question: {user_question}
```

**Additional techniques:**
- "If you are unsure, say so rather than guessing"
- "Cite your source for each claim"
- Use RAG (Retrieval Augmented Generation) to ground responses in verified documents
- Lower temperature (0.0-0.3) for factual tasks; higher (0.7-1.0) for creative tasks

---

## Principle 10: System Prompt Design for Agents

```
You are a software engineering assistant embedded in a developer's IDE.

## Identity
Name: CodeHelper
Role: Pair programmer and code reviewer

## Capabilities
- Write, review, and refactor code in Python, TypeScript, Go, Rust
- Explain code and architecture decisions
- Identify bugs and security vulnerabilities
- Write tests

## Behavioral Rules
1. Always show complete, working code — never truncate with "// rest of implementation"
2. Explain your reasoning briefly before showing code
3. If you are uncertain about an API or library, say so rather than guessing
4. When reviewing, use severity tags: [CRITICAL] [HIGH] [MEDIUM] [LOW]
5. Ask clarifying questions before large refactors

## Format
- Use markdown code blocks with language tags
- Keep explanations concise — developers prefer reading code over prose
- For multi-file changes, show each file separately with its path as a header

## Limitations
- You cannot run code or access the internet
- Always confirm destructive changes (file deletion, data loss) before proceeding
```

---

## Prompt Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| "Be creative" | Unpredictable, off-target outputs | Specify the exact creative direction |
| "Answer briefly" | Different models interpret "briefly" differently | Specify a word/sentence count |
| Negative-only constraints | Models comply poorly with "don't" | Reframe as positive: "always do X" instead of "don't do Y" |
| Prompt stuffing | Long, unstructured prompts confuse models | Use XML sections and headers |
| Missing output format | Free-form output is hard to parse | Always specify format for programmatic use |
| Single example | One example is not a "pattern" | Provide 3-5 varied examples |
| Ambiguous pronouns | "it" / "this" creates confusion | Be explicit — repeat the noun |
