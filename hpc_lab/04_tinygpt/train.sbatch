#!/bin/bash
# Exercise 4: train a tiny GPT on one GPU
#
#   cd 04_tinygpt && mkdir -p logs && sbatch train.sbatch
#   tail -f logs/tinygpt-<jobid>.out          # watch the loss go down
#
# Afterwards:
#   python sample.py --ckpt $WS_DIR/runs/tinygpt-<jobid>/ckpt.pt --prompt "ROMEO:"
#
# Things to try:
#   A bigger model. Everything after the script name is passed on to Python:
#     sbatch train.sbatch --n-layer 6 --n-embd 384
#   A job that runs out of time. Is ckpt.pt still saved?
#     sbatch --time=00:02:00 train.sbatch
#
#SBATCH --job-name=tinygpt
#SBATCH --account=p_lv_llmsecrets
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --signal=TERM@60              # send SIGTERM 60 s before the time limit, so we can save
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

source ../00_setup/setup_env.sh

export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
srun python -u train_tinygpt.py \
    --data "$WS_DIR/data/input.txt" \
    --out  "$WS_DIR/runs/tinygpt-$SLURM_JOB_ID" \
    --steps 5000 \
    "$@"
