"""
Vibhu-Oska AI-OS — Sovereign GPT Architecture
Custom decoder-only Transformer language model built entirely from scratch.
"""

from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class GPTConfig:
    vocab_size:      int   = 4000        # Custom small vocabulary
    hidden_size:     int   = 256         # Embedding dimension
    intermediate_size: int = 1024        # FFN intermediate
    num_layers:      int   = 6           # Number of transformer blocks
    num_heads:       int   = 8           # Number of attention heads
    max_seq_len:     int   = 256         # Maximum sequence length
    dropout:         float = 0.1
    layer_norm_eps:  float = 1e-5
    pad_token_id:    int   = 0


class RotaryEmbedding(nn.Module):
    """Rotary Position Embedding (RoPE) for relative position representation."""

    def __init__(self, dim: int, max_seq_len: int = 256, base: int = 10000) -> None:
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


class CausalSelfAttention(nn.Module):
    """Multi-Head Causal Self-Attention with causal masking."""

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.num_heads = config.num_heads
        self.head_dim  = config.hidden_size // config.num_heads
        self.scale     = 1.0 / math.sqrt(self.head_dim)

        self.q_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.k_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.v_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)
        self.o_proj = nn.Linear(config.hidden_size, config.hidden_size, bias=False)

        self.rotary  = RotaryEmbedding(self.head_dim, config.max_seq_len)
        self.dropout = nn.Dropout(config.dropout)

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

        # Apply causal masking
        causal_mask = torch.triu(
            torch.full((S, S), float("-inf"), device=hidden_states.device), diagonal=1
        )
        attn = attn + causal_mask

        if attention_mask is not None:
            # attention_mask: (B, 1, 1, S) or similar
            attn = attn + attention_mask

        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, S, H)
        return self.o_proj(out)


class FeedForward(nn.Module):
    """Standard FFN with SwiGLU activation."""

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.up_proj   = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization (Llama-style)."""

    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        return x * torch.rsqrt(variance + self.eps) * self.weight


class TransformerBlock(nn.Module):
    """Transformer decoder block."""

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.norm1 = RMSNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.attn  = CausalSelfAttention(config)
        self.norm2 = RMSNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.ffn   = FeedForward(config)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        hidden_states = hidden_states + self.attn(self.norm1(hidden_states), attention_mask)
        hidden_states = hidden_states + self.ffn(self.norm2(hidden_states))
        return hidden_states


class VibhuOskaGPT(nn.Module):
    """Custom Generative language model (GPT decoder-only)."""

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.config    = config
        self.embedding = nn.Embedding(config.vocab_size, config.hidden_size, padding_idx=config.pad_token_id)
        self.layers    = nn.ModuleList([TransformerBlock(config) for _ in range(config.num_layers)])
        self.norm      = RMSNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.lm_head   = nn.Linear(config.hidden_size, config.vocab_size, bias=False)

        # Tie weights
        self.embedding.weight = self.lm_head.weight

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
        labels: Optional[torch.Tensor] = None
    ) -> dict[str, torch.Tensor]:
        B, S = input_ids.shape

        x = self.embedding(input_ids)
        for layer in self.layers:
            x = layer(x, attention_mask)
        x = self.norm(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            # Shift logits/labels for causal prediction
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(shift_logits.view(-1, self.config.vocab_size), shift_labels.view(-1), ignore_index=-100)

        return {
            "logits": logits,
            "loss": loss
        }

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
