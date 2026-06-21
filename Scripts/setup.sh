#!/usr/bin/env bash
# ============================================================================
# Vibhu-Oska AI-OS — One-shot Environment Setup Script
# Bootstraps the complete development environment from scratch.
#
# Prerequisites:
#   - Python 3.11+
#   - CUDA 12.x + cuDNN (for RTX 4060 training)
#   - Git
#
# Usage:
#   bash Scripts/setup.sh
#   bash Scripts/setup.sh --skip-venv    # Skip venv creation if exists
#   bash Scripts/setup.sh --gpu          # Also install GPU-specific deps
# ============================================================================

set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
GPU_MODE=false
SKIP_VENV=false

# ── Parse flags ───────────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --gpu)        GPU_MODE=true ;;
        --skip-venv)  SKIP_VENV=true ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "\033[1;36m[INFO]\033[0m  $*"; }
success() { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error()   { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ── Step 1: Verify Python version ─────────────────────────────────────────────
info "Checking Python version..."
PY_VERSION=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [[ "$PY_MAJOR" -lt 3 || "$PY_MINOR" -lt 11 ]]; then
    error "Python 3.11+ required. Found: $PY_VERSION"
fi
success "Python $PY_VERSION"

# ── Step 2: Create virtual environment ────────────────────────────────────────
if [[ "$SKIP_VENV" == false ]]; then
    if [[ -d "$VENV_DIR" ]]; then
        warn "Virtual environment already exists at $VENV_DIR — skipping creation"
    else
        info "Creating virtual environment at $VENV_DIR..."
        $PYTHON_BIN -m venv "$VENV_DIR"
        success "Virtual environment created"
    fi
fi

VENV_PIP="$VENV_DIR/bin/pip"
VENV_PY="$VENV_DIR/bin/python"
[[ -f "$VENV_DIR/Scripts/pip.exe" ]] && VENV_PIP="$VENV_DIR/Scripts/pip.exe"
[[ -f "$VENV_DIR/Scripts/python.exe" ]] && VENV_PY="$VENV_DIR/Scripts/python.exe"

# ── Step 3: Upgrade pip ───────────────────────────────────────────────────────
info "Upgrading pip..."
"$VENV_PIP" install --quiet --upgrade pip wheel
success "pip upgraded"

# ── Step 4: Install CPU dependencies ──────────────────────────────────────────
info "Installing base requirements..."
"$VENV_PIP" install --quiet -r "$PROJECT_ROOT/requirements.txt"
success "Base requirements installed"

# ── Step 5: Editable install ──────────────────────────────────────────────────
info "Installing Vibhu-Oska in editable mode (absolute imports)..."
"$VENV_PIP" install --quiet -e "$PROJECT_ROOT"
success "Editable install complete"

# ── Step 6: GPU dependencies (optional) ───────────────────────────────────────
if [[ "$GPU_MODE" == true ]]; then
    info "Installing GPU dependencies (PyTorch CUDA, bitsandbytes, flash-attn)..."
    "$VENV_PIP" install --quiet \
        torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    "$VENV_PIP" install --quiet bitsandbytes transformers accelerate peft unsloth
    success "GPU dependencies installed"
fi

# ── Step 7: Create required directories ───────────────────────────────────────
info "Creating runtime directories..."
mkdir -p \
    "$PROJECT_ROOT/Data/chromadb" \
    "$PROJECT_ROOT/Data/training/sovereign_gpt" \
    "$PROJECT_ROOT/Data/training/router_dataset" \
    "$PROJECT_ROOT/Data/training/reasoning_dataset" \
    "$PROJECT_ROOT/Data/training/feedback" \
    "$PROJECT_ROOT/Models/sovereign_gpt/checkpoints" \
    "$PROJECT_ROOT/Models/router/checkpoints" \
    "$PROJECT_ROOT/Log"
success "Directories created"

# ── Step 8: Verify imports ────────────────────────────────────────────────────
info "Verifying system imports..."
"$VENV_PY" -c "from Backend.Gateway.App import app; print('  Gateway: OK')"
"$VENV_PY" -c "from Backend.Core.MainCore.OrchestratorCore.OrchestratorCore import OrchestratorCore; print('  Orchestrator: OK')"
"$VENV_PY" -c "from Backend.Core.SpecializedCore.DataCore.datacore import DataCore; print('  DataCore: OK')"
success "All core imports verified"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Vibhu-Oska AI-OS — Environment Ready"
echo "  Run: .venv/bin/python -m Backend.EntryPoint"
echo "  Or:  python -m uvicorn Backend.Gateway.App:app --reload"
echo "════════════════════════════════════════════════════════════"
