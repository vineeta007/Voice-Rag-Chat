# Evaluation Run: baseline_local

- Timestamp: 20260324_094117
- Benchmark: eval/benchmark_sample.jsonl
- Base URL: http://localhost:8000
- Total: 28 | OK: 28 | Errors: 0

## Core Metrics

| Metric | Value |
|---|---:|
| retrieval_hit@1 | 0.7143 |
| retrieval_hit@3 | 0.7857 |
| retrieval_hit@5 | 0.7857 |
| answer_correctness | 0.1551 |
| hallucination_rate | 0.6429 |
| latency_avg_ms | 2939.8277 |
| latency_p50_ms | 2964.4448 |
| latency_p95_ms | 3902.5654 |

## Multilingual Parity

| Language | Count | Correctness | Hallucination | Avg Latency (ms) |
|---|---:|---:|---:|---:|
| English | 14 | 0.2483 | 0.4286 | 2802.12 |
| Hindi | 14 | 0.0618 | 0.8571 | 3077.53 |

## Artifacts

- Results: eval/runs/20260324_094117_baseline_local_results.jsonl
- Summary: eval/runs/20260324_094117_baseline_local_summary.json
