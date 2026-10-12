#!/bin/bash
# The conda route, an alternative to setup_env.sh for people who prefer conda.
# Builds a conda environment with PyTorch, transformers, pandas and evaluate in its
# own workspace. Run it once, from this folder, on an Alpha login node:
#
#   cd ~/behind-llms-lab/hpc_lab/00_setup/conda
#   mkdir -p logs && sbatch create_env.sbatch
#   cat logs/create-env-<jobid>.out          # the last line should say OK
#
# Running it again builds the environment from scratch.
#
# ZIH recommends the venv from setup_env.sh. Anaconda's licence now covers universities
# of TU Dresden's size and TU Dresden has no central licence, so this script installs
# only from conda-forge. If in doubt, use the venv.
#
#SBATCH --job-name=create-env
#SBATCH --account=p_lv_llmsecrets
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --gres=gpu:1                  # Alpha takes only GPU jobs, and the last line tests CUDA
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

WS_NAME=llm-conda

module purge
module load Anaconda3                                 # if this fails: module spider Anaconda3
source $EBROOTANACONDA3/etc/profile.d/conda.sh        # ZIH asks for this instead of "conda init"

# The environment lives in its own workspace, not in the small $HOME
ws_allocate -F horse $WS_NAME 30 > /dev/null
ENV=$(ws_find -F horse $WS_NAME)/env

conda create -y --prefix $ENV --override-channels -c conda-forge python=3.11 pip
conda activate $ENV

# pip on ZIH systems refuses to run outside a venv, and a conda env does not count as one
export PIP_REQUIRE_VIRTUALENV=false
# PyTorch for CUDA 12.x fits the drivers on Alpha and Capella (see setup_env.sh)
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu128
pip install --no-cache-dir transformers pandas evaluate

python -c "import torch, transformers, pandas, evaluate; print('OK | CUDA:', torch.cuda.is_available())"
