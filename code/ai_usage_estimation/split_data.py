import argparse
from pathlib import Path

import pandas as pd


def _read_balanced_chunks(input_path, chunk_sizes):
    reader = pd.read_csv(input_path, chunksize=100_000)
    source = iter(reader)
    buffer = None
    try:
        for chunk_size in chunk_sizes:
            pieces = []
            remaining = chunk_size
            while remaining:
                if buffer is None or buffer.empty:
                    buffer = next(source)
                take = min(remaining, len(buffer))
                pieces.append(buffer.iloc[:take])
                buffer = buffer.iloc[take:]
                remaining -= take
            yield pd.concat(pieces, ignore_index=True)
    finally:
        reader.close()


def split_csv(input_path, output_dir, num_chunks=None, rows_per_chunk=None):
    """Split every input row using exactly one chunking strategy."""
    if (num_chunks is None) == (rows_per_chunk is None):
        raise ValueError("Provide exactly one of num_chunks or rows_per_chunk.")
    if num_chunks is not None and num_chunks <= 0:
        raise ValueError("num_chunks must be positive.")
    if rows_per_chunk is not None and rows_per_chunk <= 0:
        raise ValueError("rows_per_chunk must be positive.")

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_rows = sum(len(chunk) for chunk in pd.read_csv(input_path, chunksize=100_000, usecols=[0]))
    if total_rows == 0:
        raise ValueError("The input CSV contains no data rows.")

    if num_chunks is not None:
        actual_chunks = min(num_chunks, total_rows)
        base_size, remainder = divmod(total_rows, actual_chunks)
        chunk_sizes = [base_size + (index < remainder) for index in range(actual_chunks)]
        chunks = _read_balanced_chunks(input_path, chunk_sizes)
    else:
        chunks = pd.read_csv(input_path, chunksize=rows_per_chunk)

    paths = []
    for index, chunk in enumerate(chunks):
        output_path = output_dir / f"chunk_{index:03d}.csv"
        chunk.to_csv(output_path, index=False)
        paths.append(output_path)
    return paths


def parse_args():
    parser = argparse.ArgumentParser(description="Split a complete CSV into processing chunks.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output_dir", required=True)
    strategy = parser.add_mutually_exclusive_group(required=True)
    strategy.add_argument("--num_chunks", type=int)
    strategy.add_argument("--rows_per_chunk", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    paths = split_csv(args.input, args.output_dir, args.num_chunks, args.rows_per_chunk)
    print(f"Created {len(paths)} chunks in {args.output_dir}.")


if __name__ == "__main__":
    main()
