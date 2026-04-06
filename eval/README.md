# Evaluation Framework (Research-Grade)

This module provides an end-to-end benchmark and reporting pipeline for Voice RAG.

## What it measures

- Retrieval quality: `hit@1`, `hit@3`, `hit@5`
- Answer quality: exact match and token-F1 correctness proxy
- Hallucination proxy: groundedness against retrieved evidence
- Latency: average, p50, p95
- Multilingual parity: English/Hindi quality and latency gap by paired questions

## Files

- `benchmark_schema.json`: schema for benchmark entries
- `benchmark_sample.jsonl`: starter benchmark with multilingual pairs
- `run_benchmark.py`: runs benchmark against live backend (`/api/query`)
- `compare_runs.py`: creates before/after comparison report with charts

## Quick start

1. Start backend server.
2. Run baseline:

```bash
python3 eval/run_benchmark.py --label baseline_v1
```

3. Make model/prompt/retrieval changes.
4. Run candidate:

```bash
python3 eval/run_benchmark.py --label candidate_v2
```

5. Compare runs:

```bash
python3 eval/compare_runs.py \
  --baseline eval/runs/<baseline_summary.json> \
  --candidate eval/runs/<candidate_summary.json>
```

The comparison script generates:

- `eval/reports/comparison_<timestamp>.md`
- `eval/reports/comparison_<timestamp>.html`

## Benchmark scaling guidance (must-do)

The included sample is a starter dataset. For faculty review, expand to 200-500 questions.

Checklist:

- Cover all categories: admissions, fees, hostel, faculty, academics, placements, policies.
- Add both English and Hindi for at least 30-40% of questions.
- Keep 10-15% abstain questions (`requires_abstain=true`) for safety testing.
- Add `gold_chunk_ids` that map to your indexed chunk metadata IDs.

## Notes on correctness and hallucination

This framework uses deterministic proxies for repeatability:

- Correctness proxy = token F1 vs `gold_answer`
- Hallucination proxy = answer token grounding against retrieved context

For publication-level rigor, pair this with manual review or LLM-judge labels on a stratified sample.
