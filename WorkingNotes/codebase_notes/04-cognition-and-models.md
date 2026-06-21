# 04 — Cognition & Models

## CognitionCore Overview

```
File: Backend/Core/MainCore/CognitionCore/cognition.py
Size: 423 lines, 19.4KB
```

CognitionCore is the **only** place in the system where model weights are accessed. It implements the BaseService interface and dispatches to three possible backends.

## Inference Hierarchy

```
generate(prompt, system_prompt, context, model_id)
          ↓
model_id == "sovereign-gpt"?  → generate_sovereign()
model_id == "vibhu-core"?     → generate_direct() [Qwen2.5-0.5B]
model_id == "" (default)?     → auto-fallback chain:
    1. Check sovereign_gpt.pt exists → generate_sovereign()
       ↓ fails
    2. Load Qwen2.5-0.5B in-process → generate_direct()
       ↓ fails
    3. Raise exception → HybridCore catches → BackupCore
```

## Sovereign GPT Inference Path

```python
async def generate_sovereign(self, prompt, system_prompt, context, ...):
    # 1. Check checkpoints exist:
    #    Models/sovereign_gpt/checkpoints/sovereign_gpt.pt
    #    Models/sovereign_gpt/checkpoints/tokenizer_vocab.json
    #    → Missing: return error TaskResponse (no crash)
    
    # 2. Lazy-load SovereignGPTGenerator (first call only)
    self._sovereign_generator = SovereignGPTGenerator(checkpoints_dir)
    
    # 3. Format prompt: "Context:\n- ...\n\nQuery: {prompt}\nResponse:"
    
    # 4. Run generation in asyncio.to_thread() (non-blocking)
    output = await asyncio.to_thread(self._sovereign_generator.generate, ...)
    
    # 5. Return TaskResponse with content + token counts
```

## Qwen2.5-0.5B Inference Path (Direct)

```python
async def load_direct_model(self):
    # Loads Qwen/Qwen2.5-0.5B-Instruct from HuggingFace (downloads on first use)
    # Runs in-process — no separate server
    self._tokenizer = AutoTokenizer.from_pretrained(model_name)
    self._model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32).to(device)

async def generate_direct(self, prompt, system_prompt, context, ...):
    # Uses apply_chat_template for instruct format
    # Runs model.generate() in asyncio.to_thread() (non-blocking)
```

## Corpus Spell Checker

CognitionCore includes a Norvig-style probabilistic spell checker. It's seeded with ~600 common English words plus domain terms from `Data/training/sovereign_gpt/corpus.txt`.

```python
typo_info = self._spell_checker.find_typo(prompt)
if typo_info:
    # Modify system prompt to: "Start your response with 'Aha, I see typo there...'"
```

This runs on **every** prompt before inference — it's fast (pure Python string ops).

## HybridCore

```
File: Backend/Core/MainCore/HybridCore/HybridCore.py
Size: 185 lines, 8.1KB
```

Manages the primary/backup routing decision:

```python
async def process_request(self, prompt, system_prompt, context, model_id):
    # 1. If model_id is empty: run speculative Router model to assign model_id
    # 2. If model_id == "backup-1": route directly to BackupCore
    # 3. Try primary CognitionCore.generate()
    #    → On exception: route to BackupCore, mark status as DEGRADED
    # 4. Tag response.metadata.executed_on = GPU or CPU
```

### Speculative Router Loading

```python
def _load_router(self):
    # Lazy — runs only once on first request
    # Loads Models/router/checkpoints/best_router.pt
    # Loads Models/router/checkpoints/router_vocab.json (SovereignBPETokenizer)
    # Creates VibhuOskaRouter in eval() mode
```

Router prediction output:
```python
prediction = {
    "task":        "CODE",   # or CHAT / OS / DESIGN / IMAGE
    "target":      "vibhu-core",
    "task_conf":   0.92,
    "target_conf": 0.88
}
```

## BackupCore

```
File: Backend/Core/BackupCore/BackupCore.py
Size: 5.8KB
```

CPU-only fallback. No GPU, no ML libraries. Pattern-matching responses for basic queries. Marks all responses with `executed_on = ExecutionTarget.CPU`.

## Sovereign GPT Architecture

Custom decoder-only transformer built from PyTorch primitives:

```
Embedding Layer
    ↓
RoPE Position Encoding (applied inside attention)
    ↓
6× Transformer Blocks:
    RMSNorm → Multi-Head Causal Self-Attention (RoPE) → Residual
    RMSNorm → SwiGLU Feed-Forward → Residual
    ↓
RMSNorm (final)
    ↓
LM Head (weight-tied to embedding)
    ↓
Softmax → Token probabilities → Sample (temperature, top-k, top-p)
```

**Default config**: vocab=4000, hidden=256, 6 layers, 8 heads, max_seq=256 → ~5MB model

**SovereignBPETokenizer**: Custom BPE tokenizer trained on the corpus, not tiktoken. Encodes/decodes with the same vocabulary used during model training. Saved as `tokenizer_vocab.json`.

## Router Model Architecture

A compact encoder transformer with dual classification heads:
- Shared transformer backbone (3 layers, 64 hidden)
- Task head: softmax over [CHAT, CODE, OS, DESIGN, IMAGE]
- Target head: softmax over [sovereign-gpt, vibhu-core, backup]
