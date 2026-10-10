#!/usr/bin/env python3
"""
Exercise 1: where am I running, and what did Slurm give me?

Prints the node name, the Python version and the Slurm variables of the job.
Then it estimates pi with random numbers, split over all the CPU cores the job
got. Run it with --cpus-per-task=1 and with 4, and compare the time.

Only uses the standard library, so the system python3 is enough.
"""
import argparse
import multiprocessing as mp
import os
import platform
import random
import socket
import time


def slurm_info():
    keys = [
        "SLURM_JOB_ID", "SLURM_JOB_NAME", "SLURM_JOB_ACCOUNT", "SLURM_JOB_PARTITION",
        "SLURM_JOB_NODELIST", "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_CPU",
        "SLURM_ARRAY_TASK_ID", "SLURM_SUBMIT_DIR",
    ]
    return {k: os.environ.get(k, "-") for k in keys}


def available_cpus():
    """CPUs this process may use (respects Slurm's CPU binding, unlike os.cpu_count())."""
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:  # macOS / Windows
        return os.cpu_count() or 1


def count_hits(args):
    """Throw n random darts at the unit square; count those inside the quarter circle."""
    n, seed = args
    rng = random.Random(seed)
    hits = 0
    for _ in range(n):
        x, y = rng.random(), rng.random()
        if x * x + y * y <= 1.0:
            hits += 1
    return hits


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=10_000_000, help="total number of darts")
    args = p.parse_args()

    print("=" * 60)
    print(f"Hello from        : {socket.gethostname()}")
    print(f"Python            : {platform.python_version()}  ({platform.python_implementation()})")
    print(f"os.cpu_count()    : {os.cpu_count()}   <- all cores of the node")
    n_cpus = available_cpus()
    print(f"CPUs I may use    : {n_cpus}   <- what Slurm allocated to me")
    print("-" * 60)
    for k, v in slurm_info().items():
        print(f"{k:<20}: {v}")
    print("=" * 60)

    # split the work into one chunk per CPU
    chunk = args.samples // n_cpus
    jobs = [(chunk, seed) for seed in range(n_cpus)]
    t0 = time.perf_counter()
    with mp.Pool(processes=n_cpus) as pool:
        hits = sum(pool.map(count_hits, jobs))
    dt = time.perf_counter() - t0

    pi = 4.0 * hits / (chunk * n_cpus)
    print(f"pi ~ {pi:.6f}   ({chunk * n_cpus:,} samples on {n_cpus} CPU(s) in {dt:.2f} s)")
    print(f"throughput        : {chunk * n_cpus / dt / 1e6:.2f} M samples/s")


if __name__ == "__main__":
    main()
