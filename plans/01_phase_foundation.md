# Phase 1: Foundation

## Goal

Create the base framework where every component communicates through structured data.

This phase is not about intelligence yet. It is about architecture discipline.

## Why this phase matters

If the internal pipeline is messy, adding an LLM will hide bugs instead of solving them. The first version should be simple, inspectable, and deterministic.

## Folder structure

```text
colony_ai/
  run_colony.py
  colony/
    __init__.py
    schemas.py
    config.py
    router.py
    operator.py
    verifier.py
    atma.py
  suboperators/
    __init__.py
    math_op.py
    keyword_op.py
    code_op.py
    planner_op.py
  memory/
    __init__.py
    memory_store.py
  tests/
    test_router.py
    test_math_op.py
    test_verifier.py
    test_pipeline.py
```

## Internal data contract

Every suboperator should return the same shape:

```json
{
  "operator": "math_op",
  "success": true,
  "confidence": 0.99,
  "facts": [],
  "warnings": [],
  "errors": [],
  "evidence": []
}
```

## Core principle

Natural language is for input and output only.

Inside the system, use structured JSON-like dictionaries.

Bad internal output:

```text
The answer is 5535.
```

Good internal output:

```json
{
  "type": "calculation",
  "expression": "45 * 123",
  "result": 5535,
  "method": "safe_arithmetic_eval"
}
```

## First implementation steps

1. Create project folder.
2. Create `schemas.py` with standard response helpers.
3. Create `run_colony.py` CLI.
4. Create empty router that always selects `keyword_op`.
5. Create placeholder `keyword_op`.
6. Create simple verifier that accepts successful outputs.
7. Create template Atma that prints verified facts.

## Success criteria

Command:

```bash
python3 run_colony.py "hello colony"
```

Expected behavior:

- Program runs without model.
- Router selects a fallback operator.
- Suboperator returns structured result.
- Verifier accepts it.
- Atma prints a readable answer.

## Mistakes to avoid

- Do not install heavy frameworks yet.
- Do not download models yet.
- Do not use raw `eval()`.
- Do not let suboperators return only strings.
- Do not build a web UI before CLI works.
