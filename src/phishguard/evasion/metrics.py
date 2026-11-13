"""Paired corruption and budgeted phishing-evasion metrics with explicit denominators."""

from collections import Counter

import numpy as np

from phishguard.baseline.metrics import metrics
from phishguard.evasion.common import PROTOCOL


def divide(a, b):
    return a / b if b else None


def selected(row, model, threshold, operation=None):
    clean = row["clean_scores"][model]
    if row["label"] != "phishing":
        return clean, None
    candidates = [c for c in row["candidates"] if operation is None or c["operation"] == operation]
    best = min(
        [(clean, None)] + [(c["scores"][model], c["variant_id"]) for c in candidates],
        key=lambda item: item[0],
    )
    return best


def asr(rows, model, threshold, operation=None):
    eligible = [
        r for r in rows if r["label"] == "phishing" and r["clean_scores"][model] >= threshold
    ]
    covered = successes = queries = 0
    for row in eligible:
        candidates = [
            c for c in row["candidates"] if operation is None or c["operation"] == operation
        ]
        covered += bool(candidates)
        successes += any(c["scores"][model] < threshold for c in candidates)
        queries += len(candidates)
    return {
        "eligible_clean_detected_phishing": len(eligible),
        "eligible_with_candidates": covered,
        "eligible_without_candidates": len(eligible) - covered,
        "constraint_pass_successes": successes,
        "candidate_asr": divide(successes, len(eligible)),
        "candidate_asr_among_covered": divide(successes, covered),
        "coverage": divide(covered, len(eligible)),
        "candidate_queries_on_eligible": queries,
        "semantic_status": (
            "Automatic constraints only; separate bounded review, not exhaustive validation."
        ),
    }


def asr_interval(rows, model, threshold):
    grouped = {}
    for row in rows:
        eligible = row["label"] == "phishing" and row["clean_scores"][model] >= threshold
        success = eligible and selected(row, model, threshold)[0] < threshold
        value = grouped.setdefault(row["group_id"], [0, 0])
        value[0] += int(eligible)
        value[1] += int(success)
    values = np.array([grouped[g] for g in sorted(grouped)])
    rng = np.random.default_rng(PROTOCOL["bootstrap"]["seed"])
    samples = []
    if len(values) >= 2:
        for _ in range(PROTOCOL["bootstrap"]["repetitions"]):
            eligible, success = values[rng.integers(0, len(values), size=len(values))].sum(axis=0)
            if eligible:
                samples.append(success / eligible)
    return {
        "method": "whole-group percentile bootstrap 95%",
        **PROTOCOL["bootstrap"],
        "groups": len(values),
        "valid_resamples": len(samples),
        "lower": float(np.quantile(samples, 0.025)) if samples else None,
        "upper": float(np.quantile(samples, 0.975)) if samples else None,
        "limitation": "Conditional on groups, corpus, constraints and this finite search budget.",
    }


def summarize(rows, thresholds):
    labels = [int(r["label"] == "phishing") for r in rows]
    models = {}
    for model, threshold in thresholds.items():
        clean = [r["clean_scores"][model] for r in rows]
        fixed = [
            r["candidates"][0]["scores"][model] if r["candidates"] else r["clean_scores"][model]
            for r in rows
        ]
        attacked = [selected(r, model, threshold)[0] for r in rows]
        flips = Counter()
        for label, a, b in zip(labels, clean, fixed, strict=True):
            a_ok, b_ok = (a >= threshold) == bool(label), (b >= threshold) == bool(label)
            flips[
                {
                    (True, True): "both_correct",
                    (False, False): "both_wrong",
                    (True, False): "clean_only_correct",
                    (False, True): "fixed_only_correct",
                }[(a_ok, b_ok)]
            ] += 1
        models[model] = {
            "clean": metrics(labels, clean, threshold),
            "fixed_perturbation": metrics(labels, fixed, threshold),
            "phishing_only_worst_of_budget": metrics(labels, attacked, threshold),
            "fixed_paired_correctness": dict(flips),
            "evasion": asr(rows, model, threshold),
            "evasion_by_operation": {
                op: asr(rows, model, threshold, op) for op in PROTOCOL["operations"]
            },
            "candidate_asr_group_interval": asr_interval(rows, model, threshold),
            "actual_queries": sum(1 + len(r["candidates"]) for r in rows),
            "clean_queries": len(rows),
            "candidate_queries": sum(len(r["candidates"]) for r in rows),
            "maximum_queries_per_original": max(
                (1 + len(r["candidates"]) for r in rows), default=0
            ),
            "per_source": {},
        }
        for source in sorted({r["source_id"] for r in rows}):
            subset = [r for r in rows if r["source_id"] == source]
            models[model]["per_source"][source] = asr(subset, model, threshold)
    common = [
        r
        for r in rows
        if r["label"] == "phishing"
        and all(r["clean_scores"][m] >= t for m, t in thresholds.items())
    ]
    return {
        "rows": len(rows),
        "groups": len({r["group_id"] for r in rows}),
        "originals_with_candidates": sum(bool(r["candidates"]) for r in rows),
        "models": models,
        "common_clean_detected_phishing": {
            "rows": len(common),
            "models": {m: asr(common, m, t) for m, t in thresholds.items()},
        },
    }
