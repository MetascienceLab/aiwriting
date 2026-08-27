#!/bin/bash

# Default runtime configuration for the AI-usage estimation pipeline.
export INPUT_FILE="${INPUT_FILE:-../../data/interim/pmc/intro_discussion_sentences.csv}"
export OUTPUT_FILE="${OUTPUT_FILE:-../../data/interim/ai_usage/ai_usage_estimates.csv}"
export WORD_PARQUET_PATH="${WORD_PARQUET_PATH:-../../data/reference/biorxiv_token_probabilities.parquet}"
export CONTENT_COLUMN="${CONTENT_COLUMN:-processed_sentences}"

export NUM_CHUNKS="${NUM_CHUNKS:-200}"
export MAX_PARALLEL_JOBS="${MAX_PARALLEL_JOBS:-20}"

export CHUNKS_DIR="${CHUNKS_DIR:-../../data/interim/ai_usage/chunks}"
export RESULTS_DIR="${RESULTS_DIR:-../../data/interim/ai_usage/chunk_results}"
export LOG_DIR="${LOG_DIR:-../../data/interim/ai_usage/logs}"

export AUTO_CLEANUP="${AUTO_CLEANUP:-false}"
export VALIDATE_RESULTS="${VALIDATE_RESULTS:-true}"
export PYTHON_CMD="${PYTHON_CMD:-python3}"

check_system_resources() {
    echo "CPU cores: $(nproc 2>/dev/null || echo unknown)"
    echo "Available disk space: $(df -h . | tail -1 | awk '{print $4}')"
    echo "Parallel jobs: $MAX_PARALLEL_JOBS"
    echo "Requested chunks: $NUM_CHUNKS"
}

export -f check_system_resources
