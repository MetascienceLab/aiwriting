#!/usr/bin/env python3
import argparse
import ast
import logging
from pathlib import Path

import pandas as pd

from mle import MLE


LOGGER = logging.getLogger(__name__)


def configure_logging(level):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def parse_sentences(value):
    """Parse one serialized list of tokenized sentences."""
    parsed = ast.literal_eval(value) if isinstance(value, str) else value
    if not isinstance(parsed, (list, tuple)):
        raise ValueError("The content column must contain a list of sentences.")
    parsed_list = list(parsed)
    for sentence in parsed_list:
        if not isinstance(sentence, (list, tuple)):
            raise ValueError("Each sentence must be stored as a list of tokens.")
    return parsed_list


def apply_mle_to_chunk(input_file, output_file, word_parquet_path, content_column):
    """Estimate alpha for each article in one chunk CSV."""
    dataframe = pd.read_csv(input_file)
    required = {"id", content_column}
    missing = required.difference(dataframe.columns)
    if missing:
        raise ValueError(f"Input chunk is missing columns: {sorted(missing)}")

    dataframe[content_column] = dataframe[content_column].map(parse_sentences)
    dataframe["num_sentences"] = dataframe[content_column].map(len)
    model = MLE(word_parquet_path)
    estimates = []

    for row_index, sentences in enumerate(dataframe[content_column]):
        try:
            inference_frame = pd.DataFrame({"inference_sentence": sentences})
            estimates.append(model.estimate_from_dataframe(inference_frame, exploded_data=True))
        except Exception as error:
            raise RuntimeError(f"Failed to estimate row {row_index}: {error}") from error

    dataframe["alpha_estimate"] = estimates
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe[["id", "num_sentences", "alpha_estimate"]].to_csv(output_path, index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Apply MLE estimation to one CSV chunk.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--word_parquet", required=True)
    parser.add_argument("--content_column", default="processed_sentences")
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.log_level)
    apply_mle_to_chunk(args.input, args.output, args.word_parquet, args.content_column)
    LOGGER.info("Saved chunk results to %s.", args.output)


if __name__ == "__main__":
    main()
