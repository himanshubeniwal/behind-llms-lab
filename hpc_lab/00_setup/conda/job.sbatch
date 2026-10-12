#!/bin/bash
# The conda route: a job that runs a Python script inside the conda environment.
# Run create_env.sbatch once first. Then, from this folder:
#
#   mkdir -p logs && sbatch job.sbatch
#   cat logs/conda-job-<jobid>.out           # ends with ALL GOOD
#
# For your own code, copy this file and change the last line.
#
#SBATCH --job-name=conda-job
#SBATCH --account=p_lv_llmsecrets
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

WS_NAME=llm-conda

module purge
module load Anaconda3
source $EBROOTANACONDA3/etc/profile.d/conda.sh
conda activate $(ws_find -F horse $WS_NAME)/env
export HF_HOME=$(ws_find -F horse $WS_NAME)/hf-cache   # downloaded models go to the workspace, not $HOME

export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
srun python -u check_env.py
