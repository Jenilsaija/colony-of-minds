# Phase 9: Runtime, Parallelism, and Low-RAM Engineering

## Goal

Make the colony run smoothly on 1 GB RAM and 2-core CPU.

## Runtime principles

1. Lazy-load everything.
2. Run only necessary suboperators.
3. Limit parallelism to hardware.
4. Keep prompts small.
5. Prefer deterministic code over model calls.
6. Use the model only at final synthesis.

## Parallelism strategy

For 2-core CPU:

```text
max_workers = 2
```

Good parallel tasks:

- math_op + keyword_op
- file search + keyword extraction
- API fetch + local parsing

Bad parallel tasks:

- multiple LLM calls
- many subprocesses
- heavy model plus CPU-intensive tools

## Memory budget target

Approximate v0.1 without model:

- Python runtime: 30-70 MB
- suboperators: 1-20 MB
- memory store: 1-20 MB
- total: under 150 MB

With model Atma:

- Python pipeline: 50-120 MB
- llama.cpp model: depends on model
- OS reserve: must leave enough RAM

## Model runtime rule

On 1 GB RAM, do not keep unnecessary services running.

If using `llama-server`, monitor memory.
If memory is too tight, use `llama-cli` per request or use Template Atma.

## Observability

Every request should log:

- prompt length
- selected operators
- execution time per operator
- memory usage if available
- final Atma mode: template or model

## Success criteria

Run 20 requests in a row without memory crash.

Measure:

- average latency
- max memory usage
- failure rate

## Future optimization

- operator result caching
- compiled math parser
- Rust or Go runtime for extreme low memory
- persistent llama.cpp server for machines with more RAM
- microservice mode for larger deployments
