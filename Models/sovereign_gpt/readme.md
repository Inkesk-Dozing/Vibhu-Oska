# Sovereign GPT — Custom Language Model

Vibhu-Oska's own language model, built entirely from PyTorch primitives with no external inference APIs. A decoder-only transformer trained on project-specific Q&A pairs.

## Architecture

| Parameter | Value |
|---|---|
| Type | Decoder-only transformer (GPT-style) |
| Attention | Multi-Head Causal Self-Attention |
| Position encoding | RoPE (Rotary Positional Embeddings) |
| Feed-forward | SwiGLU activation (Llama-style) |
| Normalization | RMSNorm (Llama-style) |
| Default config | vocab=4000, hidden=256, 6 layers, 8 heads, max_seq=256 |
| Weight tying | `embedding.weight == lm_head.weight` |
| Tokenizer | Custom BPE (SovereignBPETokenizer) |

## Files

| File | Purpose |
|---|---|
| `architecture.py` | Full model definition: RMSNorm, RoPE, SwiGLU, GPT class (7.9KB) |
| `tokenizer.py` | BPE tokenizer: training, encode/decode, save/load (6KB) |
| `train.py` | AdamW + OneCycleLR training loop with corpus seeding (24.5KB) |
| `generate.py` | `SovereignGPTGenerator`: load checkpoint + temperature sampling (8.4KB) |

## Training

```bash
# Train with defaults
python -m Models.sovereign_gpt.train

# Custom run
python -m Models.sovereign_gpt.train --epochs 20 --batch-size 32 --lr 3e-4 --vocab-size 8000
```

**Training corpus**: `Data/training/sovereign_gpt/corpus.txt`
The training script self-seeds the corpus with 200+ Q&A pairs covering Python, FastAPI, SQL, CSS, and Vibhu-Oska internals. Add domain-specific pairs to this file before training for better performance.

## Checkpoints

After training, checkpoints are saved to `checkpoints/`:
- `sovereign_gpt.pt` — model weights + optimizer state + config
- `tokenizer_vocab.json` — BPE vocabulary and merge rules

**Current status**: ✅ `sovereign_gpt.pt` (5.2MB), `tokenizer_vocab.json` (178KB) — trained and ready.

## Inference

```python
from Models.sovereign_gpt.generate import SovereignGPTGenerator
from pathlib import Path

gen = SovereignGPTGenerator(Path("Models/sovereign_gpt/checkpoints"))
output = gen.generate("Query: What is Vibhu-Oska?\nResponse:", max_tokens=128, temperature=0.7)
print(output)
```

## Notes on Scale

The default configuration (256 hidden, 6 layers) produces a ~5MB model — deliberately small for fast iteration on local hardware. When training data grows and VRAM allows, increase `hidden_size` to 512 or 768, `num_layers` to 12, and `vocab_size` to 16000 for significantly better quality. The architecture scales cleanly.
