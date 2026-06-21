#!/usr/bin/env bash
# ============================================================================
# Vibhu-Oska AI-OS — Protobuf Compilation Script
# Compiles .proto schemas to Python, TypeScript, and C# bindings.
#
# Prerequisites:
#   pip install grpcio-tools                  (Python generation)
#   npm install -g ts-proto                   (TypeScript generation)
#   dotnet-grpc (optional, for Unity C# bindings)
#
# Usage:
#   bash Scripts/generate_protos.sh
#   bash Scripts/generate_protos.sh --py-only
#   bash Scripts/generate_protos.sh --ts-only
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$ROOT_DIR/Shared/protos"
GEN_DIR="$ROOT_DIR/Shared/generated"
VENV_PY="$ROOT_DIR/.venv/bin/python"
[[ -f "$ROOT_DIR/.venv/Scripts/python.exe" ]] && VENV_PY="$ROOT_DIR/.venv/Scripts/python.exe"

PY_ONLY=false
TS_ONLY=false
for arg in "$@"; do
    case $arg in
        --py-only) PY_ONLY=true ;;
        --ts-only) TS_ONLY=true ;;
    esac
done

info()    { echo -e "\033[1;36m[INFO]\033[0m  $*"; }
success() { echo -e "\033[1;32m[OK]\033[0m    $*"; }
error()   { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ── Create output directories ──────────────────────────────────────────────────
mkdir -p \
    "$GEN_DIR/python" \
    "$GEN_DIR/typescript" \
    "$GEN_DIR/csharp"

# ── Find all .proto files ──────────────────────────────────────────────────────
PROTO_FILES=($(find "$PROTO_DIR" -name "*.proto" -type f))
if [[ ${#PROTO_FILES[@]} -eq 0 ]]; then
    error "No .proto files found in $PROTO_DIR"
fi
info "Found ${#PROTO_FILES[@]} proto files: ${PROTO_FILES[*]##*/}"

# ── Python bindings ────────────────────────────────────────────────────────────
if [[ "$TS_ONLY" == false ]]; then
    info "Generating Python bindings..."
    if "$VENV_PY" -c "import grpc_tools" 2>/dev/null; then
        "$VENV_PY" -m grpc_tools.protoc \
            --proto_path="$PROTO_DIR" \
            --python_out="$GEN_DIR/python" \
            --grpc_python_out="$GEN_DIR/python" \
            "${PROTO_FILES[@]}"
        # Create __init__.py for the generated package
        touch "$GEN_DIR/python/__init__.py"
        success "Python bindings → $GEN_DIR/python/"
    else
        echo "  grpcio-tools not installed — skipping Python generation"
        echo "  Install: pip install grpcio-tools"
    fi
fi

# ── TypeScript bindings ────────────────────────────────────────────────────────
if [[ "$PY_ONLY" == false ]]; then
    info "Generating TypeScript bindings..."
    if command -v protoc &>/dev/null && command -v protoc-gen-ts &>/dev/null; then
        protoc \
            --proto_path="$PROTO_DIR" \
            --plugin="protoc-gen-ts=$(command -v protoc-gen-ts)" \
            --ts_out="$GEN_DIR/typescript" \
            "${PROTO_FILES[@]}"
        success "TypeScript bindings → $GEN_DIR/typescript/"
    else
        echo "  protoc or protoc-gen-ts not found — skipping TypeScript generation"
        echo "  Install: npm install -g ts-proto; apt install protobuf-compiler"
    fi
fi

echo ""
success "Proto compilation complete. Generated outputs in $GEN_DIR"
