
# Phase 23: Making AtmaCore Multi-Domain Without Growing

## The tension

A 25M parameter model cannot hold as much knowledge as a 7B model.
But it can be very good at specific domains if:
- it is trained heavily on those domains
- it uses external memory for facts
- it defers to suboperators for computation

## Strategy: domain-adaptive LoRA

Instead of one model that does everything,
use one base AtmaCore plus domain-specific adapters.

```text
base_atmacore_25M
|
+-- math_lora (rank 4, ~300K params)
+-- code_lora (rank 4, ~300K params)
+-- business_lora (rank 4, ~300K params)
+-- writing_lora (rank 4, ~300K params)
+-- conversation_lora (rank 4, ~300K params)
```

At runtime:
1. Router detects domain.
2. Load only the relevant LoRA adapter on top of base model.
3. Inference uses base LoRA for that domain.

The base model provides general language ability.
The LoRA adapter provides domain style and vocabulary.

This gives the impression of a much larger system
while staying very small in memory.

## Domain definition for AtmaCore

Recommend creating LoRAs for:

### math_synthesis
- synthesizing calculation results into natural language
- explaining unit conversions
- describing percentage changes

### code_explanation
- describing code behavior
- explaining bugs
- summarizing code processes

### business_response
- invoices, metrics, reports, summaries
- professional tone

### casual_conversation
- everyday chat
- style adaptation

## Training data per domain

Each LoRA needs only 10000-50000 domain-specific examples.
This trains in minutes on ARM instance.

And domain LoRA can be trained as data accumulates
without retraining the base model.

This is the most powerful scaling strategy:
the base stays stable, domains grow independently.

## Multi-domain at inference

If the prompt is cross-domain:
```text
Calculate 18% GST on 25000 and write a professional summary.
```

The system can:
- use math_lora for the calculation synthesis
- use business_lora for the summary tone
- or stack both LoRAs

Stacking approach:
```python
output = model(input, lora_math)
output = output_style_transfer(output, lora_business)
```

Keeping it simple at first is better.
Start with choosing the primary domain, do stacking later.
