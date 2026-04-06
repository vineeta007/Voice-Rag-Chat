# Evaluation Run: baseline_local

- Timestamp: 20260324_094010
- Benchmark: eval/benchmark_sample.jsonl
- Base URL: http://localhost:8000
- Total: 28 | OK: 28 | Errors: 0

## Core Metrics

| Metric | Value |
|---|---:|
| retrieval_hit@1 | 0.7143 |
| retrieval_hit@3 | 0.7857 |
| retrieval_hit@5 | 0.7857 |
| answer_correctness | 0.1576 |
| hallucination_rate | 0.6071 |
| latency_avg_ms | 2284.8256 |
| latency_p50_ms | 2646.7492 |
| latency_p95_ms | 3984.4962 |

## Multilingual Parity

| Language | Count | Correctness | Hallucination | Avg Latency (ms) |
|---|---:|---:|---:|---:|
| English | 14 | 0.2508 | 0.3571 | 1772.33 |
| Hindi | 14 | 0.0643 | 0.8571 | 2797.32 |

## Artifacts

- Results: eval/runs/20260324_094010_baseline_local_results.jsonl
- Summary: eval/runs/20260324_094010_baseline_local_summary.json
