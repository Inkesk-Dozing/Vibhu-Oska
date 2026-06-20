# 11 — Complete Run Guide (New Machine → System Live)

> This is the definitive step-by-step reference for setting up and running Vibhu-Oska from scratch.
> All commands assume Windows PowerShell unless noted otherwise.

---

## Prerequisites

| Requirement | Check command | Notes |
|---|---|---|
| Python 3.11+ | `python --version` | Must be 3.11.x |
| Git | `git --version` | For cloning |
| CUDA 12.1+ | `nvidia-smi` | Optional — CPU fallback works |
| 20GB free disk | — | For models + venv |

---

## Step 1: Get the Code

```powershell
# If you already have the directory:
cd C:\Users\USER\Desktop\Extras\.i-oska\Vibhu-Oska

# If cloning fresh:
git clone <your-repo-url> Vibhu-Oska
cd Vibhu-Oska
```

---

## Step 2: Create Virtual Environment

```powershell
# Create isolated environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Verify Python path
python -c "import sys; print(sys.executable)"
# Should show: C:\...\Vibhu-Oska\.venv\Scripts\python.exe
```

If PowerShell blocks script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Step 3: Install Core Dependencies (Editable Install)

```powershell
# This is the critical step — makes Backend/* importable everywhere
pip install -e .

# Verify editable install worked
python -c "from Backend.EntryPoint import main; print('OK')"
```

---

## Step 4: Install ML Dependencies

```powershell
# For NVIDIA GPU (CUDA 12.1) — strongly recommended
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes peft sentencepiece datasets

# Verify GPU is accessible
python -c "import torch; print(torch.cuda.is_available())"
# True → GPU available
# False → CPU fallback mode
```

---

## Step 5: Configure

```powershell
# Copy environment template
copy .env.example .env

# Edit .env with your settings (JWT secret, log level, etc.)
notepad .env
```

`config/default.yaml` controls all runtime settings. Edit directly for custom host/port/model selection.

---

## Step 6: Verify Models Are Ready

```powershell
# Check Sovereign GPT checkpoint
python -c "from pathlib import Path; p = Path('Models/sovereign_gpt/checkpoints/sovereign_gpt.pt'); print('GPT OK' if p.exists() else 'MISSING - train first')"

# Check Router checkpoint
python -c "from pathlib import Path; p = Path('Models/router/checkpoints/best_router.pt'); print('Router OK' if p.exists() else 'MISSING - train first')"
```

If missing, train them:
```powershell
# Train Sovereign GPT (~5-30 min depending on epochs)
python -m Models.sovereign_gpt.train

# Train Router (~2-10 min)
python -m Models.router.train
```

---

## Step 7: Run Tests (Verify Everything Works)

```powershell
pip install pytest pytest-asyncio  # if not already installed
python -m pytest Tests/ -v
# Expected: 65 passed
```

---

## Step 8: Start the System

```powershell
# Method 1: Module entry (most verbose, good for debugging)
python -m Backend.EntryPoint

# Method 2: CLI entry (after editable install)
vibhu-oska

# Method 3: Development mode with auto-reload
$env:ENVIRONMENT = "development"
python -m Backend.EntryPoint
```

**Expected startup output:**
```
[INFO] ==========================================
[INFO]   Vibhu-Oska AI-OS
[INFO]   Version: 0.2.0
[INFO]   Codename: sovereign
[INFO]   Environment: development
[INFO]   Tier: private
[INFO] ==========================================
[INFO] Starting API Gateway host=127.0.0.1 port=8000
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
[INFO] EventBus started
[INFO] ToolRegistry initialized with N plugins
[INFO] OrchestratorCore registered on EventBus
[INFO] Watchdog started
[INFO] System is LIVE
```

---

## Step 9: Test the API

```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:8000/health -Method GET | Select-Object -ExpandProperty Content

# Chat request
$body = '{"prompt": "What is your purpose?", "session_id": "test-001"}'
Invoke-WebRequest -Uri http://localhost:8000/chat -Method POST -Body $body -ContentType "application/json" | Select-Object -ExpandProperty Content
```

**Or use FastAPI docs**: http://localhost:8000/docs

---

## Optional: Train QLoRA Fine-Tuning Adapter

```powershell
# Requires: GPU ≥8GB VRAM + bitsandbytes + peft
python -m Models.reasoning.finetune --model qwen2.5-coder --epochs 1
# Downloads Qwen2.5-Coder-3B (~6GB on first run)
# Saves adapters to: Models/reasoning/lora_adapters/
```

---

## Optional: Run MCP Server

```powershell
vibhu-oska-mcp
# Starts Model Context Protocol server for IDE integration
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: Backend` | Editable install not done | `pip install -e .` |
| `CUDA out of memory` | GPU VRAM insufficient | Use CPU: `export CUDA_VISIBLE_DEVICES=""` |
| `ZMQ error: Address in use` | Old server still running | Kill the old process, restart |
| `sqlite3.OperationalError` | DB schema mismatch | Delete `Data/vibhu_oska.db` and restart |
| `bitsandbytes CUDA setup error` | bitsandbytes not built for your CUDA | Install correct version: `pip install bitsandbytes --upgrade` |
