# Statistical Analysis and Figure Reproduction

Run Jupyter from this directory so all repository-relative paths resolve:

```bash
jupyter lab
```

Execute the notebooks in order:

1. `01_prepare_figure_data.ipynb`
2. `02_regression_analysis.ipynb`
3. `03_generate_figures.ipynb`

## Notebook responsibilities

### `01_prepare_figure_data.ipynb`

Reads the released paper- and author-level files under `../../data/processed/` plus country reference tables under `../../data/reference/`. It generates the plotting inputs for Figure 1, Figure S2, Figure 3, and Figure 4 under `../../results/figure_data/`.

### `02_regression_analysis.ipynb`

Contains:

- the parallel-trends/event-study analysis;
- Difference-in-Differences models with no fixed effects, journal-subfield fixed effects, and journal-subfield plus author fixed effects;
- Difference-in-Difference-in-Differences models for affiliation-country and name-nationality definitions across the reported seniority/productivity indicators;
- author-level OLS models for AI-author status and productivity change.

Regression and contrast outputs are written to `../../results/tables/`; the event-study plotting input is written to `../../results/figure_data/data_figure_s1.csv`.

### `03_generate_figures.ipynb`

Reads the generated and released files in `../../results/figure_data/` and `../../results/tables/` and renders the main and supplementary figures. Figure S10 and Figure S11 rely on the supplied `data_figure_s10.csv` and `data_figure_s11_4sections.csv`; the source package did not contain their upstream generation code.

## Computing requirements

`paper_level_analysis.csv` is approximately 493 MB. Fixed-effect models can use substantially more memory than the input file size, and some specifications drop singleton fixed-effect groups. Run the regression notebook from a fresh kernel, close other memory-intensive applications, and preserve warnings in the execution record. Exact runtime and peak memory depend on hardware and are not represented as laptop-scale guarantees.

The plotting notebook contains stored outputs for visual inspection. Re-execution may create SVG files in the notebook working directory through its existing `savefig` calls; this release does not redirect those files or add a separate figure-output workflow.
