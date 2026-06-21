#!/usr/bin/env bash
# ============================================================================
# Vibhu-Oska AI-OS — Router Model Training Script
# Full pipeline: generate data → train → export ONNX
# ============================================================================

set -e  # Exit on any error

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Vibhu-Oska AI-OS — Router Model Training Pipeline       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Move to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Verify environment
echo "→ Python: $(python --version 2>&1)"
echo "→ CUDA: $(python -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only")' 2>/dev/null || echo 'PyTorch not installed')"
echo ""

# Step 1: Generate synthetic dataset
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Generating training dataset..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -m Models.router.dataset_generator
echo ""

# Step 2: Train the router
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Training Router (150M params)..."
echo "Estimated time: 2-4 hours on RTX 4060"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -m Models.router.train \
  --epochs 3 \
  --batch-size 8 \
  --lr 3e-4 \
  --device auto \
  --export-onnx
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[SUCCESS] Router training complete!"
echo "  Checkpoint: Models/router/checkpoints/best_router.pt"
echo "  ONNX:       Models/router/checkpoints/router.onnx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
