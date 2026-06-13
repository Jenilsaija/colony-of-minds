# Phase 4: Verifier

## Goal

Create a quality-control layer between suboperators and Atma.

The verifier is what prevents the Atma from speaking garbage confidently.

## Verifier responsibilities

1. Validate schema.
2. Reject empty outputs.
3. Reject low-confidence outputs.
4. Recompute critical facts when possible.
5. Detect contradictions between operators.
6. Mark missing information.
7. Produce a clean verified-facts bundle.

## Verifier output

```json
{
  "verified": true,
  "facts": [],
  "rejected": [],
  "warnings": [],
  "missing": []
}
```

## Verification examples

### Math verification

If `math_op` returns:

```json
{
  "expression": "45 * 123",
  "result": 5535
}
```

Verifier recomputes independently.

If result matches, accept.
If result does not match, reject.

### Confidence verification

If any suboperator returns confidence below threshold, mark as uncertain.

Suggested thresholds:

- 0.90+ = strong
- 0.70-0.89 = usable with warning
- below 0.70 = do not use for final answer unless no alternative

### Contradiction example

`operator_a` says language is Python.
`operator_b` says language is JavaScript.

Verifier should either:

- choose higher-confidence fact
- ask for clarification
- present uncertainty

## Atma boundary

Atma should only receive verified facts.

Do not pass raw suboperator outputs directly into Atma unless debugging mode is enabled.

## Success criteria

Test case:

```json
{
  "operator": "math_op",
  "success": true,
  "confidence": 0.99,
  "facts": [
    {"type": "calculation", "expression": "45 * 123", "result": 9999}
  ]
}
```

Expected:

Verifier rejects it.

## Long-term idea

Verifier can become a whole council:

- schema verifier
- math verifier
- safety verifier
- factual consistency verifier
- policy verifier
- memory consistency verifier

But v0.1 should stay simple.
