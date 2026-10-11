#!/bin/bash
# Exercise 2: watch a job, then cancel it
#
#   mkdir -p logs
#   sbatch sleepy.sbatch                 # prints "Submitted batch job <jobid>"
#   squeue --me                          # the ST column goes from PD (pending) to R (running)
#   scontrol show job <jobid>            # everything Slurm knows about the job
#   tail -f logs/sleepy-<jobid>.out      # live log, Ctrl+C stops tail but not the job
#   scancel <jobid>                      # stop it, then look for "received signal" in the log
#   sacct -j <jobid> --format=JobID,JobName,State,Elapsed,ExitCode
#
# Bonus, a job that waits on purpose:
#   sbatch --begin=now+5minutes sleepy.sbatch
#   squeue --me                          # the REASON column says (BeginTime)
#   whypending <jobid>                   # ZIH helper that explains why a job waits
#
#SBATCH --job-name=sleepy
#SBATCH --account=p_lv_llmsecrets
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=500M
#SBATCH --time=00:10:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

# -u turns off output buffering, so tail -f shows every line right away
srun python3 -u sleepy.py --minutes 8 --every 10
