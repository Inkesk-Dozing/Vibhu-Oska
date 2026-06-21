"""
Vibhu-Oska AI-OS — Router Model Architecture
Custom 150M decoder-only transformer for intent routing.
Classifies prompts to execution targets: GPU/CPU/NPU + task type.

Architecture:
  - 12 transformer layers
  - 768 hidden dimension
  - 12 attention heads (64 dims/head)
  - 1024 max sequence length
  - SwiGLU activation (like LLaMA)
  - RoPE positional embeddings
  - ~150M parameters

Classification targets:
  - Target: GPU | CPU | NPU
  - Task type: CHAT | CODE | RESEARCH | MEMORY | SYSTEM
"""

from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional


# ══════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════

@dataclass
class RouterConfig:
    vocab_size:      int   = 32000       # Shared vocabulary size
    hidden_size:     int   = 768
    intermediate_size: int = 2048        # SwiGLU intermediate
    num_layers:      int   = 12
    num_heads:       int   = 12
    max_seq_len:     int   = 1024
    dropout:         float = 0.1
    layer_norm_eps:  float = 1e-5
    num_target_classes: int = 3          # GPU | CPU | NPU
    num_task_classes:   int = 5          # CHAT | CODE | RESEARCH | MEMORY | SYSTEM
    pad_token_id:    int   = 0


# ══════════════════════════════════════════════════════════════════
# RoPE Positional Embeddings
# ══════════════════════════════════════════════════════════════════

class RotaryEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE) — same as used in LLaMA."""

    def __init__(self, dim: int, max_seq_len: int = 1024, base: int = 10000) -> None:
        super().__init__()
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq)
        self._build_cache(max_seq_len)

    def _build_cache(self, seq_len: int) -> None:
        t = torch.arange(seq_len, device=self.inv_freq.device).float()
        freqs = torch.einsum("i,j->ij", t, self.inv_freq)
        emb = torch.cat([freqs, freqs], dim=-1)
        self.register_buffer("cos_cached", emb.cos()[None, None, :, :], persistent=False)
        self.register_buffer("sin_cached", emb.sin()[None, None, :, :], persistent=False)

    def forward(self, x: torch.Tensor, seq_len: int) -> tuple[torch.Tensor, torch.Tensor]:
        if seq_len > self.cos_cached.shape[2]:
            self._build_cache(seq_len)
        return self.cos_cached[:, :, :seq_len, :], self.sin_cached[:, :, :seq_len, :]


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x[..., : x.shape[-1] // 2], x[..., x.shape[-1] // 2 :]
    return torch.cat([-x2, x1], dim=-1)


def apply_rotary_pos_emb(q, k, cos, sin):
    q_rot = (q * cos) + (rotate_half(q) * sin)
    k_rot = (k * cos) + (rotate_half(k) * sin)
    return q_rot, k_rot


# ══════════════════════════════════════════════════════════════════
# Multi-Head Attention
# ══════════════════════════════════════════════════════════════════

class RouterAttention(nn.Module):
    def __init__(self, config: RouterConfig) -> None:
        super().__init__()
        self.num_heads  = config.num_heads
        self.head_dim   = config.hidden_size // config.num_heads
        self.scale      = 1.0 / math.sqrt(self.head_dim)

        self.q_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.k_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.v_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.o_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)

        self.rotary   = RotaryEmbedding(self.head_dim, config.max_seq_len)
        self.dropout  = nn.Dropout(config.dropout)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        B, S, H = hidden_states.shape

        q = self.q_proj(hidden_states).view(B, S, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(hidden_states).view(B, S, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(hidden_states).view(B, S, self.num_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rotary(q, S)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if attention_mask is not None:
            attn = attn + attention_mask

        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, S, H)
        return self.o_proj(out)


# ══════════════════════════════════════════════════════════════════
# SwiGLU FFN
# ══════════════════════════════════════════════════════════════════

class RouterFFN(nn.Module):
    """SwiGLU feed-forward network (same as LLaMA)."""

    def __init__(self, config: RouterConfig) -> None:
        super().__init__()
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.up_proj   = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


# ══════════════════════════════════════════════════════════════════
# Transformer Block
# ══════════════════════════════════════════════════════════════════

class RouterBlock(nn.Module):
    def __init__(self, config: RouterConfig) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.attn  = RouterAttention(config)
        self.norm2 = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.ffn   = RouterFFN(config)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        # Pre-norm residual (like LLaMA)
        hidden_states = hidden_states + self.attn(self.norm1(hidden_states), attention_mask)
        hidden_states = hidden_states + self.ffn(self.norm2(hidden_states))
        return hidden_states


# ══════════════════════════════════════════════════════════════════
# Router Model (Main)
# ══════════════════════════════════════════════════════════════════

class VibhuOskaRouter(nn.Module):
    """
    150M parameter intent router for Vibhu-Oska AI-OS.

    Input:  Tokenized prompt (B, S)
    Output: (target_logits, task_logits)
      - target_logits: (B, 3) → softmax → [GPU, CPU, NPU] probability
      - task_logits:   (B, 5) → softmax → [CHAT, CODE, RESEARCH, MEMORY, SYSTEM]
    """

    TARGET_LABELS = ["GPU", "CPU", "NPU"]
    TASK_LABELS   = ["CHAT", "CODE", "RESEARCH", "MEMORY", "SYSTEM"]

    def __init__(self, config: RouterConfig) -> None:
        super().__init__()
        self.config    = config
        self.embedding = nn.Embedding(config.vocab_size, config.hidden_size, padding_idx=config.pad_token_id)
        self.layers    = nn.ModuleList([RouterBlock(config) for _ in range(config.num_layers)])
        self.norm      = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.dropout   = nn.Dropout(config.dropout)

        # Classification heads
        self.target_head = nn.Sequential(
            nn.Linear(config.hidden_size, 256),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(256, config.num_target_classes),
        )
        self.task_head = nn.Sequential(
            nn.Linear(config.hidden_size, 256),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(256, config.num_task_classes),
        )

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        B, S = input_ids.shape

        # Build causal attention mask
        if attention_mask is None:
            causal_mask = torch.triu(
                torch.full((S, S), float("-inf"), device=input_ids.device), diagonal=1
            ).unsqueeze(0).unsqueeze(0)  # (1, 1, S, S)
        else:
            pad_mask = (1.0 - attention_mask.unsqueeze(1).unsqueeze(2).float()) * -10000.0
            causal_mask = torch.triu(
                torch.full((S, S), float("-inf"), device=input_ids.device), diagonal=1
            ).unsqueeze(0).unsqueeze(0) + pad_mask

        # Forward pass
        x = self.dropout(self.embedding(input_ids))
        for layer in self.layers:
            x = layer(x, causal_mask)
        x = self.norm(x)

        # Pool: use the last non-pad token representation (causal attention pooling)
        if attention_mask is not None:
            # Sum of attention mask gives length of sequence
            seq_len = attention_mask.sum(dim=-1) - 1
            seq_len = seq_len.clamp(min=0)
            cls_repr = x[torch.arange(B, device=x.device), seq_len]
        else:
            cls_repr = x[:, -1, :]

        return {
            "target_logits": self.target_head(cls_repr),
            "task_logits":   self.task_head(cls_repr),
            "hidden_states": cls_repr,
        }

    @torch.no_grad()
    def predict(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> dict[str, Any]:
        """Inference-mode prediction with human-readable labels."""
        self.eval()
        out = self(input_ids, attention_mask)
        target_probs = F.softmax(out["target_logits"], dim=-1)
        task_probs   = F.softmax(out["task_logits"], dim=-1)

        target_idx = target_probs.argmax(dim=-1).item()
        task_idx   = task_probs.argmax(dim=-1).item()

        return {
            "target":       self.TARGET_LABELS[target_idx],
            "task":         self.TASK_LABELS[task_idx],
            "target_conf":  float(target_probs[0, target_idx]),
            "task_conf":    float(task_probs[0, task_idx]),
            "target_probs": {l: float(p) for l, p in zip(self.TARGET_LABELS, target_probs[0])},
            "task_probs":   {l: float(p) for l, p in zip(self.TASK_LABELS, task_probs[0])},
        }

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


from typing import Any  # noqa: E402
