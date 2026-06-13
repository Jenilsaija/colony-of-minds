
# Phase 24: Safety, Alignment, and Hallucination Prevention

## Why this phase is critical

AtmaCore will be the voice of the colony.
If it hallucinates, the entire system misleads the user.

Existing small LLMs hallucinate frequently.
AtmaCore must be fundamentally stronger at fact adherence.

## Hallucination sources in small models

1. Pattern completion bias:
   the model learned to complete patterns from internet text,
   so it generates plausible-sounding text even without facts.

2. Insufficient context grounding:
   small models lose track of which facts apply to which part.

3. Overconfidence calibration:
   small models do not know what they do not know.

## Prevention strategies

### Hard fact anchoring

During training, every fact used in the answer is specially tagged.
The model learns:
"attend to fact tokens, then verbalize them."

Use:
```
<fact>type=calculation</fact>
<fact>expression=45*123</fact>
<fact>result=5535</fact>
```

If the model produces a fact not in the tagged list,
it is a hallucination. Penalize heavily in training.

### Uncertainty training

Teach three confidence levels:
- confident: all facts are present and verified
- partial: some facts are present, answer includes "based on available information"
- unknown: facts are missing, model explicitly says so

The model must learn to calibrate its own confidence.

### Consistency verification loss

During training, add a loss term that penalizes:
- a fact in the answer that does not appear in the input facts
- a number in the answer that is not in the facts
- a name in the answer that is not in the facts

This is entity-level consistency checking via a simple script
that runs during training.

### Output constraints at runtime

Do not let AtmaCore generate numbers that are not in the verified facts.
Do not let it generate specific facts without evidence tokens.
Implement this as a post-processing checker.

### Red-team test suite

Create 100 tricky prompts designed to cause hallucinations:
- prompts with no facts
- prompts with misleading facts
- prompts that ask for opinions as facts
- prompts with numerical traps

Measure how often AtmaCore hallucinates compared to TinyLlama, Qwen 0.5B.
The target: AtmaCore hallucinates at least 50% less.

## Alignment principles for AtmaCore

1. Never claim certainty without facts.
2. Never generate URLs, phone numbers, or specific details without facts.
3. Always prefer "I do not know" over fabrication.
4. When asked for opinions, label them as opinions, not facts.
5. Always stay within the verified fact boundary.

This is not just training.
It is architectural alignment.
The model should find it harder to hallucinate than to be correct.
