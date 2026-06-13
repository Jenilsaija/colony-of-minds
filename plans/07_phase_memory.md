# Phase 7: Memory

## Goal

Give the colony long-term knowledge without increasing model size.

Memory should be outside the LLM.

## First memory design

Start with SQLite or JSON.

Recommended v0.1 memory tables:

### facts

- id
- key
- value
- source
- created_at
- updated_at
- confidence

### interactions

- id
- user_prompt
- selected_operators
- verified_facts
- final_answer
- created_at

### preferences

- id
- name
- value
- confidence
- updated_at

## Why SQLite first

SQLite is:

- lightweight
- reliable
- local
- low RAM
- easy to query
- good enough for many use cases

## Avoid early

Do not start with:

- Chroma
- FAISS
- full embedding pipeline
- cloud vector DB
- massive memory frameworks

These can come later.

## Memory operators

Add a `memory_op` suboperator.

Responsibilities:

- retrieve relevant facts
- store durable facts
- detect repeated user preferences
- provide context to Atma

## Memory safety

Not everything should be saved.

Save:

- stable user preferences
- project facts
- reusable instructions
- trusted knowledge

Do not save:

- temporary calculations
- sensitive secrets
- one-time commands
- unverified claims

## Success criteria

User says:

```text
Remember my project name is OpenPrompt.
```

System stores:

```json
{"key": "project_name", "value": "OpenPrompt"}
```

Later user says:

```text
What is my project name?
```

System retrieves and answers:

```text
Your project name is OpenPrompt.
```
