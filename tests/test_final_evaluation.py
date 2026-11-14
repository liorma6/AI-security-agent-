"""Final-evaluation gates use invented mail only; never open the real reserve."""

import copy
from types import SimpleNamespace

import pytest

from phishguard import final_evaluation as f
from phishguard.baseline.model import text_hash
from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest


@pytest.fixture
def reserve(tmp_path, monkeypatch):
    rows = []
    for i, label in enumerate(("legitimate", "phishing", "legitimate", "phishing")):
        source = next(v for v in f.SOURCE["files"].values() if v.get("label") == label)
        rows.append(
            EmailExample(
                example_id=f"fixture-{i}",
                group_id=f"group-{i}",
                label=label,
                source_id=source["source_id"],
                source_revision=source["sha256"],
                license=source["license"],
                email=EmailInput(
                    body="please confirm information about tomorrow planning meeting "
                    + "ordinary project discussion " * 10
                    + str(i)
                ),
            )
        )
    data = b"".join((r.model_dump_json() + "\n").encode() for r in rows)
    metadata = {"bytes": len(data), "sha256": digest(data)}
    for key, value in {
        "rows": 4,
        "groups": 4,
        "labels": {"legitimate": 2, "phishing": 2},
        "reserve_file": metadata,
    }.items():
        monkeypatch.setitem(f.PROTOCOL, key, value)
    manifest = {
        "source_sha256": f.SOURCE_SHA256,
        "protocol_sha256": f.AUDIT_PROTOCOL_SHA256,
        "source": f.SOURCE,
        "files": {"reserve.jsonl": metadata},
        "groups": [
            {"group_id": r.group_id, "cohort": "reserve", "members": [r.example_id]} for r in rows
        ],
        "partitions": {"reserve": f.cohort_stats(rows)},
    }
    (tmp_path / "manifest.json").write_bytes(json_bytes(manifest))
    (tmp_path / "reserve.jsonl").write_bytes(data)
    return tmp_path, rows, manifest


def test_reserve_reader_needs_no_train_validation_or_audit_file(reserve):
    directory, rows, _ = reserve
    loaded, _ = f.load_reserve(directory, directory / "manifest.json")
    assert loaded == rows
    assert all(r.split == "unassigned" for r in loaded)


def test_reserve_tamper_is_rejected(reserve):
    directory, _, _ = reserve
    with (directory / "reserve.jsonl").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError):
        f.load_reserve(directory, directory / "manifest.json")


def test_repeated_group_is_rejected(reserve):
    directory, _, manifest = reserve
    manifest["groups"].append(copy.deepcopy(manifest["groups"][0]))
    (directory / "manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises(f.FinalError, match="membership"):
        f.load_reserve(directory, directory / "manifest.json")


def test_wrong_source_label_is_rejected(reserve, monkeypatch):
    directory, rows, manifest = reserve
    rows[0] = rows[0].model_copy(update={"label": "phishing"})
    data = b"".join((r.model_dump_json() + "\n").encode() for r in rows)
    meta = {"bytes": len(data), "sha256": digest(data)}
    manifest["files"]["reserve.jsonl"] = meta
    monkeypatch.setitem(f.PROTOCOL, "reserve_file", meta)
    (directory / "manifest.json").write_bytes(json_bytes(manifest))
    (directory / "reserve.jsonl").write_bytes(data)
    with pytest.raises(f.FinalError, match="membership"):
        f.load_reserve(directory, directory / "manifest.json")


def test_bank_retains_originals_and_parent_groups(reserve):
    _, rows, _ = reserve
    before = [r.model_dump_json() for r in rows]
    views, bank = f.prepare_bank(rows, set())
    assert bank and all(r.split == "test" for r in views)
    assert before == [r.model_dump_json() for r in rows]
    assert bank == f.prepare_bank(rows, set())[1]
    parents = {r.example_id: r for r in rows}
    for v in bank:
        assert v["group_id"] == parents[v["parent_id"]].group_id
        assert v["cohort"] == "final-reserve" and v["seed"] == 9042
        assert v["candidate_index"] <= 12 and v["changed_words"] <= 3


def test_original_development_overlap_aborts(reserve):
    _, rows, _ = reserve
    with pytest.raises(f.FinalError, match="original_development_overlap"):
        f.prepare_bank(rows, {text_hash(rows[0].email)})


def test_candidate_development_overlap_aborts(reserve):
    _, rows, _ = reserve
    _, bank = f.prepare_bank(rows, set())
    fingerprint = text_hash(EmailInput.model_validate(bank[0]["email"]))
    with pytest.raises(f.FinalError, match="candidate_development_overlap"):
        f.prepare_bank(rows, {fingerprint})


@pytest.mark.parametrize("dirty,committed", [(True, True), (False, False)])
def test_uncommitted_or_dirty_freeze_aborts(tmp_path, monkeypatch, dirty, committed):
    reference = tmp_path / "freeze.json"
    payload = json_bytes(
        {"protocol_sha256": f.PROTOCOL_SHA256, "code_and_references": {}, "preserved_inputs": {}}
    )
    reference.write_bytes(payload)

    def fake_run(command, **kwargs):
        return SimpleNamespace(
            stdout=(payload if committed else b"other")
            if command[1] == "show"
            else (b" M file" if dirty else b"")
        )

    monkeypatch.setattr(f.subprocess, "run", fake_run)
    with pytest.raises(f.FinalError, match="freeze_not_committed"):
        f.check_freeze(reference)


def test_changed_frozen_code_aborts(tmp_path, monkeypatch):
    code = tmp_path / "runner.py"
    code.write_bytes(b"changed")
    reference = tmp_path / "freeze.json"
    payload = json_bytes(
        {
            "protocol_sha256": f.PROTOCOL_SHA256,
            "code_and_references": {str(code): digest(b"original")},
            "preserved_inputs": {},
        }
    )
    reference.write_bytes(payload)
    monkeypatch.setattr(
        f.subprocess,
        "run",
        lambda cmd, **kw: SimpleNamespace(stdout=payload if cmd[1] == "show" else b""),
    )
    with pytest.raises(f.FinalError, match="code_or_reference_changed"):
        f.check_freeze(reference)


def test_gate_fails_before_model_or_reserve_read(tmp_path, monkeypatch):
    def fail():
        raise f.FinalError("not_committed")

    monkeypatch.setattr(f, "check_freeze", fail)
    monkeypatch.setattr(f, "load_models", lambda: pytest.fail("must not load models"))
    monkeypatch.setattr(f, "load_reserve", lambda: pytest.fail("must not read reserve"))
    with pytest.raises(f.FinalError, match="not_committed"):
        f.evaluate(tmp_path / "new")


def test_existing_output_refused_before_freeze_or_mail_read(tmp_path, monkeypatch):
    monkeypatch.setattr(f, "check_freeze", lambda: pytest.fail("must not start"))
    with pytest.raises(f.FinalError, match="output_already_exists"):
        f.evaluate(tmp_path)


def test_paired_group_interval_identical_decisions_is_zero(reserve):
    _, rows, _ = reserve
    scores = [0.0, 1.0, 0.0, 1.0]
    result = f.paired_defense_interval(rows, scores, scores)
    assert result["groups"] == 4
    assert all(v["lower"] == v["upper"] == 0 for v in result["intervals"].values())


def test_postscore_review_selection_does_not_change_scores():
    rows = [
        {
            "example_id": f"fixture-{i}",
            "label": "phishing",
            "clean_scores": dict.fromkeys(f.PROTOCOL["models"], 0.0),
            "candidates": [],
        }
        for i in range(7)
    ]
    before = copy.deepcopy(rows)
    selection = f.review_ids(rows)
    assert rows == before and len(selection["clean"]["finetuned/false_negative"]) == 2
    assert selection["attacks"] == []
    assert selection == f.review_ids(list(reversed(rows)))
