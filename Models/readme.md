# Vibhu-Oska Models Directory

This directory contains the neural network architectures, custom tokenizers, training scripts, and model registry configurations for the Vibhu-Oska local intelligence layer.

## Overview

Vibhu-Oska relies on localized, self-hosted transformers running entirely on local hardware (CPU, GPU, NPU) without external API dependencies. The intelligence cortex is bifurcated into:

1. **Sovereign GPT** (`sovereign_gpt`): A custom causal language model and self-contained BPE tokenizer built from scratch, optimized for offline text generation, code templates, and contextual RAG reasoning.
2. **Intent Router** (`router`): A custom multi-class classifier transformer that inspects prompt parameters and dynamically directs execution target (GPU | CPU | NPU) and task categories (CHAT | CODE | RESEARCH | MEMORY | SYSTEM).

---

## 1. Intent Router (`Models/router/`)

The Intent Router operates as the speculative gateway of the system, implementing an in-process Cascadeflow-style scheduling network.

### Architecture
- **Type**: Causal decoder-only Transformer with classification heads.
- **Parameters**: 
  - **GPU/NPU Zone**: 12 Layers, 768 Hidden Dim, 12 Heads (approx. 86M parameters).
  - **CPU (Scaled)**: 2 Layers, 128 Hidden Dim, 4 Heads (approx. 760K parameters) to avoid slow convergence during local testing/CPU fallbacks.
- **Pooling**: Causal attention sequence pooling (uses the final non-padded token representation instead of the causal BOS token representation).
- **Activation**: SwiGLU (matching LLaMA architecture standards).
- **Positional Embeddings**: Rotary Position Embeddings (RoPE).

### Execution Scripts
- **Dataset Generation**: Generates 1,000 synthetic task queries mapped to GPU/CPU/NPU targets and task types.
  ```powershell
  .venv\Scripts\python -m Models.router.dataset_generator
  ```
- **Training Pipeline**: Trains the BPE tokenizer and optimizes model weights using AdamW with Cosine Annealing.
  ```powershell
  .venv\Scripts\python -m Models.router.train --epochs 10
  ```
- **ONNX Export**: Compiles the trained model to ONNX format for deployment inside edge NPUs.
  ```powershell
  .venv\Scripts\python -m Models.router.train --export-onnx
  ```

---

## 2. Sovereign GPT (`Models/sovereign_gpt/`)

The primary in-process reasoning engine designed to perform private inference, text processing, and fallback assistance.

### Architecture
- **Type**: Decoder-only Causal GPT transformer.
- **Tokenizer**: Custom Sovereign BPE Tokenizer (`SovereignBPETokenizer`) generating deterministic, persistent vocabulary keys without randomized hashing.
- **Seeding**: Seeds a local text corpus of instructions, programming examples, database connectors, and spellchecker structures to bootstrap the model offline.

### Execution Scripts
- **Training Loop**:
  ```powershell
  .venv\Scripts\python -m Models.sovereign_gpt.train --epochs 40
  ```
- **Inference**:
  ```powershell
  .venv\Scripts\python -m Models.sovereign_gpt.generate --prompt "your query here"
  ```
