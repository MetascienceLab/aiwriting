# PMC Data Collection and Text Preprocessing

Run the programs from this directory. Their default paths are relative to this location.

## Supported data source

PMC completed its article-dataset distribution transition in August 2026. The supported bulk source is now the official [PMC Article Datasets on AWS](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/). Legacy FTP baseline/incremental packages and the former OA Web Service are no longer available. Automated retrieval must use a service permitted by PMC, and article-level license terms remain controlling.

`download_pmc_cloud.py` is the acquisition adapter for this repository. It accepts a plain-text manifest containing one identifier per line:

```text
PMC12345678.1
PMC12345679
```

A versioned identifier is deterministic and preferred. For an unversioned PMCID, the script queries the public S3 bucket and proceeds only if exactly one article version is available. If several versions exist, it reports them and requires the intended version to be entered explicitly. This avoids treating a numerically higher version as scientifically preferable when PMC does not make that guarantee.

Run:

```bash
python download_pmc_cloud.py \
  --pmcid_file /path/to/pmc_article_versions.txt \
  --output_directory ../../data/raw/pmc \
  --manifest ../../data/raw/pmc/download_manifest.csv
```

For each article version, the script:

- retrieves the official JSON metadata and JATS XML without requiring an AWS account;
- validates PMCID and version identity;
- verifies the MD5 supplied in the official XML URL when present;
- records SHA-256, license, retraction, version, and retrieval metadata;
- writes consistently named `pmc_cloud_*.tar.gz` batches compatible with the scripts below.

The downloader refuses to overwrite existing `pmc_cloud_*.tar.gz` archives. The generated `download_manifest.csv` is the acquisition audit trail and should be archived with a reproducibility release, subject to any applicable data-sharing constraints.

For corpus-scale acquisition, use the official daily S3 inventory to construct an explicit article-version manifest instead of listing the entire bucket. The source material provided for this repository did not include the original raw archives or exact article-version manifest, so they cannot be reconstructed from repository history.

## Text-processing sequence

After licensed XML archives are present under `../../data/raw/pmc/`, run:

```bash
python collect_pmc_metadata.py
python extract_article_sections.py
python filter_target_sections.py
python tokenize_sentences.py
```

1. `collect_pmc_metadata.py` scans `.tar.gz` archives and writes `../../data/interim/pmc/pmc_metadata.csv` plus a processing report.
2. `extract_article_sections.py` selects articles accepted from 2021 through 2024 by default and writes `../../data/interim/pmc/extracted_article_sections.csv`.
3. `filter_target_sections.py` retains papers containing both introduction and discussion/conclusion text and writes `../../data/interim/pmc/intro_discussion_sections.csv`.
4. `tokenize_sentences.py` tokenizes the retained text and writes `../../data/interim/pmc/intro_discussion_sentences.csv`.

Install dependencies from the repository root and install the spaCy model separately:

```bash
python -m pip install -r ../../requirements.txt
python -m spacy download en_core_web_sm
```

Every program exposes path, year, worker, batching, and logging options as applicable. Inspect them with `python SCRIPT_NAME.py --help`. The default tokenizer worker count is intended for a compute server; reduce `--n_processes` on smaller machines.
