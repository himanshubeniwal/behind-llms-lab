#!/usr/bin/env python3
"""
Exercise 2: a job that is slow on purpose, so you can practise squeue,
scontrol and scancel.

It prints a line every few seconds. When you cancel the job, Slurm first sends
SIGTERM ("please stop") and only later SIGKILL. We catch SIGTERM and write a
small checkpoint file. A real training script should do the same.

Only uses the standard library, so the system python3 is enough.
"""
import argparse
import json
import os
import signal
import sys
import time

STATE = {"step": 0}


def save_checkpoint(reason):
    path = f"checkpoint-{os.environ.get('SLURM_JOB_ID', 'local')}.json"
    with open(path, "w") as f:
        json.dump({"step": STATE["step"], "reason": reason, "time": time.ctime()}, f)
    print(f"[sleepy] saved {path} at step {STATE['step']} ({reason})", flush=True)


def on_sigterm(signum, frame):
    print(f"[sleepy] received signal {signum} (SIGTERM) -> cleaning up", flush=True)
    save_checkpoint("cancelled")
    sys.exit(0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--minutes", type=float, default=8.0)
    p.add_argument("--every", type=float, default=10.0, help="seconds between heartbeats")
    args = p.parse_args()

    signal.signal(signal.SIGTERM, on_sigterm)
    print(f"[sleepy] pid {os.getpid()} on {os.uname().nodename}, "
          f"running for {args.minutes} min. Cancel me with: scancel {os.environ.get('SLURM_JOB_ID', '<jobid>')}",
          flush=True)

    t_end = time.time() + 60 * args.minutes
    while time.time() < t_end:
        STATE["step"] += 1
        print(f"[sleepy] step {STATE['step']:4d}  {time.strftime('%H:%M:%S')}  still working...", flush=True)
        time.sleep(args.every)

    save_checkpoint("finished")


if __name__ == "__main__":
    main()
