# QLoRA Fine-Tuning Pipeline

Fine-tune Qwen2.5-Coder-3B on Vibhu-Oska-specific data using 4-bit NF4 quantization and LoRA adapters. Produces domain-adapted LoRA adapters that improve the `vibhu-core` inference target for project-specific tasks.

## What It Produces

LoRA adapters saved to `Models/reasoning/lora_adapters/`:
- `epoch_N/` — per-epoch adapter checkpoints
- `final/` — final adapter (use this for inference)
- `training_info.json` — training hyperparameters record

## Requirements

- GPU with ≥ 8 GB VRAM (RTX 4060 or equivalent)
- `pip install transformers peft bitsandbytes accelerate`

## Usage

```bash
# Default: Qwen2.5-Coder-3B, 1 epoch, micro-batch 1, grad_accum 16
python -m Models.reasoning.finetune

# Extended training
python -m Models.reasoning.finetune --model qwen2.5-coder --epochs 3 --lr 1e-4

# Larger model (needs 16GB VRAM)
python -m Models.reasoning.finetune --model qwen2.5-coder-7b

# Custom data directory
python -m Models.reasoning.finetune --data-dir /path/to/custom/data
```

## Training Data Sources

1. `Data/training/feedback/feedback_dataset.jsonl` — RLHF feedback from FeedbackCollector plugin (approved examples with `reward=1.0`)
2. `Data/training/vibhu_oska_instructions.jsonl` — manually curated instruction pairs (optional)
3. Minimal built-in demo dataset (if no data files exist — runs but produces low-quality adapters)

## LoRA Configuration

| Parameter | Value | Rationale |
|---|---|---|
| LoRA rank (r) | 16 | Good balance of quality vs. adapter size |
| LoRA alpha | 32 | 2× rank — standard stable scaling |
| Dropout | 0.05 | Light regularization |
| Target modules | q, k, v, o, gate, up, down projections | Full attention + FFN coverage |
| Quantization | 4-bit NF4 + double quant | Maximum VRAM savings |
| Effective batch | 16 (1×16 grad accum) | Fits 8GB VRAM |
| Learning rate | 2e-4 + CosineAnnealingLR | Standard LoRA tuning range |

## File

`finetune.py` — 299 lines, 12.7KB — complete and runnable.
