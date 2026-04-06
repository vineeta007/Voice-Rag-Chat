#!/usr/bin/env python3
"""
Compare two benchmark summaries and generate before/after markdown + HTML charts.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


METRIC_KEYS = [
    "retrieval_hit@1",
    "retrieval_hit@3",
    "retrieval_hit@5",
    "answer_correctness",
    "hallucination_rate",
    "latency_avg_ms",
    "latency_p95_ms",
]


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def delta(candidate: float, baseline: float) -> float:
    return candidate - baseline


def format_delta(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.4f}"


def build_markdown(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Benchmark Comparison: {baseline.get('label')} -> {candidate.get('label')}")
    lines.append("")
    lines.append(f"- Baseline summary: {baseline.get('artifacts', {}).get('summary_json', 'N/A')}")
    lines.append(f"- Candidate summary: {candidate.get('artifacts', {}).get('summary_json', 'N/A')}")
    lines.append("")
    lines.append("## Metric Deltas")
    lines.append("")
    lines.append("| Metric | Baseline | Candidate | Delta |")
    lines.append("|---|---:|---:|---:|")

    for key in METRIC_KEYS:
        b = float(baseline["metrics"].get(key, 0.0))
        c = float(candidate["metrics"].get(key, 0.0))
        lines.append(f"| {key} | {b:.4f} | {c:.4f} | {format_delta(delta(c, b))} |")

    lines.append("")
    lines.append("## Multilingual Parity")
    lines.append("")
    lines.append("| Gap Metric | Baseline | Candidate | Delta |")
    lines.append("|---|---:|---:|---:|")

    for key in ("correctness_gap_abs", "hallucination_gap_abs", "latency_gap_ms_abs"):
        b = float(baseline["multilingual"]["parity"].get(key, 0.0))
        c = float(candidate["multilingual"]["parity"].get(key, 0.0))
        lines.append(f"| {key} | {b:.4f} | {c:.4f} | {format_delta(delta(c, b))} |")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Higher is better: retrieval_hit@k, answer_correctness")
    lines.append("- Lower is better: hallucination_rate, latency metrics, parity gaps")
    return "\n".join(lines) + "\n"


def build_html(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    labels = METRIC_KEYS
    baseline_vals = [float(baseline["metrics"].get(k, 0.0)) for k in labels]
    candidate_vals = [float(candidate["metrics"].get(k, 0.0)) for k in labels]

    parity_labels = ["correctness_gap_abs", "hallucination_gap_abs", "latency_gap_ms_abs"]
    parity_baseline = [float(baseline["multilingual"]["parity"].get(k, 0.0)) for k in parity_labels]
    parity_candidate = [float(candidate["multilingual"]["parity"].get(k, 0.0)) for k in parity_labels]

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Benchmark Comparison</title>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f9fc; color: #1f2a44; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ margin-bottom: 24px; color: #41506f; }}
    .card {{ background: white; border: 1px solid #dce3f0; border-radius: 10px; padding: 16px; margin-bottom: 18px; }}
    canvas {{ max-width: 100%; }}
  </style>
</head>
<body>
  <h1>Benchmark Comparison</h1>
  <div class=\"meta\">Baseline: {baseline.get('label')} | Candidate: {candidate.get('label')}</div>

  <div class=\"card\">
    <h3>Core Metrics (Before vs After)</h3>
    <canvas id=\"metricsChart\"></canvas>
  </div>

  <div class=\"card\">
    <h3>Multilingual Parity Gaps (Lower is better)</h3>
    <canvas id=\"parityChart\"></canvas>
  </div>

  <script>
    const labels = {json.dumps(labels)};
    const baselineVals = {json.dumps(baseline_vals)};
    const candidateVals = {json.dumps(candidate_vals)};

    new Chart(document.getElementById('metricsChart'), {{
      type: 'bar',
      data: {{
        labels,
        datasets: [
          {{ label: 'Baseline', data: baselineVals, backgroundColor: 'rgba(90, 123, 161, 0.6)' }},
          {{ label: 'Candidate', data: candidateVals, backgroundColor: 'rgba(71, 173, 132, 0.6)' }}
        ]
      }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});

    const parityLabels = {json.dumps(parity_labels)};
    const parityBaseline = {json.dumps(parity_baseline)};
    const parityCandidate = {json.dumps(parity_candidate)};

    new Chart(document.getElementById('parityChart'), {{
      type: 'bar',
      data: {{
        labels: parityLabels,
        datasets: [
          {{ label: 'Baseline', data: parityBaseline, backgroundColor: 'rgba(228, 103, 74, 0.6)' }},
          {{ label: 'Candidate', data: parityCandidate, backgroundColor: 'rgba(52, 152, 219, 0.6)' }}
        ]
      }},
      options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two benchmark summaries")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output-dir", default="eval/reports")
    args = parser.parse_args()

    baseline = load_json(args.baseline)
    candidate = load_json(args.candidate)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"comparison_{ts}.md"
    html_path = out_dir / f"comparison_{ts}.html"

    md_path.write_text(build_markdown(baseline, candidate), encoding="utf-8")
    html_path.write_text(build_html(baseline, candidate), encoding="utf-8")

    print("✅ Comparison generated")
    print(f"Markdown: {md_path}")
    print(f"HTML:     {html_path}")


if __name__ == "__main__":
    main()
