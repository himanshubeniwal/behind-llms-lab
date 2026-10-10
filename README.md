# Behind the Secrets of LLMs: lab material

Lab material for the course *Behind the Secrets of Large Language Models* at TU Dresden
(ScaDS.AI). There are two parts.

**Website:** <https://himanshubeniwal.github.io/behind-llms-lab/>. It has everything in this
repository in a readable form: an introduction to the clusters, the setup, all exercises with
their code, the notebooks with their outputs, a crash course and a cheat sheet.

**Part 1, the HPC lab** (`hpc_lab/`). You log in to the ZIH clusters, send your first
Slurm jobs, get a GPU, train a tiny GPT and run a real language model. Every exercise is
one folder with a small Python script and the job script that runs it. Start with
[`hpc_lab/README.md`](hpc_lab/README.md).

**Part 2, the crash course** (`notebooks/`). Three notebooks that build a language model
from scratch and then look inside real ones. They run in Google Colab and need no big GPU.

| notebook | what it covers | runtime |
|---|---|---|
| [4 - Tokens and Bigram LM](notebooks/4%20-%20Tokens%20and%20Bigram%20LM.ipynb) | tokenization, a small BPE, a counting language model, cross-entropy and perplexity | CPU |
| [5 - Attention and TinyGPT](notebooks/5%20-%20Attention%20and%20TinyGPT.ipynb) | self-attention from scratch, a Transformer block, training a small GPT | CPU or T4 |
| [6 - Pretrained LLMs for Text Analysis](notebooks/6%20-%20Pretrained%20LLMs%20for%20Text%20Analysis.ipynb) | tokenizers across languages, decoding, perplexity, zero-shot labels, embeddings | CPU or T4 |

They follow the warm-up notebooks 0 to 3b from the first crash course (regression,
arbitrary functions, MNIST, autograd and neurons).

## Quick start

On the cluster (university network or VPN):

```bash
ssh <zih-login>@login1.alpha.hpc.tu-dresden.de
git clone https://github.com/himanshubeniwal/behind-llms-lab.git
cd behind-llms-lab/hpc_lab
```

In Colab: File > Open notebook > GitHub, paste `himanshubeniwal/behind-llms-lab` and pick
a notebook. For notebooks 5 and 6, switch to a T4 GPU under Runtime > Change runtime type.

## Layout

```
hpc_lab/
  00_setup/        workspace, modules and a venv in one script
  01_hello/        your first batch job
  02_cancel/       squeue, scontrol, scancel, sacct
  03_gpu/          ask for a GPU and measure it
  04_tinygpt/      train a tiny GPT as a batch job
  05_sweep/        a learning-rate sweep with a job array
  06_hf_generate/  run a pretrained LLM on a GPU node
notebooks/
  4 - Tokens and Bigram LM.ipynb
  5 - Attention and TinyGPT.ipynb
  6 - Pretrained LLMs for Text Analysis.ipynb
website/           the source of the website
docs/              the built website, served by GitHub Pages
```

## The website

The pages in `docs/` are built from this repository. After you change a script, a notebook
or a page in `website/pages/`, build the site again and commit `docs/`:

```bash
pip install markdown pygments
python website/build.py
```

Every PDF you put into a folder `slides/` gets its own entry on a Slides page.

Questions about the cluster itself: see the [ZIH HPC Compendium](https://compendium.hpc.tu-dresden.de)
or write to hpc-support@tu-dresden.de.
