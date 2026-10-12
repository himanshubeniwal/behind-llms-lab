#!/bin/bash
# Exercise 5: a tiny CPU job that prints the sweep results.
# submit_sweep.sh sends it with --dependency=afterok:<array job id>,
# so it only starts after all array tasks have finished without errors.
# It asks for a GPU only because Alpha accepts nothing else.
#
#SBATCH --job-name=lr-collect
#SBATCH --account=p_lv_llmsecrets
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=1G
#SBATCH --gres=gpu:1
#SBATCH --time=00:05:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

# SWEEP_ID comes from submit_sweep.sh (sbatch --export=ALL,SWEEP_ID=...)
python3 collect_results.py "$WS_DIR/runs/sweep-$SWEEP_ID"
