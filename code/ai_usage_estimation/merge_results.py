#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd


RESULT_COLUMNS = ["id", "num_sentences", "alpha_estimate"]


def merge_result_files(
    input_dir,
    output_file,
    pattern="*_result.csv",
    expected_files=None,
    expected_rows=None,
):
    """Merge result files only after every integrity check succeeds."""
    input_dir = Path(input_dir)
    result_files = sorted(input_dir.glob(pattern))
    if not result_files:
        raise ValueError(f"No result files match {pattern} in {input_dir}.")
    if expected_files is not None and len(result_files) != expected_files:
        raise ValueError(f"Expected {expected_files} result files, found {len(result_files)}.")

    dataframes = []
    for path in result_files:
        dataframe = pd.read_csv(path)
        if dataframe.columns.tolist() != RESULT_COLUMNS:
            raise ValueError(f"{path.name} must contain the exact columns {RESULT_COLUMNS}.")
        if dataframe.empty:
            raise ValueError(f"{path.name} contains no result rows.")
        dataframes.append(dataframe)

    merged = pd.concat(dataframes, ignore_index=True)
    if expected_rows is not None and len(merged) != expected_rows:
        raise ValueError(f"Expected {expected_rows} merged rows, found {len(merged)}.")
    if merged["id"].isna().any():
        raise ValueError("Merged results contain missing IDs.")
    if merged["num_sentences"].isna().any() or (merged["num_sentences"] < 0).any():
        raise ValueError("Merged results contain invalid num_sentences values.")
    if merged["alpha_estimate"].isna().any():
        raise ValueError("Merged results contain missing alpha_estimate values.")
    if not merged["alpha_estimate"].between(0.0, 1.0).all():
        raise ValueError("Merged results contain alpha_estimate values outside [0, 1].")

    merged = merged.sort_values("id").reset_index(drop=True)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_file, index=False)
    return merged


def parse_args():
    parser = argparse.ArgumentParser(description="Validate and merge MLE chunk results.")
    parser.add_argument("--input_dir", default="../../data/interim/ai_usage/chunk_results")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pattern", default="*_result.csv")
    parser.add_argument("--expected_files", type=int)
    parser.add_argument("--expected_rows", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    merged = merge_result_files(
        args.input_dir,
        args.output,
        args.pattern,
        args.expected_files,
        args.expected_rows,
    )
    print(f"Merged {len(merged)} rows into {args.output}.")


if __name__ == "__main__":
    main()
