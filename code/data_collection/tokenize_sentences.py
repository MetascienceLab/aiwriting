import argparse
import csv
import logging
import sys
import time
from multiprocessing import Pool

import spacy


LOGGER = logging.getLogger(__name__)
csv.field_size_limit(sys.maxsize)
NLP = None


def configure_logging(level):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def init_worker(model_name):
    """Load the spaCy model once per worker process."""
    global NLP
    NLP = spacy.load(model_name)


def tokenize_sentences(text):
    """Split a document into lowercase alphabetic token lists."""
    global NLP
    doc = NLP(text.replace("\n", " "))
    sentence_list = []
    for sent in doc.sents:
        words_alpha = [token.text.lower() for token in sent if token.is_alpha]
        if words_alpha:
            sentence_list.append(words_alpha)
    return sentence_list


def process_chunk(chunk_data):
    """Tokenize one chunk of CSV rows."""
    processed_chunk = []
    for row_index, row in chunk_data:
        try:
            if len(row) >= 2 and row[1]:
                processed_sentences = tokenize_sentences(row[1])
                processed_chunk.append([row[0], processed_sentences, len(processed_sentences)])
            elif len(row) >= 1:
                processed_chunk.append([row[0], [], 0])
            else:
                processed_chunk.append([row_index, [], 0])
        except Exception as error:  # pragma: no cover - batch jobs should keep going
            LOGGER.warning("Failed to tokenize row %s: %s", row_index, error)
            processed_chunk.append([row[0] if len(row) > 0 else row_index, [], 0])
    return processed_chunk


def read_csv_chunks(filename, chunk_size=100):
    """Yield CSV rows in fixed-size chunks."""
    with open(filename, "r", newline="", encoding="utf-8") as file_handle:
        reader = csv.reader(file_handle)
        header = next(reader)
        if len(header) < 2:
            raise ValueError("Input CSV must contain at least two columns: id and section content.")

        chunk = []
        row_index = 0
        for row in reader:
            chunk.append((row_index, row))
            row_index += 1
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


def process_file_ge_min_sentences(input_file, output_file, chunk_size, min_sentences, n_processes, spacy_model):
    """Tokenize documents and keep only rows with at least the requested sentence count."""
    start_time = time.time()
    with open(output_file, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow(["id", "processed_sentences"])

    total_processed = 0
    total_filtered = 0
    chunk_count = 0

    LOGGER.info(
        "Starting sentence tokenization with %s workers, chunk size %s, and minimum %s sentences.",
        n_processes,
        chunk_size,
        min_sentences,
    )

    with Pool(n_processes, initializer=init_worker, initargs=(spacy_model,)) as pool:
        batch_size = n_processes * 2
        current_batch = []

        for chunk in read_csv_chunks(input_file, chunk_size):
            current_batch.append(chunk)
            if len(current_batch) >= batch_size:
                total_processed, total_filtered = write_processed_batch(
                    pool.map(process_chunk, current_batch),
                    output_file,
                    min_sentences,
                    total_processed,
                    total_filtered,
                )
                chunk_count += len(current_batch)
                LOGGER.info(
                    "Processed %s chunks: kept %s rows and filtered %s rows.",
                    chunk_count,
                    total_processed,
                    total_filtered,
                )
                current_batch = []

        if current_batch:
            total_processed, total_filtered = write_processed_batch(
                pool.map(process_chunk, current_batch),
                output_file,
                min_sentences,
                total_processed,
                total_filtered,
            )
            chunk_count += len(current_batch)

    total_time = time.time() - start_time
    LOGGER.info(
        "Finished sentence tokenization: kept %s rows, filtered %s rows, total runtime %.2fs.",
        total_processed,
        total_filtered,
        total_time,
    )


def write_processed_batch(results, output_file, min_sentences, total_processed, total_filtered):
    """Append filtered sentence lists for one processed batch."""
    with open(output_file, "a", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        for processed_chunk in results:
            for row in processed_chunk:
                sentence_count = row[2] if len(row) >= 3 else len(row[1])
                if sentence_count >= min_sentences:
                    writer.writerow([row[0], row[1]])
                    total_processed += 1
                else:
                    total_filtered += 1
    return total_processed, total_filtered


def parse_args():
    parser = argparse.ArgumentParser(description="Tokenize introduction/discussion text into sentence-level token lists.")
    parser.add_argument("--input_file", default="../../data/interim/pmc/intro_discussion_sections.csv")
    parser.add_argument("--output_file", default="../../data/interim/pmc/intro_discussion_sentences.csv")
    parser.add_argument("--chunk_size", type=int, default=90)
    parser.add_argument("--min_sentences", type=int, default=30)
    parser.add_argument("--n_processes", type=int, default=80)
    parser.add_argument("--spacy_model", default="en_core_web_sm")
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.log_level)
    try:
        process_file_ge_min_sentences(
            input_file=args.input_file,
            output_file=args.output_file,
            chunk_size=args.chunk_size,
            min_sentences=args.min_sentences,
            n_processes=args.n_processes,
            spacy_model=args.spacy_model,
        )
    except OSError as error:
        if args.spacy_model in str(error):
            raise RuntimeError(
                f"spaCy model '{args.spacy_model}' is not available. Install it before running this script."
            ) from error
        raise


if __name__ == "__main__":
    main()
