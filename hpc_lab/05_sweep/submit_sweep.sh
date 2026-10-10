#!/bin/bash
# Exercise 5: send the array job, then a second job that waits for it.
#
#   source ../00_setup/setup_env.sh      # so that $WS_DIR is set
#   mkdir -p logs && ./submit_sweep.sh
set -e
: "${WS_DIR:?run 'source ../00_setup/setup_env.sh' first}"

# --parsable makes sbatch print only the job ID, so we can keep it in a variable
SWEEP_ID=$(sbatch --parsable sweep.sbatch)
echo "sweep (array) job : $SWEEP_ID"

COLLECT_ID=$(sbatch --parsable --dependency=afterok:"$SWEEP_ID" \
                    --export=ALL,SWEEP_ID="$SWEEP_ID" collect.sbatch)
echo "collect job       : $COLLECT_ID (waits for $SWEEP_ID, squeue shows it as Dependency)"
echo
echo "watch with:  squeue --me"
echo "results in:  logs/lr-collect-$COLLECT_ID.out"
