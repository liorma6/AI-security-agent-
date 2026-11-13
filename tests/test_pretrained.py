"""Offline source, inference and held-out comparison checks; no public checkpoint download."""

import io
import json
import urllib.request

import pytest

from phishguard.baseline.runner import evaluate_baseline, train_baseline
from phishguard.cli import main
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.pretrained import source
from phishguard.pretrained.selection import Selection, load_selection, save_selection
from phishguard.pretrained.source import PROTOCOL_SHA256, SOURCE_SHA256, PretrainedError

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
from transformers import BertTokenizerFast, DistilBertConfig, DistilBertForSequenceClassification  # noqa: E402 - optional dependencies are checked above

from phishguard.pretrained import adapter, runner  # noqa: E402
from phishguard.pretrained.adapter import PretrainedClassifier, ScoredBatch, phishing_scores  # noqa: E402


@pytest.fixture
def tiny(tmp_path):
    vocab = tmp_path / "vocab.txt"
    vocab.write_text("[PAD]\n[UNK]\n[CLS]\n[SEP]\n[MASK]\nHello\nhello\nworld\n", encoding="utf-8")
    tokenizer = BertTokenizerFast(vocab_file=str(vocab), do_lower_case=False, model_max_length=512)
    torch.manual_seed(42)
    config = DistilBertConfig(
        vocab_size=8,
        dim=8,
        hidden_dim=16,
        n_layers=1,
        n_heads=2,
        max_position_embeddings=512,
        id2label=source.SOURCE["id2label"],
        attn_implementation="eager",
    )
    return PretrainedClassifier(tokenizer, DistilBertForSequenceClassification(config))


def test_mapping_direction_is_explicit():
    logits = torch.tensor([[0.0, 2.0], [2.0, 0.0]])
    forward = phishing_scores(logits, {0: "SAVE EMAIL", 1: "PHISHING EMAIL"})
    reverse = phishing_scores(logits, {0: "PHISHING EMAIL", 1: "SAVE EMAIL"})
    assert forward[0] == pytest.approx(0.880797)
    assert reverse == pytest.approx(list(reversed(forward)))


@pytest.mark.parametrize(
    "mapping",
    [
        None,
        {},
        {0: "LABEL_0", 1: "LABEL_1"},
        {0: "SAVE EMAIL", 1: "PHISHING EMAIL", 2: "URL"},
        {0: [], 1: "PHISHING EMAIL"},
        {0: "SAVE EMAIL", "0": "SAVE EMAIL", 1: "PHISHING EMAIL"},
    ],
)
def test_ambiguous_mapping_rejected(mapping):
    with pytest.raises(PretrainedError, match="incompatible_label_mapping"):
        adapter.phishing_index(mapping)


@pytest.mark.parametrize("logits", [[[float("nan"), 0]], [[float("inf"), 0]], [[0, 1, 2]], [0, 1]])
def test_invalid_logits_rejected(logits):
    with pytest.raises(PretrainedError, match="invalid_model_output"):
        phishing_scores(torch.tensor(logits, dtype=torch.float32), source.SOURCE["id2label"])


def test_real_transformer_inference_is_frozen_cased_and_repeatable(tiny):
    assert tiny.tokenizer("Hello")["input_ids"] != tiny.tokenizer("hello")["input_ids"]
    emails = [EmailInput(body="Hello world <<synthetic_marker>>"), EmailInput(body="Hello world")]
    before = {key: value.clone() for key, value in tiny.network.state_dict().items()}
    observed = []
    hook = tiny.network.register_forward_pre_hook(
        lambda *_: observed.append((torch.is_inference_mode_enabled(), tiny.network.training))
    )
    result = tiny.score(emails)
    hook.remove()
    assert observed == [(True, False)]
    assert result.scores[0] == result.scores[1]
    assert tiny.score(emails).scores == result.scores
    assert all(torch.equal(before[key], value) for key, value in tiny.network.state_dict().items())
    assert all(parameter.grad is None for parameter in tiny.network.parameters())
    assert tiny.network.device.type == "cpu"


def test_long_input_is_reported_and_not_dropped(tiny):
    email = EmailInput(body="hello " * 600)
    result = tiny.predict(email)
    assert result["input"] == {"original_tokens": 602, "used_tokens": 512, "truncated": True}
    assert 0 <= result["prediction"]["score"] <= 1
    batch = tiny.score([email, EmailInput(body="Hello world")])
    assert len(batch.scores) == 2 and batch.token_report()["truncated_rows"] == 1


def test_loader_requires_local_complete_safetensors(tmp_path, monkeypatch, tiny):
    raw = {
        "architectures": [source.SOURCE["architecture"]],
        "id2label": source.SOURCE["id2label"],
        "max_position_embeddings": 512,
        "model_type": "distilbert",
        "vocab_size": 28996,
    }
    (tmp_path / "config.json").write_bytes(json_bytes(raw))
    monkeypatch.setattr(adapter, "verify_source", lambda _: None)

    class Tokenizer:
        def __len__(self):
            return 28996

        def convert_tokens_to_ids(self, _):
            return [0, 100, 101, 102, 103]

    monkeypatch.setattr(adapter, "BertTokenizerFast", lambda **_: Tokenizer())
    captured = {}

    def load(*args, **kwargs):
        captured.update(kwargs)
        return tiny.network, {"missing_keys": ["classifier.weight"]}

    monkeypatch.setattr(adapter.DistilBertForSequenceClassification, "from_pretrained", load)
    with pytest.raises(PretrainedError, match="incomplete_model_weights"):
        adapter.load_classifier(tmp_path)
    assert captured["local_files_only"] and captured["use_safetensors"]
    assert captured["trust_remote_code"] is False
    assert captured["output_loading_info"] and captured["attn_implementation"] == "eager"


@pytest.fixture
def small_source(monkeypatch):
    payload = b"reviewed model bytes"
    monkeypatch.setitem(
        source.SOURCE,
        "files",
        {"model.safetensors": {"bytes": len(payload), "sha256": digest(payload)}},
    )
    return payload


def test_download_verified_cache_and_no_overwrite(tmp_path, monkeypatch, small_source):
    requests = []

    class Response(io.BytesIO):
        url = "https://download.example.invalid/file"

    class Opener:
        def open(self, request, **kwargs):
            requests.append(request.full_url)
            return Response(small_source)

    monkeypatch.setattr(source.urllib.request, "build_opener", lambda *_: Opener())
    source.download_source(tmp_path)
    source.download_source(tmp_path)
    assert len(requests) == 1 and source.SOURCE["revision"] in requests[0]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["model.safetensors"]
    (tmp_path / "model.safetensors").write_bytes(b"changed")
    with pytest.raises(PretrainedError, match="model_integrity_mismatch"):
        source.download_source(tmp_path)
    assert len(requests) == 1


@pytest.mark.parametrize("payload", [b"short", b"x" * 100])
def test_partial_or_oversized_download_never_published(
    tmp_path, monkeypatch, small_source, payload
):
    class Response(io.BytesIO):
        url = "https://download.example.invalid/file"

    class Opener:
        def open(self, *args, **kwargs):
            return Response(payload)

    monkeypatch.setattr(source.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises(PretrainedError, match="model_integrity_mismatch"):
        source.download_source(tmp_path)
    assert not list(tmp_path.iterdir())


def test_download_rejects_http_redirect_before_following():
    with pytest.raises(PretrainedError, match="insecure_model_redirect"):
        source.HTTPSRedirect().redirect_request(
            urllib.request.Request("https://example.invalid"),
            None,
            302,
            "redirect",
            {},
            "http://example.invalid",
        )


@pytest.fixture
def fake_classifier(monkeypatch):
    class Fake:
        def score(self, emails, progress=None):
            return ScoredBatch(
                [0.4 if "password" in e.body else 0.1 for e in emails], [10] * len(emails), 0.01
            )

    monkeypatch.setattr(runner, "load_classifier", lambda _: Fake())


def test_selection_does_not_open_test_or_training(prepared, tmp_path, fake_classifier):
    directory, reference = prepared
    train_baseline(directory, reference, tmp_path / "baseline")
    (directory / "train.jsonl").unlink()
    (directory / "test.jsonl").unlink()
    report = runner.select_pretrained(
        directory, reference, tmp_path, tmp_path / "baseline", tmp_path / "selection"
    )
    assert report["test_rows_used"] == 0 and not report["weights_updated"]
    assert load_selection(tmp_path / "selection").threshold == 0.4


@pytest.mark.parametrize("part", ["threshold", "source", "validation", "bytes"])
def test_tampered_selection_rejected(tmp_path, part):
    report = {"metrics": "fixture"}
    state = Selection(
        source_sha256=SOURCE_SHA256,
        protocol_sha256=PROTOCOL_SHA256,
        dataset_sha256="a" * 64,
        baseline_revision="b" * 64,
        threshold=0.4,
        validation_report_sha256=digest(json_bytes(report)),
    )
    output = tmp_path / "selection"
    save_selection(output, state, report)
    assert load_selection(output) == state
    if part == "validation":
        (output / "validation-report.json").write_bytes(b"{}")
    elif part == "bytes":
        (output / "selection.json").write_bytes(b"{}")
    else:
        manifest = json.loads((output / "manifest.json").read_bytes())
        manifest[part] = 0.5 if part == "threshold" else "https://example.invalid"
        (output / "manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises(PretrainedError):
        load_selection(output)


def test_same_rows_comparison_frozen_threshold_and_receipt(
    prepared, tmp_path, fake_classifier, monkeypatch
):
    directory, reference = prepared
    baseline = tmp_path / "baseline"
    train_baseline(directory, reference, baseline)
    evaluate_baseline(directory, reference, baseline, tmp_path / "baseline-test")
    selection = tmp_path / "selection"
    runner.select_pretrained(directory, reference, tmp_path, baseline, selection)

    def no_selection(*args):
        raise AssertionError("Final test must not select thresholds")

    monkeypatch.setattr(runner, "select_threshold", no_selection)
    report_path = tmp_path / "baseline-test/report.json"
    report = runner.evaluate_pretrained(
        directory, reference, tmp_path, baseline, selection, report_path, tmp_path / "result"
    )
    assert report["metrics"]["pretrained_default"]["confusion"]["fn"] == 2
    assert report["metrics"]["pretrained_selected"]["accuracy"] == 1
    assert sum(report["paired_correctness"]["selected"].values()) == 4
    assert "body" not in (tmp_path / "result/predictions.jsonl").read_text()
    prior = json.loads(report_path.read_bytes())
    prior["test_ids_sha256"] = "c" * 64
    report_path.write_bytes(json_bytes(prior))
    with pytest.raises(PretrainedError, match="baseline_report_mismatch"):
        runner.evaluate_pretrained(
            directory, reference, tmp_path, baseline, selection, report_path, tmp_path / "bad"
        )
    assert not (tmp_path / "bad").exists()


def test_paired_counts_match_manual_example():
    assert runner.paired_correctness([0, 0, 1, 1], [0, 0, 0, 0], 0.5, [0, 1, 1, 0], 0.5) == {
        "both_correct": 1,
        "baseline_only": 1,
        "pretrained_only": 1,
        "both_wrong": 1,
    }


def test_cli_prediction_privacy_and_missing_model(tmp_path, monkeypatch, tiny, capsys):
    path = tmp_path / "email.json"
    path.write_bytes(json_bytes({"body": "PRIVATE-MARKER Hello world"}))
    assert (
        main(["pretrained", "predict", "--model", str(tmp_path / "absent"), "--file", str(path)])
        == 1
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["reason"] == "model_not_loaded"
    assert "score" not in json.loads(captured.out)
    monkeypatch.setattr(adapter, "load_classifier", lambda _: tiny)
    before = set(tmp_path.rglob("*"))
    assert main(["pretrained", "predict", "--file", str(path)]) == 0
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err
    assert json.loads(captured.out)["prediction"]["status"] == "ok"
    assert set(tmp_path.rglob("*")) == before
