#!/bin/bash
# Exercise 6: let a pretrained language model answer a file of prompts
#
#   source ../00_setup/setup_env.sh
#   python generate.py --download-only        # on the login node, fetches the model once
#   mkdir -p logs && sbatch generate.sbatch
#
# Things to try:
#   Another model:   sbatch generate.sbatch --model gpt2
#   CPU vs GPU:      copy this file, remove the --gres line, ask for more CPUs
#   Languages:       do the German and Hindi prompts get answers in the same language?
#
#SBATCH --job-name=hf-generate
#SBATCH --account=p_lv_llmsecrets
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

source ../00_setup/setup_env.sh
export HF_HUB_OFFLINE=1               # use the downloaded copy, don't wait for the network

export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
srun python -u generate.py --out "outputs-$SLURM_JOB_ID.jsonl" "$@"
