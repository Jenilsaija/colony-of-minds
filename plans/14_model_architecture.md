
# Phase 14: AtmaCore Architecture Design

## Target specification

- Parameter count: 15M to 50M
- RAM at inference: under 250 MB
- Inference speed: on 2-core CPU, under 2 seconds for 100 tokens
- Primary task: faithful synthesis of verified facts

This puts AtmaCore between a very small model and a small model.
But architecture quality matters more than size here.

## Why transformer variants and not standard transformer

A standard GPT-style decoder-only transformer at 15-50M parameters
will be too weak for the synthesis quality you need.

Instead, use these architectural ideas:

### 1. Mixture of Experts (MoE) at tiny scale

Instead of one feed-forward network per transformer block,
use 4-8 expert sub-networks.

At each token, a lightweight router picks 1-2 experts.

This means:
- total parameter count stays small
- effective capacity is much higher
- each expert specializes
- inference cost stays low because only 1-2 experts are active

For a 30M parameter model, MoE gives you a much wider "knowledge surface"
than a dense 30M model.

### 2. Shared-kv attention with sliding window

To reduce memory during inference:
- use grouped-query attention to reduce KV cache size
- use sliding window attention of 256-512 tokens
- this keeps the model focused on relevant context

### 3. Fact-anchored attention layers

Add special attention heads that are designed to anchor on
structured key-value pairs from verified facts.

Regular transformer heads can attend to patterns in language.
But dedicated "fact heads" attend to the structured fact input
and learn to ground their output in that structure.

This is inspired by retrieval-augmented generation
but done inside the model's own attention pattern.

### 4. Dual-tokenizer design

Standard tokenizers are good at natural language
but wasteful on structured symbols.

AtmaCore should use:
- a natural language tokenizer (standard subword)
- a structured data tokenizer that handles JSON-like patterns efficiently

During training, both tokenizers share the same embedding space
but are routed based on input type.

### 5. Depth vs width

For CPU inference:
- more layers means sequential computation but less memory per step
- wider models compute faster in parallel but need more RAM

On 2-core CPU:
- prefer 12-16 layers, moderate width
- keep hidden dimension at 512 or 768
- use 8-12 attention heads

## AtmaCore architecture summary

```text
Embedding Layer (shared natural + structured)
+
Embedding Position Encoding (RoPE)
+
Nx TransformerBlocks:
  - Grouped-Query Self-Attention (8 heads, GQA)
  - Fact-Anchored Attention Heads (2 dedicated heads)
  - MoE Feed-Forward (4 experts, top-2 routing)
  - RMSNorm
  - Residual Connections
+
Output Projection Layer
```

Target sizes:

```yaml
atmacore_tiny:
  layers: 12
  hidden_dim: 512
  ffn_dim: 2048
  heads: 8
  experts: 4
  active_experts: 2
  vocab_size: 32000
  context_length: 1024
  params_estimate: ~25M

atmacore_small:
  layers: 16
  hidden_dim: 768
  ffn_dim: 3072
  heads: 12
  experts: 8
  active_experts: 2
  vocab_size: 32000
  context_length: 2048
  params_estimate: ~50M
```

## Implementation approach

Write the model in pure Python + NumPy first for correctness.
Then optimize with:
- Cython for CPU kernels
- or a minimal C backend for matrix operations
- or Metal/Vulkan if deploying on Apple/Linux later

Do not use PyTorch for the initial training if you want
fine-grained control over memory.

But for faster experimentation,
you can prototype in PyTorch and later port to custom runtime.
