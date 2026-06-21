"""
Vibhu-Oska AI-OS — Sovereign BPE Tokenizer
Self-contained BPE tokenizer built completely from scratch in Python.
"""

from __future__ import annotations

import json
import collections
from pathlib import Path
from typing import Any


class SovereignBPETokenizer:
    """Byte Pair Encoding (BPE) tokenizer trained on-device."""

    def __init__(self, vocab: dict[str, int] | None = None, merges: list[tuple[str, str]] | None = None) -> None:
        self.vocab = vocab or {}
        self.merges = merges or []
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}

        # Special tokens
        self.pad_token = "<pad>"
        self.unk_token = "<unk>"
        self.bos_token = "<s>"
        self.eos_token = "</s>"

        self.pad_id = 0
        self.unk_id = 1
        self.bos_id = 2
        self.eos_id = 3

        if not self.vocab:
            self.vocab = {
                self.pad_token: self.pad_id,
                self.unk_token: self.unk_id,
                self.bos_token: self.bos_id,
                self.eos_token: self.eos_id,
            }
            self.inverse_vocab = {v: k for k, v in self.vocab.items()}

    def train(self, text: str, target_vocab_size: int = 4000) -> None:
        """Trains vocabulary and BPE merges from raw text, preserving spaces."""
        import re
        # Pre-replace spaces with U+0120 (Ġ)
        processed_text = text.replace(" ", "Ġ")
        
        # Start with all individual characters in processed text
        unique_chars = sorted(list(set(processed_text)))
        
        # Add characters to vocab
        for char in unique_chars:
            if char not in self.vocab:
                self.vocab[char] = len(self.vocab)
        
        # Split text into block tokens using regex (words, special characters, sequences of Ġ)
        blocks = re.findall(r'Ġ+|\w+|[^\wĠ]', processed_text)
        block_freqs = collections.Counter(blocks)
        
        # Format blocks: list of characters
        splits = {block: list(block) for block in block_freqs.keys()}
        
        # Merging iterations
        num_merges = target_vocab_size - len(self.vocab)
        print(f"BPE training: unique chars = {len(unique_chars)}, target merges = {num_merges}")

        for i in range(num_merges):
            # Count pair frequencies
            pair_freqs: dict[tuple[str, str], int] = collections.defaultdict(int)
            for block, freq in block_freqs.items():
                split = splits[block]
                if len(split) < 2:
                    continue
                for j in range(len(split) - 1):
                    pair_freqs[(split[j], split[j + 1])] += freq

            if not pair_freqs:
                break

            # Find the most frequent pair
            best_pair = max(pair_freqs, key=lambda k: pair_freqs[k])
            
            # Add to merges and vocab
            merged_token = "".join(best_pair)
            self.vocab[merged_token] = len(self.vocab)
            self.merges.append(best_pair)

            # Apply merges to splits
            for block in block_freqs.keys():
                split = splits[block]
                j = 0
                while j < len(split) - 1:
                    if split[j] == best_pair[0] and split[j + 1] == best_pair[1]:
                        split[j:j + 2] = [merged_token]
                    else:
                        j += 1
            
            if (i + 1) % 500 == 0:
                best_pair_str = str(best_pair).replace('Ġ', ' ')
                merged_token_str = str(merged_token).replace('Ġ', ' ')
                print(f"  Merges complete: {i + 1}/{num_merges} | Best pair: {best_pair_str} -> {merged_token_str}")

        self.inverse_vocab = {v: k for k, v in self.vocab.items()}
        print(f"Training complete. Vocab size: {len(self.vocab)}")

    def encode(self, text: str) -> list[int]:
        """Encodes string to a list of token IDs, preserving spaces."""
        if not text:
            return []
        
        import re
        processed_text = text.replace(" ", "Ġ")
        blocks = re.findall(r'Ġ+|\w+|[^\wĠ]', processed_text)
        
        token_ids = [self.bos_id]

        for block in blocks:
            # Start with characters of this block
            chars = list(block)
            
            # Apply merges in order
            for pair in self.merges:
                p0, p1 = pair
                j = 0
                while j < len(chars) - 1:
                    if chars[j] == p0 and chars[j + 1] == p1:
                        chars[j:j + 2] = ["".join(pair)]
                    else:
                        j += 1
            
            # Map tokens to IDs
            for token in chars:
                token_ids.append(self.vocab.get(token, self.unk_id))

        token_ids.append(self.eos_id)
        return token_ids

    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        """Decodes list of token IDs back into string, replacing space tokens."""
        tokens = []
        for token_id in ids:
            if skip_special_tokens and token_id in (self.pad_id, self.unk_id, self.bos_id, self.eos_id):
                continue
            token = self.inverse_vocab.get(token_id, "")
            tokens.append(token)
        
        # Join tokens together and restore spaces
        return "".join(tokens).replace("Ġ", " ")

    def save(self, path: Path | str) -> None:
        """Save vocabulary and merge rules to JSON."""
        data = {
            "vocab": self.vocab,
            "merges": [list(m) for m in self.merges]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> SovereignBPETokenizer:
        """Load vocabulary and merges from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merges = [tuple(m) for m in data["merges"]]
        return cls(vocab=data["vocab"], merges=merges)
