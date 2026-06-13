# Master Roadmap

## Vision

Build a low-resource AI operator framework where intelligence comes from composition, not from one huge model.

The system should behave like a small digital organism:

1. Sense the user request.
2. Decide which organs/suboperators are needed.
3. Execute precise specialist work.
4. Verify the result.
5. Speak through Atma.
6. Store useful knowledge in memory.
7. Improve through tests and feedback.

## Phase summary

### Phase 1: Foundation

Goal: Create the project skeleton, data contracts, and CLI pipeline.

Deliverable:

- `colony_ai` folder
- standard JSON schema for all suboperators
- CLI entry point
- no LLM yet

Success test:

```bash
python3 run_colony.py "hello"
```

The system should route the prompt and return a basic response.

---

### Phase 2: Main Operator / Router

Goal: Decide which suboperators should run.

Deliverable:

- keyword router
- intent router
- confidence score
- fallback strategy

Success test:

Prompt: `calculate 45 * 123`

Expected selected operator:

```json
["math_op"]
```

---

### Phase 3: First Suboperators

Goal: Add deterministic micro-specialists.

Start with:

1. `math_op`
2. `keyword_op`
3. `code_op`
4. `planner_op`

Success test:

Suboperators return structured JSON, not natural-language paragraphs.

---

### Phase 4: Verifier

Goal: Reject weak, empty, contradictory, or unsafe outputs.

Deliverable:

- confidence threshold
- independent math checking
- schema validation
- missing-facts detection

Success test:

If `math_op` says `45 * 123 = 9999`, verifier rejects it.

---

### Phase 5: Template Atma

Goal: Generate final answers without any LLM.

Deliverable:

- template-based answer generator
- math response template
- explanation response template
- fallback response template

Success test:

Prompt: `calculate 45 * 123 and explain it`

Expected answer includes `5535` and does not invent extra facts.

---

### Phase 6: Tiny Model Atma

Goal: Add a small GGUF model for natural wording only.

Recommended model class:

- Qwen2.5 0.5B Instruct GGUF Q4
- SmolLM2 360M Instruct GGUF
- TinyLlama 1.1B Q4 only if RAM allows

Success test:

Atma uses only verified facts. If facts are missing, it says so.

---

### Phase 7: Memory

Goal: Add persistent knowledge without increasing model size.

Recommended first memory:

- SQLite
- JSON for settings
- FTS5 search if available

Avoid initially:

- Chroma
- FAISS
- heavy embedding models

Success test:

The system stores a user preference and recalls it later.

---

### Phase 8: Tools

Goal: Let suboperators call controlled tools.

Tools can include:

- safe calculator
- shell command runner with permission rules
- file reader
- code runner
- HTTP/API caller
- local document search

Success test:

Tool calls are logged and verified before Atma speaks.

---

### Phase 9: Runtime and Parallelism

Goal: Make it work well on 1 GB RAM and 2-core CPU.

Rules:

- max 2 concurrent workers
- lazy-load heavy components
- unload model when not needed if possible
- keep context small
- prefer processes for isolation only when needed

Success test:

Common requests complete without swap death or memory explosion.

---

### Phase 10: Evaluation

Goal: Prove the architecture works.

Metrics:

- routing accuracy
- suboperator accuracy
- verifier rejection accuracy
- memory usage
- latency
- hallucination rate

Success test:

A small benchmark suite runs after every change.

---

### Phase 11: Productization

Goal: Turn framework into a usable operator product.

Possible products:

- CLI personal assistant
- WhatsApp/Telegram AI operator
- business automation agent
- local-first AI workstation
- SaaS micro-agent framework

Success test:

A real user can install and use it with clear docs.

## Best first milestone

Build `v0.1` with:

- router
- safe math operator
- keyword operator
- verifier
- template Atma
- CLI
- tests

No LLM yet.

This gives the architecture a working skeleton before adding model complexity.
