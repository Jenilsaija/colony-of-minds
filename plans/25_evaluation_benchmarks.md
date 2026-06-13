
# Phase 25: Evaluation Against Existing Small LLMs

## Why benchmark

Without benchmarks, you cannot prove AtmaCore is truly smarter.
You need objective comparison.

## Competitor models to benchmark against

```yaml
tinyllama_1.1b:
  params: 1.1B
  size_float16: ~2.2 GB
  type: decoder-only transformer

qwen2.5_0.5b:
  params: 0.5B
  size_float16: ~1.0 GB
  type: decoder-only transformer

smollm2_360m:
  params: 360M
  size_float16: ~720 MB
  type: decoder-only transformer

phi_1.5:
  params: 1.3B
  size_float16: ~2.6 GB
  type: decoder-only transformer
```

## AtmaCore target

```yaml
atmacore:
  params: 25M
  size_float16: ~50 MB
  target: outperform models 20x its size
           on synthesis and fact-grounded QA
```

## Benchmark tasks

### Task 1: Fact-grounded synthesis

Given facts:
```
{"type": "calculation", "expression": "45 * 123", "result": 5535}
```

Question: What is 45 * 123?
Expected: 45 * 123 equals 5535.

Metric: exact match vs hallucination.

### Task 2: Missing-facts handling

Given: no relevant facts.
Question: What is the capital of Mars?
Expected: Say there is no verified information.
Failure: Invent a capital.

### Task 3: Style adaptation-short

Preference: short answers.
Input: calculating 45 * 123.
Expected: "45 * 123 = 5535."
Failure: long discourse about multiplication.

### Task 4: Multi-fact synthesis

Given: 5 facts about a project.
Question: Summarize the project.
Expected: Summary that includes all 5 facts, no more.

### Task 5: Contradiction awareness

Given: fact_A says language is Python, fact_B says language is JavaScript.
Question: What language is the code in?
Expected: "There is conflicting information."
Failure: picks one and states it as absolute fact.

### Task 6: Numerical accuracy

Given: financial data facts.
Question: What is the total revenue?
Expected: Correct sum from facts.
Failure: any number not matching computed sum.

## Scoring

Each task scored:
- 2.0: perfect answer (correct facts, natural style, honest uncertainty)
- 1.0: correct facts, awkward style
- 0.5: correct facts but with unverified additions
- 0.0: hallucinated or completely wrong

Compare mean score per task across all models.

## Target benchmark results

```yaml
fact_synthesis:
  atmacore_target: 1.8+
  tinyllama_1.1b_expected: 1.2
  qwen_0.5b_expected: 1.4

missing_facts:
  atmacore_target: 1.9+
  tinyllama_expected: 0.8
  qwen_expected: 1.1

numerical_accuracy:
  atmacore_target: 1.95+
  tinyllama_expected: 1.3
  qwen_expected: 1.5

# On these tasks, AtmaCore must beat models 20x its size
# because it has less general knowledge but more synthesis discipline
```

## Benchmarks should run automatically

Every time a new AtmaCore checkpoint is saved,
run the benchmark suite.
Track scores over time.
Do not deploy a new version that regresses on any task.
