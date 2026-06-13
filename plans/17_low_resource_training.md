
# Phase 17: Training AtmaCore on Low-Resource Hardware

## The challenge

Training even a 25M parameter model requires:
- forward pass (compute)
- backward pass (gradient computation)
- optimizer state storage
- gradient accumulation

A 25M parameter model in float32 needs:
- 100 MB for weights
- 100 MB for gradients
- 200 MB for optimizer states (Adam)
- Plus activations during training

On a 1 GB RAM machine, this is very tight.

## Solution: extreme optimization techniques

### 1. Train in int8 or float16

Use mixed-precision training:
- forward pass in float16
- master weights in float32
- gradients in float16

This cuts memory roughly in half.

### 2. Gradient accumulation with micro-batches

Instead of batch size 32:
- batch size 2 with gradient accumulation over 16 steps
- same effective batch size, much lower peak memory

### 3. Gradient checkpointing

Save only some intermediate activations.
Recompute others during backward pass.
Trade compute for memory.

### 4. LoRA-style training for finetuning

Do not update all 25M parameters during finetuning.
Use Low-Rank Adaptation:
- freeze the pretrained weights
- add small rank-4 or rank-8 matrices
- only train these small adapters

This reduces update memory from 25M params to maybe 200K params.

### 5. CPU-friendly optimizer

Avoid Adam if too memory-hungry.
Use SGD with momentum for some stages.
Or Adafactor which has smaller state.

### 6. Sequential curriculum

Do not train on all data at once.
Start with easy small datasets first.
Then increase complexity.

This means faster convergence and less wasted compute.

## Recommended training setups

### Option A: Train on Oracle Cloud free tier

Jenil uses Oracle Cloud.
Oracle Cloud free tier offers:
- ARM instances with up to 24 GB RAM
- 4 OCPUs
- still free or very cheap

This is probably the best choice.
24 GB RAM can handle 25M parameter training comfortably
with float16 and gradient accumulation.

### Option B: Train on Google Colab

Free tier Tesla T4 GPU.
Can train 25M models easily.
Limitation: session time limits.

### Option C: Train on local machine

Only if more than 4 GB RAM available.
Use all the memory-saving techniques above.

## Training stages

```yaml
stage_1_pretrain:
  data: general high-quality text (2-5M tokens)
  hardware: Oracle Cloud ARM or Colab
  time: 6-12 hours
  goal: learn language patterns

stage_2_synthesis_finetune:
  data: synthetic synthesis pairs (500k+)
  hardware: same as stage 1
  time: 3-8 hours
  goal: learn fact-grounded synthesis

stage_3_preference_finetune:
  data: contrastive pairs (good answer vs bad answer)
  hardware: same as stage 1
  time: 2-4 hours
  goal: learn to prefer accurate over fluent

stage_4_colony_online:
  data: production colony interactions
  frequency: weekly or after significant data
  time: incremental
  goal: continuous improvement
```

## Budget estimate

Training a 25M parameter model fully:
- on Oracle Cloud free ARM: effectively free
- on Colab free: effectively free
- on a paid GPU: under $5 total
- the real cost is your time and data quality
