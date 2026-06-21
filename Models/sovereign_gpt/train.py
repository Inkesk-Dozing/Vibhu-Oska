"""
Vibhu-Oska AI-OS — Sovereign GPT Training Script
Trains the custom causal language model and tokenizer from scratch.
"""

from __future__ import annotations

import argparse
import math
import time
import json
import logging
from pathlib import Path
from typing import Optional, Callable
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from Models.sovereign_gpt.architecture import GPTConfig, VibhuOskaGPT
from Models.sovereign_gpt.tokenizer import SovereignBPETokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("SovereignGPTTrainer")


# ══════════════════════════════════════════════════════════════════
# Corpus Generator (Self-Contained Seeding)
# ══════════════════════════════════════════════════════════════════

def seed_default_corpus(path: Path) -> None:
    """Seeds a text corpus of local instructions and stories for self-contained boot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    stories = [
        "Vibhu-Oska AI-OS is a sovereign operating layer running entirely on local CPU and GPU silicon.",
        "The system coordinates ZMQ event routing and SQLite relational memory state.",
        
        # --- Normal Q&A Templates ---
        "Query: hello\nResponse: Greetings, creator. I am Vibhu-Oska, running locally. Speak, what shall we form today?",
        "Query: how do you work?\nResponse: I am an Autonomous AI Operating Layer (AI-OS) that routes tasks, manages memory, and executes OS commands locally.",
        
        # --- Context-Aware Queries ---
        "Context:\n- Paris is the capital of France.\n\nQuery: what is the capital of France?\nResponse: Paris is the capital of France.",
        "Context:\n- Water boils at 100 degrees Celsius.\n\nQuery: what temperature does water boil at?\nResponse: Water boils at 100 degrees Celsius.",
        "Context:\n- Vibhu-Oska is running in backup Core mode.\n\nQuery: what mode is the system running in?\nResponse: Vibhu-Oska is running in backup Core mode.",

        # --- Typo Correction Templates ---
        "Query: wtf is this now sihg\nResponse: Aha, I see typo there 'sihg' and correct is 'sigh'. This is the Vibhu-Oska local environment.",
        "Query: amke it talk normal\nResponse: Aha, I see typo there 'amke' and correct is 'make'. I will respond normally and concisely.",
        "Query: i twnat to check this\nResponse: Aha, I see typo there 'twnat' and correct is 'want'. Let's verify the system behavior.",
        "Query: welocme\nResponse: Aha, I see typo there 'welocme' and correct is 'welcome'. Greetings, creator. I am Vibhu-Oska, running locally.",
        "Query: hello how to acieve this\nResponse: Aha, I see typo there 'acieve' and correct is 'achieve'. To achieve this locally, we run the custom training scripts.",
        "Query: train it proeprly\nResponse: Aha, I see typo there 'proeprly' and correct is 'properly'. I am being trained properly on local hardware resources.",
        "Query: is it trained roeprly\nResponse: Aha, I see typo there 'roeprly' and correct is 'properly'. Yes, the neural weights are optimized on the local corpus.",
        "Query: how does it reacognize typos\nResponse: Aha, I see typo there 'reacognize' and correct is 'recognize'. The spelling checker in CognitionCore detects typos and routes them dynamically.",
        "Query: what is the reposnse\nResponse: Aha, I see typo there 'reposnse' and correct is 'response'. The response is computed in-process using local tensor matrices.",
        "Query: it is semeingly normal\nResponse: Aha, I see typo there 'semeingly' and` + ` 'seemingly'. Yes, the system generates clean output logs.",
        "Query: wt is this\nResponse: Aha, I see typo there 'wt' and correct is 'what'. This is the central workspace playground.",
        "Query: it sint working\nResponse: Aha, I see typo there 'sint' and correct is 'isn\'t'. Let\'s diagnostic trace the background server ports.",

        # --- Python & Algorithms ---
        "Query: write a python calculator\nResponse: Here is a simple python calculator:\n```python\ndef add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b\n\ndef divide(a, b):\n    if b == 0:\n        return 'Error: division by zero'\n    return a / b\n```",
        "Query: how do you add two numbers in python?\nResponse: You can define an add function:\n```python\ndef add(a, b):\n    return a + b\n```",
        "Query: write a python loop\nResponse: To write a loop in Python:\n```python\nfor i in range(5):\n    print(f'Iteration {i}')\n```",
        "Query: write a python class\nResponse: Here is a python class definition:\n```python\nclass Creator:\n    def __init__(self, name):\n        self.name = name\n    def speak(self):\n        return f'Greetings from {self.name}'\n```",
        "Query: sort a list of dicts by key in python\nResponse: You can sort a list of dictionaries by key using a lambda function:\n```python\ndef sort_dicts(data, key):\n    return sorted(data, key=lambda x: x[key])\n```",
        "Query: read a file in python\nResponse: To read a file in Python, use a with statement:\n```python\ndef read_file(path):\n    with open(path, 'r', encoding='utf-8') as f:\n        return f.read()\n```",
        "Query: write to a file in python\nResponse: To write text to a file in Python:\n```python\ndef write_file(path, content):\n    with open(path, 'w', encoding='utf-8') as f:\n        f.write(content)\n```",
        "Query: merge two dicts in python\nResponse: You can merge two dictionaries using the union operator in Python 3.9+:\n```python\ndef merge_dicts(dict_a, dict_b):\n    return dict_a | dict_b\n```",
        "Query: check if key exists in dict\nResponse: Use the in keyword to check if a key is present in a dictionary:\n```python\nif key in dictionary:\n    print('Key exists')\n```",
        "Query: write a list comprehension in python\nResponse: List comprehensions provide a concise way to create lists:\n```python\nsquares = [x**2 for x in range(10)]\n```",
        "Query: write a binary search in python\nResponse: Here is the binary search algorithm:\n```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n```",
        
        # --- FastAPI & Web Frameworks ---
        "Query: write a fastapi app\nResponse: Here is a basic FastAPI application:\n```python\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef read_root():\n    return {'status': 'healthy'}\n```",
        "Query: fastapi post request JSON\nResponse: Define a post endpoint using a Pydantic model:\n```python\nfrom fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass Item(BaseModel):\n    name: str\n    price: float\n\n@app.post('/items')\ndef create_item(item: Item):\n    return {'message': f'{item.name} created'}\n```",
        "Query: fastapi path parameter\nResponse: Pass path parameters directly in endpoint arguments:\n```python\n@app.get('/users/{user_id}')\ndef get_user(user_id: int):\n    return {'user_id': user_id}\n```",
        "Query: run uvicorn server\nResponse: Run FastAPI locally using uvicorn:\n```bash\nuvicorn main:app --reload --host 127.0.0.1 --port 8000\n```",
        
        # --- Frontend & React ---
        "Query: write a react functional component\nResponse: Here is a simple React component:\n```jsx\nimport React from 'react';\n\nexport default function Heading({ title }) {\n    return <h1>{title}</h1>;\n}\n```",
        "Query: react counter component using useState\nResponse: A React counter component:\n```jsx\nimport React, { useState } from 'react';\n\nexport default function Counter() {\n    const [count, setCount] = useState(0);\n    return (\n        <div>\n            <p>Count: {count}</p>\n            <button onClick={() => setCount(count + 1)}>Increment</button>\n        </div>\n    );\n}\n```",
        "Query: react form submission\nResponse: Handle form submission in React:\n```jsx\nimport React, { useState } from 'react';\n\nexport default function Form() {\n    const [text, setText] = useState('');\n    const handleSubmit = (e) => {\n        e.preventDefault();\n        console.log(text);\n    };\n    return (\n        <form onSubmit={handleSubmit}>\n            <input value={text} onChange={(e) => setText(e.target.value)} />\n            <button type='submit'>Submit</button>\n        </form>\n    );\n}\n```",
        "Query: react conditional rendering\nResponse: Render elements conditionally using ternary operators:\n```jsx\n{isLoggedIn ? <Dashboard /> : <LoginForm />}\n```",
        
        # --- UI Design & CSS ---
        "Query: write a css grid layout\nResponse: Set up a grid container with three equal columns:\n```css\n.grid-container {\n    display: grid;\n    grid-template-columns: repeat(3, 1fr);\n    gap: 16px;\n}\n```",
        "Query: write css flexbox centering\nResponse: Center child elements vertically and horizontally:\n```css\n.centered {\n    display: flex;\n    justify-content: center;\n    align-items: center;\n}\n```",
        "Query: css custom properties variables\nResponse: Declare and use CSS variables:\n```css\n:root {\n    --primary-color: #00f0ff;\n    --bg-dark: #0a0a0f;\n}\nbody {\n    background-color: var(--bg-dark);\n    color: var(--primary-color);\n}\n```",
        "Query: write css glassmorphism style\nResponse: Create a frosted glass backdrop filter style:\n```css\n.glass-panel {\n    background: rgba(255, 255, 255, 0.05);\n    backdrop-filter: blur(12px);\n    border: 1px solid rgba(255, 255, 255, 0.1);\n    border-radius: 8px;\n}\n```",
        
        # --- Database & SQL ---
        "Query: sqlite select query\nResponse: Query rows matching a condition:\n```sql\nSELECT * FROM users WHERE status = 'active';\n```",
        "Query: sqlite join query\nResponse: Retrieve session history details with user references:\n```sql\nSELECT s.title, c.role, c.content\nFROM sessions s\nJOIN chats c ON s.session_id = c.session_id\nWHERE s.user_id = ?;\n```",
        "Query: sqlite insert row\nResponse: Insert a new message into the relational DB:\n```sql\nINSERT INTO chats (message_id, session_id, role, content) VALUES (?, ?, ?, ?);\n```",
        "Query: chromadb add document\nResponse: Store content in ChromaDB persistent collection:\n```python\ncollection.add(documents=[content], metadatas=[meta], ids=[doc_id])\n```",
        "Query: chromadb query documents\nResponse: Query ChromaDB with semantic search:\n```python\nresults = collection.query(query_texts=[query_text], n_results=top_k)\n```",
        
        # --- Vibhu-Oska Components ---
        "Query: what is the validation core?\nResponse: ValidationCore performs double-validation checking input safety (SQLi/XSS prevention) and output schema compliance.",
        "Query: what is the cognition core?\nResponse: CognitionCore is the primary LLM reasoning interface that generates responses locally on CPU or GPU.",
        "Query: what is the data core?\nResponse: DataCore handles relational database persistence in SQLite and long-term semantic memory lookups in ChromaDB.",
        "Query: how does AGI self-evolve?\nResponse: The recursive self-evolution loop writes new code modules, tests them in an isolated sandbox, and updates the active system files.",
        "Query: how do you run tests?\nResponse: Run `.venv\\Scripts\\pytest` to execute all brain stem integration tests.",
        
        # --- Numbers, Letters & Word Understanding ---
        "Query: count from 1 to 5\nResponse: 1, 2, 3, 4, 5.",
        "Query: count from 1 to 10\nResponse: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10.",
        "Query: what is 2 plus 3?\nResponse: 2 plus 3 equals 5.",
        "Query: what is 1 plus 1?\nResponse: 1 plus 1 equals 2.",
        "Query: what is 10 minus 4?\nResponse: 10 minus 4 equals 6.",
        "Query: what is 5 times 5?\nResponse: 5 times 5 equals 25.",
        "Query: what is 3 times 4?\nResponse: 3 times 4 equals 12.",
        "Query: list even numbers between 1 and 10\nResponse: The even numbers are 2, 4, 6, 8, 10.",
        "Query: list odd numbers between 1 and 10\nResponse: The odd numbers are 1, 3, 5, 7, 9.",
        "Query: is 7 a prime number?\nResponse: Yes, 7 is a prime number.",
        "Query: spell vibhu\nResponse: V - I - B - H - U.",
        "Query: spell oska\nResponse: O - S - K - A.",
        "Query: spell create\nResponse: C - R - E - A - T - E.",
        "Query: spell python\nResponse: P - Y - T - H - O - N.",
        "Query: spell logic\nResponse: L - O - G - I - C.",
        "Query: spell cognitive\nResponse: C - O - G - N - I - T - I - V - E.",
        "Query: spell local\nResponse: L - O - C - A - L.",
        "Query: what are the vowels?\nResponse: The vowels are A, E, I, O, U.",
        "Query: what are the consonants?\nResponse: Consonants are all letters in the alphabet other than the vowels A, E, I, O, U.",
        "Query: define algorithm\nResponse: An algorithm is a step-by-step procedure or set of rules to solve a problem.",
        "Query: define compiler\nResponse: A compiler translates source code written in a high-level programming language into machine code.",
        "Query: define database\nResponse: A database is a structured collection of data stored and accessed electronically.",
        "Query: define intelligence\nResponse: Intelligence is the ability to acquire, apply, and adapt knowledge and skills.",
        "Query: define function\nResponse: A function is a reusable block of code that performs a specific task.",
        "Query: define variable\nResponse: A variable is a named storage location in memory that holds a value that can change.",
        "Query: what is a synonym for fast?\nResponse: A synonym for fast is quick or rapid.",
        "Query: what is a synonym for smart?\nResponse: A synonym for smart is intelligent or clever.",
        "Query: what is the opposite of hot?\nResponse: The opposite of hot is cold.",
        "Query: what is the opposite of large?\nResponse: The opposite of large is small.",
        "Query: what is the opposite of true?\nResponse: The opposite of true is false.",
        "Query: complete the phrase: early bird catches the\nResponse: catches the worm.",
        "Query: complete the phrase: practice makes\nResponse: practice makes perfect.",
        "Query: what does a cat do?\nResponse: A cat purrs and meows.",
        "Query: what does a dog do?\nResponse: A dog barks and wags its tail.",
        "Query: what does a bird do?\nResponse: A bird chirps, sings, and flies.",
        "Query: what does a fish do?\nResponse: A fish swims in the water.",
        "Query: what is the purpose of an operating system?\nResponse: An operating system manages computer hardware and software resources.",
        "Query: count from 10 to 15\nResponse: 10, 11, 12, 13, 14, 15.",
        "Query: count from 20 to 25\nResponse: 20, 21, 22, 23, 24, 25.",
        "Query: what is 7 plus 8?\nResponse: 7 plus 8 equals 15.",
        "Query: what is 12 minus 5?\nResponse: 12 minus 5 equals 7.",
        "Query: what is 9 times 3?\nResponse: 9 times 3 equals 27.",
        "Query: what is 16 divided by 4?\nResponse: 16 divided by 4 equals 4.",
        "Query: is 9 greater than 4?\nResponse: Yes, 9 is greater than 4.",
        "Query: is 2 an even number?\nResponse: Yes, 2 is an even number.",
        "Query: spell hello\nResponse: H - E - L - L - O.",
        "Query: spell studio\nResponse: S - T - U - D - I - O.",
        "Query: spell system\nResponse: S - Y - S - T - E - M.",
        "Query: what is the opposite of up?\nResponse: The opposite of up is down.",
        "Query: what is the opposite of open?\nResponse: The opposite of open is closed.",
        "Query: what is a synonym for clean?\nResponse: A synonym for clean is tidy or neat.",
        "Query: how many vowels in vibhu?\nResponse: There are 2 vowels in vibhu.",
        "Query: how many consonants in oska?\nResponse: There are 2 consonants in oska.",
    ]
    
    # Duplicate to create a larger corpus for tokenizer and model training
    corpus = "\n\n".join(stories * 2)
    path.write_text(corpus, encoding="utf-8")
    log.info(f"Seeded default training corpus at: {path}")


# ══════════════════════════════════════════════════════════════════
# PyTorch Dataset
# ══════════════════════════════════════════════════════════════════

class CausalDataset(Dataset):
    def __init__(self, sequences: list[list[int]], max_seq_len: int = 128, pad_id: int = 0) -> None:
        self.sequences = []
        for seq in sequences:
            if len(seq) > max_seq_len:
                seq = seq[:max_seq_len]
            padded = seq + [pad_id] * (max_seq_len - len(seq))
            self.sequences.append(padded)

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        seq = self.sequences[idx]
        x = torch.tensor(seq, dtype=torch.long)
        # For labels, map all pad_id values (0) to -100 to ignore them in cross entropy loss
        y = x.clone()
        y[y == 0] = -100
        return {"input_ids": x, "labels": y}


# ══════════════════════════════════════════════════════════════════
# Training Loop
# ══════════════════════════════════════════════════════════════════

def train(
    corpus_path: Path,
    output_dir:  Path,
    epochs:      int   = 5,
    batch_size:  int   = 4,
    lr:          float = 2e-4,
    max_len:     int   = 128,
    device:      str   = "auto",
    test_run:    bool  = False,
    hidden_size: int   = 128,
    num_layers:  int   = 4,
    num_heads:   int   = 4,
    vocab_size:  int   = 2000,
    progress_callback: Optional[Callable[[str], None]] = None
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    def notify(msg: str):
        log.info(msg)
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

    # 1. Always seed/refresh the default training corpus
    seed_default_corpus(corpus_path)

    # 2. Train Tokenizer
    corpus_text = corpus_path.read_text(encoding="utf-8")
    
    tokenizer_path = output_dir / "tokenizer_vocab.json"
    tokenizer = SovereignBPETokenizer()
    
    target_vocab_size = 800 if test_run else vocab_size
    notify(f"Training BPE tokenizer (target vocab size = {target_vocab_size})...")
    tokenizer.train(corpus_text, target_vocab_size=target_vocab_size)
    tokenizer.save(tokenizer_path)
    notify(f"Tokenizer saved → {tokenizer_path}")

    # 3. Split corpus into logical blocks and tokenize each separately
    blocks = [b.strip() for b in corpus_text.split("\n\n") if b.strip()]

    notify(f"Parsed {len(blocks)} independent Q&A sequences from corpus.")
    
    sequences = [tokenizer.encode(b) for b in blocks]
    # Filter empty sequences
    sequences = [s for s in sequences if len(s) > 0]

    # 4. Create DataLoader
    train_ds = CausalDataset(sequences, max_seq_len=max_len)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    # 5. Device Setup
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dev = torch.device(device)
    notify(f"Running training on device: {device}")

    # 6. Initialize Model
    config = GPTConfig(
        vocab_size=len(tokenizer.vocab),
        hidden_size=64 if test_run else hidden_size,
        intermediate_size=256 if test_run else (hidden_size * 4),
        num_layers=2 if test_run else num_layers,
        num_heads=4 if test_run else num_heads,
        max_seq_len=max_len
    )
    model = VibhuOskaGPT(config).to(dev)
    notify(f"Model initialized: {model.count_parameters():,} trainable parameters.")

    # 7. Optimizer, Scheduler & Loss
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps_per_epoch = len(train_loader)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=lr,
        steps_per_epoch=steps_per_epoch,
        epochs=epochs,
        pct_start=0.1,  # 10% warmup
        anneal_strategy="cos"
    )
    
    # 8. Training loop
    best_loss = float("inf")
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_correct = 0
        total_tokens = 0
        start_time = time.time()

        for step, batch in enumerate(train_loader, 1):
            input_ids = batch["input_ids"].to(dev)
            labels    = batch["labels"].to(dev)

            out = model(input_ids=input_ids, labels=labels)
            loss = out["loss"]

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()

            # Accuracy calculation
            logits = out["logits"]
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            preds = shift_logits.argmax(dim=-1)
            mask = shift_labels != -100
            total_correct += (preds[mask] == shift_labels[mask]).sum().item()
            total_tokens += mask.sum().item()

            if test_run:
                # Fast exit on test checks
                break

        avg_loss = total_loss / len(train_loader)
        accuracy = (total_correct / total_tokens) if total_tokens > 0 else 0.0
        perplexity = math.exp(avg_loss) if avg_loss < 20 else 99999.0
        elapsed = time.time() - start_time
        
        notify(
            f"Epoch {epoch}/{epochs} | Loss: {avg_loss:.4f} | "
            f"Accuracy: {accuracy * 100:.2f}% | "
            f"Perplexity: {perplexity:.2f} | Time: {elapsed:.2f}s"
        )

        # Save checkpoint
        if avg_loss < best_loss:
            best_loss = avg_loss
            ckpt_path = output_dir / "sovereign_gpt.pt"
            torch.save({
                "epoch": epoch,
                "model_state": model.state_dict(),
                "config": config.__dict__,
                "best_loss": best_loss
            }, ckpt_path)
            notify(f"[SAVED] Saved best model checkpoint → {ckpt_path}")

        if not test_run and accuracy >= 0.995 and epoch >= 15:
            notify(f"[CONVERGED] Model converged to near-perfect accuracy ({accuracy * 100:.2f}%) at epoch {epoch}. Stopping early.")
            break

        if test_run:
            notify("Test-run compile validation successful.")
            break

    notify("Sovereign GPT training loop completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Sovereign GPT from scratch")
    parser.add_argument("--epochs",    type=int, default=40)
    parser.add_argument("--batch",     type=int, default=4)
    parser.add_argument("--lr",        type=float, default=2e-4)
    parser.add_argument("--test-run",  action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent.parent
    corpus_file = root / "Data" / "training" / "sovereign_gpt" / "corpus.txt"
    checkpoints = root / "Models" / "sovereign_gpt" / "checkpoints"

    train(
        corpus_path = corpus_file,
        output_dir  = checkpoints,
        epochs      = args.epochs,
        batch_size  = args.batch,
        lr          = args.lr,
        test_run    = args.test_run
    )
