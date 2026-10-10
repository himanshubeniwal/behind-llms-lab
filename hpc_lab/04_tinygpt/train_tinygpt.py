#!/usr/bin/env python3
"""
Exercise 4: train a tiny character-level GPT as a batch job. It is the same
model as in notebook "5 - Attention and TinyGPT".

    python train_tinygpt.py --data $WS_DIR/data/input.txt --steps 3000 --out $WS_DIR/runs/base

It writes three files into --out:
    ckpt.pt        the weights and the vocabulary (sample.py reads this)
    metrics.json   final train and val loss, run time, settings (used in exercise 5)
    samples.txt    some text written by the trained model

A few cluster habits are built in: it uses the GPU if Slurm gave you one, it
prints with flush=True so the log updates while the job runs, and it saves a
checkpoint when Slurm sends SIGTERM (scancel or time limit).
"""
import argparse
import json
import math
import os
import signal
import time

import torch
import torch.nn as nn
import torch.nn.functional as F


# ----------------------------------------------------------------------------- model
class CausalSelfAttention(nn.Module):
    """softmax(Q K^T / sqrt(d_head) + causal mask) V, for n_head heads in parallel."""

    def __init__(self, n_embd, n_head, block_size, dropout):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head = n_head
        self.qkv = nn.Linear(n_embd, 3 * n_embd, bias=False)  # Q, K, V in one matmul
        self.proj = nn.Linear(n_embd, n_embd)
        self.drop = nn.Dropout(dropout)
        mask = torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size)
        self.register_buffer("mask", mask)

    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=2)
        # (B, T, C) -> (B, n_head, T, head_size)
        q, k, v = (t.view(B, T, self.n_head, C // self.n_head).transpose(1, 2) for t in (q, k, v))
        att = (q @ k.transpose(-2, -1)) / math.sqrt(k.size(-1))       # (B, nh, T, T)
        att = att.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))  # no peeking ahead
        att = self.drop(F.softmax(att, dim=-1))
        y = (att @ v).transpose(1, 2).contiguous().view(B, T, C)     # re-assemble heads
        return self.drop(self.proj(y))


class Block(nn.Module):
    """Transformer block: communicate (attention) then compute (MLP), with residuals."""

    def __init__(self, n_embd, n_head, block_size, dropout):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = CausalSelfAttention(n_embd, n_head, block_size, dropout)
        self.ln2 = nn.LayerNorm(n_embd)
        self.mlp = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd), nn.GELU(), nn.Linear(4 * n_embd, n_embd), nn.Dropout(dropout)
        )

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    def __init__(self, vocab_size, block_size=128, n_layer=4, n_head=4, n_embd=128, dropout=0.1):
        super().__init__()
        self.block_size = block_size
        self.tok_emb = nn.Embedding(vocab_size, n_embd)     # which character?
        self.pos_emb = nn.Embedding(block_size, n_embd)     # at which position?
        self.blocks = nn.Sequential(*[Block(n_embd, n_head, block_size, dropout) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size)        # scores for the next character

    def forward(self, idx, targets=None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        x = self.ln_f(self.blocks(x))
        logits = self.lm_head(x)                            # (B, T, vocab)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=1.0, top_k=None):
        for _ in range(max_new_tokens):
            logits, _ = self(idx[:, -self.block_size:])     # crop to the context window
            logits = logits[:, -1, :] / temperature          # only the last position matters
            if top_k is not None:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            idx = torch.cat([idx, torch.multinomial(probs, num_samples=1)], dim=1)
        return idx


# ----------------------------------------------------------------------------- data
def load_text(path):
    if not os.path.isfile(path):
        raise SystemExit(
            f"Could not find the data file '{path}'.\n"
            "   Download it (login node) with:\n"
            "   curl -sSL -o input.txt https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
        )
    with open(path, encoding="utf-8") as f:
        return f.read()


def get_batch(data, block_size, batch_size, device):
    ix = torch.randint(len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix])
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix])   # the same, shifted by one
    return x.to(device), y.to(device)


@torch.no_grad()
def estimate_loss(model, splits, args, device):
    model.eval()
    out = {}
    for name, data in splits.items():
        losses = torch.zeros(args.eval_iters)
        for k in range(args.eval_iters):
            x, y = get_batch(data, args.block_size, args.batch_size, device)
            losses[k] = model(x, y)[1].item()
        out[name] = losses.mean().item()
    model.train()
    return out


# ----------------------------------------------------------------------------- main
def main():
    default_data = os.path.join(os.environ.get("WS_DIR", "."), "data", "input.txt")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=default_data)
    p.add_argument("--out", default="runs/tinygpt")
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--block-size", type=int, default=128)
    p.add_argument("--n-layer", type=int, default=4)
    p.add_argument("--n-head", type=int, default=4)
    p.add_argument("--n-embd", type=int, default=128)
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--eval-interval", type=int, default=250)
    p.add_argument("--eval-iters", type=int, default=50)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--device", default="auto", help="auto | cpu | cuda")
    args = p.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if (args.device == "auto" and torch.cuda.is_available()) else
                          ("cpu" if args.device == "auto" else args.device))
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True     # free speed-up on A100 / H100
    os.makedirs(args.out, exist_ok=True)

    # --- data: characters -> integers
    text = load_text(args.data)
    chars = sorted(set(text))
    stoi = {ch: i for i, ch in enumerate(chars)}
    data = torch.tensor([stoi[c] for c in text], dtype=torch.long)
    n = int(0.9 * len(data))
    splits = {"train": data[:n], "val": data[n:]}

    # --- model + optimiser
    model = TinyGPT(len(chars), args.block_size, args.n_layer, args.n_head, args.n_embd, args.dropout).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"device={device}  vocab={len(chars)}  chars={len(text):,}  params={n_params / 1e6:.2f}M  "
          f"job={os.environ.get('SLURM_JOB_ID', 'local')}", flush=True)

    # --- save a checkpoint before Slurm kills us
    stop = {"flag": False}

    def on_sigterm(signum, frame):
        print("Got SIGTERM, saving a checkpoint and stopping", flush=True)
        stop["flag"] = True

    signal.signal(signal.SIGTERM, on_sigterm)

    def save(step, losses):
        torch.save({"model": model.state_dict(), "chars": chars, "args": vars(args), "step": step},
                   os.path.join(args.out, "ckpt.pt"))
        with open(os.path.join(args.out, "metrics.json"), "w") as f:
            json.dump({"step": step, **losses, "lr": args.lr, "params": n_params,
                       "seconds": round(time.time() - t0, 1), "device": str(device),
                       "job_id": os.environ.get("SLURM_JOB_ID", "local"),
                       "array_task": os.environ.get("SLURM_ARRAY_TASK_ID", "-")}, f, indent=2)

    # --- training loop: forward, loss, backward, update (the same as in notebook 3b)
    t0 = time.time()
    losses = {"train": float("nan"), "val": float("nan")}
    step = 0
    for step in range(1, args.steps + 1):
        x, y = get_batch(splits["train"], args.block_size, args.batch_size, device)
        _, loss = model(x, y)
        optim.zero_grad(set_to_none=True)
        loss.backward()
        optim.step()

        if step % args.eval_interval == 0 or step == args.steps or stop["flag"]:
            losses = estimate_loss(model, splits, args, device)
            tok_s = step * args.batch_size * args.block_size / (time.time() - t0)
            print(f"step {step:5d} | train {losses['train']:.4f} | val {losses['val']:.4f} | "
                  f"{tok_s / 1e3:7.1f}k tok/s | {time.time() - t0:6.1f}s", flush=True)
            save(step, losses)
        if stop["flag"]:
            break

    # --- show what it learned
    model.eval()
    start = torch.tensor([[stoi.get("\n", 0)]], device=device)
    sample = "".join(chars[i] for i in model.generate(start, 500, temperature=0.8)[0].tolist())
    with open(os.path.join(args.out, "samples.txt"), "w", encoding="utf-8") as f:
        f.write(sample)
    print("-" * 60 + "\n" + sample + "\n" + "-" * 60, flush=True)
    print(f"done: {step} steps in {time.time() - t0:.1f}s -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
