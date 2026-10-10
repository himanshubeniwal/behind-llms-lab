#!/usr/bin/env python3
"""
Exercise 3: did I really get a GPU, and how fast is it?

1. Prints the PyTorch and CUDA versions and the GPUs this job can see.
2. Multiplies two big matrices (the main work inside every LLM layer), first on
   the CPU and then on the GPU, and prints the speed in TFLOP/s.

Needs PyTorch, so run "source 00_setup/setup_env.sh" first.
"""
import argparse
import os
import time

import torch


def bench(device, n, dtype, repeats):
    a = torch.randn(n, n, device=device, dtype=dtype)
    b = torch.randn(n, n, device=device, dtype=dtype)
    _ = a @ b                                   # warm-up (CUDA kernels get loaded lazily)
    if device.type == "cuda":
        torch.cuda.synchronize()                # GPU work is asynchronous: wait for it!
    t0 = time.perf_counter()
    for _ in range(repeats):
        c = a @ b
    if device.type == "cuda":
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / repeats
    flops = 2 * n ** 3                          # n^3 multiply-adds = 2 n^3 floating point ops
    return dt, flops / dt / 1e12


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=4096, help="matrix size n x n")
    p.add_argument("--repeats", type=int, default=10)
    args = p.parse_args()

    print("=" * 60)
    print(f"torch version         : {torch.__version__}")
    print(f"CUDA available        : {torch.cuda.is_available()}")
    print(f"CUDA_VISIBLE_DEVICES  : {os.environ.get('CUDA_VISIBLE_DEVICES', '-')}")
    if torch.cuda.is_available():
        print(f"CUDA (torch build)    : {torch.version.cuda}")
        for i in range(torch.cuda.device_count()):
            prop = torch.cuda.get_device_properties(i)
            print(f"GPU {i}                 : {prop.name}, {prop.total_memory / 2**30:.1f} GiB")
    else:
        print("No GPU found. Did you ask for one with --gres=gpu:1 ?")
    print("=" * 60)

    n_cpu_threads = torch.get_num_threads()
    cpu_n = min(args.n, 2048)                   # keep the CPU run short
    dt, tflops = bench(torch.device("cpu"), cpu_n, torch.float32, max(1, args.repeats // 5))
    print(f"CPU  ({n_cpu_threads:2d} threads) fp32 {cpu_n}x{cpu_n}: {dt * 1e3:8.1f} ms  ->  {tflops:6.2f} TFLOP/s")

    if torch.cuda.is_available():
        gpu = torch.device("cuda")
        for dtype in (torch.float32, torch.bfloat16):
            dt, tflops = bench(gpu, args.n, dtype, args.repeats)
            name = str(dtype).replace("torch.", "")
            print(f"GPU  {name:>8s} {args.n}x{args.n}: {dt * 1e3:8.1f} ms  ->  {tflops:6.2f} TFLOP/s")
        print(f"peak GPU memory used  : {torch.cuda.max_memory_allocated() / 2**20:.0f} MiB")


if __name__ == "__main__":
    main()
