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

### `03_generate_figures.ipynb`

Reads the generated and released files in `../../results/figure_data/` and `../../results/tables/` and renders the main and supplementary figures.
