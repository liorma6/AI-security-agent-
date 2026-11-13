"""Explicit confusion counts and undefined denominators; phishing is positive."""

import math
from fractions import Fraction

from phishguard.baseline.common import PROTOCOL, BaselineError


def metrics(labels: list[int], scores: list[float], threshold: float) -> dict:
    if (
        len(labels) != len(scores)
        or type(threshold) not in (int, float)
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 1
        or any(type(y) is not int or y not in (0, 1) for y in labels)
        or any(
            type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in scores
        )
    ):
        raise BaselineError("invalid_metric_input")
    tp = fp = tn = fn = 0
    for actual, score in zip(labels, scores, strict=True):
        predicted = score >= threshold
        tp += int(actual == 1 and predicted)
        fp += int(actual == 0 and predicted)
        tn += int(actual == 0 and not predicted)
        fn += int(actual == 1 and not predicted)

    def divide(numerator, denominator):
        return numerator / denominator if denominator else None

    return {
        "rows": len(labels),
        "labels": {"legitimate": tn + fp, "phishing": tp + fn},
        "threshold": threshold,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "accuracy": divide(tp + tn, len(labels)),
        "precision": divide(tp, tp + fp),
        "recall": divide(tp, tp + fn),
        "f1": divide(2 * tp, 2 * tp + fp + fn),
        "false_positive_rate": divide(fp, fp + tn),
    }


def select_threshold(labels: list[int], scores: list[float]) -> tuple[float, list[dict]]:
    if set(labels) != {0, 1}:
        raise BaselineError("validation_requires_both_labels")
    candidates = [
        metrics(labels, scores, threshold) for threshold in PROTOCOL["threshold_candidates"]
    ]

    def ranking(result):
        c = result["confusion"]
        threshold = Fraction(str(result["threshold"]))
        return (
            Fraction(2 * c["tp"], 2 * c["tp"] + c["fp"] + c["fn"]),
            -c["fp"],
            -abs(threshold - Fraction(1, 2)),
            threshold,
        )

    best = max(candidates, key=ranking)
    return best["threshold"], candidates
