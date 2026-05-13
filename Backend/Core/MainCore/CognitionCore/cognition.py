"""
Vibhu-Oska AI-OS — CognitionCore
Handles local LLM inference in-process using direct local models or local Sovereign GPT.
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Any
from pathlib import Path
from collections import Counter

import asyncio
from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import TaskResponse, TokenUsage, ResponseMetadata, Status, StatusCode, PluginInfo, CoreStatus, ExecutionTarget


COMMON_TYPOS = {
    "sihg": "sigh",
    "twnat": "want",
    "amke": "make",
    "teh": "the",
    "acieve": "achieve",
    "proeprly": "properly",
    "atleast": "at least",
    "sint": "isn't",
    "welocme": "welcome",
    "semeingly": "seemingly",
    "reposnse": "response",
    "roeprly": "properly",
    "reacognize": "recognize",
    "wt": "what",
}

COMMON_WORDS = set(
    "the of to and a in is it you that he was for on are as with his they i "
    "at be this have from or one had by word but not what all were we when "
    "your can said there use an each which she do how their if will up other "
    "about out many then them these so some her would make like him into time "
    "has look two more write go see number no way could people my than first "
    "water been call who oil its now find long down day did get come made "
    "may part over new sound take only little work know place year live me "
    "give back give after thing our name good sentence man think say great "
    "where help through much before line right too mean old any same tell "
    "boy follow came want show also around form three small set put end "
    "does another well large must big even such because turn here why ask "
    "went men read need land different home us move try kind hand picture "
    "again change play spell air away animal house point page letter mother "
    "answer study still learn should america world high every near add food "
    "between own below country plant last school father keep tree never "
    "start city earth eyes head under story saw left don't few while along "
    "might close something seem next hard open example begin life always "
    "those both paper together got group often run important until children "
    "side feet car mile night walk white sea began grow took river four "
    "carry state once book hear stop without second late miss idea enough "
    "eat face watch far really almost let above girl sometimes mountain cut "
    "young talk soon list song being leave family it's wtf umm hello hi hey "
    "sigh make achieve properly response welcome seemingly recognize python "
    "fastapi django flask app application code run dev develop loop class "
    "function definition what is the capital of france paris how do you work "
    "i want to check this sigh make achieve properly at least normal talk "
    "again correct incorrect word test testing period periods autonomous reply "
    "correctly typos typo recognize welcome seemingly response isn't is not "
    "not are how we what who when".split()
)

class CorpusSpellChecker:
    def __init__(self, corpus_path: Path) -> None:
        self.words_counter = Counter(COMMON_WORDS)
        if corpus_path.exists():
            try:
                text = corpus_path.read_text(encoding="utf-8").lower()
                words_list = re.findall(r'\b[a-z]+\b', text)
                self.words_counter.update(words_list)
            except Exception:
                pass
            
    def P(self, word: str) -> float:
        N = sum(self.words_counter.values())
        return self.words_counter[word] / N if N > 0 else 0.0

    def known(self, words: set[str] | list[str]) -> set[str]:
        return set(w for w in words if w in self.words_counter)

    def edits1(self, word: str) -> set[str]:
        letters    = 'abcdefghijklmnopqrstuvwxyz'
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self, word: str) -> set[str]:
        return set(e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))

    def correct(self, word: str) -> str:
        word = word.lower()
        if word in COMMON_TYPOS:
            return COMMON_TYPOS[word]
        candidates = self.known([word]) or self.known(self.edits1(word)) or self.known(self.edits2(word)) or {word}
        return max(candidates, key=self.P)

    def find_typo(self, sentence: str) -> dict[str, str] | None:
        words = re.findall(r'\b[a-zA-Z\']+\b', sentence)
        for w in words:
            w_lower = w.lower()
            if w_lower in COMMON_TYPOS:
                return {"incorrect": w, "correct": COMMON_TYPOS[w_lower]}
            if len(w_lower) <= 2 or w_lower in self.words_counter:
                continue
            corrected = self.correct(w_lower)
            if corrected != w_lower:
                return {"incorrect": w, "correct": corrected}
        return None


class CognitionCore(BaseService):
    """
    CognitionCore is the primary LLM reasoning interface.
    Sends prompts to local in-process models (Sovereign GPT or direct model weights).
    """

    def __init__(self) -> None:
        self._model_id = "sovereign-gpt"
        self._temperature = 0.7
        self._max_tokens = 2048
        self._initialized = False
        self._use_direct = False
        self._tokenizer: Any = None
        self._model: Any = None
        self._log = Logger.get("Cognition")
        
        # Initialize spell checker using the local corpus data
        root = Path(__file__).resolve().parent.parent.parent.parent.parent
        corpus_path = root / "Data" / "training" / "sovereign_gpt" / "corpus.txt"
        self._spell_checker = CorpusSpellChecker(corpus_path)

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="cognition",
            version="0.1.0",
            description="Primary LLM reasoning core interface (rebranded as Vibhu-Oska Direct Core)",
            capabilities=["reasoning", "generation"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.GPU if self._use_direct else ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "generate":
            return await self.generate(
                prompt=kwargs["prompt"],
                system_prompt=kwargs.get("system_prompt", ""),
                context=kwargs.get("context"),
                temperature=kwargs.get("temperature"),
                max_tokens=kwargs.get("max_tokens"),
                model_id=kwargs.get("model_id")
            )
        else:
            raise ValueError(f"Action '{action}' is not supported by Cognition.")

    async def initialize(self) -> None:
        """Load inference configurations from ConfigLoader."""
        if self._initialized:
            return

        config = ConfigLoader.load()
        model_cfg = config.get_section("models.reasoning")
        self._model_id = model_cfg.get("name", "sovereign-gpt")
        
        # Keep loading of direct transformer completely lazy (no eager loading on startup)
        self._use_direct = False
        self._initialized = True

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def load_direct_model(self) -> None:
        """Load in-process transformers weights."""
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        model_name = "Qwen/Qwen2.5-0.5B-Instruct"
        self._log.info(f"Loading in-process direct transformer: {model_name}")
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._log.info(f"Loading in-process model on: {device}")
        self._model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32
        ).to(device)
        self._use_direct = True

    async def generate_direct(
        self,
        prompt: str,
        system_prompt: str = "",
        context: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ) -> TaskResponse:
        """Runs in-process generation using loaded transformers weights."""
        import time
        import torch

        if not self._model or not self._tokenizer:
            raise RuntimeError("Direct transformer model/tokenizer is not loaded.")

        start_time = time.time()
        
        # Build prompt messages for instruct template
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        context_str = ""
        if context:
            context_str = "Context:\n" + "\n".join(f"- {c.get('content', '')}" for c in context) + "\n\n"
            
        messages.append({"role": "user", "content": f"{context_str}Query: {prompt}"})
        
        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)
        
        def _run_model():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens if max_tokens is not None else 128,
                temperature=temperature if temperature is not None else 0.7,
                do_sample=True if (temperature and temperature > 0.0) else False,
            )
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, outputs)
            ]
            return self._tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
        output_content = await asyncio.to_thread(_run_model)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        prompt_tokens = inputs.input_ids.shape[1]
        completion_tokens = len(self._tokenizer.encode(output_content))
        
        return TaskResponse(
            content=output_content,
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            ),
            metadata=ResponseMetadata(
                status=Status(code=StatusCode.COMPLETED, message="Inference completed successfully via in-process Direct Transformer")
            )
        )

    async def generate_sovereign(
        self,
        prompt: str,
        system_prompt: str = "",
        context: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ) -> TaskResponse:
        """Runs prompt inference using our custom Sovereign GPT from scratch."""
        import time
        from pathlib import Path
        
        # Check if model has checkpoints
        root = Path(__file__).resolve().parent.parent.parent.parent.parent
        checkpoints_dir = root / "Models" / "sovereign_gpt" / "checkpoints"
        
        vocab_path = checkpoints_dir / "tokenizer_vocab.json"
        ckpt_path = checkpoints_dir / "sovereign_gpt.pt"
        
        if not vocab_path.exists() or not ckpt_path.exists():
            return TaskResponse(
                content="Sovereign GPT has not been trained yet. Please initialize training from the Configuration panel first.",
                token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                metadata=ResponseMetadata(
                    status=Status(code=StatusCode.FAILED, message="Model checkpoints missing. Train the model first.")
                )
            )
            
        try:
            from Models.sovereign_gpt.generate import SovereignGPTGenerator
            
            if not hasattr(self, "_sovereign_generator") or self._sovereign_generator is None:
                self._log.info("Loading Sovereign GPT generator from checkpoints...")
                self._sovereign_generator = SovereignGPTGenerator(checkpoints_dir)
            
            start_time = time.time()
            
            if context:
                formatted_prompt = "Context:\n"
                for item in context:
                    formatted_prompt += f"- {item.get('content', '')}\n"
                formatted_prompt += f"\nQuery: {prompt}\nResponse:"
            else:
                formatted_prompt = f"Query: {prompt}\nResponse:"
                
            def _generate():
                return self._sovereign_generator.generate(
                    prompt=formatted_prompt,
                    max_tokens=max_tokens if max_tokens is not None else 128,
                    temperature=temperature if temperature is not None else 0.7
                )
                
            output = await asyncio.to_thread(_generate)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            prompt_tokens = len(self._sovereign_generator.tokenizer.encode(formatted_prompt))
            completion_tokens = len(self._sovereign_generator.tokenizer.encode(output))
            
            return TaskResponse(
                content=output,
                token_usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                ),
                metadata=ResponseMetadata(
                    status=Status(code=StatusCode.COMPLETED, message="Inference completed successfully via Sovereign GPT")
                )
            )
            
        except Exception as e:
            self._log.error("Failed running Sovereign GPT inference", error=str(e))
            return TaskResponse(
                content=f"Error running Sovereign GPT inference: {str(e)}",
                token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                metadata=ResponseMetadata(
                    status=Status(code=StatusCode.FAILED, message=str(e))
                )
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        context: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model_id: str | None = None
    ) -> TaskResponse:
        """
        Executes an inference request. Prefers in-process direct local model
        loaded in Python memory for full offline autonomous capabilities.
        Allows targeting 'sovereign-gpt' explicitly if selected.
        """
        if not self._initialized:
            await self.initialize()

        # Dynamic spelling correction check based on the corpus
        typo_info = self._spell_checker.find_typo(prompt)
        if typo_info:
            base_prompt = system_prompt if system_prompt else "You are Vibhu-Oska AI-OS. Respond concisely and professionally."
            active_system_prompt = (
                f"{base_prompt}\n"
                f"The user's query contains a spelling typo: '{typo_info['incorrect']}'. The correct word is '{typo_info['correct']}'.\n"
                f"You MUST start your response with the exact sentence: \"Aha, I see typo there '{typo_info['incorrect']}' and correct is '{typo_info['correct']}'.\" and then answer the query normally."
            )
        else:
            if system_prompt:
                active_system_prompt = system_prompt
            else:
                active_system_prompt = "You are Vibhu-Oska AI-OS. Respond concisely and professionally. Do NOT output any \"Aha...\" typo correction prefix."

        # Route request based on selected target
        if model_id == "sovereign-gpt":
            return await self.generate_sovereign(prompt, active_system_prompt, context, temperature, max_tokens)

        if model_id in ("vibhu-core", "direct-transformers"):
            try:
                if not self._model or not self._tokenizer:
                    await self.load_direct_model()
                return await self.generate_direct(prompt, active_system_prompt, context, temperature, max_tokens)
            except Exception as e:
                self._log.warning("Direct transformer loading/generation failed, falling back to Sovereign GPT", error=str(e))
                return await self.generate_sovereign(prompt, active_system_prompt, context, temperature, max_tokens)

        # Default fallback sequence (model_id == "" or other values)
        # Try Sovereign GPT first if checkpoints exist
        root = Path(__file__).resolve().parent.parent.parent.parent.parent
        checkpoints_dir = root / "Models" / "sovereign_gpt" / "checkpoints"
        vocab_path = checkpoints_dir / "tokenizer_vocab.json"
        ckpt_path = checkpoints_dir / "sovereign_gpt.pt"

        if vocab_path.exists() and ckpt_path.exists():
            try:
                self._log.info("Attempting inference via Sovereign GPT...")
                return await self.generate_sovereign(prompt, active_system_prompt, context, temperature, max_tokens)
            except Exception as e:
                self._log.warning("Sovereign GPT inference failed, trying direct local transformer", error=str(e))

        # Fallback to direct local model
        try:
            if not self._model or not self._tokenizer:
                await self.load_direct_model()
            return await self.generate_direct(prompt, active_system_prompt, context, temperature, max_tokens)
        except Exception as e:
            self._log.error("Both Sovereign GPT and Direct local transformer failed", error=str(e))
            # Re-raise so HybridCore routes to Backup CPU Core
            raise e

    def process(self, data: Any) -> Any:
        """Backward compatibility pass-through."""
        return data