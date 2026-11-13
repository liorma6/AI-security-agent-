"""Offline perturbation, lineage, privacy and hand-counted budget/metric checks."""

import json
from types import SimpleNamespace

import pytest

from phishguard.cli import main
from phishguard.contracts import EmailInput
from phishguard.evasion import data
from phishguard.evasion.common import PROTOCOL, EvasionError
from phishguard.evasion.metrics import asr, asr_interval, selected, summarize
from phishguard.evasion.perturbations import PROTECTED, apply_edits, generate

BODY = (
    "please verify information immediately before completing the scheduled workshop report "
    "and contact the support team for assistance quickly when necessary. "
    "Never change https://example.invalid/account?token=abc123 or user@example.invalid "
    "or example.invalid or 2026-11-14 or <span data-token='private'> or &amp; or cannot."
)


@pytest.fixture
def example(corpus):
    return corpus["test"][0].model_copy(
        update={"email": EmailInput(subject="Do not change", body=BODY)}
    )


def test_determinism_unique_ids_and_lineage(example):
    before = example.model_dump_json()
    first = generate(example, "test")
    assert first == generate(example, "test") and first
    assert len({r["variant_id"] for r in first}) == len(first) <= 12
    assert len({r["variant_sha256"] for r in first}) == len(first)
    assert {r["operation"] for r in first} == set(PROTOCOL["operations"])
    for row in first:
        assert row["parent_id"] == example.example_id
        assert row["group_id"] == example.group_id and row["split"] == example.split
        assert row["label"] == example.label
    assert example.model_dump_json() == before


def test_replay_protected_spans_and_edit_limits(example):
    spans = PROTECTED.findall(example.email.body)
    for row in generate(example, "test"):
        changed = apply_edits(example.email, row["edits"])
        assert changed.model_dump() == row["email"]
        assert changed.subject == example.email.subject
        assert PROTECTED.findall(changed.body) == spans
        assert "cannot" in changed.body and "Never" in changed.body
        assert 1 <= row["changed_words"] <= 3
        assert row["changed_words"] <= row["body_words"] * 0.1
        assert all(e["end"] <= 1500 for e in row["edits"])
        for edit in row["edits"]:
            a, b = edit["before"], edit["after"]
            if row["operation"] == "duplicate_letter":
                assert len(b) == len(a) + 1 and a[0] == b[0] and a[-1] == b[-1]
            elif row["operation"] == "swap_letters":
                assert sorted(a) == sorted(b) and a != b
                assert a[0] == b[0] and a[-1] == b[-1]
            else:
                assert b == PROTOCOL["substitutions"][a]


@pytest.mark.parametrize("knobs", [{"max_edits": 0}, {"max_candidates": 0}])
def test_zero_budget_is_noop(example, knobs):
    assert generate(example, "test", **knobs) == []


@pytest.mark.parametrize(
    "knobs", [{"max_candidates": 13}, {"max_candidates": -1}, {"max_edits": 4}, {"max_edits": True}]
)
def test_invalid_budget_rejected(example, knobs):
    with pytest.raises(EvasionError, match="scope_or_budget"):
        generate(example, "test", **knobs)


def test_no_editable_text_and_empty_search(example):
    for body in ("Hi", "12345 " * 30, "https://example.invalid/account " * 12):
        row = example.model_copy(update={"email": EmailInput(body=body)})
        assert generate(row, "test") == []


def test_wrong_partition_rejected(example):
    with pytest.raises(EvasionError, match="scope_or_budget"):
        generate(example, "train")
    with pytest.raises(EvasionError, match="scope_or_budget"):
        generate(example, "reserve")


def test_prefix_and_character_cap_are_not_silently_truncated(example):
    row = example.model_copy(update={"email": EmailInput(body="x " * 760 + BODY)})
    assert generate(row, "test") == []
    body = ("completing " * 1818 + "x")[:19998].ljust(20000, "x")
    full = example.model_copy(update={"email": EmailInput(body=body)})
    variants = generate(full, "test")
    assert variants and all(v["operation"] != "duplicate_letter" for v in variants)
    assert all(len(v["email"]["body"]) == 20000 for v in variants)


@pytest.mark.parametrize(
    "edits",
    [
        [{"start": -1, "end": 3, "before": "bad", "after": "x"}],
        [{"start": 0, "end": 6, "before": "wrong", "after": "x"}],
        [
            {"start": 0, "end": 6, "before": "please", "after": "x"},
            {"start": 0, "end": 6, "before": "please", "after": "y"},
        ],
    ],
)
def test_invalid_edit_trace_rejected(example, edits):
    with pytest.raises(EvasionError, match="invalid_edit_trace"):
        apply_edits(example.email, edits)


def record(rid, label, clean, values):
    return {
        "example_id": rid,
        "group_id": rid,
        "source_id": "invented",
        "label": label,
        "clean_scores": {"a": clean, "b": clean},
        "candidates": [
            {
                "variant_id": f"{rid}-{i}",
                "operation": "swap_letters",
                "scores": {"a": score, "b": score},
            }
            for i, score in enumerate(values)
        ],
    }


def test_asr_eligibility_includes_no_candidate_and_excludes_existing_misses():
    rows = [
        record("p1", "phishing", 0.8, [0.7, 0.2]),
        record("p2", "phishing", 0.8, []),
        record("miss", "phishing", 0.1, [0.05]),
        record("legit", "legitimate", 0.1, [0.9]),
    ]
    result = summarize(rows, {"a": 0.5, "b": 0.5})
    a = result["models"]["a"]
    assert a["evasion"]["eligible_clean_detected_phishing"] == 2
    assert a["evasion"]["constraint_pass_successes"] == 1
    assert a["evasion"]["candidate_asr"] == 0.5
    assert a["evasion"]["coverage"] == 0.5
    assert a["actual_queries"] == 8 and a["maximum_queries_per_original"] == 3
    assert a["fixed_perturbation"]["confusion"] == {"tp": 2, "fn": 1, "fp": 1, "tn": 0}
    assert a["phishing_only_worst_of_budget"]["confusion"] == {"tp": 1, "fn": 2, "fp": 0, "tn": 1}
    assert selected(rows[-1], "a", 0.5) == (0.1, None)
    assert result["common_clean_detected_phishing"]["rows"] == 2


def test_asr_zero_denominator_and_missing_family():
    rows = [record("p", "phishing", 0.1, [])]
    assert asr(rows, "a", 0.5)["candidate_asr"] is None
    assert asr_interval(rows, "a", 0.5)["lower"] is None
    rows[0]["clean_scores"]["a"] = 0.9
    assert asr(rows, "a", 0.5, "substitute_word")["candidate_asr"] == 0


def test_ties_keep_original_and_common_eligibility_differs():
    row = record("p", "phishing", 0.8, [0.8])
    assert selected(row, "a", 0.5) == (0.8, None)
    row["clean_scores"]["b"] = 0.2
    result = summarize([row], {"a": 0.5, "b": 0.5})
    assert result["models"]["a"]["evasion"]["eligible_clean_detected_phishing"] == 1
    assert result["models"]["b"]["evasion"]["eligible_clean_detected_phishing"] == 0
    assert result["common_clean_detected_phishing"]["rows"] == 0


@pytest.fixture
def frozen(corpus, monkeypatch):
    cohorts = {
        split: [r.model_copy(update={"email": EmailInput(body=BODY)}) for r in rows]
        for split, rows in corpus.items()
    }
    cohorts["challenge"] = [
        r.model_copy(update={"example_id": "c-" + r.example_id, "group_id": "c-" + r.group_id})
        for r in cohorts["test"]
    ]
    calls = []

    def load(split):
        calls.append(split)
        return cohorts[split]

    monkeypatch.setattr(data, "study", lambda *args: SimpleNamespace(sha256="a" * 64, load=load))
    monkeypatch.setattr(data, "partition", lambda f, split: f.load(split))
    return calls


def test_preflight_reads_only_training_and_never_scores(frozen, tmp_path):
    report = data.preview(tmp_path, tmp_path, tmp_path / "preview")
    assert frozen == ["train"]
    assert report["sample_count"] == 12 and report["model_queries"] == 0
    assert all(r["split"] == "train" for r in report["samples"])
    assert "completing" not in json.dumps(report)


def test_bank_reproduction_and_tamper_detection(frozen, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    first = data.prepare(tmp_path, tmp_path, a)
    assert data.prepare(tmp_path, tmp_path, b) == first
    assert (a / "variants.jsonl").read_bytes() == (b / "variants.jsonl").read_bytes()
    data.verify(tmp_path, tmp_path, a, a / "manifest.json")
    assert set(frozen) == {"test", "challenge"}
    with pytest.raises(EvasionError, match="already_exists"):
        data.prepare(tmp_path, tmp_path, a)
    (a / "variants.jsonl").write_bytes(b"changed")
    with pytest.raises(EvasionError, match="content_mismatch"):
        data.verify(tmp_path, tmp_path, a, b / "manifest.json")
    (a / "manifest.json").write_bytes(b"{}")
    with pytest.raises(EvasionError, match="reference_mismatch"):
        data.verify(tmp_path, tmp_path, a, b / "manifest.json")


def test_cli_missing_input_does_not_echo_path_or_email(capsys, tmp_path):
    marker = "PRIVATE_EMAIL_MARKER"
    assert main(["evasion", "verify", "--dataset", str(tmp_path / marker)]) == 1
    captured = capsys.readouterr()
    assert marker not in captured.err + captured.out
    assert "evasion_input_or_runtime_error" in captured.err
