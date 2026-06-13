# Phase 5: Template Atma

## Goal

Create the final response layer without using an LLM.

This proves the architecture before model integration.

## Why template Atma first

A small LLM can hide architecture problems.
A template system exposes them.

If verified facts are bad, the output will clearly be bad.
If verified facts are good, even a template can produce useful answers.

## Template Atma responsibilities

- Read verified facts.
- Choose a response template.
- Produce concise final answer.
- Mention uncertainty when facts are incomplete.
- Never invent information.

## Example templates

### Math answer

Input facts:

```json
{
  "type": "calculation",
  "expression": "45 * 123",
  "result": 5535
}
```

Output:

```text
45 * 123 = 5535.
```

### Math with explanation

If prompt asks `explain`, output:

```text
45 * 123 = 5535. This means 45 multiplied by 123 gives 5535.
```

### Missing facts

```text
I could not find enough verified information to answer safely. I detected the topic, but no reliable calculation or fact was produced.
```

## Atma rule

Atma is the mouth, not the brain.

The brain is the whole pipeline.

## Success criteria

Prompt:

```text
calculate 45 * 123 and explain it
```

Expected:

```text
45 * 123 = 5535. This means 45 multiplied by 123 gives 5535.
```

## Debug mode

Template Atma can include debug output:

```text
Selected operators: math_op
Verified facts: 1
Rejected facts: 0
Final answer: 45 * 123 = 5535.
```

This is useful during development.
