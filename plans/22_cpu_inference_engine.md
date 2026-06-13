
# Phase 22: Optimized CPU Inference Engine

## Why custom inference runtime matters

Using PyTorch or llama.cpp to run AtmaCore wastes memory.
PyTorch has overhead for features you do not need.
llama.cpp is optimized for GGUF format, not your custom model.

A custom runtime can:
- load only the weights
- skip unnecessary allocations
- use CPU-specific optimizations
- keep memory flat

## Target inference budget

```yaml
model_weights: 50 MB (25M params in float16)
kv_cache: 30-60 MB (depends on context)
runtime_overhead: 10-20 MB
total: under 150 MB for inference alone
```

## Inference engine design

### Weight storage

Store weights in flat binary files:
- one file per layer
- float16 quantization
- memory-mapped loading (load only what is needed)

### Attention kernel optimization

CPU attention can be slow.
Optimize with:
- pre-computed RoPE tables
- cache-friendly memory layout (NHWC or optimized transpose)
- tiling to fit in CPU L1/L2 cache
- SIMD if possible (AVX2 or NEON on ARM)

### KV cache management

For synthesis tasks, context is usually under 1024 tokens.
Pre-allocate KV cache at this size.
Reallocate only if context grows beyond this.

### Expert routing in MoE

The MoE routing is a small matrix multiply.
Optimize as:
```python
gate_logits = token_embedding @ gate_weight  # small matmul
top_k = argsort(gate_logits)[:active_experts]
```
This is O(hidden_dim * num_experts).
With 4-8 experts, this is negligible computation.

### Batch vs single inference

For colony use, inferences are always single requests.
Optimize for single-request latency, not throughput for large batches.

## Optional: C/Rust inference core

Write the inference engine in C or Rust, call from Python.
Benefits:
- 2-5x faster than pure Python + NumPy
- lower memory overhead
- portable to other systems later

This matters most on 2-core CPU where every cycle counts.

## Profiling

Always profile inference after each change.
Measure:
- time to first token
- tokens per second
- peak memory
- any allocation spikes

Use `time` command and `/proc/self/status` for memory.
Or `psutil` for Python-level monitoring.
