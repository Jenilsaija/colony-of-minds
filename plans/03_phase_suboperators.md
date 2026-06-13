# Phase 3: Suboperators

## Goal

Create small specialist modules that solve narrow tasks accurately.

Suboperators are the real strength of the architecture.

They should be tiny, testable, and deterministic where possible.

## Suboperator design rule

Each suboperator should do one thing well.

It should not try to chat.
It should not produce long explanations.
It should not invent missing information.

## Standard function signature

```python
def execute(prompt: str, context: dict) -> dict:
    ...
```

## First suboperators

### 1. math_op

Responsibilities:

- Extract arithmetic expressions.
- Calculate safely.
- Support percentage patterns.
- Return exact results.

Must avoid:

- raw `eval()`
- arbitrary Python execution
- unsupported symbolic math claims

Example facts:

```json
[
  {
    "type": "calculation",
    "expression": "45 * 123",
    "result": 5535,
    "method": "safe_arithmetic_eval"
  }
]
```

### 2. keyword_op

Responsibilities:

- Extract numbers, URLs, emails, dates, languages, key nouns.
- Identify action verbs.
- Provide useful metadata to other operators.

Example facts:

```json
[
  {"type": "number", "value": 45},
  {"type": "number", "value": 123},
  {"type": "intent_word", "value": "calculate"}
]
```

### 3. code_op

Responsibilities:

- Detect programming language.
- Run syntax checks if safe.
- Identify likely bug category.
- Return structured findings.

Example facts:

```json
[
  {
    "type": "code_language",
    "language": "python",
    "confidence": 0.8
  }
]
```

### 4. planner_op

Responsibilities:

- Break large requests into phases.
- Return task list.
- Estimate dependencies.

Example facts:

```json
[
  {
    "type": "plan",
    "steps": ["Build router", "Add math_op", "Add verifier"]
  }
]
```

## Operator metadata

Each operator should define:

```python
OPERATOR_INFO = {
    "name": "math_op",
    "version": "0.1.0",
    "capabilities": ["arithmetic", "percentage"],
    "cost": "low",
    "safe_for_parallel": True
}
```

## Success criteria

- Each suboperator can run alone.
- Each suboperator has tests.
- Each suboperator returns valid schema.
- Failures return `success: false`, not crashes.

## Future suboperators

- `file_op`: reads local files safely.
- `web_op`: fetches web/API data.
- `database_op`: queries data.
- `invoice_op`: handles billing calculations.
- `social_media_op`: drafts posts from structured points.
- `business_strategy_op`: creates business plans.
- `prompt_engineering_op`: improves prompts.
