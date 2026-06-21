"""
Vibhu-Oska AI-OS — Router Model Training Script
Trains the 150M intent router on synthetic + feedback-augmented data.

Usage:
    # 1. Generate dataset first:
    python -m Models.router.dataset_generator

    # 2. Train the router:
    python -m Models.router.train

    # 3. Export to ONNX for NPU:
    python -m Models.router.train --export-onnx

Hardware target: RTX 4060 8GB (uses gradient checkpointing + micro-batching)
Expected time: ~2-4 hours for 3 epochs on 5000 examples
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from Models.sovereign_gpt.tokenizer import SovereignBPETokenizer

# ══════════════════════════════════════════════════════════════════
# Tokenizer Helper
# ══════════════════════════════════════════════════════════════════

def pad_sequence(ids: list[int], max_len: int, pad_id: int) -> tuple[list[int], list[int]]:
    attn = [1] * len(ids)
    if len(ids) < max_len:
        pad_len = max_len - len(ids)
        ids  = ids  + [pad_id] * pad_len
        attn = attn + [0] * pad_len
    else:
        ids  = ids[:max_len]
        attn = attn[:max_len]
    return ids, attn


# ══════════════════════════════════════════════════════════════════
# Dataset
# ══════════════════════════════════════════════════════════════════

class RouterDataset(Dataset):
    def __init__(self, jsonl_path: Path, tokenizer: SovereignBPETokenizer, max_len: int = 128) -> None:
        self.samples   = []
        self.tokenizer = tokenizer
        self.max_len   = max_len

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    self.samples.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        sample = self.samples[idx]
        raw_ids = self.tokenizer.encode(sample["text"])
        ids, attn = pad_sequence(raw_ids, self.max_len, pad_id=self.tokenizer.pad_id)
        return {
            "input_ids":      torch.tensor(ids,                     dtype=torch.long),
            "attention_mask": torch.tensor(attn,                    dtype=torch.long),
            "target_label":   torch.tensor(sample["target_id"],     dtype=torch.long),
            "task_label":     torch.tensor(sample["task_id"],       dtype=torch.long),
        }


# ══════════════════════════════════════════════════════════════════
# Training
# ══════════════════════════════════════════════════════════════════

def train(
    data_dir:    Path,
    output_dir:  Path,
    epochs:      int   = 3,
    batch_size:  int   = 8,
    grad_accum:  int   = 8,     # Effective batch = 8 * 8 = 64
    lr:          float = 3e-4,
    max_len:     int   = 128,
    device:      str   = "auto",
    export_onnx: bool  = False,
) -> None:
    from Models.router.architecture import RouterConfig, VibhuOskaRouter

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    log = logging.getLogger("RouterTrainer")

    # Device selection
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dev = torch.device(device)
    log.info(f"Training on device: {device}")
    if device == "cuda":
        log.info(f"GPU: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    output_dir.mkdir(parents=True, exist_ok=True)
    if dev.type == "cpu":
        log.info("CPU detected: Setting grad_accum=1 and increasing lr to 1e-3 for faster convergence on CPU.")
        grad_accum = 1
        lr = 1e-3

    # ── Tokenizer & Datasets ──
    vocab_path = output_dir / "router_vocab.json"
    if vocab_path.exists():
        log.info(f"Loading existing BPE tokenizer from {vocab_path}")
        tokenizer = SovereignBPETokenizer.load(vocab_path)
    else:
        log.info("Training BPE tokenizer from training dataset...")
        tokenizer = SovereignBPETokenizer()
        prompts = []
        with open(data_dir / "train.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                try:
                    prompts.append(json.loads(line.strip())["text"])
                except Exception:
                    pass
        corpus_text = "\n".join(prompts)
        tokenizer.train(corpus_text, target_vocab_size=2000)
        tokenizer.save(vocab_path)

    train_ds  = RouterDataset(data_dir / "train.jsonl", tokenizer, max_len)
    val_ds    = RouterDataset(data_dir / "val.jsonl",   tokenizer, max_len)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)
    log.info(f"Dataset: {len(train_ds)} train / {len(val_ds)} val examples")

    # ── Model ──
    if dev.type == "cpu":
        log.info("CPU environment detected. Custom scaling router architecture to be lightweight for CPU training...")
        config = RouterConfig(
            vocab_size=len(tokenizer.vocab),
            max_seq_len=max_len,
            hidden_size=128,
            intermediate_size=512,
            num_layers=2,
            num_heads=4
        )
    else:
        config = RouterConfig(vocab_size=len(tokenizer.vocab), max_seq_len=max_len)

    model  = VibhuOskaRouter(config).to(dev)
    log.info(f"Router model: {model.count_parameters():,} parameters")

    # Gradient checkpointing (saves VRAM at the cost of ~20% speed)
    # model.gradient_checkpointing_enable()  # Uncomment if OOM

    # ── Optimizer & Scheduler ──
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01, betas=(0.9, 0.95))
    total_steps  = (len(train_loader) // grad_accum) * epochs
    scheduler    = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps, eta_min=lr * 0.1)

    # ── Loss ──
    target_criterion = nn.CrossEntropyLoss()
    task_criterion   = nn.CrossEntropyLoss()

    # ── Training Loop ──
    best_val_acc = 0.0
    best_ckpt    = output_dir / "best_router.pt"

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = target_correct = task_correct = total = 0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader, 1):
            input_ids      = batch["input_ids"].to(dev)
            attention_mask = batch["attention_mask"].to(dev)
            target_labels  = batch["target_label"].to(dev)
            task_labels    = batch["task_label"].to(dev)

            out = model(input_ids, attention_mask)
            loss = (
                target_criterion(out["target_logits"], target_labels) +
                task_criterion(out["task_logits"], task_labels)
            ) / grad_accum

            loss.backward()
            total_loss += loss.item() * grad_accum

            # Gradient accumulation
            if step % grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            target_correct += (out["target_logits"].argmax(1) == target_labels).sum().item()
            task_correct   += (out["task_logits"].argmax(1)   == task_labels).sum().item()
            total          += input_ids.size(0)

            if step % 50 == 0:
                log.info(
                    f"Epoch {epoch} | Step {step}/{len(train_loader)} | "
                    f"Loss: {total_loss/step:.4f} | "
                    f"Target Acc: {target_correct/total:.3f} | "
                    f"Task Acc: {task_correct/total:.3f} | "
                    f"LR: {scheduler.get_last_lr()[0]:.2e}"
                )

        # ── Validation ──
        model.eval()
        val_target_correct = val_task_correct = val_total = 0
        with torch.no_grad():
            for batch in val_loader:
                input_ids      = batch["input_ids"].to(dev)
                attention_mask = batch["attention_mask"].to(dev)
                target_labels  = batch["target_label"].to(dev)
                task_labels    = batch["task_label"].to(dev)
                out = model(input_ids, attention_mask)
                val_target_correct += (out["target_logits"].argmax(1) == target_labels).sum().item()
                val_task_correct   += (out["task_logits"].argmax(1)   == task_labels).sum().item()
                val_total          += input_ids.size(0)

        val_target_acc = val_target_correct / val_total
        val_task_acc   = val_task_correct   / val_total
        log.info(
            f"━━ Epoch {epoch} Val | Target Acc: {val_target_acc:.3f} | Task Acc: {val_task_acc:.3f}"
        )

        # Save best checkpoint
        avg_val_acc = (val_target_acc + val_task_acc) / 2
        if avg_val_acc > best_val_acc:
            best_val_acc = avg_val_acc
            torch.save({
                "epoch":          epoch,
                "model_state":    model.state_dict(),
                "config":         config.__dict__,
                "best_val_acc":   best_val_acc,
                "target_acc":     val_target_acc,
                "task_acc":       val_task_acc,
            }, best_ckpt)
            log.info(f"[SAVED] New best model saved → {best_ckpt} (avg acc: {best_val_acc:.3f})")

        # Epoch checkpoint
        torch.save(model.state_dict(), output_dir / f"router_epoch_{epoch}.pt")

    log.info(f"Training complete. Best validation accuracy: {best_val_acc:.3f}")

    # ── ONNX Export ──
    if export_onnx:
        log.info("Exporting to ONNX for NPU deployment...")
        onnx_path = output_dir / "router.onnx"
        dummy_ids  = torch.zeros(1, max_len, dtype=torch.long).to(dev)
        dummy_mask = torch.ones(1, max_len, dtype=torch.long).to(dev)
        torch.onnx.export(
            model,
            (dummy_ids, dummy_mask),
            str(onnx_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["target_logits", "task_logits"],
            dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}},
            opset_version=17,
        )
        log.info(f"[EXPORTED] ONNX model exported → {onnx_path}")


# ══════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Vibhu-Oska Router Model")
    parser.add_argument("--epochs",       type=int,   default=3)
    parser.add_argument("--batch-size",   type=int,   default=8)
    parser.add_argument("--lr",           type=float, default=3e-4)
    parser.add_argument("--device",       type=str,   default="auto")
    parser.add_argument("--export-onnx",  action="store_true")
    args = parser.parse_args()

    root     = Path(__file__).resolve().parent.parent.parent
    data_dir = root / "Data" / "training" / "router_dataset"
    out_dir  = root / "Models" / "router" / "checkpoints"

    if not (data_dir / "train.jsonl").exists():
        print("Dataset not found. Run: python -m Models.router.dataset_generator")
        exit(1)

    train(
        data_dir    = data_dir,
        output_dir  = out_dir,
        epochs      = args.epochs,
        batch_size  = args.batch_size,
        lr          = args.lr,
        device      = args.device,
        export_onnx = args.export_onnx,
    )
