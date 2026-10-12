#!/bin/bash
# Exercise 1: your first batch job (the work itself runs on the CPU)
#
# Alpha only accepts jobs that ask for a GPU, so this script asks for one even
# though it does not use it. On Barnard (no GPUs), delete the --gres line.
#
# Submit it from a login node:
#   mkdir -p logs && sbatch hello.sbatch
# Check on it:
#   squeue --me
# Read the result:
#   cat logs/hello-hpc-<jobid>.out
#
# Then try other core counts without editing this file:
#   sbatch --cpus-per-task=1 hello.sbatch
#   sbatch --cpus-per-task=6 hello.sbatch   (6 cores per GPU is the most Alpha allows)
#
#SBATCH --job-name=hello-hpc          # the name you see in squeue
#SBATCH --account=p_lv_llmsecrets      # our course project, it pays for the CPU time
#SBATCH --nodes=1                     # one machine (ZIH wants this line in every job)
#SBATCH --ntasks=1                    # one process
#SBATCH --cpus-per-task=4             # with 4 cores
#SBATCH --mem-per-cpu=1G              # memory per core
#SBATCH --gres=gpu:1                  # Alpha takes only GPU jobs; on Barnard delete this line
#SBATCH --time=00:05:00               # hard time limit, hh:mm:ss
#SBATCH --output=logs/%x-%j.out       # %x is the job name, %j the job ID
#SBATCH --error=logs/%x-%j.err        # the logs folder has to exist before you submit

echo "Job $SLURM_JOB_ID started on $(hostname) at $(date)"

# Make sure srun passes all our cores on to the program
# (newer Slurm versions don't do this by themselves).
export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK

# The system python3 is enough for this one.
srun python3 hello_hpc.py --samples 20000000

echo "Job finished at $(date)"
