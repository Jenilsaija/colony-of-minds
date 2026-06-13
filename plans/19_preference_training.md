
# Phase 19: Contrastive and Preference Training

## Why this phase matters

After distillation, AtmaCore "imitates" the teacher.
But imitation alone is not enough.

You want AtmaCore to know:
- which answers are better than others
- why an answer with a hallucination is worse than one without
- what "good synthesis" really means beyond just matching text

This is preference training.

## Contrastive training method

For each training example, create three versions:

### Version A (correct answer)

```text
Input: prompt + verified facts
Target: 45 * 123 = 5535.
```

### Version B (hallucinating answer)

```text
Input: prompt + verified facts
Target: 45 * 123 = 5535. This is also equal to 5500 + 35, and 5535 is a prime number.
```

(5535 is NOT a prime number, so this is a hallucination.)

### Version C (over-confident incomplete answer)

```text
Input: prompt + verified facts
Target: The answer is definitely 5535. There is no other possible result.
```

(Over-confident tone, not ideal for uncertain cases.)

## Training signal

The model learns:
- reward high when output matches Version A
- penalty high when output matches Version B (hallucination)
- penalty medium when output matches Version C (over-confident)

This teaches the model to rank answers internally
and prefer factually grounded responses.

## Reward modeling approach

Train a small reward model (can be 1-2 layer classifier)
that takes a candidate answer and returns a score:
- 1.0 = perfect fact adherence, natural style
- 0.5 = correct facts, awkward style
- 0.0 = hallucinated facts, dangerous output

Then use this reward model during RL-style training
to push AtmaCore toward higher-reward outputs.

## Reinforcement Learning from Human Feedback (RLHF) with tiny scale

You do not need massive human feedback.
But you do need:
- 200-500 manual ratings of AtmaCore's outputs
- preference pairs: answer A is better than answer B
- clear rubric for what makes an answer better

Even 200 human-rated pairs can significantly improve instruction
following in small models.

## Simplified approach if RLHF is too complex

Use DPO (Direct Preference Optimization):
- collect preference pairs (chosen vs rejected)
- train AtmaCore to prefer the chosen answer directly
- this is simpler than full RLHF

Libraries like `trl` support DPO well
and can work with 25M parameter models on limited hardware.
