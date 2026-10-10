#!/usr/bin/env python3
"""
Exercise 6: run a small pretrained language model from Hugging Face on a GPU node.

    # 1) on the login node: download the model once into $HF_HOME (in your workspace)
    python generate.py --download-only

    # 2) as a GPU job: answer every line of prompts.txt
    sbatch generate.sbatch

The default model is Qwen/Qwen2.5-0.5B-Instruct. It has 0.5 billion parameters,
speaks many languages and needs about 1 GB in bf16. You can also try --model gpt2,
which only knows English and has no chat template.
"""
import argparse
import json
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def build_inputs(tok, prompts):
    """Instruct models expect their chat format; base models just get the raw text."""
    if getattr(tok, "chat_template", None):
        return [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                        add_generation_prompt=True) for p in prompts]
    return prompts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    p.add_argument("--prompts", default="prompts.txt")
    p.add_argument("--out", default="outputs.jsonl")
    p.add_argument("--max-new-tokens", type=int, default=120)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--download-only", action="store_true")
    args = p.parse_args()

    print(f"HF_HOME = {os.environ.get('HF_HOME', '~/.cache/huggingface (careful: $HOME quota!)')}", flush=True)
    if args.download_only:                    # only fetch the files, do not load the model
        from huggingface_hub import snapshot_download
        path = snapshot_download(args.model)
        print(f"downloaded {args.model} to {path}. Now submit the GPU job.")
        return
    tok = AutoTokenizer.from_pretrained(args.model)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype).to(device).eval()
    n_params = sum(p.numel() for p in model.parameters())
    print(f"model {args.model}: {n_params / 1e6:.0f}M params on {device} ({dtype})", flush=True)

    tok.padding_side = "left"                 # decoder-only models: pad on the left for batching
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    with open(args.prompts, encoding="utf-8") as f:
        prompts = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    n_new_total, t0 = 0, time.time()
    with open(args.out, "w", encoding="utf-8") as fout:
        for i in range(0, len(prompts), args.batch_size):
            batch = prompts[i:i + args.batch_size]
            enc = tok(build_inputs(tok, batch), return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=args.max_new_tokens, do_sample=True,
                                     temperature=args.temperature, top_p=args.top_p,
                                     pad_token_id=tok.pad_token_id)
            new_tokens = out[:, enc["input_ids"].shape[1]:]          # drop the prompt part
            for prompt, ids in zip(batch, new_tokens):
                answer = tok.decode(ids, skip_special_tokens=True).strip()
                n_new_total += int((ids != tok.pad_token_id).sum())
                fout.write(json.dumps({"prompt": prompt, "answer": answer}, ensure_ascii=False) + "\n")
                print(f"\n>>> {prompt}\n{answer}", flush=True)

    dt = time.time() - t0
    print(f"\n{len(prompts)} prompts, {n_new_total} new tokens in {dt:.1f}s "
          f"-> {n_new_total / dt:.1f} tokens/s  (written to {args.out})")


if __name__ == "__main__":
    main()
