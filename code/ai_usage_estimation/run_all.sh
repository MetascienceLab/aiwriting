#!/bin/bash
set -Eeuo pipefail

# End-to-end driver for chunking, parallel processing, and result merging.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
source config.sh

INPUT_FILE="${1:-$INPUT_FILE}"
OUTPUT_FILE="${2:-$OUTPUT_FILE}"
NUM_CHUNKS="${3:-$NUM_CHUNKS}"
export INPUT_FILE OUTPUT_FILE NUM_CHUNKS

reset_directory() {
    local target=$1
    case "$target" in
        ""|"/"|"."|"./")
            echo "Refusing to clear unsafe directory: $target" >&2
            return 1
            ;;
    esac
    rm -rf -- "$target"
    mkdir -p -- "$target"
}

remove_directory() {
    local target=$1
    case "$target" in
        ""|"/"|"."|"./")
            echo "Refusing to remove unsafe directory: $target" >&2
            return 1
            ;;
    esac
    rm -rf -- "$target"
}

[[ -f "$INPUT_FILE" ]] || { echo "Input CSV not found: $INPUT_FILE" >&2; exit 1; }
[[ -f "$WORD_PARQUET_PATH" ]] || { echo "Vocabulary parquet not found: $WORD_PARQUET_PATH" >&2; exit 1; }
[[ "$NUM_CHUNKS" =~ ^[1-9][0-9]*$ ]] || { echo "NUM_CHUNKS must be a positive integer." >&2; exit 1; }

reset_directory "$CHUNKS_DIR"
reset_directory "$RESULTS_DIR"
reset_directory "$LOG_DIR"

echo "Splitting the complete input into up to $NUM_CHUNKS chunks."
"$PYTHON_CMD" split_data.py \
    --input "$INPUT_FILE" \
    --output_dir "$CHUNKS_DIR" \
    --num_chunks "$NUM_CHUNKS"

EXPECTED_ROWS=$("$PYTHON_CMD" -c 'import pandas as pd, sys; print(sum(len(chunk) for chunk in pd.read_csv(sys.argv[1], chunksize=100000, usecols=[0])))' "$INPUT_FILE")
CHUNK_COUNT=$(find "$CHUNKS_DIR" -type f -name 'chunk_*.csv' | wc -l)

echo "Processing $CHUNK_COUNT chunks."
bash run_parallel.sh

merge_args=(
    --input_dir "$RESULTS_DIR"
    --output "$OUTPUT_FILE"
)
if [[ "$VALIDATE_RESULTS" == "true" ]]; then
    merge_args+=(--expected_files "$CHUNK_COUNT" --expected_rows "$EXPECTED_ROWS")
fi
"$PYTHON_CMD" merge_results.py "${merge_args[@]}"

if [[ "$AUTO_CLEANUP" == "true" ]]; then
    remove_directory "$CHUNKS_DIR"
    remove_directory "$RESULTS_DIR"
    remove_directory "$LOG_DIR"
fi

echo "Pipeline completed: $OUTPUT_FILE"
