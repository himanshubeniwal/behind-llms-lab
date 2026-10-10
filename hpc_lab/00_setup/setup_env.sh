#!/bin/bash
# Behind the Secrets of LLMs, HPC lab
# 00_setup/setup_env.sh: sets up your Python environment once, and switches it on later.
#
# The first time it installs packages, which takes 5 to 10 minutes. Do that inside
# a small interactive job, not on the login node:
#
#     srun --account=p_scads_lv_llm --ntasks=1 --cpus-per-task=4 --mem-per-cpu=2G \
#          --time=00:45:00 --pty bash -l
#     source 00_setup/setup_env.sh
#
# After that, in every new shell and in every batch job, it only takes a second:
#
#     source 00_setup/setup_env.sh
#
# Use "source", not "bash", so that the venv stays active in your shell.
#
# What it does:
#   1. creates (or reuses) a workspace, which is big and fast storage for venv, data and models
#   2. loads a Python module
#   3. creates (or reuses) a venv with PyTorch and transformers inside the workspace
#   4. points the pip, Hugging Face and tmp caches into the workspace instead of $HOME
#   5. downloads the tiny Shakespeare text for exercise 4

# ---- settings you may change ------------------------------------------------
WS_NAME="${WS_NAME:-llm-lab}"     # workspace name
WS_FS="${WS_FS:-horse}"           # file system, horse works on all clusters
WS_DAYS="${WS_DAYS:-30}"          # lifetime in days, extend it later with ws_extend
VENV_NAME="${VENV_NAME:-venv-llm}"

# Python module. If it does not exist on your cluster, look with: module spider Python
PY_MODULES="release/24.10 GCCcore/13.3.0 Python/3.12.3"

# PyTorch built for CUDA 12.x runs with the drivers on Alpha (A100) and Capella (H100).
# A plain "pip install torch" may pick a CUDA 13 build that needs a newer driver.
# If nvidia-smi shows CUDA 13.0 or newer you can use .../whl/cu130 instead.
TORCH_INDEX="https://download.pytorch.org/whl/cu128"
# -----------------------------------------------------------------------------

# 1) workspace. If this shell (or the shell that submitted the job) already has it, reuse it.
if [ -z "$WS_DIR" ] || [ ! -d "$WS_DIR" ]; then
    # ws_allocate prints the path. For a workspace that already exists it just reuses it.
    WS_DIR="$(ws_allocate -F "$WS_FS" "$WS_NAME" "$WS_DAYS" 2>/dev/null)"
fi
if [ -z "$WS_DIR" ] || [ ! -d "$WS_DIR" ]; then
    echo "Could not create the workspace '$WS_NAME' on '$WS_FS'. Check with: ws_list -l" >&2
    return 1 2>/dev/null || exit 1
fi
export WS_DIR
echo "workspace : $WS_DIR"

# 2) modules
module purge > /dev/null 2>&1
if ! module load $PY_MODULES; then
    echo "'module load $PY_MODULES' did not work. Run 'module spider Python' and change PY_MODULES." >&2
    return 1 2>/dev/null || exit 1
fi

# 3) caches go into the workspace, because the $HOME quota is small
export PIP_CACHE_DIR="$WS_DIR/.cache/pip"
export HF_HOME="$WS_DIR/.cache/huggingface"
export TMPDIR="$WS_DIR/tmp"
mkdir -p "$PIP_CACHE_DIR" "$HF_HOME" "$TMPDIR" "$WS_DIR/data" "$WS_DIR/runs"

# 4) venv
if [ ! -f "$WS_DIR/$VENV_NAME/bin/activate" ]; then
    echo "creating the venv $WS_DIR/$VENV_NAME (only the first time, this takes a few minutes)"
    python -m venv "$WS_DIR/$VENV_NAME"
    source "$WS_DIR/$VENV_NAME/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet torch --index-url "$TORCH_INDEX"
    pip install --quiet numpy matplotlib tqdm transformers accelerate ipykernel
    # the same environment as a kernel in JupyterHub
    python -m ipykernel install --user --name "$VENV_NAME" --display-name "LLM Lab ($VENV_NAME)"
else
    source "$WS_DIR/$VENV_NAME/bin/activate"
fi
echo "python    : $(which python) ($(python --version 2>&1))"

# 5) the training text for exercise 4
if [ ! -s "$WS_DIR/data/input.txt" ]; then
    curl -sSL -o "$WS_DIR/data/input.txt" \
        https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt \
        && echo "downloaded tiny Shakespeare to $WS_DIR/data/input.txt"
fi

echo "environment ready"
