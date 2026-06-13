
# Phase 18: Knowledge Distillation for AtmaCore

## The idea

You do not have a big local model.
But you can borrow the knowledge of a big model temporarily.

Use a strong teacher model (GPT-4, Claude, Mistral 7B)
to generate training data, then learn from that data.
The small model imitates the teacher's answers.

This is called knowledge distillation.

AtmaCore will be smaller than the teacher
but can capture the teacher's synthesis quality.

## Distillation strategy

### Step 1: Generate teacher outputs

For each prompt-fact pair in your dataset,
ask the teacher model to generate the ideal answer.

System prompt to teacher:
```
You are a synthesis engine.
Given the user prompt and verified facts,
produce the best possible answer.
Only use the verified facts.
Do not hallucinate.
Be concise and natural.
```

Collect 50000-100000 high-quality teacher outputs.

### Step 2: Filter teacher outputs

Not all teacher outputs are good.
Filter out:
- answers that add unverified facts
- answers that are too long or too short
- answers that do not match the style you want
- answers with hallucination markers

Keep only the best 30000-60000.

### Step 3: Train AtmaCore on filtered outputs

Standard cross-entropy loss:
AtmaCore learns to predict what the teacher would say.

### Step 4: Divergence loss

Use KL divergence between:
- teacher's token probability distribution (soft labels)
- AtmaCore's token probability distribution

This teaches AtmaCore the teacher's uncertainty patterns too,
not just the most likely token.

## Important: do not just copy the teacher

The goal is not to be the teacher.
The goal is to be:
- as accurate as the teacher on synthesis tasks
- faster at inference
- runnable on small hardware
- more consistent in fact adherence (the teacher might still hallucinate)

So after distillation training, add:
- hard fact-verification losses
- penalties for tokens that introduce unverified content
- rewards for matching the facts exactly

## Data augmentation through distillation

Use the teacher to create:
- 5 different answers for the same prompt-facts pair
- paraphrases of good answers
- wrong answers with labeled error types

This creates contrastive pairs:
1. The teacher says X (good)
2. AtmaCore says Y (adds fake fact)
3. Loss penalizes Y heavily

This kind of training is what makes AtmaCore smarter than simply
scaling up a generic small model.
