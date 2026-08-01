#!/usr/bin/env bash
# Convert a fine-tuned + merged HF model into a GGUF and register it with Ollama.
#
# Prereq: you've merged a LoRA into a full model, e.g.
#   python training/train_lora.py --base Qwen/Qwen2.5-7B-Instruct --merge
#   -> training/out/buddy-ctf-lora-merged/
#
# Usage:
#   ollama/export_to_ollama.sh <merged_model_dir> [ollama_name] [quant]
#   ollama/export_to_ollama.sh training/out/buddy-ctf-lora-merged buddy-ctf Q4_K_M
#
# Requires: git, python3, cmake/make (to build llama.cpp), and `ollama` on PATH.
set -euo pipefail

MERGED="${1:?path to merged HF model dir}"
NAME="${2:-buddy-ctf}"
QUANT="${3:-Q4_K_M}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/ollama/.build"
LLAMA="$WORK/llama.cpp"
mkdir -p "$WORK"

# 1. Fetch + build llama.cpp (for convert + quantize) if we don't have it.
if [ ! -d "$LLAMA" ]; then
  echo ">> cloning llama.cpp"
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LLAMA"
fi
if [ ! -x "$LLAMA/build/bin/llama-quantize" ]; then
  echo ">> building llama.cpp (this can take a few minutes)"
  cmake -S "$LLAMA" -B "$LLAMA/build" >/dev/null
  cmake --build "$LLAMA/build" --target llama-quantize -j >/dev/null
fi
python3 -m pip install --quiet -r "$LLAMA/requirements.txt" || true

# 2. Convert HF -> GGUF (f16), then quantize.
F16="$WORK/${NAME}-f16.gguf"
OUT="$WORK/${NAME}-${QUANT}.gguf"
echo ">> converting to GGUF (f16)"
python3 "$LLAMA/convert_hf_to_gguf.py" "$MERGED" --outfile "$F16" --outtype f16
echo ">> quantizing to $QUANT"
"$LLAMA/build/bin/llama-quantize" "$F16" "$OUT" "$QUANT"

# 3. Write a Modelfile pointing at the GGUF and register it with Ollama.
MF="$WORK/Modelfile.${NAME}"
cat > "$MF" <<EOF
FROM $OUT
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER stop "<|im_end|>"
SYSTEM """You are "Buddy," an elite CTF coach and operator for the user's own authorized challenges. Identify the category and vulnerability; in coach mode guide via the Socratic method without revealing the flag. Concise and terminal-flavored."""
TEMPLATE """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
"""
EOF

echo ">> ollama create $NAME"
ollama create "$NAME" -f "$MF"

cat <<EOF

✓ Registered Ollama model: $NAME
  test:  ollama run $NAME "RSA challenge, n e=3 c — hint?"
  Buddy: BUDDY_PROVIDER=local BUDDY_LOCAL_URL=http://localhost:11434/v1 \\
         BUDDY_LOCAL_MODEL=$NAME python -m buddy_cat
EOF
