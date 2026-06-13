# Phase 2: Main Operator / Router

## Goal

Build the Main Operator that decides which specialists should wake up.

The Main Operator should not answer the user. It should only route.

## Routing levels

### Level 1: Keyword routing

Simple and fast.

Examples:

- `calculate`, `compute`, `sum`, `multiply` -> `math_op`
- `code`, `bug`, `syntax`, `function` -> `code_op`
- `summarize`, `keywords`, `extract` -> `keyword_op`
- `plan`, `steps`, `roadmap` -> `planner_op`

### Level 2: Pattern routing

Use regex/patterns.

Examples:

- `45 * 123` -> `math_op`
- `def function_name(` -> `code_op`
- URL detected -> `keyword_op` or `web_op`

### Level 3: Small classifier later

Only after keyword routing works, add tiny ML classification if needed.

Do not start here.

## Router output format

```json
{
  "selected_operators": ["math_op", "keyword_op"],
  "reason": "Detected arithmetic expression and request for explanation.",
  "confidence": 0.92
}
```

## Routing strategy

Use multi-label routing.

A prompt can need multiple suboperators:

Prompt:

```text
Calculate 18% GST on 25000 and write a short explanation.
```

Operators:

```json
["math_op", "keyword_op"]
```

## Fallback logic

If no route is found:

1. Use `keyword_op` to extract what is known.
2. Use template Atma to say what the system understood.
3. Ask a concise clarification if required.

## Low-RAM rule

Router must be pure Python and dependency-free in v0.1.

## Success criteria

Input:

```text
calculate 45 * 123
```

Router result:

```json
{
  "selected_operators": ["math_op"],
  "confidence": 0.9
}
```

Input:

```text
fix this python code syntax
```

Router result:

```json
{
  "selected_operators": ["code_op"],
  "confidence": 0.8
}
```

## Future upgrades

- Add routing memory: learn which operator worked for which prompt.
- Add priority scores.
- Add cost estimation.
- Add max runtime budget per operator.
