"""The conda route: check that the environment works on a GPU node.

Run it with job.sbatch. It tests the GPU, transformers, pandas and evaluate,
and ends with ALL GOOD. The first run downloads a small model (about 250 MB).
"""
import time

import evaluate
import pandas as pd
import torch
import transformers
from transformers import pipeline

# 1. Versions
print(f"torch {torch.__version__} | transformers {transformers.__version__} | "
      f"pandas {pd.__version__} | evaluate {evaluate.__version__}")

# 2. GPU
assert torch.cuda.is_available(), "No GPU visible. Is '#SBATCH --gres=gpu:1' in the job script?"
print("GPU:", torch.cuda.get_device_name(0))
x = torch.randn(4096, 4096, device="cuda")
x @ x  # warm-up
torch.cuda.synchronize()
t = time.time()
x @ x
torch.cuda.synchronize()
print(f"4096x4096 matmul: {(time.time() - t) * 1000:.1f} ms")

# 3. transformers: a small sentiment model on the GPU
clf = pipeline(
    "sentiment-analysis",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
    device=0,
)
texts = [
    "The cluster finally runs my jobs.",
    "Waiting in the queue all day is awful.",
    "This environment setup was painless.",
    "The error messages were confusing.",
]
labels = [1, 0, 1, 0]  # 1 = positive, 0 = negative
preds = clf(texts)

# 4. pandas
df = pd.DataFrame({
    "text": texts,
    "pred": [p["label"] for p in preds],
    "score": [round(p["score"], 3) for p in preds],
})
print(df.to_string(index=False))

# 5. evaluate
accuracy = evaluate.load("accuracy")
pred_ids = [1 if p["label"] == "POSITIVE" else 0 for p in preds]
print("accuracy:", accuracy.compute(predictions=pred_ids, references=labels)["accuracy"])

print("ALL GOOD")
