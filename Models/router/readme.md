# Router Model — Speculative Task Classifier

A trained classifier that reads an incoming prompt and predicts the best execution target (model) and task type. HybridCore uses this to route requests without trial-and-error fallbacks.

## Purpose

Route prompts to the right inference engine before even attempting generation:
- `CODE` task → `vibhu-core` (Qwen2.5-0.5B, better at code)
- `CHAT` task → `sovereign-gpt` (custom trained for conversation)

This avoids the latency cost of loading the wrong model, failing, then retrying.

## Architecture

A compact transformer classifier with dual classification heads:

| Parameter | Value |
|---|---|
| Type | Encoder transformer (classification) |
| Input | Tokenized prompt (SovereignBPETokenizer) |
| Output | Task class + Execution target class |
| Task classes | CHAT, CODE, OS, DESIGN, IMAGE |
| Target classes | sovereign-gpt, vibhu-core, backup |
| Checkpoint size | ~3MB (`best_router.pt`) |

## Files

| File | Purpose |
|---|---|
| `architecture.py` | RouterConfig + VibhuOskaRouter model (12.5KB) |
| `train.py` | Training loop with synthetic dataset (12.8KB) |
| `dataset_generator.py` | Generate labeled prompt→(task, target) pairs (10.3KB) |

## Training

```bash
# Generate training data (optional — train.py includes a built-in dataset)
python -m Models.router.dataset_generator

# Train the router
python -m Models.router.train
```

**Current status**: ✅ Fully trained — 10 epoch checkpoints + `best_router.pt` (3MB) in `checkpoints/`.

## Checkpoints

```
checkpoints/
├── best_router.pt        ← Best validation accuracy checkpoint (used in production)
├── router_vocab.json     ← BPE vocabulary for prompt tokenization
├── router_epoch_1.pt     ← ... through epoch_10.pt
```

## Integration

HybridCore lazy-loads the router on first request:

```python
self._load_router()
prediction = self._router.predict(input_ids, attention_mask)
# prediction = {"task": "CODE", "target": "vibhu-core", "task_conf": 0.92, "target_conf": 0.88}
```
