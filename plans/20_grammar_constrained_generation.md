
# Phase 20: Grammar-Constrained Generation

## The problem

Even after distillation and preference training,
AtmaCore might occasionally produce output that:
- has invalid JSON when JSON output is required
- omits required fields when structured output is needed
- breaks formatting rules for specific response types

## Solution: grammar-constrained generation

Teach AtmaCore to always produce valid structured output
by adding grammar constraints during inference.

## What this means

During text generation, not all next tokens are allowed.
The generation is constrained by a formal grammar.

Example:

User asks for JSON output:
```json
{
  "answer": "...",
  "confidence": 0-1,
  "uses_facts": true
}
```

Grammar rules:
- After `{`, next token must be a quote for a key
- After `"answer":`, next token must start a string
- After string, next token must be a comma or closing brace
- After `"confidence":`, next token must be a number 0-1

This is called "constrained decoding" or "grammar-guided generation."

## Training with grammar awareness

During training, add grammar-related tokens to the data:
- `<json_start>`
- `<json_key>` `<json_value>` `<json_end>`
- `<bullet_list>` `<number_list>`

The model learns which format to use based on the user's request.

Eventually, constrained decoding can be handled at runtime
so even if the model slightly drifts, the grammar enforces correctness.

## Implementing constrained decoding on CPU

Several approaches:
1. Filter the token probabilities at each step:
   eliminate tokens that would break grammar,renormalize.
2. Use a finite-state machine that tracks grammar state
   and only allows transitions that are valid.
3. Use a library like `outlines` or `guidance` that supports
   grammar-constrained generation.

For AtmaCore on CPU:
- the FSSM (finite-state machine) approach is low-overhead
- adds almost zero latency
- works without GPU

## Why this gives AtmaCore an edge

Most small LLMs cannot guarantee:
- valid JSON output
- correct markdown tables
- required fields present
- consistent formatting

AtmaCore can guarantee these by design.
This makes it more trustworthy in production systems.

And for synthesis tasks, formatting consistency
is a huge part of "accuracy."
