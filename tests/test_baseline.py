"""Small invented corpora verify learning boundaries, arithmetic and persistence."""

import json
import math

import numpy as np
import pytest
from pydantic import ValidationError

from phishguard.baseline import model as model_module
from phishguard.baseline.common import BaselineError, parse_json
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.metrics import metrics, select_threshold
from phishguard.baseline.model import ModelState, fit_baseline, load_model, save_model
from phishguard.baseline.preprocessing import preprocess
from phishguard.baseline.runner import evaluate_baseline, train_baseline
from phishguard.cli import main
from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets.preparation import (
    GROUPING,
    PIPELINE_VERSION,
    SPLITS,
    json_bytes,
    membership,
    partition_stats,
)
from phishguard.datasets.source import SOURCE, digest


@pytest.fixture
def corpus():
    partitions = {}
    for split, tag, count in [
        ("train", "alpha", 4),
        ("validation", "bravo", 2),
        ("test", "charlie", 2),
    ]:
        records = []
        for label in ("legitimate", "phishing"):
            for index in range(count):
                rid = f"{split}-{label}-{index}"
                signal = (
                    "agenda collaboration workshop"
                    if label == "legitimate"
                    else "verify password urgent"
                )
                extra = "heldoutonlytoken" if split == "validation" else ""
                marker = "<<infected_payload>>" if label == "phishing" else ""
                body = f"{signal} {tag}{chr(97 + index)} {extra} {marker}"
                records.append(
                    EmailExample(
                        example_id=rid,
                        email=EmailInput(body=body),
                        label=label,
                        source_id=SOURCE["source_id"],
                        source_revision=SOURCE["revision"],
                        license=SOURCE["license"],
                        group_id=f"group-{rid}",
                        split=split,
                    )
                )
        partitions[split] = records
    return partitions


@pytest.fixture
def prepared(tmp_path, corpus):
    directory = tmp_path / "dataset"
    directory.mkdir()
    records = [r for values in corpus.values() for r in values]
    manifest = {
        "format_version": "1.0",
        "pipeline_version": PIPELINE_VERSION,
        "source": SOURCE,
        "target_ratios": SPLITS,
        "grouping": GROUPING,
        "groups": membership(records),
        "partitions": partition_stats(records),
        "files": {},
    }
    for split, values in corpus.items():
        payload = b"".join((r.model_dump_json() + "\n").encode() for r in values)
        name = f"{split}.jsonl"
        (directory / name).write_bytes(payload)
        manifest["files"][name] = {"bytes": len(payload), "sha256": digest(payload)}
    payload = json_bytes(manifest)
    (directory / "manifest.json").write_bytes(payload)
    reference = tmp_path / "frozen.json"
    reference.write_bytes(payload)
    return directory, reference


@pytest.fixture
def fitted(corpus):
    return fit_baseline(corpus["train"], corpus["validation"], "a" * 64)[0]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Review <<malicious_url>> now", "Review now"),
        ("A <<multi\nline>> message", "A message"),
        ("Before<<one>><<two>> after", "Before after"),
        ("<b>Text</b> at https://example.invalid", "<b>Text</b> at https://example.invalid"),
        ("  Caf\u00e9\nproject  ", "Caf\u00e9 project"),
    ],
)
def test_preprocessing_has_fixed_inert_behavior(text, expected):
    assert preprocess(text) == expected


@pytest.mark.parametrize("text", ["<<infected_download>>", "!!!", " "])
def test_unusable_preprocessed_text_rejected(text):
    with pytest.raises(BaselineError, match="no_usable_text"):
        preprocess(text)


def test_metrics_match_hand_calculated_counts():
    result = metrics([1, 1, 1, 0, 0, 0, 0, 0, 1, 1], [1, 1, 1, 1, 0, 0, 0, 0, 0, 0], 0.5)
    assert result["confusion"] == {"tp": 3, "fp": 1, "tn": 4, "fn": 2}
    assert result["accuracy"] == 0.7
    assert result["precision"] == 0.75
    assert result["recall"] == 0.6
    assert result["f1"] == pytest.approx(2 / 3)
    assert result["false_positive_rate"] == 0.2


def test_undefined_metrics_and_threshold_equality():
    empty = metrics([], [], 0.5)
    assert all(
        empty[key] is None
        for key in ("accuracy", "precision", "recall", "f1", "false_positive_rate")
    )
    assert metrics([0], [0.1], 0.5)["precision"] is None
    assert metrics([1], [0.5], 0.5)["confusion"]["tp"] == 1
    assert metrics([1], [0.5], 0.5)["false_positive_rate"] is None


@pytest.mark.parametrize(
    "labels,scores,threshold",
    [
        ([0], [], 0.5),
        ([True], [0.5], 0.5),
        ([2], [0.5], 0.5),
        ([0], [float("nan")], 0.5),
        ([0], [float("inf")], 0.5),
        ([0], [1.1], 0.5),
        ([0], [True], 0.5),
        ([0], [0.5], True),
        ([0], [0.5], -0.1),
    ],
)
def test_invalid_metric_inputs_fail(labels, scores, threshold):
    with pytest.raises(BaselineError, match="invalid_metric_input"):
        metrics(labels, scores, threshold)


def test_threshold_selected_by_validation_f1_with_declared_ties():
    threshold, table = select_threshold([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4])
    assert threshold == 0.3
    assert max(row["f1"] for row in table) == 1
    assert select_threshold([0, 1], [0.1, 0.9])[0] == 0.5
    with pytest.raises(BaselineError, match="validation_requires_both_labels"):
        select_threshold([1], [0.9])


def test_vocabulary_idf_and_coefficients_fit_training_only(corpus, fitted):
    assert "heldoutonlytoken" not in fitted.transform.vocabulary_
    assert "infected_payload" not in fitted.transform.vocabulary_
    position = fitted.transform.vocabulary_["password"]
    # Eight training documents, four containing password; validation is excluded.
    assert fitted.state.idf[position] == pytest.approx(math.log(9 / 5) + 1)
    changed = [
        r.model_copy(update={"email": EmailInput(body=r.email.body + " uniqueword")})
        for r in corpus["validation"]
    ]
    another, _ = fit_baseline(corpus["train"], changed, "a" * 64)
    assert another.state.terms == fitted.state.terms
    assert another.state.idf == fitted.state.idf
    assert another.state.coefficients == fitted.state.coefficients


def test_fit_does_not_mutate_original_text_and_is_reproducible(corpus, fitted):
    before = [r.model_dump() for r in corpus["train"]]
    second, details = fit_baseline(corpus["train"], corpus["validation"], "a" * 64)
    assert second.state == fitted.state
    assert details["roundtrip_max_absolute_score_error"] <= 1e-12
    assert [r.model_dump() for r in corpus["train"]] == before


@pytest.mark.parametrize("case", ["split", "id", "group", "duplicate", "parent"])
def test_leakage_or_wrong_training_split_rejected(corpus, case):
    validation = list(corpus["validation"])
    updates = {
        "split": {"split": "test"},
        "id": {"example_id": corpus["train"][0].example_id},
        "group": {"group_id": corpus["train"][0].group_id},
        "duplicate": {"email": corpus["train"][0].email},
        "parent": {"parent_id": corpus["train"][0].example_id},
    }
    validation[0] = validation[0].model_copy(update=updates[case])
    with pytest.raises(BaselineError):
        fit_baseline(corpus["train"], validation, "a" * 64)


def test_marker_removal_cannot_create_cross_split_exact_duplicates(corpus):
    train, validation = list(corpus["train"]), list(corpus["validation"])
    train[0] = train[0].model_copy(update={"email": EmailInput(body="Identical words <<alpha>>")})
    validation[0] = validation[0].model_copy(
        update={"email": EmailInput(body="Identical words <<beta>>")}
    )
    with pytest.raises(BaselineError, match="preprocessed_text_leakage"):
        fit_baseline(train, validation, "a" * 64)


def test_saved_model_roundtrip_and_prediction_contract(tmp_path, fitted, corpus):
    output = tmp_path / "model"
    save_model(fitted, output)
    restored = load_model(output)
    emails = [r.email for r in corpus["test"]]
    np.testing.assert_allclose(restored.scores(emails), fitted.scores(emails), rtol=0, atol=1e-12)
    prediction = restored.predict(emails[0])
    assert prediction.status == "ok"
    assert prediction.model_revision == fitted.revision
    assert prediction.label == (
        "phishing" if prediction.score >= prediction.threshold else "legitimate"
    )
    assert prediction.elapsed_ms >= 0
    with pytest.raises(BaselineError, match="output_already_exists"):
        save_model(fitted, output)


@pytest.mark.parametrize(
    "mutation",
    ["coefficients", "idf", "duplicate_term", "label_mapping", "version", "extra", "nonfinite"],
)
def test_malformed_numerical_state_rejected(fitted, mutation):
    state = fitted.state.model_dump()
    if mutation == "coefficients":
        state["coefficients"] = []
    if mutation == "idf":
        state["idf"][0] = -1.0
    if mutation == "duplicate_term":
        state["terms"][0] = state["terms"][1]
    if mutation == "label_mapping":
        state["label_mapping"] = {"legitimate": 1, "phishing": 0}
    if mutation == "version":
        state["sklearn_version"] = "unsupported"
    if mutation == "extra":
        state["execute"] = "PRIVATE-COMMAND"
    if mutation == "nonfinite":
        state["intercept"] = float("nan")
    with pytest.raises(ValidationError):
        ModelState.model_validate(state)


@pytest.mark.parametrize(
    "change,code",
    [("bytes", "artifact_integrity_mismatch"), ("threshold", "artifact_manifest_mismatch")],
)
def test_tampered_model_or_manifest_is_rejected(tmp_path, fitted, change, code):
    output = tmp_path / "model"
    save_model(fitted, output)
    if change == "bytes":
        with (output / "model.json").open("ab") as stream:
            stream.write(b" ")
    else:
        manifest = json.loads((output / "manifest.json").read_bytes())
        manifest["threshold"] = 0.12345
        (output / "manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises(BaselineError, match=code):
        load_model(output)


@pytest.mark.parametrize("payload", [b'{"x":1,"x":2}', b'{"x":NaN}', b"[]", b"PRIVATE-MARKER"])
def test_model_json_parser_rejects_ambiguous_input(payload):
    with pytest.raises(BaselineError, match="invalid_artifact_json"):
        parse_json(payload)


def test_training_does_not_open_test_partition(prepared, tmp_path):
    directory, reference = prepared
    (directory / "test.jsonl").unlink()
    report = train_baseline(directory, reference, tmp_path / "model")
    assert report["test_rows_used"] == 0
    assert report["fit_rows"] == 8
    assert report["shortcut_diagnostics"]["train"]["remaining_markers_after_preprocessing"] == 0


def test_end_to_end_train_load_evaluate_with_independent_counts(prepared, tmp_path, monkeypatch):
    directory, reference = prepared
    output = tmp_path / "model"
    training = train_baseline(directory, reference, output)

    def no_training(*args, **kwargs):
        raise AssertionError("Evaluation must never refit")

    monkeypatch.setattr(model_module.LogisticRegression, "fit", no_training)
    evaluation = evaluate_baseline(directory, reference, output, tmp_path / "evaluation")
    assert evaluation["metrics"]["threshold"] == training["model"]["threshold"]
    assert evaluation["metrics"]["rows"] == 4
    predictions = [
        json.loads(line)
        for line in (tmp_path / "evaluation/predictions.jsonl").read_bytes().splitlines()
    ]
    correct = sum(row["label"] == row["decision"] for row in predictions)
    assert evaluation["metrics"]["accuracy"] == correct / 4
    assert all("body" not in row and "email" not in row for row in predictions)
    repeat = evaluate_baseline(directory, reference, output, tmp_path / "repeat")
    assert repeat["metrics"] == evaluation["metrics"]
    assert repeat["predictions_sha256"] == evaluation["predictions_sha256"]


def test_wrong_reference_and_modified_partition_fail(prepared, tmp_path):
    directory, reference = prepared
    wrong = tmp_path / "wrong.json"
    wrong.write_bytes(b"{}")
    with pytest.raises(BaselineError, match="frozen_manifest_mismatch"):
        FrozenDataset(directory, wrong)
    (directory / "train.jsonl").write_bytes(b"PRIVATE-TEXT")
    with pytest.raises(BaselineError, match="partition_integrity_mismatch"):
        train_baseline(directory, reference, tmp_path / "model")
    assert not (tmp_path / "model").exists()


def test_cli_predict_does_not_echo_or_store_email(tmp_path, fitted, capsys):
    output = tmp_path / "model"
    save_model(fitted, output)
    source = tmp_path / "email.json"
    source.write_bytes(json_bytes({"body": "PRIVATE-MARKER agenda workshop"}))
    existing = set(tmp_path.rglob("*"))
    assert main(["baseline", "predict", "--model", str(output), "--file", str(source)]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "ok" and "score" in result
    assert "PRIVATE" not in captured.out + captured.err
    assert set(tmp_path.rglob("*")) == existing


def test_cli_missing_model_has_no_fabricated_score(tmp_path, capsys):
    source = tmp_path / "email.json"
    source.write_bytes(json_bytes({"body": "PRIVATE-MARKER"}))
    assert (
        main(["baseline", "predict", "--model", str(tmp_path / "absent"), "--file", str(source)])
        == 1
    )
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["reason"] == "model_not_loaded"
    assert "score" not in result and "PRIVATE" not in captured.out + captured.err


def test_cli_train_and_evaluate(prepared, tmp_path, capsys):
    directory, reference = prepared
    common = ["--dataset", str(directory), "--reference", str(reference)]
    model = tmp_path / "model"
    assert main(["baseline", "train", *common, "--output", str(model)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "trained"
    assert (
        main(
            [
                "baseline",
                "evaluate",
                *common,
                "--model",
                str(model),
                "--output",
                str(tmp_path / "evaluation"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "evaluated"


def test_non_convergence_aborts_before_artifact_creation(prepared, tmp_path, monkeypatch):
    import warnings

    from sklearn.exceptions import ConvergenceWarning

    def not_converged(*args, **kwargs):
        warnings.warn("PRIVATE-MARKER", ConvergenceWarning, stacklevel=2)

    monkeypatch.setattr(model_module.LogisticRegression, "fit", not_converged)
    directory, reference = prepared
    output = tmp_path / "model"
    with pytest.raises(BaselineError, match="training_not_converged"):
        train_baseline(directory, reference, output)
    assert not output.exists()


def test_evaluation_rejects_another_dataset(prepared, tmp_path, fitted):
    directory, reference = prepared
    save_model(fitted, tmp_path / "model")
    with pytest.raises(BaselineError, match="model_dataset_mismatch"):
        evaluate_baseline(directory, reference, tmp_path / "model", tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_evaluation_rejects_cleaned_development_test_overlap(prepared, corpus, tmp_path, fitted):
    directory, reference = prepared
    state = fitted.state.model_copy(
        update={
            "dataset_sha256": digest(reference.read_bytes()),
            "development_text_hashes": fitted.state.development_text_hashes
            + [model_module.text_hash(corpus["test"][0].email)],
        }
    )
    save_model(model_module.Baseline.from_state(state), tmp_path / "model")
    with pytest.raises(BaselineError, match="preprocessed_test_leakage"):
        evaluate_baseline(directory, reference, tmp_path / "model", tmp_path / "result")
    assert not (tmp_path / "result").exists()
