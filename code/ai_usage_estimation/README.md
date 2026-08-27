# Population-Level AI-Usage Estimation

This directory contains the distribution-based maximum-likelihood workflow used to estimate the fraction of AI-assisted writing. It runs article-level estimation in chunks and validates that every input row appears in the merged output.

## Method implemented in `mle.py`

Let `P` denote the reference distribution for human-authored text and `Q` the reference distribution for AI-generated text. For each tokenized sentence, the implementation computes its log probability under both distributions using token-presence and token-absence probabilities. It then estimates the mixture share `alpha` by maximizing

```text
mean_i log((1 - alpha) P(sentence_i) + alpha Q(sentence_i)),
subject to 0 <= alpha <= 1.
```

The optimizer uses bounded L-BFGS-B and reports `alpha_estimate` rounded to six decimal places. `alpha = 0` corresponds to the human reference component and `alpha = 1` to the AI reference component.

The vocabulary table `../../data/reference/biorxiv_token_probabilities.parquet` must contain:

- `Word`
- `logP` and `logQ`
- `log1-P` and `log1-Q`

The source package did not include complete provenance, construction code, or licensing metadata for this probability table. The exact file is included so the released estimates can be rerun, but independent reconstruction of the reference distributions is outside the reproducible boundary of this release.

## Inputs and outputs

Default input:

- `../../data/interim/pmc/intro_discussion_sentences.csv`
- required columns: `id`, `processed_sentences`
- `processed_sentences` must serialize a list of token lists

Reference input:

- `../../data/reference/biorxiv_token_probabilities.parquet`

Merged output:

- `../../data/interim/ai_usage/ai_usage_estimates.csv`
- columns: `id`, `num_sentences`, `alpha_estimate`

## Run the complete estimation stage

Use a Bash-compatible environment and run from this directory:

```bash
bash run_all.sh
```

`config.sh` defines paths, chunk count, parallel jobs, validation, cleanup, and the Python command. Override settings through environment variables, for example:

```bash
MAX_PARALLEL_JOBS=4 NUM_CHUNKS=40 bash run_all.sh
```

The workflow performs these steps:

1. `split_data.py` partitions every CSV row into balanced chunks.
2. `run_parallel.sh` invokes `process_chunk.py` through GNU Parallel or `xargs -P`.
3. `process_chunk.py` parses tokenized sentences and applies `MLE` to each article.
4. `merge_results.py` validates file counts, row counts, IDs, sentence counts, and the `[0, 1]` range before writing the merged output.

Temporary chunks, chunk outputs, and logs are stored under `../../data/interim/ai_usage/` and are excluded from Git. The defaults request 200 chunks and 20 concurrent jobs; reduce these values on machines with limited CPU or memory.
