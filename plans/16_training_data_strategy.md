
# Phase 16: Training Data Strategy for AtmaCore

## Core principle

AtmaCore is not trained on "the internet."
It is trained on high-quality synthesis pairs.

Input: user prompt + verified facts
Output: perfect human-written answer

Every data point teaches the model one thing:
"Given these exact facts, produce this exact response."

## Data categories

### Category 1: Verified-fact synthesis pairs (60% of data)

Source: manually created or verified by the colony.

Format:
```json
{
  "prompt": "What is 45 * 123?",
  "facts": [{"type": "calculation", "expression": "45 * 123", "result": 5535}],
  "answer": "45 multiplied by 123 equals 5535."
}
```

### Category 2: Template synthesis (15% of data)

Multiple styles of answering the same facts:
- formal tone
- casual tone
- bullet-point format
- one-line answer
- step-by-step explanation

This teaches the model that facts are fixed but expression is flexible.

### Category 3: Missing-fact responses (10% of data)

Teaches the model what to say when facts are incomplete.

```json
{
  "prompt": "What is the capital of Mars?",
  "facts": [],
  "answer": "There is no verified information about a capital of Mars in the provided facts."
}
```

### Category 4: Contradiction handling (10% of data)

Two suboperators disagree.
Model learns to express uncertainty.

### Category 5: Style adaptation (5% of data)

Given user preference "use short answers" or "explain like I am five",
model adapts style while keeping facts fixed.

## Data sources

### Synthetic generation (recommended for initial training)

Use existing larger models to generate your training data.
But verify every output manually or with automated checks.

Process:
1. Write a Python script that generates 10000 prompt-fact-answer pairs.
2. Use a strong existing model (even GPT-4 API) to draft answers.
3. Run automated fact-checking scripts to filter bad pairs.
4. Manually verify a random sample of 500.
5. Keep only verified pairs.

This is called "synthetic data generation"
and it is how many modern efficient models are bootstrapped.

### High-quality public datasets (filtered)

- FLAN (for instruction following)
- Alpaca-style datasets (for structured responses)
- MathQA (for math synthesis)
- SQuAD (for grounded QA, good for fact adherence)

Filter these heavily.
Remove any pairs with hallucinations, errors, or ambiguity.

### Colony-generated data (best source, long-term)

As the colony runs in production, every verified interaction
becomes a training example.

The colony improves its own model over time.

## Dataset size targets

```yaml
phase_1_pretrain: 2-5 million tokens (quality over quantity)
phase_2_finetune: 500k-1 million synthesis pairs
phase_3_colony_data: continuous from production usage
```

## Data quality over quantity

1 bad example can teach the model bad habits.
1000 good examples can teach it precision.

Prioritize:
- diversity of prompts
- correctness of facts
- naturalness of answers
- coverage of failure modes (missing facts, contradictions)
