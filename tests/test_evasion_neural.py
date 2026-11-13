"""End-to-end frozen scoring with invented tiny models and unavailable training files."""

# Reuse existing miniature source/dataset fixtures; never download research weights.
# ruff: noqa: E402
import json
from unittest.mock import Mock

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
from test_finetune import dataset as dataset
from test_finetune import source as source

from phishguard.baseline.model import fit_baseline, save_model, text_hash
from phishguard.contracts import EmailInput
from phishguard.evasion import data, runner
from phishguard.evasion.common import PROTOCOL, EvasionError
from phishguard.finetune import common, training


@pytest.fixture
def corpus(corpus):
    return {
        split: [
            row.model_copy(
                update={
                    "email": EmailInput(
                        body=row.email.body
                        + " "
                        + " ".join(
                            f"{split}message{chr(97 + index)}{chr(97 + j)}" for j in range(15)
                        )
                    )
                }
            )
            for index, row in enumerate(rows)
        ]
        for split, rows in corpus.items()
    }


@pytest.fixture
def experiment(source, dataset, corpus, tmp_path, monkeypatch):
    directory, reference = dataset
    baseline, _ = fit_baseline(
        corpus["train"], corpus["validation"], common.STUDY["dataset_sha256"]
    )
    baseline_path, model_path = tmp_path / "baseline", tmp_path / "model"
    save_model(baseline, baseline_path)
    train_report = training.train(directory, reference, source, model_path)
    for key, value in {
        "baseline_revision": baseline.revision,
        "baseline_threshold": baseline.state.threshold,
        "finetuned_revision": train_report["model_revision"],
        "finetuned_threshold": train_report["selection"]["threshold"],
    }.items():
        monkeypatch.setitem(PROTOCOL, key, value)
    selection = tmp_path / "selection.json"
    selection.write_bytes((model_path / "selection.json").read_bytes())
    (directory / "train.jsonl").unlink()
    (directory / "validation.jsonl").unlink()
    monkeypatch.setattr(torch.optim.AdamW, "step", Mock(side_effect=AssertionError("No updates")))
    monkeypatch.setattr(training, "train", Mock(side_effect=AssertionError("No training")))
    bank = tmp_path / "bank"
    manifest = data.prepare(directory, reference, bank)
    assert manifest["variants"] > 0
    return (
        directory,
        reference,
        bank,
        bank / "manifest.json",
        baseline_path,
        model_path,
        selection,
    )


def test_frozen_evaluation_repeats_and_counts_queries_without_training(experiment, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    result = runner.evaluate(*experiment, a)
    second = runner.evaluate(*experiment, b)
    assert (a / "predictions.jsonl").read_bytes() == (b / "predictions.jsonl").read_bytes()
    assert result["predictions_sha256"] == second["predictions_sha256"]
    assert result["model_files_and_neural_tensors_unchanged"]
    assert not result["training_validation_or_reserve_files_opened"]
    rows = [json.loads(line) for line in (a / "predictions.jsonl").read_bytes().splitlines()]
    for cohort, summary in result["cohorts"].items():
        subset = [r for r in rows if r["cohort"] == cohort]
        for model in summary["models"].values():
            assert model["actual_queries"] == sum(1 + len(r["candidates"]) for r in subset)
            assert model["maximum_queries_per_original"] <= 13
    with pytest.raises(EvasionError, match="already_exists"):
        runner.evaluate(*experiment, a)


@pytest.mark.parametrize("case", ["threshold", "selection"])
def test_model_identity_and_threshold_cannot_change(experiment, tmp_path, monkeypatch, case):
    if case == "threshold":
        monkeypatch.setitem(PROTOCOL, "baseline_threshold", -1)
        # Keep the already-frozen bank intact; isolate the model identity check.
        with pytest.raises(EvasionError, match="model_or_threshold"):
            runner.load_pair(
                experiment[4], experiment[5], experiment[6], common.STUDY["dataset_sha256"]
            )
    else:
        experiment[6].write_bytes(experiment[6].read_bytes() + b" ")
        with pytest.raises(EvasionError, match="model_or_threshold"):
            runner.evaluate(*experiment, tmp_path / "result")


def test_variant_development_overlap_stops_before_scoring(experiment, tmp_path, monkeypatch):
    _, variants, _ = data.verify(*experiment[:4])
    baseline, detector = runner.load_pair(
        experiment[4], experiment[5], experiment[6], common.STUDY["dataset_sha256"]
    )
    detector.manifest["development_text_hashes"].append(
        text_hash(EmailInput.model_validate(variants[0]["email"]))
    )
    monkeypatch.setattr(runner, "load_pair", lambda *args: (baseline, detector))
    monkeypatch.setattr(runner, "neural_score", Mock(side_effect=AssertionError("No scoring")))
    with pytest.raises(EvasionError, match="candidate_development_overlap"):
        runner.evaluate(*experiment, tmp_path / "result")


def test_budget_guard_never_scores_extra_candidates(experiment, tmp_path, monkeypatch):
    cohorts, variants, manifest = data.verify(*experiment[:4])
    parent = variants[0]["parent_id"]
    family = [v for v in variants if v["parent_id"] == parent]
    altered = (
        [v for v in variants if v["parent_id"] != parent]
        + family
        + [family[0]] * (13 - len(family))
    )
    monkeypatch.setattr(runner, "verify", lambda *args: (cohorts, altered, manifest))
    original = runner.neural_score
    sizes = []

    def bounded(detector, emails):
        sizes.append(len(emails))
        assert len(sizes) == 1  # Only clean scoring is allowed before rejection.
        return original(detector, emails)

    monkeypatch.setattr(runner, "neural_score", bounded)
    with pytest.raises(EvasionError, match="query_budget_exceeded"):
        runner.evaluate(*experiment, tmp_path / "result")
