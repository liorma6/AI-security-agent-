"""Training boundaries, protected artifacts and realistic miniature defense integration."""

# Reuse random local fixtures; no research data or remote model downloads.
# ruff: noqa: E402
import json
from unittest.mock import Mock

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
from test_evasion_neural import corpus as corpus
from test_finetune import dataset as dataset
from test_finetune import source as source

from phishguard.baseline.model import fit_baseline, save_model
from phishguard.cli import main
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.defense import common, data, evaluation, model, training
from phishguard.defense.common import DefenseError
from phishguard.evasion import common as evasion_common
from phishguard.evasion import data as evasion_data
from phishguard.evasion.perturbations import generate
from phishguard.finetune import common as ft_common
from phishguard.finetune import training as ft_training
from phishguard.pretrained.source import PretrainedError


@pytest.fixture
def prepared_defense(source, dataset, corpus, tmp_path, monkeypatch):
    directory, reference = dataset
    baseline, _ = fit_baseline(
        corpus["train"], corpus["validation"], ft_common.STUDY["dataset_sha256"]
    )
    save_model(baseline, tmp_path / "baseline")
    parent_path = tmp_path / "parent"
    original = ft_training.train(directory, reference, source, parent_path)
    for key, value in {
        "parent_revision": original["model_revision"],
        "parent_threshold": original["selection"]["threshold"],
        "epochs": 2,
        "batch_size": 2,
    }.items():
        monkeypatch.setitem(common.PROTOCOL, key, value)
    for key, value in {
        "baseline_revision": baseline.revision,
        "baseline_threshold": baseline.state.threshold,
        "finetuned_revision": original["model_revision"],
        "finetuned_threshold": original["selection"]["threshold"],
    }.items():
        monkeypatch.setitem(evasion_common.PROTOCOL, key, value)
    augmentation = tmp_path / "augmentation"
    manifest = data.prepare(directory, reference, augmentation)
    review = tmp_path / "review.json"
    review.write_bytes(
        json_bytes(
            {
                "augmentation_manifest_sha256": digest(
                    (augmentation / "manifest.json").read_bytes()
                ),
                "decisions": [
                    {"variant_id": v, "decision": "supported"}
                    for v in manifest["review_variant_ids"]
                ],
            }
        )
    )
    return (
        directory,
        reference,
        parent_path,
        parent_path / "selection.json",
        augmentation,
        augmentation / "manifest.json",
        review,
    )


def test_training_only_copies_lineage_and_seed_reproduction(corpus):
    a = data.copies(corpus["train"], "train")
    assert a == data.copies(corpus["train"], "train")
    for row, copy in zip(corpus["train"], a, strict=True):
        assert (copy["parent_id"], copy["group_id"], copy["split"], copy["label"]) == (
            row.example_id,
            row.group_id,
            "train",
            row.label,
        )
        assert copy["seed"] == 101
    original = corpus["test"][0]
    assert generate(original, "test") == generate(original, "test", seed=42)
    assert generate(original, "test", seed=43) != generate(original, "test", seed=42)


@pytest.mark.parametrize("split", ["test", "challenge", "reserve"])
def test_heldout_cannot_be_augmented_for_training(corpus, split):
    with pytest.raises(DefenseError, match="development_only"):
        data.copies(corpus["test"], split)


def test_prepare_and_train_without_benchmark_files_preserves_parent(prepared_defense, tmp_path):
    args = prepared_defense
    (args[0] / "test.jsonl").unlink()
    (args[0] / "challenge.jsonl").unlink()
    initial = model.snapshot(args[2])
    repeated = data.prepare(args[0], args[1], tmp_path / "again")
    assert repeated == json.loads(args[5].read_bytes())
    report = training.train(*args, tmp_path / "defended")
    assert not report["test_challenge_or_reserve_files_opened"]
    assert report["fit_rows"] == 2 * report["fit_original_parents"]
    assert report["encoder_updated"] and report["parent_files_unchanged"]
    assert model.snapshot(args[2]) == initial
    assert (
        report["selected_epoch"]
        == min(report["epochs"], key=lambda x: x["validation_mixed_mean_loss"])["epoch"]
    )
    assert report["reload_max_absolute_score_error"] == 0
    detector = model.load_detector(tmp_path / "defended")
    prediction = detector.predict(EmailInput(body="review meeting report"))
    assert prediction["prediction"]["model_id"] == common.MODEL_ID
    assert prediction["prediction"]["model_revision"] != common.PROTOCOL["parent_revision"]


def test_repeat_training_is_identical(prepared_defense, tmp_path):
    first = training.train(*prepared_defense, tmp_path / "one")
    second = training.train(*prepared_defense, tmp_path / "two")
    assert first["epochs"] == second["epochs"]
    assert first["selection"] == second["selection"]
    assert model.snapshot(tmp_path / "one") == model.snapshot(tmp_path / "two")
    with pytest.raises(DefenseError, match="already_exists"):
        training.train(*prepared_defense, tmp_path / "one")


@pytest.mark.parametrize("case", ["missing", "ambiguous", "invalid", "identity"])
def test_bad_review_blocks_fitting(prepared_defense, tmp_path, monkeypatch, case):
    args = prepared_defense
    review = json.loads(args[6].read_bytes())
    if case == "missing":
        review["decisions"] = []
    elif case == "identity":
        review["augmentation_manifest_sha256"] = "0" * 64
    else:
        review["decisions"][0]["decision"] = case
    args[6].write_bytes(json_bytes(review))
    monkeypatch.setattr(torch.optim.AdamW, "step", Mock(side_effect=AssertionError("No fit")))
    with pytest.raises(DefenseError, match="review_incomplete_or_unsupported"):
        training.train(*args, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()


def test_modified_bank_rejected_before_fit(prepared_defense, tmp_path):
    args = prepared_defense
    with (args[4] / "copies.jsonl").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(DefenseError, match="content_mismatch"):
        training.train(*args, tmp_path / "blocked")


def test_mismatched_parent_rejected(prepared_defense, tmp_path, monkeypatch):
    monkeypatch.setitem(common.PROTOCOL, "parent_revision", "0" * 64)
    with pytest.raises(DefenseError, match="parent_identity"):
        training.train(*prepared_defense, tmp_path / "blocked")


@pytest.mark.parametrize("case", ["weights", "selection"])
def test_defended_artifact_tamper_rejected(prepared_defense, tmp_path, case):
    path = tmp_path / "defended"
    training.train(*prepared_defense, path)
    if case == "weights":
        (path / "model.safetensors").write_bytes(b"PRIVATE broken")
    else:
        selected = json.loads((path / "selection.json").read_bytes())
        selected["threshold"] = -1
        (path / "selection.json").write_bytes(json_bytes(selected))
    with pytest.raises((DefenseError, PretrainedError)):
        model.load_detector(path)


def test_evaluation_reads_no_development_and_repeats(prepared_defense, tmp_path, monkeypatch):
    args = prepared_defense
    directory, reference = args[:2]
    defended = tmp_path / "defended"
    training.train(*args, defended)
    fixed, fresh = tmp_path / "fixed", tmp_path / "fresh"
    evasion_data.prepare(directory, reference, fixed)
    data.prepare_fresh(directory, reference, fresh)
    (directory / "train.jsonl").unlink()
    (directory / "validation.jsonl").unlink()
    monkeypatch.setattr(torch.optim.AdamW, "step", Mock(side_effect=AssertionError("No updates")))
    parameters = (
        directory,
        reference,
        fixed,
        fixed / "manifest.json",
        fresh,
        fresh / "manifest.json",
        tmp_path / "baseline",
        args[2],
        args[3],
        defended,
        defended / "selection.json",
    )
    first = evaluation.evaluate(*parameters, tmp_path / "a")
    second = evaluation.evaluate(*parameters, tmp_path / "b")
    assert first["model_files_and_tensors_unchanged"]
    assert not first["training_validation_or_reserve_files_opened"]
    assert first["predictions_sha256"] == second["predictions_sha256"]
    predictions = [
        json.loads(line) for line in (tmp_path / "a/predictions.jsonl").read_bytes().splitlines()
    ]
    for bank, cohorts in first["banks"].items():
        for cohort, summary in cohorts.items():
            rows = [r for r in predictions if r["bank"] == bank and r["cohort"] == cohort]
            for report in summary["models"].values():
                assert report["actual_queries"] == sum(1 + len(r["candidates"]) for r in rows)
                assert report["maximum_queries_per_original"] <= 13
    with pytest.raises(DefenseError, match="already_exists"):
        evaluation.evaluate(*parameters, tmp_path / "a")


def test_private_missing_prediction(tmp_path, capsys):
    message = tmp_path / "email.json"
    message.write_text(json.dumps({"body": "PRIVATE email"}))
    assert (
        main(["defense", "predict", "--model", str(tmp_path / "missing"), "--file", str(message)])
        == 1
    )
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "unavailable"
