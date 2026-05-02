"""
Threshold calibration sweep for skills_find_relevant.

Runs each query in the eval dataset through find_relevant_skills(), then sweeps
over (t_high, t_low) pairs and computes precision, recall, F1, and specificity.

Usage:
    python -m skill_mcp.eval.calibrate
    python -m skill_mcp.eval.calibrate --dataset tests/eval/threshold_calibration.json
    python -m skill_mcp.eval.calibrate --top-k 5 --top 10
    python -m skill_mcp.eval.calibrate --quiet          # one-line best-pair summary only

Exit codes:
    0  Best pair meets precision >= 0.90 AND recall >= 0.85
    1  No pair meets target thresholds
    2  Setup / IO error
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATASET = _REPO_ROOT / "tests" / "eval" / "threshold_calibration.json"

# Sweep ranges
_T_HIGH_CANDIDATES = [0.50, 0.55, 0.60, 0.65, 0.70]
_T_LOW_CANDIDATES  = [0.30, 0.35, 0.40, 0.45]

# Pass/fail targets
_TARGET_PRECISION = 0.90
_TARGET_RECALL    = 0.85


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class EvalTriple:
    query: str
    expected_skill_id: Optional[str]  # None → negative example
    relevance: str                     # "strong" | "none"


@dataclass
class SearchHit:
    skill_id: str
    score: float


@dataclass
class ThresholdResult:
    t_high: float
    t_low: float
    tp: int   # positive query → expected skill found with score >= t_high
    fn: int   # positive query → expected skill not found at t_high
    tn: int   # negative query → top score < t_low
    fp: int   # negative query → top score >= t_low

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def specificity(self) -> float:
        denom = self.tn + self.fp
        return self.tn / denom if denom else 0.0

    def meets_target(self) -> bool:
        return self.precision >= _TARGET_PRECISION and self.recall >= _TARGET_RECALL


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_dataset(path: Path) -> list[EvalTriple]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalTriple(
            query=item["query"],
            expected_skill_id=item.get("expected_skill_id"),
            relevance=item.get("relevance", "none"),
        )
        for item in raw
    ]


def _run_queries(
    triples: list[EvalTriple],
    top_k: int,
    quiet: bool,
) -> dict[str, list[SearchHit]]:
    """Run every unique query and return results keyed by query string."""
    from ..tools.find_skills import find_relevant_skills

    results: dict[str, list[SearchHit]] = {}
    unique = list({t.query for t in triples})

    for i, query in enumerate(unique, 1):
        if not quiet:
            print(f"  [{i:3d}/{len(unique)}] {query[:70]}", end="\r", flush=True)
        raw = find_relevant_skills(query=query, top_k=top_k)
        data = json.loads(raw)
        hits = [
            SearchHit(skill_id=r["skill_id"], score=r.get("score") or 0.0)
            for r in data.get("results", [])
        ]
        results[query] = hits
        time.sleep(0.05)  # polite pause between queries

    if not quiet:
        print(" " * 90, end="\r")  # clear progress line

    return results


def _sweep(
    triples: list[EvalTriple],
    query_results: dict[str, list[SearchHit]],
) -> list[ThresholdResult]:
    rows: list[ThresholdResult] = []
    for t_high in _T_HIGH_CANDIDATES:
        for t_low in _T_LOW_CANDIDATES:
            if t_low >= t_high:
                continue
            tp = fn = tn = fp = 0
            for triple in triples:
                hits = query_results.get(triple.query, [])
                if triple.relevance == "strong" and triple.expected_skill_id:
                    top_expected = next(
                        (h for h in hits if h.skill_id == triple.expected_skill_id), None
                    )
                    if top_expected and top_expected.score >= t_high:
                        tp += 1
                    else:
                        fn += 1
                elif triple.relevance == "none":
                    top_score = hits[0].score if hits else 0.0
                    if top_score < t_low:
                        tn += 1
                    else:
                        fp += 1
            rows.append(ThresholdResult(t_high=t_high, t_low=t_low, tp=tp, fn=fn, tn=tn, fp=fp))

    rows.sort(key=lambda r: (r.f1, r.precision, r.recall), reverse=True)
    return rows


def _print_table(rows: list[ThresholdResult], top: int) -> None:
    header = (
        f"{'t_high':>7}  {'t_low':>6}  "
        f"{'prec':>6}  {'recall':>7}  {'F1':>6}  {'spec':>6}  "
        f"{'TP':>4}  {'FN':>4}  {'TN':>4}  {'FP':>4}  {'OK':>3}"
    )
    print()
    print(header)
    print("─" * len(header))
    for r in rows[:top]:
        ok = "✓" if r.meets_target() else " "
        print(
            f"{r.t_high:7.2f}  {r.t_low:6.2f}  "
            f"{r.precision:6.3f}  {r.recall:7.3f}  {r.f1:6.3f}  {r.specificity:6.3f}  "
            f"{r.tp:4d}  {r.fn:4d}  {r.tn:4d}  {r.fp:4d}  {ok:>3}"
        )
    print()


def _best(rows: list[ThresholdResult]) -> Optional[ThresholdResult]:
    return next((r for r in rows if r.meets_target()), None)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", default=str(_DEFAULT_DATASET), help="Path to eval dataset JSON")
    parser.add_argument("--top-k", type=int, default=5, help="top_k for find_relevant_skills (default 5)")
    parser.add_argument("--top", type=int, default=15, help="Rows to print in table (default 15)")
    parser.add_argument("--quiet", action="store_true", help="Print only best-pair line (CI mode)")
    args = parser.parse_args(argv)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"[calibrate] Dataset not found: {dataset_path}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"[calibrate] Dataset:  {dataset_path}")
        print(f"[calibrate] top_k:    {args.top_k}")
        print(f"[calibrate] Targets:  precision >= {_TARGET_PRECISION:.0%}, recall >= {_TARGET_RECALL:.0%}")
        print()

    try:
        triples = _load_dataset(dataset_path)
    except Exception as exc:
        print(f"[calibrate] Failed to load dataset: {exc}", file=sys.stderr)
        return 2

    pos = sum(1 for t in triples if t.relevance == "strong")
    neg = sum(1 for t in triples if t.relevance == "none")
    if not args.quiet:
        print(f"[calibrate] Loaded {len(triples)} triples: {pos} positive, {neg} negative")
        print(f"[calibrate] Running {len({t.query for t in triples})} unique queries …")

    try:
        query_results = _run_queries(triples, top_k=args.top_k, quiet=args.quiet)
    except Exception as exc:
        print(f"[calibrate] Query execution failed: {exc}", file=sys.stderr)
        return 2

    rows = _sweep(triples, query_results)

    if not args.quiet:
        _print_table(rows, top=args.top)

    best = _best(rows)
    if best:
        print(
            f"[calibrate] BEST  t_high={best.t_high:.2f}  t_low={best.t_low:.2f}  "
            f"precision={best.precision:.3f}  recall={best.recall:.3f}  F1={best.f1:.3f}"
        )
        return 0
    else:
        best_f1 = rows[0] if rows else None
        if best_f1 and not args.quiet:
            print(
                f"[calibrate] WARN  No pair meets targets "
                f"(precision >= {_TARGET_PRECISION:.0%}, recall >= {_TARGET_RECALL:.0%}). "
                f"Best F1={best_f1.f1:.3f} at t_high={best_f1.t_high:.2f}/t_low={best_f1.t_low:.2f}."
            )
        else:
            print("[calibrate] FAIL  No threshold pair meets precision/recall targets.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
