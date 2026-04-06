#!/usr/bin/env bash
set -euo pipefail

LABEL="${1:-baseline}"
BASE_URL="${2:-http://localhost:8000}"

PYTHON_BIN="python3"
if [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="venv/bin/python"
fi

mkdir -p eval/runs eval/reports

"$PYTHON_BIN" eval/run_benchmark.py \
  --label "$LABEL" \
  --base-url "$BASE_URL" \
  --benchmark eval/benchmark_sample.jsonl

LATEST_SUMMARY=$(ls -1t eval/runs/*"_${LABEL}_summary.json" | head -n 1)

echo "Latest summary: $LATEST_SUMMARY"
