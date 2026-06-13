
# Phase 15: Dual-Tokenizer for AtmaCore

## Why standard tokenizers are not ideal

Byte-Pair Encoding (BPE) tokenizers are optimized for natural language.
They treat JSON brackets, colons, numbers, and keys as inefficient token splits.

AtmaCore's input is always a mix of:
```
USER_PROMPT: {natural language}
VERIFIED_FACTS: {structured JSON-like data}
```

The model needs to understand both fluidly.

## Dual-tokenizer design

### Natural tokenizer

Standard BPE with:
- 24000-32000 merges
- optimized on your training corpus
- handles English plus code tokens

### Structured tokenizer

Designed specifically for:
- JSON syntax: braces, brackets, colons, commas, quotes
- number patterns: integers, floats, scientific notation
- key-value patterns
- field names from your colony's output schemas
- boolean, null-like values

Use a rule-based pre-tokenizer that segments structured data
before subword merging.

Example:
```json
{"type": "calculation", "result": 5535}
```

Standard BPE might tokenize this as:
```text
{" type ":" calculation "," result ": 5535 }
```
(many tokens for braces and punctuation)

Structured tokenizer produces:
```text
{ "type": "calculation", "result": 5535 }
```
(fewer tokens because JSON symbols are single tokens)

### Shared embedding space

Both tokenizers map into the same vocabulary of 32000 tokens.
The structured tokenizer is injected into the training data
so the model learns to process it naturally.

## Training the tokenizer

Step 1: Collect a sample of 1M lines from your training corpus.
Step 2: Split into natural and structured segments.
Step 3: Train natural BPE on natural segments.
Step 4: Train structured BPE on structured segments.
Step 5: Merge vocabularies, deduplicate, cap at 32000.

Use `sentencepiece` or `tokenizers` library for training.

## Special tokens

Reserve special tokens for:
- `<|user_prompt|>`
- `<|verified_facts|>`
- `<|end_facts|>`
- `<|final_answer|>`
- `<|missing_facts|>`
- `<|uncertain|>`
- `<|pad|>`

These help the model learn the input-output structure
and handle synthesis boundaries correctly.
