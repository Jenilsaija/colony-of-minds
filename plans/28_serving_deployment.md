
# Phase 28: Serving Infrastructure and Model Deployment

## Deployment modes

### Mode A: Embedded in colony (default)

AtmaCore runs as a Python library within the colony process.

Pros:
- simplest
- no network overhead
- lowest latency
- works offline

Cons:
- model in same memory as colony

### Mode B: Local HTTP server

Run AtmaCore as a tiny HTTP server on localhost:9090.

Request:
```json
POST /synthesize
{
  "prompt": "What is 45 * 123?",
  "facts": [{"type": "calculation", "result": 5535}],
  "max_tokens": 100
}
```

Response:
```json
{
  "answer": "45 multiplied by 123 is 5535.",
  "tokens_used": 12
}
```

Pros:
- colony and model separate
- can upgrade model independently
- faster "warm" inference if server stays up

Cons:
- always consumes RAM while running

### Mode C: On-demand subprocess

Call AtmaCore CLI script when needed.

Pros:
- zero RAM when not in use
- simplest failure recovery

Cons:
- process startup time per request

## Recommended: Mode A for v0.1

Keep it simple.
Embed the model in the colony process.
Split into a server only when you need to scale.

## Model versioning

Name model files clearly:
```
atmacore-v1.0.0-float16.bin
atmacore-v1.1.0-float16.bin
atmacore-v1.1.0-int8.bin
```

Keep a `model_registry.json`:
```json
{
  "current": "atmacore-v1.1.0-float16.bin",
  "fallback": "atmacore-v1.0.0-float16.bin",
  "int8_version": "atmacore-v1.1.0-int8.bin"
}
```

## Health check

Every model serve should include a health endpoint:
```
GET /health -> {"status": "ok", "version": "v1.1.0", "memory_mb": 142}
```

## Monitoring

Log every request:
- prompt length
- facts count
- output tokens
- latency
- fallback to template mode (if model fails)

This helps detect degradation early.

## Deployment targets

1. Developer machine (local, Mode A)
2. Oracle Cloud ARM VPS (small server, Mode A or B)
3. Edge devices (Raspberry Pi-like, Mode A with int8)
4. Docker container (Mode B, easy to ship)

Start with Mode A on Oracle Cloud ARM.
Then add Mode B when you build multi-instance colonies.
