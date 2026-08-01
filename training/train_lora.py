#!/usr/bin/env python3
"""QLoRA fine-tune of a small open model into Buddy's CTF specialist.

Runs on a single consumer GPU for 7B-class models thanks to 4-bit QLoRA. This
does NOT run in the Buddy app container (no GPU) — run it on your own machine,
Colab, or a cloud GPU, then point Buddy at the result with training/serve.py.

Quickstart:
    pip install -r training/requirements-train.txt
    python training/build_dataset.py
    python training/train_lora.py \
        --base Qwen/Qwen2.5-7B-Instruct \
        --data training/data \
        --out training/out/buddy-ctf-lora

Small/CPU smoke test (tiny model, no 4-bit):
    python training/train_lora.py --base Qwen/Qwen2.5-0.5B-Instruct \
        --no-4bit --epochs 1 --out training/out/smoke
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="QLoRA fine-tune Buddy's CTF model")
    ap.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct",
                    help="base instruct model on the HF hub")
    ap.add_argument("--data", type=Path, default=Path("training/data"),
                    help="dir containing train.jsonl (+ optional val.jsonl)")
    ap.add_argument("--out", type=Path, default=Path("training/out/buddy-ctf-lora"))
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument("--no-4bit", action="store_true",
                    help="disable 4-bit QLoRA (needed on CPU/macOS)")
    ap.add_argument("--merge", action="store_true",
                    help="also save a merged fp16 model (base + adapter)")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    # Imported lazily so `--help` works without the heavy stack installed.
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from trl import SFTConfig, SFTTrainer

    train_file = args.data / "train.jsonl"
    if not train_file.exists():
        raise SystemExit(
            f"{train_file} not found — run: python training/build_dataset.py"
        )

    data_files = {"train": str(train_file)}
    val_file = args.data / "val.jsonl"
    if val_file.exists():
        data_files["validation"] = str(val_file)
    dataset = load_dataset("json", data_files=data_files)

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = None
    if not args.no_4bit and torch.cuda.is_available():
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.base,
        quantization_config=quant_config,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    sft_config = SFTConfig(
        output_dir=str(args.out),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        max_seq_length=args.max_seq_len,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch" if "validation" in data_files else "no",
        bf16=torch.cuda.is_available(),
        gradient_checkpointing=True,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        packing=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        peft_config=peft_config,
        processing_class=tokenizer,
    )

    trainer.train()
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    print(f"\n✓ adapter saved to {args.out}")

    if args.merge:
        merged_dir = args.out.parent / (args.out.name + "-merged")
        merged = trainer.model.merge_and_unload()
        merged.save_pretrained(str(merged_dir))
        tokenizer.save_pretrained(str(merged_dir))
        print(f"✓ merged fp16 model saved to {merged_dir}")

    print("\nnext: serve it →")
    print(f"  python training/serve.py --base {args.base} --adapter {args.out}")
    print("then run Buddy against it:")
    print("  BUDDY_PROVIDER=local python -m buddy_cat")


if __name__ == "__main__":
    main()
