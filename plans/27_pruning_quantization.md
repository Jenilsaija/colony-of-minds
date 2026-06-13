
# Phase 27: Pruning, Quantization, and Size Optimization

## Goal

Make AtmaCore even smaller without sacrificing accuracy.

## Techniques

### 1. Post-training quantization

Train in float16.
Then convert to int8 for inference.

For 25M parameters:
- float16: 50 MB
- int8: 25 MB
- int4: 12.5 MB

Use int8 for the first optimized version.
Consider int4 only if accuracy does not drop significantly.

### 2. Structured pruning

Remove entire attention heads or experts that contribute least.

Process:
1. Score each head/expert by activation magnitude.
2. Remove the lowest-scoring 20-30%.
3. Fine-tune the pruned model for a few hours.
4. Evaluate on benchmark suite.
5. Repeat until benchmark drops below target.

### 3. Embedding pruning

Not all vocabulary tokens are used equally.
Remove tokens that almost never appear in your target domain.
Reduce vocabulary from 32000 to 16000 or even 8000 if domain is narrow.

This reduces embedding table size significantly.
From:
25M parameters -> embedding layer might be:
512 * 32000 = 16M parameters (64% of the model)

After pruning to 8000 vocab:
512 * 8000 = 4M parameters

Saves 12 MB at float16.

### 4. Knowledge sharing between layers

Some tiny models share weights across layers.
For example, layers 1 and 2 share the same weight matrix.

This can cut model size 2-4x with small accuracy cost.

For extreme compression, this can make AtmaCore as small as 5-10 MB
while still being functional for synthesis tasks.

## Size targets

```yaml
atmacore_full:
  params: 25M
  float16_size: 50 MB
  int8_size: 25 MB

atmacore_pruned:
  params: 15M
  float16_size: 30 MB
  int8_size: 15 MB

atmacore_tiny:
  params: 8M
  float16_size: 16 MB
  int8_size: 8 MB
  use_case: ultra-constrained devices
```

## When to optimize

Do not optimize too early.
First train the best model you can.
Then systematically shrink it while monitoring benchmarks.
Stop when accuracy starts to drop.

The result is a highly optimized model that is both
smaller and more accurate per parameter than generic small LLMs.
