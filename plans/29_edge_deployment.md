
# Phase 29: On-Device Deployment and Edge AI

## The eventual goal

AtmaCore is specifically designed to run without GPU, on minimal hardware.
This means it can eventually run on:
- Raspberry Pi (1-4 GB RAM, 4-core ARM)
- Old laptops
- Android phones (via NDK or Termux)
- IoT devices with sufficient RAM
- Chromebooks in developer mode

This is not the first milestone.
But the architecture decisions from the beginning should enable this.

## Key constraints on edge devices

```yaml
raspberry_pi_4:
  RAM: 1-8 GB
  CPU: 4-core ARM Cortex-A72
  no GPU acceleration

android_phone:
  RAM: 4-12 GB for the app
  CPU: ARM but thermal throttled
  need careful battery usage
```

## Optimization for edge

### Use int8 or int4 quantized model
- atmacore_tiny int8: 8 MB
- fits easily even on 1 GB devices

### Limit context to 256 tokens
- synthesis tasks rarely need long context
- memory load proportional to context length

### Use efficient attention implementations
- avoid allocating large matrices on low-RAM devices
- streaming attention kernels

### Load model weights with mmap
- do not load entire model into heap
- memory-map the file, OS pages in as needed
- this can reduce initial RAM by 30-50%

## Edge deployment roadmap

### Stage 1: Linux ARM VPS (current)
- Oracle Cloud ARM instances
- 24 GB RAM, free tier
- confirm everything works

### Stage 2: Raspberry Pi 4
- 4-8 GB RAM
- install Python, NumPy
- confirm 5-10 tokens/second inference

### Stage 3: Android via Termux or native
- Termux gives a Linux-like environment
- later, wrap in Android app with JNI calls
- target 2-5 tokens/sec on phone

### Stage 4: Docker on edge devices
- ship colony + atmacore in single container
- one command deployment
- run on NAS devices, home servers, etc.

## Why this matters commercially

Running AI locally on-device is a massive competitive advantage:
- no cloud cost per inference
- privacy: user data never leaves the device
- works offline
- no API rate limits
- subscription model instead of per-call billing

Positioning:
"AtmaCore - the 10 MB AI brain that runs anywhere."
