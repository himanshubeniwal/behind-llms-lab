# HPC lab

This folder is the hands-on part of the lab. Every subfolder is one exercise: a small
Python script and the Slurm job script that runs it.

| folder | what you practise | where |
|---|---|---|
| `00_setup` | workspace, modules, venv, moving caches out of `$HOME` | Alpha or Capella |
| `01_hello` | your first `sbatch`, Slurm variables, why `--cpus-per-task` matters | any cluster |
| `02_cancel` | `squeue`, `scontrol`, `scancel`, `sacct`, and saving on SIGTERM | any cluster |
| `03_gpu` | `--gres=gpu:1`, `nvidia-smi`, CPU vs GPU speed | Alpha or Capella |
| `04_tinygpt` | train a tiny GPT as a batch job and sample from it | Alpha or Capella |
| `05_sweep` | job arrays (`--array`) and dependencies (`--dependency=afterok`) | Alpha or Capella |
| `06_hf_generate` | run a pretrained LLM from Hugging Face on a GPU node | Alpha or Capella |

Our project (account) is **`p_scads_lv_llm`**.

## 1. Log in

You need the university network or the VPN.

```bash
ssh <zih-login>@login1.alpha.hpc.tu-dresden.de      # GPU cluster, 8 A100 per node
ssh <zih-login>@login1.capella.hpc.tu-dresden.de    # GPU cluster, 4 H100 per node
ssh <zih-login>@login1.barnard.hpc.tu-dresden.de    # CPU cluster
```

Every cluster has its own Slurm, so GPU jobs have to be sent from an Alpha or Capella login node.

Then get the lab kit:

```bash
git clone https://github.com/himanshubeniwal/behind-llms-lab.git
cd behind-llms-lab/hpc_lab
```

## 2. Set up Python once (about 10 minutes)

```bash
srun --account=p_scads_lv_llm --ntasks=1 --cpus-per-task=4 --mem-per-cpu=2G \
     --time=00:45:00 --pty bash -l          # a small interactive job
cd ~/behind-llms-lab/hpc_lab
source 00_setup/setup_env.sh                # workspace, venv, training text
exit                                        # give the machine back
```

After that, `source 00_setup/setup_env.sh` only switches the environment on, which takes a second.
The job scripts do this themselves.

## 3. The exercises

```bash
cd 01_hello  && mkdir -p logs && sbatch hello.sbatch
cd ../02_cancel && mkdir -p logs && sbatch sleepy.sbatch     # and then cancel it
cd ../03_gpu    && mkdir -p logs && sbatch gpu.sbatch
cd ../04_tinygpt && mkdir -p logs && sbatch train.sbatch
cd ../05_sweep  && mkdir -p logs && source ../00_setup/setup_env.sh && ./submit_sweep.sh
cd ../06_hf_generate && source ../00_setup/setup_env.sh && python generate.py --download-only
mkdir -p logs && sbatch generate.sbatch
```

## Slurm commands

| what you want | command |
|---|---|
| see partitions and free nodes | `sinfo`, `sinfo -s`, `sinfo -o "%20P %5a %10l %6D %20G"` |
| send a batch job | `sbatch job.sbatch` (options on the command line win over `#SBATCH` lines) |
| a terminal on a compute node | `srun --account=p_scads_lv_llm --ntasks=1 --cpus-per-task=2 --mem-per-cpu=2G --time=00:30:00 --pty bash -l` |
| the same with a GPU | add `--gres=gpu:1` (on Alpha, for quick tests: `--partition=alpha-interactive`) |
| my jobs | `squeue --me`, and the expected start time with `squeue --me --start` |
| why is my job waiting? | `whypending <jobid>` (a ZIH helper) or `scontrol show job <jobid>` |
| cancel | `scancel <jobid>`, one array task: `scancel <jobid>_3`, all of mine: `scancel -u $USER` |
| what did it use? | `sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS,ExitCode` |
| change the time limit | `scontrol update timelimit=00:20:00 jobid=<jobid>` (normally you can only make it shorter) |

Job states: `PD` pending, `R` running, `CG` completing, `CD` completed, `F` failed,
`CA` cancelled, `TO` timeout, `OOM` out of memory.

## Workspaces

| what you want | command |
|---|---|
| create or reuse | `ws_allocate -F horse llm-lab 30` prints `/data/horse/ws/<user>-llm-lab` |
| list | `ws_list` |
| extend | `ws_extend -F horse llm-lab 30` (sets the remaining time to 30 days) |
| delete | `ws_release -F horse --name llm-lab` |
| e-mail reminder | `ws_allocate -F horse -r 7 -m <you>@tu-dresden.de llm-lab 30` |

Keep data, models and caches out of `$HOME`. It is small and backed up, so it fills up fast.

## When something goes wrong

* **The job ends at once and there is no log file.** The `logs/` folder is missing: `mkdir -p logs`.
* **`CUDA available: False`.** You forgot `--gres=gpu:1`, or you sent the job from Barnard.
* **`Disk quota exceeded` in `$HOME`.** The pip or Hugging Face caches are in your home folder. `source 00_setup/setup_env.sh` moves them to the workspace.
* **`module load` fails.** Module versions change about twice a year. Run `module spider Python` and change `PY_MODULES` in `setup_env.sh`.
* **`OUT_OF_MEMORY` in `sacct`.** Ask for more memory with `--mem`.
* **The job waits for a long time.** Ask for less time or fewer GPUs, and check `whypending`.

Documentation: <https://compendium.hpc.tu-dresden.de>. Support: hpc-support@tu-dresden.de
