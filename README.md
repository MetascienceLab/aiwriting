# AI-Assisted Writing Is Growing Fastest Among Non-English-Speaking and Less Established Scientists

Jialin Liu, Yongyuan He, Zhihan Zheng, Yi Bu, and Chaoqun Ni

This repository provides the released code and data for the paper **“AI-Assisted Writing Is Growing Fastest Among Non-English-Speaking and Less Established Scientists.”** It contains code for PMC full-text acquisition and preprocessing, population-level distribution-based estimation of AI-assisted writing, DiD/DDD and author-level statistical analyses, and reproduction of the paper figures.

Last updated: August 26, 2026.

## Reproducibility scope

Two reproducibility routes are supported:

1. **Analysis and figure reproduction from released processed data.** This is the practical route for reproducing the statistical tables and figures. The three analysis datasets are downloaded with Git LFS and are consumed directly by the notebooks in `code/data_analysis/`.
2. **PMC text-processing and AI-usage estimation.** The scripts in `code/data_collection/` and `code/ai_usage_estimation/` reproduce these computational stages from appropriately licensed PMC XML.

## Repository structure

```text
code/
  data_collection/       PMC acquisition, XML extraction, section filtering, tokenization
  ai_usage_estimation/   Distribution-based maximum-likelihood estimation
  data_analysis/         Figure-data preparation, DiD/DDD/OLS analyses, figure generation
data/
  reference/             Estimator and country reference tables
  processed/             Released paper- and author-level analysis datasets (Git LFS)
results/
  tables/                Released regression outputs
  figure_data/           Released plotting inputs
```

## System requirements

- Python 3.12 (recorded in `.python-version`)
- Git and [Git LFS](https://git-lfs.com/)
- JupyterLab or Jupyter Notebook
- Bash for the parallel AI-usage estimation driver; Windows users can use WSL

The prepared analysis datasets occupy approximately 525 MB after Git LFS checkout. The full PMC workflow is a corpus-scale job and requires substantially more storage, memory, CPU time, and wall-clock time than the analysis-only route. The fixed-effect regressions may also require substantial memory. The repository therefore does not claim that the full workflow can be run on a standard laptop.

## Installation and Git LFS

Install Git LFS before cloning, then retrieve the data objects explicitly:

```bash
git lfs install
git clone --branch master https://github.com/MetascienceLab/aiwriting.git
cd aiwriting
git lfs pull
git lfs ls-files
```

`git lfs ls-files` should list the three files under `data/processed/`. If a processed CSV opens with `version https://git-lfs.github.com/spec/v1`, it is still an LFS pointer; rerun `git lfs pull` from the repository root.

Create a Python environment and install the pinned dependencies:

```bash
python -m venv .venv
```

On Linux or macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Route A: reproduce the analyses and figures

Start JupyterLab from `code/data_analysis/` so the documented relative paths resolve, then run the notebooks in order:

```bash
cd code/data_analysis
jupyter lab
```

1. `01_prepare_figure_data.ipynb`
2. `02_regression_analysis.ipynb`
3. `03_generate_figures.ipynb`

The regression notebook contains the parallel-trends analysis, Difference-in-Differences (DiD), Difference-in-Difference-in-Differences (DDD), and author-level OLS models. Generated tables are written to `results/tables/`; plotting inputs are written to `results/figure_data/`. 

## Route B: PMC text processing and AI-usage estimation

### 1. Acquire licensed PMC XML

PMC completed a dataset-distribution transition in August 2026. Legacy bulk FTP/OA-package URLs and the former OA Web Service must not be used. The supported source for corpus-scale retrieval is the official [PMC Article Datasets on AWS](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/); no AWS account is required.

From `code/data_collection/`, run:

```bash
python download_pmc_cloud.py \
  --pmcid_file /path/to/pmc_article_versions.txt \
  --output_directory ../../data/raw/pmc \
  --manifest ../../data/raw/pmc/download_manifest.csv
```

The downloader retrieves the official JATS XML and JSON metadata, verifies the NLM-provided MD5 when present, records a SHA-256 digest and license metadata, and packages the files into `pmc_cloud_*.tar.gz`. These archives are compatible with the remaining collection scripts. Users are responsible for respecting the article-level license recorded by PMC. The original raw archives and exact article-version list were not included in the source package used to prepare this release.

For very large retrievals, use the official daily S3 inventory documented by PMC rather than enumerating the bucket. See `code/data_collection/README.md` for the acquisition contract.

### 2. Extract and preprocess text

Run from `code/data_collection/`:

```bash
python collect_pmc_metadata.py
python extract_article_sections.py
python filter_target_sections.py
python tokenize_sentences.py
```

Default outputs are written under `data/interim/pmc/`. The extraction stage selects articles with accepted dates from 2021 through 2024; all scripts expose command-line overrides through `--help`.

### 3. Estimate the population-level AI-assisted-writing fraction

Run from a Bash-compatible shell in `code/ai_usage_estimation/`:

```bash
bash run_all.sh
```

The driver splits the tokenized corpus, runs the maximum-likelihood estimator in parallel, validates and merges every chunk, and writes `data/interim/ai_usage/ai_usage_estimates.csv`. Configuration is controlled by `config.sh` or environment variables. Method details and the exact input schema are documented in `code/ai_usage_estimation/README.md`.

## Data and provenance

- `data/reference/biorxiv_token_probabilities.parquet`: token-probability table required by the estimator.
- `data/reference/country_epi.tsv`: country-level English Proficiency Index table used in figure-data preparation.
- `data/reference/country_language_type.tsv`: country language-family classification used in figure-data preparation.
- `data/processed/paper_level_analysis.csv`: paper-level analysis input.
- `data/processed/first_author_analysis.csv`: first-author analysis input.
- `data/processed/last_author_analysis.csv`: corresponding/last-author analysis input.

The original material package did not include complete source, version, or license metadata for the three reference tables. They are preserved without alteration, and this limitation is recorded in `data/README.md`.

## License

Repository code is released under the MIT License; see `LICENSE`. Third-party data and PMC articles remain subject to their own source and article-level licenses.

## Citation

```bibtex
@article{liu2025ai,
  title={AI-assisted writing is growing fastest among non-english-speaking and less established scientists},
  author={Liu, Jialin and He, Yongyuan and Zheng, Zhihan and Bu, Yi and Ni, Chaoqun},
  journal={arXiv preprint arXiv:2511.15872},
  year={2025}
}
```
