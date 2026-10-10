#!/usr/bin/env python3
"""
Let a trained TinyGPT write some text.

    python sample.py --ckpt $WS_DIR/runs/base/ckpt.pt --prompt "ROMEO:" --temperature 0.8

Nice to try in an interactive session: change --temperature and --top-k and see
what happens.
"""
import argparse

import torch

from train_tinygpt import TinyGPT


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--prompt", default="\n")
    p.add_argument("--tokens", type=int, default=400)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(args.ckpt, map_location=device)
    a, chars = ck["args"], ck["chars"]
    stoi = {c: i for i, c in enumerate(chars)}

    model = TinyGPT(len(chars), a["block_size"], a["n_layer"], a["n_head"], a["n_embd"], 0.0).to(device)
    model.load_state_dict(ck["model"])
    model.eval()

    unknown = sorted(set(args.prompt) - set(chars))
    if unknown:
        print(f"(ignoring characters the model never saw: {unknown})")
    ids = [stoi[c] for c in args.prompt if c in stoi] or [0]
    out = model.generate(torch.tensor([ids], device=device), args.tokens, args.temperature, args.top_k)
    print("".join(chars[i] for i in out[0].tolist()))


if __name__ == "__main__":
    main()
