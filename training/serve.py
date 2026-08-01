#!/usr/bin/env python3
"""Serve the fine-tuned Buddy model over an OpenAI-compatible API.

Exposes ``POST /v1/chat/completions`` (non-streaming) so Buddy's ``local``
provider — and any OpenAI-compatible client — can talk to it. Loads a base
model plus the LoRA adapter produced by ``train_lora.py``.

    pip install -r training/requirements-train.txt
    python training/serve.py \
        --base Qwen/Qwen2.5-7B-Instruct \
        --adapter training/out/buddy-ctf-lora \
        --host 127.0.0.1 --port 8000

Then run Buddy against it:
    BUDDY_PROVIDER=local BUDDY_LOCAL_MODEL=buddy-ctf python -m buddy_cat

Already have vLLM / Ollama / LM Studio serving an OpenAI endpoint? You don't need
this file — just set BUDDY_LOCAL_URL / BUDDY_LOCAL_MODEL to point at it.
"""

from __future__ import annotations

import argparse
import time
import uuid


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="OpenAI-compatible server for Buddy")
    ap.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--adapter", default="training/out/buddy-ctf-lora",
                    help="LoRA adapter dir; pass '' to serve the base model")
    ap.add_argument("--served-model-name", default="buddy-ctf")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    return ap.parse_args()


def build_app(args: argparse.Namespace):
    import torch
    from fastapi import FastAPI
    from pydantic import BaseModel
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    quant_config = None
    if not args.no_4bit and torch.cuda.is_available():
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    print(f"loading base model: {args.base}")
    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForCausalLM.from_pretrained(
        args.base,
        quantization_config=quant_config,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    if args.adapter:
        from peft import PeftModel
        print(f"attaching adapter: {args.adapter}")
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    app = FastAPI(title="Buddy CTF model")

    class Message(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        model: str | None = None
        messages: list[Message]
        max_tokens: int | None = None
        temperature: float | None = 0.3

    @app.get("/v1/models")
    def list_models() -> dict:
        return {"object": "list", "data": [
            {"id": args.served_model_name, "object": "model", "owned_by": "buddy"}
        ]}

    @app.post("/v1/chat/completions")
    def chat(req: ChatRequest) -> dict:
        prompt = tokenizer.apply_chat_template(
            [m.model_dump() for m in req.messages],
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        max_new = req.max_tokens or args.max_new_tokens
        temperature = req.temperature if req.temperature and req.temperature > 0 else None
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new,
                do_sample=temperature is not None,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
        text = tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        ).strip()
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": args.served_model_name,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
        }

    return app


def main() -> None:
    args = parse_args()
    import uvicorn
    uvicorn.run(build_app(args), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
