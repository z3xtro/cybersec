# Training Buddy's CTF Specialist

This directory fine-tunes a small **open** model (Qwen/Llama/Mistral) into a
CTF-specialized model Buddy can call instead of the cloud model. It's the "train a model"
half of Buddy's specialization; the other half — a **RAG knowledge layer** —
works today with zero training (see the repo root README).

> ⚠️ **Runs on a GPU, not in the Buddy app container.** A single 12–16 GB card
> handles a 7B model via 4-bit QLoRA. No GPU? Use the `--no-4bit` CPU smoke path
> with a tiny model, or rent a cloud/Colab GPU.

> 🎓 **Scope:** for your own authorized CTF practice, competitions, and training
> labs. The solver style is meant for challenges you're permitted to solve.

## Pipeline

```
buddy_cat/knowledge/*.md ─┐
your writeups ────────────┼─▶ build_dataset.py ─▶ data/*.jsonl
                          │
                          └─▶ train_lora.py ─▶ out/buddy-ctf-lora (adapter)
                                                    │
                                          serve.py ─┴─▶ OpenAI endpoint :8000
                                                            │
                                    BUDDY_PROVIDER=local  ──┘  (Buddy calls it)
```

## 1. Install (on the GPU box)

```bash
pip install -r training/requirements-train.txt
```

## 2. Build the dataset

```bash
python training/build_dataset.py
```

This synthesizes **seed** examples (both coach and solver styles) from the
knowledge base so the pipeline runs end-to-end immediately. The seed set gets
you a working model, but the **real quality comes from your own writeups** —
add them and rebuild:

```bash
python training/build_dataset.py --writeups training/data/writeups
```

### Writeup formats (`training/data/writeups/`)

- **`*.jsonl`** — one record per line, either:
  - chat format: `{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}`
  - or simple: `{"mode": "solver", "instruction": "...", "input": "...", "output": "..."}`
    (`mode` is `coach` or `solver`)
- **`*.md` / `*.txt`** — a writeup; first line becomes the task, the body the
  answer (treated as a solver example).

Aim for a few hundred+ high-quality examples across categories for a model that
meaningfully beats prompting alone.

## 3. Fine-tune

```bash
# 7B QLoRA on a single GPU
python training/train_lora.py \
    --base Qwen/Qwen2.5-7B-Instruct \
    --data training/data \
    --out training/out/buddy-ctf-lora

# CPU/quick smoke test
python training/train_lora.py --base Qwen/Qwen2.5-0.5B-Instruct \
    --no-4bit --epochs 1 --out training/out/smoke
```

Add `--merge` to also export a merged fp16 model for engines that want full
weights (vLLM, llama.cpp conversion, etc.).

## 4. Serve it

```bash
python training/serve.py \
    --base Qwen/Qwen2.5-7B-Instruct \
    --adapter training/out/buddy-ctf-lora \
    --host 127.0.0.1 --port 8000
```

This exposes `POST /v1/chat/completions`. Already running **vLLM / Ollama /
LM Studio**? Skip `serve.py` and point Buddy at that endpoint instead.

## 5. Point Buddy at your model

```bash
BUDDY_PROVIDER=local \
BUDDY_LOCAL_URL=http://127.0.0.1:8000/v1 \
BUDDY_LOCAL_MODEL=buddy-ctf \
python -m buddy_cat
```

Buddy now runs on your fine-tuned model, still with the RAG knowledge layer and
the coach/solver toggle. Switch back anytime by unsetting `BUDDY_PROVIDER`.

## Run it on Ollama instead

Prefer Ollama? After `--merge`, import the trained weights straight into Ollama
(or skip training entirely with an instant Modelfile persona). See
[`../ollama/README.md`](../ollama/README.md):

```bash
python training/train_lora.py --base Qwen/Qwen2.5-7B-Instruct --merge
ollama create buddy-ctf -f ollama/Modelfile.trained
```

## Notes

- `out/` and `data/` are git-ignored (adapters and datasets can be large).
- The system prompts in `build_dataset.py` mirror `buddy_cat/config.py` so the
  fine-tune matches how Buddy prompts at inference.
- Start from a base model whose license fits your use.
