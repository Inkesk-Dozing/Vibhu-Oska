"""
Vibhu-Oska AI-OS — Sovereign GPT Text Generator
Loads trained weights from scratch and samples text autoregressively.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import torch
import torch.nn.functional as F

from Models.sovereign_gpt.architecture import GPTConfig, VibhuOskaGPT
from Models.sovereign_gpt.tokenizer import SovereignBPETokenizer

logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("SovereignGPTGenerator")


class SovereignGPTGenerator:
    """Autoregressive text sampler for custom from-scratch model."""

    def __init__(self, checkpoints_dir: Path | str) -> None:
        self.checkpoints_dir = Path(checkpoints_dir)
        
        # Load tokenizer
        vocab_path = self.checkpoints_dir / "tokenizer_vocab.json"
        if not vocab_path.exists():
            raise FileNotFoundError(f"Vocabulary file missing at {vocab_path}. Train the model first.")
        self.tokenizer = SovereignBPETokenizer.load(vocab_path)

        # Load model weights
        ckpt_path = self.checkpoints_dir / "sovereign_gpt.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(f"Model checkpoint missing at {ckpt_path}. Train the model first.")
        
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        cfg_dict = ckpt["config"]
        
        # Map config dict back to class parameters
        self.config = GPTConfig(
            vocab_size=cfg_dict["vocab_size"],
            hidden_size=cfg_dict["hidden_size"],
            intermediate_size=cfg_dict["intermediate_size"],
            num_layers=cfg_dict["num_layers"],
            num_heads=cfg_dict["num_heads"],
            max_seq_len=cfg_dict["max_seq_len"]
        )
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = VibhuOskaGPT(self.config).to(self.device)
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()

    @torch.no_grad()
    def generate(
        self,
        prompt: str,
        max_tokens: int = 64,
        temperature: float = 0.7,
        top_k: int = 50,
        top_p: float = 0.9,
        repetition_penalty: float = 1.2
    ) -> str:
        """Autoregressive causal generation loop with temperature/top-k/top-p filtering and repetition penalty."""
        input_ids = self.tokenizer.encode(prompt)
        if input_ids and input_ids[-1] == self.tokenizer.eos_id:
            input_ids = input_ids[:-1]
        prompt_len = len(input_ids)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        consecutive_count = 0
        last_token_id = None

        for _ in range(max_tokens):
            # Truncate input to maximum context window size
            curr_input = input_tensor[:, -self.config.max_seq_len:]
            
            # Forward pass
            out = self.model(curr_input)
            logits = out["logits"][:, -1, :]  # Logits for the final position (1, V)
            
            # Apply Repetition Penalty
            if repetition_penalty != 1.0:
                for token_id in set(input_tensor[0].tolist()):
                    if logits[0, token_id] > 0:
                        logits[0, token_id] /= repetition_penalty
                    else:
                        logits[0, token_id] *= repetition_penalty
            
            # Apply Max Consecutive Token Break (suppress repeating token after 2 consecutive occurrences)
            if last_token_id is not None and consecutive_count > 2:
                logits[0, last_token_id] = -1e9
            
            # Apply Multi-Token Alternation Sequence Penalty
            # Checks if the last n tokens match any previous sequence of n tokens.
            # If a match is found, penalize the token that followed that previous sequence.
            gen_tokens = input_tensor[0].tolist()
            if len(gen_tokens) >= 3:
                for n in [3, 4, 5]:
                    if len(gen_tokens) < n * 2:
                        continue
                    suffix = gen_tokens[-n:]
                    for idx in range(len(gen_tokens) - n * 2 + 1):
                        if gen_tokens[idx : idx + n] == suffix:
                            pen_token_id = gen_tokens[idx + n]
                            if logits[0, pen_token_id] > 0:
                                logits[0, pen_token_id] /= (repetition_penalty * 1.5)
                            else:
                                logits[0, pen_token_id] *= (repetition_penalty * 1.5)
            
            # 1. Apply Temperature scaling
            if temperature > 0.0:
                logits = logits / temperature
            else:
                # Argmax/Greedy decoding
                next_token = logits.argmax(dim=-1, keepdim=True)
                # Update consecutive count in greedy decoding
                if last_token_id is not None and next_token.item() == last_token_id:
                    consecutive_count += 1
                else:
                    consecutive_count = 1
                    last_token_id = next_token.item()
                input_tensor = torch.cat([input_tensor, next_token], dim=-1)
                if next_token.item() == self.tokenizer.eos_id:
                    break
                continue

            # 2. Apply Top-K filtering
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float("-inf")

            # 3. Apply Top-P (nucleus) filtering
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True, dim=-1)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                
                # Identify indices to exclude (cumulative probability > top_p)
                sorted_indices_to_remove = cumulative_probs > top_p
                # Shift rights so we keep the first token exceeding the threshold
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = False

                # Mask out excluded logits using correct scatter
                indices_to_remove = torch.zeros_like(logits, dtype=torch.bool)
                indices_to_remove.scatter_(1, sorted_indices, sorted_indices_to_remove)
                logits[indices_to_remove] = float("-inf")

            # Sample next token
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            
            # Update consecutive repetition trackers
            if last_token_id is not None and next_token.item() == last_token_id:
                consecutive_count += 1
            else:
                consecutive_count = 1
                last_token_id = next_token.item()

            # Concatenate to context sequence
            input_tensor = torch.cat([input_tensor, next_token], dim=-1)
            
            if next_token.item() == self.tokenizer.eos_id:
                break

        # Decode only the generated response suffix (excluding prompt)
        generated_ids = input_tensor[0].tolist()
        new_tokens = generated_ids[prompt_len:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate text from custom GPT")
    parser.add_argument("prompt",     type=str, help="Prompt text")
    parser.add_argument("--tokens",   type=int, default=64)
    parser.add_argument("--temp",     type=float, default=0.7)
    parser.add_argument("--rep-pen",  type=float, default=1.2, help="Repetition penalty coefficient")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent.parent
    checkpoints = root / "Models" / "sovereign_gpt" / "checkpoints"

    try:
        generator = SovereignGPTGenerator(checkpoints)
        print(f"Prompt: {args.prompt}")
        output = generator.generate(args.prompt, max_tokens=args.tokens, temperature=args.temp, repetition_penalty=args.rep_pen)
        print(f"Response: {output}")
    except Exception as e:
        print(f"Error loading generator: {e}. Please train the model first.")
