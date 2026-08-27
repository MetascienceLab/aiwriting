#!/bin/bash
set -Eeuo pipefail

# Parallel chunk runner for the AI-usage estimation pipeline.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
source config.sh

[[ -f process_chunk.py ]] || { echo "process_chunk.py not found." >&2; exit 1; }
[[ -f "$WORD_PARQUET_PATH" ]] || { echo "Vocabulary parquet not found: $WORD_PARQUET_PATH" >&2; exit 1; }
[[ -d "$CHUNKS_DIR" ]] || { echo "Chunk directory not found: $CHUNKS_DIR" >&2; exit 1; }
[[ "$MAX_PARALLEL_JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "MAX_PARALLEL_JOBS must be a positive integer." >&2; exit 1; }

mkdir -p -- "$RESULTS_DIR" "$LOG_DIR"
mapfile -d '' chunk_files < <(find "$CHUNKS_DIR" -type f -name 'chunk_*.csv' -print0)
CHUNK_COUNT=${#chunk_files[@]}
(( CHUNK_COUNT > 0 )) || { echo "No chunk files found in $CHUNKS_DIR." >&2; exit 1; }

process_chunk() {
    local chunk_file=$1
    local chunk_basename
    local output_file
    local log_file
    chunk_basename=$(basename "$chunk_file" .csv)
    output_file="$RESULTS_DIR/${chunk_basename}_result.csv"
    log_file="$LOG_DIR/${chunk_basename}.log"

    "$PYTHON_CMD" process_chunk.py \
        --input "$chunk_file" \
        --output "$output_file" \
        --word_parquet "$WORD_PARQUET_PATH" \
        --content_column "$CONTENT_COLUMN" \
        >"$log_file" 2>&1
}

export -f process_chunk
export RESULTS_DIR LOG_DIR WORD_PARQUET_PATH PYTHON_CMD CONTENT_COLUMN

check_system_resources
if command -v parallel >/dev/null 2>&1; then
    printf '%s\0' "${chunk_files[@]}" | parallel -0 -j "$MAX_PARALLEL_JOBS" process_chunk {}
else
    printf '%s\0' "${chunk_files[@]}" | xargs -0 -r -n 1 -P "$MAX_PARALLEL_JOBS" bash -c 'process_chunk "$1"' _
fi

SUCCESS_COUNT=$(find "$RESULTS_DIR" -type f -name '*_result.csv' | wc -l)
if (( SUCCESS_COUNT != CHUNK_COUNT )); then
    echo "Expected $CHUNK_COUNT result files, found $SUCCESS_COUNT." >&2
    exit 1
fi

echo "Processed all $SUCCESS_COUNT chunks successfully."
