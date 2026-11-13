"""Random miniature fixtures test training boundaries without downloading research models."""

# Conditional neural imports follow importorskip for core-only installations.
# ruff: noqa: E402

import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
from safetensors.torch import load_file, save_file
from transformers import BertConfig, BertForPreTraining

from phishguard.audit.data import cohort_stats
from phishguard.baseline.model import fit_baseline, save_model
from phishguard.cli import main
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.finetune import common, evaluation, model, training
from phishguard.finetune.common import FineTuneError
from phishguard.pretrained.source import PretrainedError
from phishguard.refresh import common as refresh_common


@pytest.fixture
def source(tmp_path, monkeypatch):
    path = tmp_path / "source"
    path.mkdir()
    vocab = [
        "[PAD]",
        "[UNK]",
        "[CLS]",
        "[SEP]",
        "[MASK]",
        "agenda",
        "collaboration",
        "workshop",
        "verify",
        "password",
        "urgent",
        "heldoutonlytoken",
        "meeting",
        "review",
        "report",
    ]
    config = dict(
        vocab_size=len(vocab),
        hidden_size=8,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=16,
        max_position_embeddings=512,
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        model_type="bert",
    )
    torch.manual_seed(19)
    network = BertForPreTraining(BertConfig(**config))
    weights = {
        k: v.contiguous()
        for k, v in network.state_dict().items()
        if not k.startswith("cls.predictions.decoder.")
    }
    save_file(weights, path / "model.safetensors")
    (path / "vocab.txt").write_text("\n".join(vocab) + "\n", encoding="utf-8")
    (path / "config.json").write_bytes(json_bytes(config))
    (path / "README.md").write_text("Invented test fixture; no upstream research model.")
    monkeypatch.setitem(common.SOURCE, "configuration", config)
    monkeypatch.setitem(
        common.SOURCE,
        "files",
        {
            name: {
                "bytes": (path / name).stat().st_size,
                "sha256": digest((path / name).read_bytes()),
            }
            for name in ("README.md", "config.json", "vocab.txt", "model.safetensors")
        },
    )
    for key, value in {
        "epochs": 2,
        "batch_size": 2,
        "numeric_threads": 1,
        "max_tokens": 24,
    }.items():
        monkeypatch.setitem(common.PROTOCOL, key, value)
    return path


@pytest.fixture
def dataset(corpus, tmp_path, monkeypatch):
    directory = tmp_path / "dataset"
    directory.mkdir()
    challenge = [
        r.model_copy(
            update={
                "example_id": r.example_id.replace("test", "challenge"),
                "group_id": r.group_id.replace("test", "challenge"),
                "email": EmailInput(body=r.email.body + " challenge signal"),
            }
        )
        for r in corpus["test"]
    ]
    splits = {**corpus, "challenge": challenge}
    manifest = {
        "source": refresh_common.SOURCE,
        "source_sha256": refresh_common.SOURCE_SHA256,
        "protocol": refresh_common.PROTOCOL,
        "protocol_sha256": refresh_common.PROTOCOL_SHA256,
        "groups": [],
        "files": {},
        "partitions": {},
    }
    for split, rows in splits.items():
        payload = b"".join((r.model_dump_json() + "\n").encode() for r in rows)
        name = split + ".jsonl"
        (directory / name).write_bytes(payload)
        manifest["files"][name] = {"bytes": len(payload), "sha256": digest(payload)}
        manifest["partitions"][split] = cohort_stats(rows)
        manifest["groups"].extend(
            {"group_id": r.group_id, "members": [r.example_id], "split": split} for r in rows
        )
    payload = json_bytes(manifest)
    (directory / "manifest.json").write_bytes(payload)
    reference = tmp_path / "reference.json"
    reference.write_bytes(payload)
    monkeypatch.setitem(common.STUDY, "dataset_sha256", digest(payload))
    monkeypatch.setitem(common.STUDY, "expected_rows", {s: len(v) for s, v in splits.items()})
    monkeypatch.setitem(common.STUDY, "reviewed_ids", [])
    monkeypatch.setitem(common.STUDY, "excluded_benchmark_groups", [])
    return directory, reference


def test_encoder_loaded_exactly_and_head_is_new(source):
    with model.runtime(42):
        detector = model.initialize(source)
    original = load_file(source / "model.safetensors")
    for name, tensor in detector.network.bert.state_dict().items():
        assert torch.equal(tensor, original["bert." + name])
    assert detector.network.classifier.out_features == 2
    assert detector.network.config.id2label == {0: "legitimate", 1: "phishing"}
    assert all(p.requires_grad for p in detector.network.parameters())


def test_train_has_no_benchmark_or_reserve_access_and_reloads(source, dataset, tmp_path):
    directory, reference = dataset
    (directory / "test.jsonl").unlink()
    (directory / "challenge.jsonl").unlink()
    before = (source / "model.safetensors").read_bytes()
    report = training.train(directory, reference, source, tmp_path / "trained")
    assert (
        report["test_rows_used"]
        == report["challenge_rows_used"]
        == report["reserve_rows_scored"]
        == 0
    )
    assert (
        report["encoder_updated"]
        and report["encoder_before_sha256"] != report["encoder_after_sha256"]
    )
    assert before == (source / "model.safetensors").read_bytes()
    best = min(report["epochs"], key=lambda row: row["validation_mean_loss"])
    assert report["selected_epoch"] == best["epoch"]
    assert report["reload_max_absolute_score_error"] == 0
    restored = model.load_detector(tmp_path / "trained")
    prediction = restored.predict(EmailInput(body="review the meeting report"))
    assert prediction["prediction"]["model_revision"] == report["model_revision"]
    assert "report" not in json.dumps(prediction)


def test_same_seed_reproduces_weights_and_selection(source, dataset, tmp_path):
    directory, reference = dataset
    first = training.train(directory, reference, source, tmp_path / "first")
    second = training.train(directory, reference, source, tmp_path / "second")
    assert first["epochs"] == second["epochs"] and first["selection"] == second["selection"]
    assert (tmp_path / "first/model.safetensors").read_bytes() == (
        tmp_path / "second/model.safetensors"
    ).read_bytes()


def test_truncation_is_counted_and_padding_not_treated_as_content(source):
    with model.runtime(42):
        detector = model.initialize(source)
        encoded, counts = detector.encode(
            [EmailInput(body="review " * 100), EmailInput(body="meeting")]
        )
        assert counts == [102, 3]
        assert len(encoded[0]["input_ids"]) == common.PROTOCOL["max_tokens"]
        assert encoded[0]["input_ids"][-1] == detector.tokenizer.sep_token_id
        padded = detector.batch(encoded)
        assert padded["attention_mask"][1].sum().item() == 3
        scores, _ = detector.score_encoded(encoded)
        assert len(scores) == 2 and all(0 <= s <= 1 for s in scores)
        assert model.token_report(counts)["truncated_rows"] == 1


def test_review_exclusion_removes_whole_family_and_checks_expected_count(monkeypatch):
    rows = [
        SimpleNamespace(example_id="a", group_id="family"),
        SimpleNamespace(example_id="b", group_id="family"),
        SimpleNamespace(example_id="c", group_id="safe"),
    ]
    monkeypatch.setitem(common.STUDY, "reviewed_ids", ["a"])
    monkeypatch.setitem(common.STUDY, "excluded_benchmark_groups", [{"group_id": "family"}])
    monkeypatch.setitem(common.STUDY, "expected_rows", {"test": 1})
    assert [
        r.example_id for r in common.partition(SimpleNamespace(load=lambda s: rows), "test")
    ] == ["c"]
    monkeypatch.setitem(common.STUDY, "expected_rows", {"test": 2})
    with pytest.raises(FineTuneError, match="partition_count_mismatch"):
        common.partition(SimpleNamespace(load=lambda s: rows), "test")


def test_registry_must_match_frozen_membership(dataset, monkeypatch):
    directory, reference = dataset
    monkeypatch.setitem(common.STUDY, "reviewed_ids", ["test-legitimate-0"])
    with pytest.raises(FineTuneError, match="review_registry_mismatch"):
        common.study(directory, reference)


@pytest.mark.parametrize("case", ["valid", "selection", "baseline"])
def test_evaluation_never_fits_or_reads_development(
    source, dataset, corpus, tmp_path, monkeypatch, case
):
    directory, reference = dataset
    baseline, _ = fit_baseline(
        corpus["train"], corpus["validation"], common.STUDY["dataset_sha256"]
    )
    save_model(baseline, tmp_path / "baseline")
    monkeypatch.setitem(common.STUDY, "baseline_v2_revision", baseline.revision)
    monkeypatch.setitem(common.STUDY, "baseline_v2_threshold", baseline.state.threshold)
    training.train(directory, reference, source, tmp_path / "model")
    selection = tmp_path / "selection.json"
    selection.write_bytes(
        (tmp_path / "model/selection.json").read_bytes() + (b" " if case == "selection" else b"")
    )
    (directory / "train.jsonl").unlink()
    (directory / "validation.jsonl").unlink()
    monkeypatch.setattr(torch.optim.AdamW, "step", Mock(side_effect=AssertionError("No updates")))
    if case == "baseline":
        monkeypatch.setitem(common.STUDY, "baseline_v2_revision", "0" * 64)
    if case != "valid":
        with pytest.raises(
            FineTuneError,
            match="selection_reference_mismatch"
            if case == "selection"
            else "comparison_identity_mismatch",
        ):
            evaluation.evaluate(
                directory,
                reference,
                tmp_path / "model",
                tmp_path / "baseline",
                selection,
                tmp_path / "results",
            )
    else:
        report = evaluation.evaluate(
            directory,
            reference,
            tmp_path / "model",
            tmp_path / "baseline",
            selection,
            tmp_path / "results",
        )
        assert (
            not report["development_or_reserve_files_opened"]
            and not report["model_weights_updated"]
        )
        for cohort in report["cohorts"].values():
            assert sum(cohort["paired_correctness"].values()) == cohort["rows"]


@pytest.mark.parametrize("case", ["bytes", "path", "labels", "nonfinite"])
def test_artifact_loading_rejects_corruption_and_invalid_state(source, dataset, tmp_path, case):
    directory, reference = dataset
    path = tmp_path / "model"
    training.train(directory, reference, source, path)
    manifest = json.loads((path / "manifest.json").read_bytes())
    if case == "bytes":
        (path / "model.safetensors").write_bytes(b"PRIVATE invalid model")
    elif case == "path":
        manifest["files"]["../PRIVATE"] = manifest["files"].pop("config.json")
    elif case == "labels":
        config = json.loads((path / "config.json").read_bytes())
        config["id2label"] = {"0": "phishing", "1": "legitimate"}
        payload = json_bytes(config)
        (path / "config.json").write_bytes(payload)
        manifest["files"]["config.json"] = {"bytes": len(payload), "sha256": digest(payload)}
    else:
        state = load_file(path / "model.safetensors")
        state["classifier.bias"][0] = float("nan")
        save_file(state, path / "model.safetensors")
        payload = (path / "model.safetensors").read_bytes()
        manifest["files"]["model.safetensors"] = {"bytes": len(payload), "sha256": digest(payload)}
    manifest["model_revision"] = digest(
        json_bytes({k: v for k, v in manifest.items() if k != "model_revision"})
    )
    (path / "manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises((FineTuneError, PretrainedError)):
        model.load_detector(path)


@pytest.mark.parametrize("case", ["valid", "digest", "oversize", "redirect"])
def test_source_download_is_bounded_and_atomic(tmp_path, monkeypatch, case):
    monkeypatch.setitem(common.SOURCE, "files", {"file": {"bytes": 3, "sha256": digest(b"abc")}})
    monkeypatch.setattr(common, "verify_source", lambda p: {"status": "verified"})
    response = io.BytesIO(
        b"abc" if case in {"valid", "redirect"} else b"XXX" if case == "digest" else b"abcd"
    )
    response.url = "http://insecure.invalid" if case == "redirect" else "https://fixture.invalid"
    opener = SimpleNamespace(open=Mock(return_value=response))
    monkeypatch.setattr(common.urllib.request, "build_opener", Mock(return_value=opener))
    if case == "valid":
        common.fetch(tmp_path)
        common.fetch(tmp_path)
        assert opener.open.call_count == 1
    else:
        with pytest.raises((FineTuneError, PretrainedError)):
            common.fetch(tmp_path)
        assert not list(tmp_path.iterdir())


def test_missing_model_prediction_is_unavailable_and_private(tmp_path, capsys):
    message = tmp_path / "input.json"
    message.write_text(json.dumps({"body": "PRIVATE message"}))
    assert (
        main(["finetune", "predict", "--model", str(tmp_path / "missing"), "--file", str(message)])
        == 1
    )
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "unavailable"
