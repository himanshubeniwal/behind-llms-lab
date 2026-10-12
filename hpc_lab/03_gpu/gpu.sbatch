#!/bin/bash
# Exercise 3: ask for one GPU and see how fast it is
#
# Submit it from a login node of a GPU cluster:
#   ssh <zih-login>@login1.alpha.hpc.tu-dresden.de      (A100)  or
#   ssh <zih-login>@login1.capella.hpc.tu-dresden.de    (H100)
#   cd 03_gpu && mkdir -p logs && sbatch gpu.sbatch
#
# Every cluster has its own Slurm, so a job sent from Barnard never gets a GPU.
#
#SBATCH --job-name=gpu-check
#SBATCH --account=p_lv_llmsecrets
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6             # CPU cores that come with the GPU
#SBATCH --gres=gpu:1                  # this is the line that gets you a GPU
#SBATCH --mem=32G
#SBATCH --time=00:10:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

source ../00_setup/setup_env.sh       # workspace, Python module and venv with PyTorch

echo "---- nvidia-smi ----"
nvidia-smi
echo "--------------------"

export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
srun python gpu_check.py --n 8192 --repeats 20
