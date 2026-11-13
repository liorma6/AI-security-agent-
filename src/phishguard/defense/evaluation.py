"""Fixed-bank transfer and fresh equal-budget searches after artifact selection."""

import time
from collections import defaultdict

from phishguard.baseline.common import read_bytes
from phishguard.baseline.metrics import metrics
from phishguard.baseline.model import text_hash
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.defense.common import PROTOCOL, DefenseError, identity
from phishguard.defense.data import verify_fresh
from phishguard.evasion.common import PROTOCOL as EVASION
from phishguard.evasion.common import lines_bytes
from phishguard.evasion.data import verify
from phishguard.evasion.metrics import asr, selected, summarize
from phishguard.evasion.runner import file_snapshot, load_pair, neural_score


def comparison(rows, thresholds, summary):
    labels = [int(r["label"] == "phishing") for r in rows]
    shared = [
        r
        for r in rows
        if r["label"] == "phishing"
        and all(r["clean_scores"][m] >= thresholds[m] for m in ("finetuned", "defended"))
    ]
    summary["parent_defense_common_detected"] = {
        "rows": len(shared),
        "models": {m: asr(shared, m, thresholds[m]) for m in ("finetuned", "defended")},
    }
    transfer = {m: [] for m in thresholds}
    for row in rows:
        _, variant_id = selected(row, "finetuned", thresholds["finetuned"])
        value = next(
            (v["scores"] for v in row["candidates"] if v["variant_id"] == variant_id),
            row["clean_scores"],
        )
        for model in thresholds:
            transfer[model].append(value[model])
    summary["parent_selected_transfer"] = {
        "policy": "Parent BERT chooses one input for phishing; legitimate remains clean. "
        "All models score that same input.",
        "models": {m: metrics(labels, scores, thresholds[m]) for m, scores in transfer.items()},
    }
    summary["defended_at_parent_threshold"] = summarize(
        rows, {"defended": PROTOCOL["parent_threshold"]}
    )["models"]["defended"]
    summary["defended_clean_at_default_threshold"] = metrics(
        labels, [r["clean_scores"]["defended"] for r in rows], 0.5
    )
    summary["clean_defense_minus_parent"] = {
        key: summary["models"]["defended"]["clean"][key]
        - summary["models"]["finetuned"]["clean"][key]
        for key in ("accuracy", "recall", "false_positive_rate", "f1")
    }
    summary["clean_per_source"] = {
        source: {
            m: metrics(
                [int(r["label"] == "phishing") for r in rows if r["source_id"] == source],
                [r["clean_scores"][m] for r in rows if r["source_id"] == source],
                t,
            )
            for m, t in thresholds.items()
        }
        for source in sorted({r["source_id"] for r in rows})
    }
    return summary


def score_bank(cohorts, variants, models, thresholds, development, progress=None):
    by_parent = defaultdict(list)
    for v in variants:
        if text_hash(EmailInput.model_validate(v["email"])) in development:
            raise DefenseError("defense_benchmark_candidate_development_overlap")
        by_parent[(v["cohort"], v["parent_id"])].append(v)
    reports, predictions = {}, []
    for cohort, originals in cohorts.items():
        if any(text_hash(r.email) in development for r in originals):
            raise DefenseError("defense_benchmark_original_development_overlap")
        times, queries = dict.fromkeys(models, 0.0), dict.fromkeys(models, 0)

        def score(emails, queries=queries, times=times):
            results, tokens = {}, {}
            for name, model in models.items():
                started = time.perf_counter()
                if name == "baseline_v2":
                    results[name] = model.scores(emails) if emails else []
                elif emails:
                    results[name], counts, fingerprints = neural_score(model, emails)
                    tokens[name] = list(zip(counts, fingerprints, strict=True))
                else:
                    results[name], tokens[name] = [], []
                metrics([0] * len(emails), results[name], thresholds[name])
                queries[name] += len(emails)
                times[name] += time.perf_counter() - started
            return results, tokens

        clean, clean_tokens = score([r.email for r in originals])
        rows = []
        batch_size = EVASION["score_parent_batch_size"]
        for start in range(0, len(originals), batch_size):
            batch = originals[start : start + batch_size]
            if any(
                len(by_parent[(cohort, r.example_id)]) > EVASION["max_candidates"] for r in batch
            ):
                raise DefenseError("defense_query_budget_exceeded")
            items = [v for r in batch for v in by_parent[(cohort, r.example_id)]]
            scores, tokens = score([EmailInput.model_validate(v["email"]) for v in items])
            scored = {
                v["variant_id"]: {
                    "variant_id": v["variant_id"],
                    "operation": v["operation"],
                    "candidate_index": v["candidate_index"],
                    "changed_words": v["changed_words"],
                    "scores": {m: scores[m][i] for m in models},
                    "neural_inputs": {
                        m: {"original_tokens": values[i][0], "sha256": values[i][1]}
                        for m, values in tokens.items()
                    },
                }
                for i, v in enumerate(items)
            }
            for i, r in enumerate(batch, start=start):
                rows.append(
                    {
                        "cohort": cohort,
                        "example_id": r.example_id,
                        "group_id": r.group_id,
                        "split": r.split,
                        "label": r.label,
                        "source_id": r.source_id,
                        "clean_scores": {m: clean[m][i] for m in models},
                        "clean_neural_inputs": {
                            m: {"original_tokens": values[i][0], "sha256": values[i][1]}
                            for m, values in clean_tokens.items()
                        },
                        "candidates": [
                            scored[v["variant_id"]] for v in by_parent[(cohort, r.example_id)]
                        ],
                    }
                )
            if progress:
                progress(
                    {
                        "status": "scoring",
                        "cohort": cohort,
                        "originals": len(rows),
                        "total": len(originals),
                        "queries_each": queries["defended"],
                    }
                )
        summary = comparison(rows, thresholds, summarize(rows, thresholds))
        if any(summary["models"][m]["actual_queries"] != queries[m] for m in models):
            raise DefenseError("defense_query_accounting_mismatch")
        summary["scoring_seconds"] = times
        summary["neural_effective_noops"] = {
            m: sum(
                c["neural_inputs"][m]["sha256"] == r["clean_neural_inputs"][m]["sha256"]
                for r in rows
                for c in r["candidates"]
            )
            for m in ("finetuned", "defended")
        }
        reports[cohort] = summary
        predictions.extend(rows)
    return reports, predictions


def evaluate(
    directory,
    reference,
    fixed_bank,
    fixed_reference,
    fresh_bank,
    fresh_reference,
    baseline_directory,
    parent_directory,
    parent_selection,
    model_directory,
    selection_reference,
    output,
    progress=None,
):
    from phishguard.defense.model import load_detector, snapshot
    from phishguard.finetune.model import tensor_digest

    if output.exists():
        raise DefenseError("output_already_exists")
    fixed_cohorts, fixed_variants, fixed_manifest = verify(
        directory, reference, fixed_bank, fixed_reference
    )
    fresh_cohorts, fresh_variants, fresh_manifest = verify_fresh(
        directory, reference, fresh_bank, fresh_reference
    )
    baseline, original = load_pair(
        baseline_directory, parent_directory, parent_selection, fixed_manifest["dataset_sha256"]
    )
    defended = load_detector(model_directory, selection_reference)
    models = {"baseline_v2": baseline, "finetuned": original, "defended": defended}
    thresholds = {
        "baseline_v2": baseline.state.threshold,
        "finetuned": original.manifest["threshold"],
        "defended": defended.manifest["threshold"],
    }
    before = {
        "prior": file_snapshot(baseline_directory, parent_directory),
        "defended": snapshot(model_directory),
    }
    tensors = {m: tensor_digest(models[m].network.state_dict()) for m in ("finetuned", "defended")}
    development = set(baseline.state.development_text_hashes)
    for model in (original, defended):
        development.update(model.manifest["development_text_hashes"])
    report = {
        **identity(),
        "phase": "frozen-retrospective-defense-comparison",
        "model_revisions": {
            "baseline_v2": baseline.revision,
            "finetuned": original.manifest["model_revision"],
            "defended": defended.manifest["model_revision"],
        },
        "thresholds": thresholds,
        "model_files_before": before,
        "fixed_bank_manifest_sha256": digest(read_bytes(fixed_reference)),
        "fresh_bank_manifest_sha256": digest(read_bytes(fresh_reference)),
        "selection_reference_sha256": digest(read_bytes(selection_reference)),
        "training_validation_or_reserve_files_opened": False,
        "banks": {},
        "bank_budgets_are_separate_not_pooled": True,
        "limitations": PROTOCOL["limitations"],
    }
    all_predictions = []
    for name, cohorts, variants in (
        ("fixed", fixed_cohorts, fixed_variants),
        ("fresh", fresh_cohorts, fresh_variants),
    ):
        summary, predictions = score_bank(
            cohorts, variants, models, thresholds, development, progress
        )
        report["banks"][name] = summary
        all_predictions.extend({"bank": name, **row} for row in predictions)
    fixed_texts = {(v["cohort"], v["parent_id"], v["variant_sha256"]) for v in fixed_variants}
    report["fresh_candidate_overlap_with_fixed"] = {
        "fresh_variants": len(fresh_variants),
        "fixed_variants": len(fixed_variants),
        "identical_parent_and_text": sum(
            (v["cohort"], v["parent_id"], v["variant_sha256"]) in fixed_texts
            for v in fresh_variants
        ),
        "note": "New seed, same parents and constraints. Some candidates can coincide; "
        "each bank is scored separately.",
    }
    if before != {
        "prior": file_snapshot(baseline_directory, parent_directory),
        "defended": snapshot(model_directory),
    } or tensors != {m: tensor_digest(models[m].network.state_dict()) for m in tensors}:
        raise DefenseError("defense_evaluation_changed_model")
    if fixed_manifest["dataset_sha256"] != fresh_manifest["dataset_sha256"]:
        raise DefenseError("defense_bank_dataset_mismatch")
    report["model_files_and_tensors_unchanged"] = True
    payload = lines_bytes(all_predictions)
    report["predictions_sha256"] = digest(payload)
    output.mkdir(parents=True, exist_ok=False)
    (output / "predictions.jsonl").write_bytes(payload)
    (output / "report.json").write_bytes(json_bytes(report))
    return report
