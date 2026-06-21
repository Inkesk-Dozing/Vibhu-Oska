#!/usr/bin/env bash
# ============================================================================
# Vibhu-Oska AI-OS — Sovereign GPT Training Pipeline
# End-to-end script: BPE tokenizer training + transformer training.
#
# Hardware target: NVIDIA RTX 4060 (8GB VRAM)
# Estimated time:  2-8 hours depending on config
#
# Usage:
#   bash Scripts/train_sovereign_gpt.sh
#   bash Scripts/train_sovereign_gpt.sh --epochs 120 --device cuda
#   bash Scripts/train_sovereign_gpt.sh --quick       # 5 epochs for testing
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PY="$ROOT_DIR/.venv/bin/python"
[[ -f "$ROOT_DIR/.venv/Scripts/python.exe" ]] && VENV_PY="$ROOT_DIR/.venv/Scripts/python.exe"

# ── Default training config ────────────────────────────────────────────────────
EPOCHS=60
BATCH_SIZE=4
LR=5e-4
DEVICE="auto"
VOCAB_SIZE=2000
HIDDEN_DIM=128
NUM_LAYERS=4
NUM_HEADS=4

# ── Parse overrides ────────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --epochs=*)    EPOCHS="${arg#*=}" ;;
        --epochs)      shift; EPOCHS="$1" ;;
        --batch-size=*)BATCH_SIZE="${arg#*=}" ;;
        --device=*)    DEVICE="${arg#*=}" ;;
        --quick)       EPOCHS=5; BATCH_SIZE=2; VOCAB_SIZE=500 ;;
    esac
done

info()    { echo -e "\033[1;36m[INFO]\033[0m  $*"; }
success() { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[1;33m[WARN]\033[0m  $*"; }

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Vibhu-Oska AI-OS — Sovereign GPT Training               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Config:"
echo "  ├── Epochs:       $EPOCHS"
echo "  ├── Batch size:   $BATCH_SIZE"
echo "  ├── Learning rate:$LR"
echo "  ├── Device:       $DEVICE"
echo "  ├── Vocab size:   $VOCAB_SIZE"
echo "  ├── Hidden dim:   $HIDDEN_DIM"
echo "  ├── Layers:       $NUM_LAYERS"
echo "  └── Heads:        $NUM_HEADS"
echo ""

# ── Hardware check ─────────────────────────────────────────────────────────────
info "Hardware probe..."
"$VENV_PY" -c "
import torch
if torch.cuda.is_available():
    d = torch.cuda.get_device_properties(0)
    vram = d.total_memory / 1024**3
    print(f'  GPU: {d.name} ({vram:.1f}GB VRAM)')
    if vram < 4:
        print('  WARNING: Low VRAM — using batch_size=1 with gradient accumulation')
else:
    print('  CPU mode — training will be slow')
"

# ── Corpus check ───────────────────────────────────────────────────────────────
CORPUS="$ROOT_DIR/Data/training/sovereign_gpt/corpus.txt"
if [[ ! -f "$CORPUS" ]]; then
    echo ""
    echo "  ERROR: Training corpus not found at:"
    echo "  $CORPUS"
    echo ""
    echo "  Add text data to that file, then re-run."
    exit 1
fi

CORPUS_SIZE=$(wc -w < "$CORPUS")
info "Corpus: $CORPUS_SIZE words"
if [[ "$CORPUS_SIZE" -lt 1000 ]]; then
    warn "Corpus is very small ($CORPUS_SIZE words). Model quality will be poor."
    warn "Recommended minimum: 10,000 words. Ideal: 100,000+ words."
fi

# ── Run training ───────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Starting Sovereign GPT training pipeline..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TRAIN_START=$(date +%s)

"$VENV_PY" -m Models.sovereign_gpt.train \
    --corpus "$CORPUS" \
    --output "$ROOT_DIR/Models/sovereign_gpt/checkpoints" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --lr "$LR" \
    --device "$DEVICE" \
    --vocab-size "$VOCAB_SIZE" \
    --hidden-size "$HIDDEN_DIM" \
    --num-layers "$NUM_LAYERS" \
    --num-heads "$NUM_HEADS"

TRAIN_END=$(date +%s)
ELAPSED=$(( (TRAIN_END - TRAIN_START) / 60 ))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Sovereign GPT training complete in ${ELAPSED} minutes!"
echo "  Checkpoints: Models/sovereign_gpt/checkpoints/"
echo "  Start the gateway to use the newly trained model."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
