# Phase 10: Evaluation and Benchmarking

## Goal

Prove that the colony is accurate, fast, and low-RAM.

## Why evaluation matters

Without tests, the system will feel intelligent but fail silently.

The colony must be measurable.

## Benchmark categories

### 1. Routing accuracy

Prompt:

```text
calculate 45 * 123
```

Expected:

```json
["math_op"]
```

### 2. Suboperator accuracy

Test math calculations, keyword extraction, code detection, and planning.

### 3. Verifier accuracy

Test that verifier rejects wrong facts.

### 4. Atma faithfulness

Atma must not invent facts beyond verified facts.

### 5. Latency

Measure total response time and per-operator time.

### 6. Memory usage

Track RAM before/after model usage.

## Test dataset

Start with 50 prompts:

- 15 math prompts
- 10 keyword extraction prompts
- 10 code prompts
- 10 planning prompts
- 5 ambiguous prompts

## Example test case

```json
{
  "prompt": "What is 45 * 123?",
  "expected_operators": ["math_op"],
  "expected_facts": [
    {"type": "calculation", "result": 5535}
  ]
}
```

## Success target for v0.1

- routing accuracy: 80%+
- math accuracy: 99%+
- verifier catches wrong math: 99%+
- Atma hallucination: near zero for template mode
- RAM without model: under 150 MB

## Future target

v1.0 should include a regression suite that runs before every release.
