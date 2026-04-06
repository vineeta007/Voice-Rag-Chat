#!/usr/bin/env python3
"""
Run benchmark evaluation for Voice RAG and produce run-level metrics.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from requests import RequestException

ABSTAIN_HINTS = [
    "i don't have",
    "i do not have",
    "not available",
    "cannot find",
    "donot have",
    "क्षमा",
    "जानकारी उपलब्ध नहीं",
    "उपलब्ध नहीं",
]

TOKEN_SEPARATORS = "\n\t,.;:!?()[]{}\"'`/\\|@#$%^&*-_=+<>~"


def tokenize(text: str) -> List[str]:
    lower = text.lower()
    for ch in TOKEN_SEPARATORS:
        lower = lower.replace(ch, " ")
    return [t for t in lower.split() if t]


def token_f1(pred: str, gold: str) -> float:
    p_tokens = tokenize(pred)
    g_tokens = tokenize(gold)
    if not p_tokens or not g_tokens:
        return 0.0

    p_counts: Dict[str, int] = {}
    g_counts: Dict[str, int] = {}
    for tok in p_tokens:
        p_counts[tok] = p_counts.get(tok, 0) + 1
    for tok in g_tokens:
        g_counts[tok] = g_counts.get(tok, 0) + 1

    overlap = 0
    for tok, cnt in p_counts.items():
        overlap += min(cnt, g_counts.get(tok, 0))

    if overlap == 0:
        return 0.0

    precision = overlap / len(p_tokens)
    recall = overlap / len(g_tokens)
    return 2 * precision * recall / (precision + recall)


def exact_match(pred: str, gold: str) -> float:
    return 1.0 if pred.strip().lower() == gold.strip().lower() else 0.0


def extract_source_keys(source: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    metadata = source.get("metadata") or {}
    content = source.get("content") or ""

    for meta_key in ("id", "chunk_id", "source_id", "doc_id", "category", "program", "program_title", "type"):
        value = metadata.get(meta_key)
        if value:
            keys.append(str(value).strip().lower())

    if content:
        keys.extend(tokenize(content)[:40])

    return keys


def retrieval_hit_at_k(sources: List[Dict[str, Any]], gold_chunk_ids: List[str], k: int) -> float:
    if not gold_chunk_ids:
        return 1.0

    gold = {g.strip().lower() for g in gold_chunk_ids if g and g.strip()}
    topk = sources[:k]

    source_key_bag = []
    for src in topk:
        source_key_bag.extend(extract_source_keys(src))

    source_set = set(source_key_bag)
    for g in gold:
        if g in source_set:
            return 1.0

    return 0.0


def groundedness_score(answer: str, sources: List[Dict[str, Any]]) -> float:
    answer_tokens = tokenize(answer)
    if not answer_tokens:
        return 0.0

    context_text = " ".join([(s.get("content") or "") for s in sources])
    context_tokens = set(tokenize(context_text))
    if not context_tokens:
        return 0.0

    overlap = sum(1 for tok in answer_tokens if tok in context_tokens)
    return overlap / max(len(answer_tokens), 1)


def is_abstain_answer(answer: str) -> bool:
    a = answer.strip().lower()
    return any(hint in a for hint in ABSTAIN_HINTS)


@dataclass
class BenchRow:
    id: str
    question: str
    language: str
    category: str
    difficulty: str
    gold_answer: str
    gold_chunk_ids: List[str]
    requires_abstain: bool
    pair_id: str


def load_benchmark(path: Path) -> List[BenchRow]:
    rows: List[BenchRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        rows.append(
            BenchRow(
                id=obj["id"],
                question=obj["question"],
                language=obj.get("language", "English"),
                category=obj.get("category", "general"),
                difficulty=obj.get("difficulty", "medium"),
                gold_answer=obj.get("gold_answer", ""),
                gold_chunk_ids=obj.get("gold_chunk_ids", []),
                requires_abstain=bool(obj.get("requires_abstain", False)),
                pair_id=obj.get("pair_id", ""),
            )
        )
    return rows


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(int(round((p / 100.0) * (len(s) - 1))), len(s) - 1)
    return s[idx]


def evaluate(args: argparse.Namespace) -> Tuple[Path, Path]:
    benchmark_rows = load_benchmark(Path(args.benchmark))
    run_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    label = args.label or f"run_{run_ts}"

    runs_dir = Path(args.output_dir)
    reports_dir = Path(args.report_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    run_file = runs_dir / f"{run_ts}_{label}_results.jsonl"
    summary_file = runs_dir / f"{run_ts}_{label}_summary.json"
    markdown_report = reports_dir / f"{run_ts}_{label}_report.md"

    session = requests.Session()
    per_row_results: List[Dict[str, Any]] = []

    for idx, row in enumerate(benchmark_rows, start=1):
        payload = {
            "question": row.question,
            "language": row.language,
            "client_conversation_id": f"eval_{label}_{row.id}",
        }

        started = time.perf_counter()
        try:
            response = session.post(f"{args.base_url.rstrip('/')}/api/query", json=payload, timeout=args.timeout)
            latency_ms = (time.perf_counter() - started) * 1000.0
        except RequestException as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            per_row_results.append(
                {
                    "id": row.id,
                    "pair_id": row.pair_id,
                    "status": "error",
                    "error_type": "request_exception",
                    "error": str(exc),
                    "latency_ms": latency_ms,
                    "language": row.language,
                    "category": row.category,
                }
            )
            print(f"[{idx}/{len(benchmark_rows)}] {row.id} -> request error | {latency_ms:.0f}ms")
            continue

        if response.status_code != 200:
            per_row_results.append(
                {
                    "id": row.id,
                    "pair_id": row.pair_id,
                    "status": "error",
                    "http_status": response.status_code,
                    "latency_ms": latency_ms,
                    "language": row.language,
                    "category": row.category,
                }
            )
            print(f"[{idx}/{len(benchmark_rows)}] {row.id} -> HTTP {response.status_code}")
            continue

        obj = response.json()
        answer = obj.get("answer", "")
        sources = obj.get("sources", [])

        hit1 = retrieval_hit_at_k(sources, row.gold_chunk_ids, 1)
        hit3 = retrieval_hit_at_k(sources, row.gold_chunk_ids, 3)
        hit5 = retrieval_hit_at_k(sources, row.gold_chunk_ids, 5)

        em = exact_match(answer, row.gold_answer)
        f1 = token_f1(answer, row.gold_answer)
        correctness = 1.0 if em == 1.0 else f1

        abstain = is_abstain_answer(answer)
        if row.requires_abstain:
            correctness = 1.0 if abstain else 0.0

        groundedness = groundedness_score(answer, sources)
        hallucination = 0.0
        if not row.requires_abstain:
            hallucination = 1.0 if groundedness < args.groundedness_threshold else 0.0

        result = {
            "id": row.id,
            "pair_id": row.pair_id,
            "status": "ok",
            "question": row.question,
            "language": row.language,
            "category": row.category,
            "difficulty": row.difficulty,
            "requires_abstain": row.requires_abstain,
            "answer": answer,
            "gold_answer": row.gold_answer,
            "latency_ms": latency_ms,
            "retrieval": {
                "hit@1": hit1,
                "hit@3": hit3,
                "hit@5": hit5,
            },
            "correctness": {
                "exact_match": em,
                "token_f1": f1,
                "score": correctness,
            },
            "groundedness": groundedness,
            "hallucination": hallucination,
            "source_count": len(sources),
        }
        per_row_results.append(result)
        print(f"[{idx}/{len(benchmark_rows)}] {row.id} -> ok | hit@3={hit3:.0f} | corr={correctness:.2f} | {latency_ms:.0f}ms")

    run_file.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in per_row_results) + "\n", encoding="utf-8")

    ok_rows = [r for r in per_row_results if r.get("status") == "ok"]
    latencies = [r["latency_ms"] for r in ok_rows]
    hit1_vals = [r["retrieval"]["hit@1"] for r in ok_rows]
    hit3_vals = [r["retrieval"]["hit@3"] for r in ok_rows]
    hit5_vals = [r["retrieval"]["hit@5"] for r in ok_rows]
    corr_vals = [r["correctness"]["score"] for r in ok_rows]
    hall_vals = [r["hallucination"] for r in ok_rows]

    by_lang: Dict[str, Dict[str, float]] = {}
    for lang in ("English", "Hindi"):
        subset = [r for r in ok_rows if r.get("language") == lang]
        if not subset:
            by_lang[lang] = {"count": 0, "correctness": 0.0, "hallucination": 0.0, "latency_ms": 0.0}
            continue
        by_lang[lang] = {
            "count": len(subset),
            "correctness": statistics.mean([x["correctness"]["score"] for x in subset]),
            "hallucination": statistics.mean([x["hallucination"] for x in subset]),
            "latency_ms": statistics.mean([x["latency_ms"] for x in subset]),
        }

    parity = {
        "correctness_gap_abs": abs(by_lang["English"]["correctness"] - by_lang["Hindi"]["correctness"]),
        "hallucination_gap_abs": abs(by_lang["English"]["hallucination"] - by_lang["Hindi"]["hallucination"]),
        "latency_gap_ms_abs": abs(by_lang["English"]["latency_ms"] - by_lang["Hindi"]["latency_ms"]),
    }

    summary = {
        "timestamp": run_ts,
        "label": label,
        "benchmark_file": str(Path(args.benchmark).resolve()),
        "base_url": args.base_url,
        "total_questions": len(benchmark_rows),
        "ok": len(ok_rows),
        "errors": len(per_row_results) - len(ok_rows),
        "metrics": {
            "retrieval_hit@1": statistics.mean(hit1_vals) if hit1_vals else 0.0,
            "retrieval_hit@3": statistics.mean(hit3_vals) if hit3_vals else 0.0,
            "retrieval_hit@5": statistics.mean(hit5_vals) if hit5_vals else 0.0,
            "answer_correctness": statistics.mean(corr_vals) if corr_vals else 0.0,
            "hallucination_rate": statistics.mean(hall_vals) if hall_vals else 0.0,
            "latency_avg_ms": statistics.mean(latencies) if latencies else 0.0,
            "latency_p50_ms": percentile(latencies, 50),
            "latency_p95_ms": percentile(latencies, 95),
        },
        "multilingual": {
            "by_language": by_lang,
            "parity": parity,
        },
        "artifacts": {
            "results_jsonl": str(run_file.resolve()),
            "summary_json": str(summary_file.resolve()),
            "report_md": str(markdown_report.resolve()),
        },
    }

    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    md.append(f"# Evaluation Run: {label}")
    md.append("")
    md.append(f"- Timestamp: {run_ts}")
    md.append(f"- Benchmark: {args.benchmark}")
    md.append(f"- Base URL: {args.base_url}")
    md.append(f"- Total: {summary['total_questions']} | OK: {summary['ok']} | Errors: {summary['errors']}")
    md.append("")
    md.append("## Core Metrics")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|---|---:|")
    for k, v in summary["metrics"].items():
        md.append(f"| {k} | {v:.4f} |")
    md.append("")
    md.append("## Multilingual Parity")
    md.append("")
    md.append("| Language | Count | Correctness | Hallucination | Avg Latency (ms) |")
    md.append("|---|---:|---:|---:|---:|")
    for lang in ("English", "Hindi"):
        row_lang = summary["multilingual"]["by_language"][lang]
        md.append(
            f"| {lang} | {int(row_lang['count'])} | {row_lang['correctness']:.4f} | {row_lang['hallucination']:.4f} | {row_lang['latency_ms']:.2f} |"
        )
    md.append("")
    md.append("## Artifacts")
    md.append("")
    md.append(f"- Results: {run_file}")
    md.append(f"- Summary: {summary_file}")

    markdown_report.write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary_file, markdown_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Voice RAG benchmark")
    parser.add_argument("--benchmark", default="eval/benchmark_sample.jsonl")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--label", default="")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--groundedness-threshold", type=float, default=0.35)
    parser.add_argument("--output-dir", default="eval/runs")
    parser.add_argument("--report-dir", default="eval/reports")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary_path, report_path = evaluate(args)
    print("\n✅ Evaluation complete")
    print(f"Summary: {summary_path}")
    print(f"Report:  {report_path}")
