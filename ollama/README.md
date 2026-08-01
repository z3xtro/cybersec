# Running Buddy on Ollama

Ollama is a **model runner**, not a trainer — so "train Ollama" means one of two
things, and this folder gives you both. Either way, Buddy talks to Ollama through
its OpenAI-compatible endpoint (`http://localhost:11434/v1`), so no app changes
are needed.

> 🎓 For your own authorized CTF practice, competitions, and training labs.

---

## Lane A — Instant specialization (2 minutes, no GPU)

Bake Buddy's CTF persona onto a base model with a Modelfile. This is
prompt-level specialization (no weight training), and it's genuinely useful.

```bash
ollama pull qwen2.5:7b-instruct          # or qwen2.5:3b-instruct (lighter)
ollama create buddy-ctf -f ollama/Modelfile
ollama run buddy-ctf "RSA challenge: n, e=3, c. Give me a hint."
```

## Lane B — Actually fine-tune, then import (needs a GPU)

Real weight training happens with the LoRA pipeline in [`../training/`](../training),
then Ollama serves the result.

```bash
# 1. build the dataset (knowledge base + your writeups) and fine-tune
pip install -r training/requirements-train.txt
python training/build_dataset.py --writeups training/data/writeups
python training/train_lora.py --base Qwen/Qwen2.5-7B-Instruct --merge
#    -> training/out/buddy-ctf-lora-merged/

# 2a. import the merged weights directly (simplest; Qwen2 is supported)
ollama create buddy-ctf -f ollama/Modelfile.trained

# 2b. OR convert to a quantized GGUF first (smaller/faster, more portable)
ollama/export_to_ollama.sh training/out/buddy-ctf-lora-merged buddy-ctf Q4_K_M
```

The dataset quality is what makes the fine-tune worth doing — seed data gets the
pipeline running, but drop your own solved-challenge writeups into
`training/data/writeups/` first (formats in `../training/README.md`).

---

## Point Buddy at your Ollama model (works for Lane A or B)

Ollama exposes an OpenAI-compatible API, which is exactly what Buddy's `local`
provider speaks:

```bash
BUDDY_PROVIDER=local \
BUDDY_LOCAL_URL=http://localhost:11434/v1 \
BUDDY_LOCAL_MODEL=buddy-ctf \
python -m buddy_cat
```

Buddy still applies its **RAG knowledge grounding** and the **Coach ⇄ Solver
toggle** on top of the Ollama model — it sends the mode's system prompt with
every request, so the toggle works regardless of the Modelfile's default SYSTEM.

Switch back to the cloud model anytime by unsetting `BUDDY_PROVIDER`.

---

## Which base model?

| Base | VRAM (Q4) | Notes |
|------|-----------|-------|
| `qwen2.5:3b-instruct` | ~3 GB | Fast; fine for coaching/hints |
| `qwen2.5:7b-instruct` | ~6 GB | Recommended balance |
| `qwen2.5:14b-instruct` | ~10 GB | Strongest, slower |

Any Ollama chat model works; Qwen2.5 is a solid default for tool/CTF reasoning.
For fine-tuning, keep the training base and the Ollama base the same family.

---

## Troubleshooting

- **Buddy shows "local model unreachable"** — start Ollama (`ollama serve`) and
  confirm the model: `ollama list`. Test the endpoint:
  `curl http://localhost:11434/v1/models`.
- **`ollama create` rejects the safetensors import** — your Ollama is older or
  the arch isn't supported for direct import; use `export_to_ollama.sh` (GGUF).
- **Gibberish / no stop** — the GGUF Modelfile needs the right chat template and
  `PARAMETER stop "<|im_end|>"` (already set in the provided Modelfiles).
