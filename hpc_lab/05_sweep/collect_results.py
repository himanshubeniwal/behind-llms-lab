#!/usr/bin/env python3
"""
Exercise 5: print a small table of all runs in a sweep, best one first.
It reads every metrics.json below the folder you give it.

    python collect_results.py $WS_DIR/runs/sweep-1234567
"""
import glob
import json
import os
import sys


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "**", "metrics.json"), recursive=True)):
        with open(path) as f:
            m = json.load(f)
        m["run"] = os.path.basename(os.path.dirname(path))
        rows.append(m)

    if not rows:
        sys.exit(f"no metrics.json found under {root}")

    rows.sort(key=lambda m: m.get("val", float("inf")))
    print(f"{'run':<14}{'lr':>10}{'steps':>8}{'train':>10}{'val':>10}{'secs':>8}  device")
    for m in rows:
        print(f"{m['run']:<14}{m['lr']:>10.0e}{m['step']:>8}{m['train']:>10.4f}{m['val']:>10.4f}"
              f"{m['seconds']:>8.0f}  {m['device']}")
    best = rows[0]
    print(f"\nbest: {best['run']}  (val loss {best['val']:.4f})")


if __name__ == "__main__":
    main()
