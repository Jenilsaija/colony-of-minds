
# Phase 26: Memory-Augmented Inference

## The problem

AtmaCore is small.
It cannot hold all the world's knowledge.
When asked about facts from memory,
it may not know them.

## The solution: retrieval-augmented generation (RAG)

AtmaCore should be augmented with a local knowledge store.

Process:
1. User asks a question.
2. Memory system searches for relevant facts.
3. Retrieved facts are prepended to the prompt.
4. AtmaCore synthesizes the answer from those facts.

```text
MEMORY SEARCH:
query: "OpenPrompt project"
results:
  - project_name: OpenPrompt
  - type: B2B SAI platform
  - description: GitHub for Agentic Prompts

VERIFIED_FACTS:
[
  {"key": "project_name", "value": "OpenPrompt"},
  {"key": "type", "value": "B2B SaaS platform"},
  {"key": "description", "value": "GitHub for Agentic Prompts"}
]

PROMPT: What is OpenPrompt?

ATMA OUTPUT: OpenPrompt is a B2B SaaS platform also described as "GitHub for Agentic Prompts."
```

## Retrieval mechanism

Use SQLite FTS5 for keyword search.
Only add embedding search later if needed.

```sql
SELECT value FROM facts WHERE key MATCH ? OR value MATCH ?
```

This is:
- fast enough on CPU
- low memory
- simple to implement
- surprisingly effective for most cases

## When to retrieve

Add a "retrieval trigger" list:
- questions asking "what is X"
- questions asking about past interactions
- questions asking for personal preferences
- any query that likely needs stored facts

On questions with no memory need, skip retrieval to keep latency low.

## Dynamic facts from colony

The colony suboperators produce verified facts.
These are injected as memory BEFORE retrieval.

So the flow is:
```text
1. Suboperator facts (immediate context)
2. Memory retrieval facts (stored context)
3. Combined into verified facts list
4. Sent to AtmaCore
```

## Training with memory augmentation

Some training examples should include memory-style context.
This teaches AtmaCore:
- how to use retrieved facts
- how to distinguish between present facts and missing facts
- how to admit when memory has no answer

Once AtmaCore is good at using memory,
the system's effective knowledge becomes nearly unlimited,
while the model itself stays 25M parameters.

This is one of the keys to beating models that are 20x larger:
the model stays small, the memory grows.
