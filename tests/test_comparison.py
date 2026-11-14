"""Selection boundary and refusal checks without opening research mail."""

from types import SimpleNamespace

import pytest

from phishguard import comparison as c
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.pretrained.source import PretrainedError


def test_select_reads_only_validation_and_freezes_report(tmp_path, monkeypatch):
    from phishguard.pretrained import adapter, runner

    calls = []
    rows = [
        SimpleNamespace(example_id=f"fixture-{i}", label=label, email=EmailInput(body="Fixture"))
        for i, label in enumerate(("legitimate", "phishing"))
    ]
    monkeypatch.setattr(c, "study", lambda *a: SimpleNamespace(sha256="a" * 64))
    monkeypatch.setattr(c, "frozen_baseline", lambda _: SimpleNamespace(revision="b" * 64))

    def partition(_, name):
        calls.append(name)
        assert name == "validation"
        return rows

    monkeypatch.setattr(c, "partition", partition)
    scored = SimpleNamespace(
        scores=[0.1, 0.8], elapsed_seconds=0.0, token_report=lambda: {"rows": 2}
    )
    monkeypatch.setattr(
        adapter, "load_classifier", lambda _: SimpleNamespace(score=lambda *a: scored)
    )
    monkeypatch.setattr(runner, "identity", lambda _: {})
    report = c.select(tmp_path / "selection")
    assert calls == ["validation"]
    assert report["test_challenge_reserve_rows_used"] == 0
    assert report["weights_updated"] is False
    assert (tmp_path / "selection/selection.json").is_file()


def test_existing_outputs_refused_before_any_data_read(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "study", lambda *a: pytest.fail("must not read data"))
    with pytest.raises(PretrainedError, match="output_already_exists"):
        c.select(tmp_path)
    with pytest.raises(PretrainedError, match="output_already_exists"):
        c.evaluate(tmp_path)


def test_selection_reference_mismatch_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "load_selection", lambda _: object())
    (tmp_path / "selection.json").write_bytes(b"first")
    reference = tmp_path / "reference.json"
    reference.write_bytes(b"second")
    with pytest.raises(PretrainedError, match="reference_mismatch"):
        c.checked_selection(tmp_path, reference)


def test_wrong_study_selection_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "load_selection", lambda _: SimpleNamespace(dataset_sha256="0" * 64))
    reference = tmp_path / "selection.json"
    reference.write_bytes(b"same")
    (tmp_path / "validation-report.json").write_bytes(json_bytes({}))
    with pytest.raises(PretrainedError, match="scope_mismatch"):
        c.checked_selection(tmp_path, reference)
