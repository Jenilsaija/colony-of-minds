# Architecture Decisions

## Decision 1: Suboperators are not LLMs by default

### Reason

Tiny LLMs under 10 MB are not strong enough for broad language understanding.

### Decision

Suboperators should be deterministic code, symbolic tools, small classifiers, parsers, memory lookups, and API wrappers.

### Result

Lower RAM, higher accuracy, easier debugging.

---

## Decision 2: Use structured JSON internally

### Reason

Natural language between modules causes ambiguity and hallucination.

### Decision

All internal communication uses dictionaries/JSON-like structures.

### Result

Verifier can inspect facts reliably.

---

## Decision 3: Build without LLM first

### Reason

The architecture must work before adding a model.

### Decision

v0.1 uses Template Atma.

### Result

Faster development, easier testing, lower RAM.

---

## Decision 4: Atma is the mouth, not the brain

### Reason

On tiny hardware, the model cannot do everything well.

### Decision

Atma only synthesizes verified facts.

### Result

Less hallucination and lower compute.

---

## Decision 5: Verifier is mandatory

### Reason

Suboperators can fail or disagree.

### Decision

Every output passes through verifier before Atma.

### Result

More trustworthy final answers.

---

## Decision 6: SQLite before vector DB

### Reason

1 GB RAM systems cannot waste memory on heavy databases.

### Decision

Use SQLite/JSON first. Add vector search later only if needed.

### Result

Simple, reliable, low-resource memory.

---

## Decision 7: Parallelism must be limited

### Reason

2-core CPU can be overloaded easily.

### Decision

Use max 2 workers for v0.1.

### Result

Stable runtime under small hardware.

---

## Decision 8: Safety before autonomy

### Reason

An operator system can take actions, not just talk.

### Decision

Risky tools require confirmation and logging.

### Result

Trustworthy automation path.

---

## Final architecture mantra

```text
Tools find facts.
Suboperators specialize.
Verifier protects truth.
Atma speaks clearly.
Memory keeps continuity.
```
