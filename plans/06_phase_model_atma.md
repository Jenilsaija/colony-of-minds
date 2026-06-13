# Phase 6: Tiny Model Atma

## Goal

Add a small local model only for final language synthesis.

The tiny model should not perform the main reasoning. It should convert verified facts into a natural answer.

## Recommended model category

For 1 GB RAM, prefer very small GGUF models first:

1. Qwen2.5 0.5B Instruct GGUF Q4
2. SmolLM2 360M Instruct GGUF
3. TinyLlama 1.1B Q4 only if memory allows

## Recommended runtime

Use llama.cpp.

Two integration options:

### Option A: `llama-cli`

Good for simplest integration.
Python calls a command-line process and passes the prompt.

Pros:

- simple
- fewer Python dependency issues
- good for experiments

Cons:

- process startup can be slow

### Option B: `llama-server`

Good for repeated requests.

Pros:

- model stays loaded
- faster repeated calls
- OpenAI-compatible local API

Cons:

- always consumes RAM while running

## Atma model prompt

Use a strict prompt:

```text
You are Atma, a synthesis engine.
Use only VERIFIED_FACTS.
Do not invent facts.
If the facts are insufficient, say what is missing.
Keep the answer concise and clear.

USER_PROMPT:
{user_prompt}

VERIFIED_FACTS:
{verified_facts_json}

FINAL_ANSWER:
```

## Low-RAM settings

Suggested starting settings:

- context length: 512 or 1024
- threads: 2
- batch size: small
- max output tokens: 128
- temperature: 0.2

## Important limitation

A 0.3B-0.5B model is not a genius.

It may write awkward text.
That is acceptable because its job is not deep reasoning.
The verified facts carry the intelligence.

## Fallback rule

If the model fails, use Template Atma.

Never let the whole system fail because the model is unavailable.

## Success criteria

Atma receives:

```json
[
  {"type": "calculation", "expression": "45 * 123", "result": 5535}
]
```

It outputs:

```text
45 multiplied by 123 equals 5535.
```

It must not add unrelated facts.
