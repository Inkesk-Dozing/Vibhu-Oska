"""
Vibhu-Oska AI-OS — Router Training Dataset Generator
Generates synthetic training data for the intent router model.

Creates examples of prompts mapped to:
  - Target: GPU | CPU | NPU
  - Task:   CHAT | CODE | RESEARCH | MEMORY | SYSTEM

Run: python -m Models.router.dataset_generator
Output: Data/training/router_dataset/ (HuggingFace datasets format)
"""

from __future__ import annotations

import json
import random
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
# Training Examples Template
# ══════════════════════════════════════════════════════════════════

TEMPLATES: list[dict] = [
    # ─── CHAT + GPU (requires LLM inference) ───
    {"prompt": "What is the meaning of consciousness?",                      "target": "GPU", "task": "CHAT"},
    {"prompt": "Explain quantum entanglement in simple terms",               "target": "GPU", "task": "CHAT"},
    {"prompt": "Tell me a story about a robot who learns to dream",          "target": "GPU", "task": "CHAT"},
    {"prompt": "What are the philosophical implications of AGI?",            "target": "GPU", "task": "CHAT"},
    {"prompt": "Help me write an essay about climate change",                "target": "GPU", "task": "CHAT"},
    {"prompt": "Can you translate this paragraph to Hindi?",                 "target": "GPU", "task": "CHAT"},
    {"prompt": "Summarize the history of computing",                         "target": "GPU", "task": "CHAT"},
    {"prompt": "What should I know about starting a business?",             "target": "GPU", "task": "CHAT"},
    {"prompt": "Explain the difference between machine learning and AI",    "target": "GPU", "task": "CHAT"},
    {"prompt": "Write a poem about midnight and stars",                      "target": "GPU", "task": "CHAT"},

    # ─── CODE + GPU ───
    {"prompt": "Write a Python function to sort a list of dicts by a key",  "target": "GPU", "task": "CODE"},
    {"prompt": "Create a FastAPI endpoint that returns JSON",                "target": "GPU", "task": "CODE"},
    {"prompt": "Debug this async function: async def foo(): return bar()",  "target": "GPU", "task": "CODE"},
    {"prompt": "Implement a binary search tree in Python",                   "target": "GPU", "task": "CODE"},
    {"prompt": "Write a React component for a modal dialog",                 "target": "GPU", "task": "CODE"},
    {"prompt": "Generate a Dockerfile for a Python FastAPI application",    "target": "GPU", "task": "CODE"},
    {"prompt": "How do I implement async context managers in Python?",       "target": "GPU", "task": "CODE"},
    {"prompt": "Write a SQL query to find duplicate records",                "target": "GPU", "task": "CODE"},
    {"prompt": "Implement JWT authentication in FastAPI",                    "target": "GPU", "task": "CODE"},
    {"prompt": "Create a WebSocket server in Python using asyncio",          "target": "GPU", "task": "CODE"},
    {"prompt": "Write unit tests for this function using pytest",            "target": "GPU", "task": "CODE"},
    {"prompt": "Optimize this O(n²) algorithm to O(n log n)",               "target": "GPU", "task": "CODE"},

    # ─── RESEARCH + CPU (search is IO-bound, not GPU-bound) ───
    {"prompt": "Search for the latest news about artificial intelligence",   "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Find information about quantum computing breakthroughs",     "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Research the current state of fusion energy",                "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Look up the Wikipedia page for Alan Turing",                 "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Find recent papers on transformer architectures",            "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Search for Vibhu-Oska AI-OS documentation",                 "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Research competitors to my SaaS product",                   "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Find the price of RTX 4090 graphics cards",                 "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Look up how to build a deep learning model from scratch",   "target": "CPU", "task": "RESEARCH"},
    {"prompt": "Search for Python asyncio best practices 2024",              "target": "CPU", "task": "RESEARCH"},

    # ─── MEMORY + CPU ───
    {"prompt": "Remember that my project uses ZeroMQ on port 5555",         "target": "CPU", "task": "MEMORY"},
    {"prompt": "Store this API key in your memory for later",               "target": "CPU", "task": "MEMORY"},
    {"prompt": "What did I tell you about my project architecture?",        "target": "CPU", "task": "MEMORY"},
    {"prompt": "Recall my previous conversation about data models",         "target": "CPU", "task": "MEMORY"},
    {"prompt": "Save this note: meeting with Vibhu on Tuesday at 3 PM",     "target": "CPU", "task": "MEMORY"},
    {"prompt": "What do you know about my codebase?",                       "target": "CPU", "task": "MEMORY"},
    {"prompt": "Remember my preferences: dark mode, Python 3.11, FastAPI",  "target": "CPU", "task": "MEMORY"},
    {"prompt": "Store this document in the knowledge graph",                "target": "CPU", "task": "MEMORY"},
    {"prompt": "Search your memory for anything about Ryzen processors",    "target": "CPU", "task": "MEMORY"},
    {"prompt": "Add this to my ideas hub: AI-powered code review tool",     "target": "CPU", "task": "MEMORY"},

    # ─── SYSTEM + NPU (lightweight orchestration tasks) ───
    {"prompt": "Show me the system status and all plugin health",           "target": "NPU", "task": "SYSTEM"},
    {"prompt": "What is the current GPU temperature?",                      "target": "NPU", "task": "SYSTEM"},
    {"prompt": "List all running scheduled tasks",                          "target": "NPU", "task": "SYSTEM"},
    {"prompt": "Restart the search engine plugin",                          "target": "NPU", "task": "SYSTEM"},
    {"prompt": "How much VRAM is being used?",                              "target": "NPU", "task": "SYSTEM"},
    {"prompt": "Show me the event bus activity",                            "target": "NPU", "task": "SYSTEM"},
    {"prompt": "What plugins are currently registered?",                   "target": "NPU", "task": "SYSTEM"},
    {"prompt": "Run the health check on all services",                      "target": "NPU", "task": "SYSTEM"},
    {"prompt": "Show me the uptime of the AI-OS",                           "target": "NPU", "task": "SYSTEM"},
    {"prompt": "Export the feedback training data now",                     "target": "NPU", "task": "SYSTEM"},
    {"prompt": "How many completed tasks are in the queue?",                "target": "NPU", "task": "SYSTEM"},
    {"prompt": "Show me the last 10 replay log entries",                    "target": "NPU", "task": "SYSTEM"},
]

TARGET_MAP = {"GPU": 0, "CPU": 1, "NPU": 2}
TASK_MAP   = {"CHAT": 0, "CODE": 1, "RESEARCH": 2, "MEMORY": 3, "SYSTEM": 4}

# Augmentation patterns
PREFIXES = ["", "Hey, ", "Can you ", "Please ", "I need you to ", ""]
SUFFIXES = ["", ".", "?", " right now", " for me", ""]

# ══════════════════════════════════════════════════════════════════
# Generator
# ══════════════════════════════════════════════════════════════════

def augment(prompt: str) -> list[str]:
    """Create augmented versions of a prompt."""
    variants = [prompt]
    for prefix in PREFIXES[:3]:
        for suffix in SUFFIXES[:3]:
            if prefix or suffix:
                variants.append(f"{prefix}{prompt.lower()}{suffix}")
    return list(set(variants[:5]))  # At most 5 variants


def generate_dataset(
    output_dir: Path,
    num_examples: int = 5000,
    val_split: float = 0.1,
    seed: int = 42,
) -> dict[str, int]:
    """Generate synthetic router training dataset."""
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Expand base templates with augmentation
    all_examples = []
    for tpl in TEMPLATES:
        for augmented_prompt in augment(tpl["prompt"]):
            all_examples.append({
                "text":          augmented_prompt,
                "target_label":  tpl["target"],
                "task_label":    tpl["task"],
                "target_id":     TARGET_MAP[tpl["target"]],
                "task_id":       TASK_MAP[tpl["task"]],
            })

    # Oversample to reach desired count
    while len(all_examples) < num_examples:
        all_examples.extend(random.sample(all_examples, min(len(all_examples), num_examples - len(all_examples))))

    random.shuffle(all_examples)
    all_examples = all_examples[:num_examples]

    # Split
    val_count  = int(len(all_examples) * val_split)
    train_data = all_examples[val_count:]
    val_data   = all_examples[:val_count]

    # Write JSONL files
    def write_jsonl(data: list[dict], path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    write_jsonl(train_data, output_dir / "train.jsonl")
    write_jsonl(val_data,   output_dir / "val.jsonl")

    # Write label maps
    (output_dir / "label_maps.json").write_text(
        json.dumps({"target": TARGET_MAP, "task": TASK_MAP}, indent=2)
    )

    print(f"[SUCCESS] Dataset generated: {len(train_data)} train / {len(val_data)} val examples")
    print(f"  Output: {output_dir}")
    return {"train": len(train_data), "val": len(val_data)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out  = root / "Data" / "training" / "router_dataset"
    generate_dataset(out, num_examples=1000)
