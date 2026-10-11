#!/bin/bash
# Exercise 5: a learning-rate sweep as a job array
#
#   cd 05_sweep && mkdir -p logs && ./submit_sweep.sh     (sends the sweep and the summary job)
#   squeue --me                     # you will see <jobid>_0, <jobid>_1, ...
#   scancel <jobid>_3               # cancel just one task of the array
#
# Slurm starts this script 4 times. The only thing that changes is
# $SLURM_ARRAY_TASK_ID, which goes from 0 to 3.
#
#SBATCH --job-name=lr-sweep
#SBATCH --account=p_lv_llmsecrets
#SBATCH --array=0-3                   # 4 tasks; with 0-3%2 at most 2 run at the same time
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --gres=gpu:1                  # every task gets its own GPU
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=logs/%x-%A_%a.out    # %A is the array job ID, %a the task number
#SBATCH --error=logs/%x-%A_%a.err

LEARNING_RATES=(3e-3 1e-3 3e-4 1e-4)
LR=${LEARNING_RATES[$SLURM_ARRAY_TASK_ID]}
echo "array task $SLURM_ARRAY_TASK_ID of job $SLURM_ARRAY_JOB_ID uses lr=$LR on $(hostname)"

source ../00_setup/setup_env.sh

export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
srun python -u ../04_tinygpt/train_tinygpt.py \
    --data "$WS_DIR/data/input.txt" \
    --out  "$WS_DIR/runs/sweep-$SLURM_ARRAY_JOB_ID/lr-$LR" \
    --steps 2000 \
    --lr "$LR"
