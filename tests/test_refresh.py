"""Invented fixtures exercise data refresh boundaries independently of research outcomes."""

import csv
import io
import json
from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from phishguard.audit.common import AuditError
from phishguard.audit.data import cohort_stats
from phishguard.baseline.model import fit_baseline, save_model
from phishguard.cli import main
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import DatasetError, digest
from phishguard.refresh import common, data, runner, text


def example(rid, body, label="legitimate", group="unassigned", source="fixture"):
    return data.record(rid, EmailInput(body=body), label, source, "a" * 64, group)


@pytest.mark.parametrize(
    "placeholder",
    [
        "normal",
        "no-reply",
        "This is an HTML-only message. To view it, activate HTML in your email application.",
    ],
)
def test_placeholder_uses_valid_inert_alternative(placeholder):
    message = EmailMessage()
    message.set_content(placeholder)
    message.add_alternative(
        "<html><script>PRIVATE()</script><p>Please review your report today.</p></html>",
        subtype="html",
    )
    parsed, flags = text.extract(message.as_bytes())
    assert parsed.body == "Please review your report today."
    assert flags["placeholder_html_fallback"] and "PRIVATE" not in parsed.text


def test_normal_prose_and_unusable_alternative_preserve_original():
    for body in ("normal", "Please explain <html> tags in this code review."):
        message = EmailMessage()
        message.set_content(body)
        message.add_alternative("<script>PRIVATE()</script>", subtype="html")
        parsed, flags = text.extract(message.as_bytes())
        assert parsed.body == body + "\n" and not flags["placeholder_html_fallback"]


def test_plain_html_removes_markup_without_fetching_urls():
    original = EmailInput(
        body='<BODY><script>PRIVATE()</script><p>Read the project report.</p><img src="https://never.invalid"></BODY>'
    )
    parsed, changed = text.clean_text(original)
    assert changed and parsed.body == "Read the project report."
    assert original.body.startswith("<BODY>")


def test_html_attachment_is_not_a_fallback():
    message = EmailMessage()
    message.set_content("normal")
    message.add_attachment(
        "<p>PRIVATE attachment content here</p>", subtype="html", filename="message.html"
    )
    parsed, flags = text.extract(message.as_bytes())
    assert parsed.body == "normal\n" and not flags["placeholder_html_fallback"]


def test_meajor_accepts_only_publisher_ham_and_english(tmp_path, monkeypatch):
    name = "meajor_cleaned_preprocessed.csv"
    with (tmp_path / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["source", "label", "language", "subject", "body"]
        )
        writer.writeheader()
        for source, label, language, body in [
            ("trec5", "0.0", "en;en", "Review our ordinary meeting report"),
            ("trec5", "1.0", "en", "General spam is not phishing"),
            ("unknown", "0.0", "en", "Unknown provenance"),
            ("trec6", "0.0", "fr;en", "Mixed language text"),
        ]:
            writer.writerow(
                dict(source=source, label=label, language=language, subject="", body=body)
            )
    payload = (tmp_path / name).read_bytes()
    monkeypatch.setitem(
        common.SOURCE["files"], name, {"bytes": len(payload), "sha256": digest(payload)}
    )
    monkeypatch.setattr(data, "english", lambda email: True)
    rows, counts = data.meajor(tmp_path)
    assert len(rows) == 1 and rows[0].label == "legitimate"
    assert counts["non_ham_or_unknown_source"] == 2 and counts["publisher_not_english"] == 1


def test_source_stream_hash_detects_truncation_and_excess(tmp_path):
    path = tmp_path / "file"
    for payload in (b"abc", b"abcdefg", b"XXXXXX"):
        path.write_bytes(payload)
        with pytest.raises(AuditError, match="integrity_mismatch"):
            common.verify_file(path, {"bytes": 6, "sha256": digest(b"abcdef")})


def test_fetch_preserves_existing_partial(tmp_path, monkeypatch):
    monkeypatch.setitem(
        common.SOURCE,
        "files",
        {"file": {"url": "https://fixture.invalid/file", "bytes": 3, "sha256": digest(b"abc")}},
    )
    (tmp_path / "file.partial").write_bytes(b"owned elsewhere")
    with pytest.raises(AuditError, match="partial_already_exists"):
        common.fetch(tmp_path)
    assert (tmp_path / "file.partial").read_bytes() == b"owned elsewhere"


@pytest.mark.parametrize("case", ["valid", "digest", "oversize", "redirect"])
def test_streamed_fetch_validates_before_commit(tmp_path, monkeypatch, case):
    payload = b"abc" if case in {"valid", "redirect"} else b"XXX" if case == "digest" else b"abcd"
    monkeypatch.setitem(
        common.SOURCE,
        "files",
        {"file": {"url": "https://fixture.invalid/file", "bytes": 3, "sha256": digest(b"abc")}},
    )
    response = io.BytesIO(payload)
    response.url = (
        "http://insecure.invalid" if case == "redirect" else "https://fixture.invalid/file"
    )
    opener = SimpleNamespace(open=Mock(return_value=response))
    monkeypatch.setattr(common.urllib.request, "build_opener", Mock(return_value=opener))
    if case == "valid":
        common.fetch(tmp_path)
        common.fetch(tmp_path)
        assert opener.open.call_count == 1 and (tmp_path / "file").read_bytes() == b"abc"
    else:
        with pytest.raises(AuditError):
            common.fetch(tmp_path)
        assert not (tmp_path / "file").exists() and not (tmp_path / "file.partial").exists()


def test_known_families_unite_transitively_with_text_relatives():
    rows = [
        example("a", "A completely unrelated sentence.", group="template-one"),
        example(
            "b", "Another message with enough identical body characters.", group="template-one"
        ),
        example("c", "Another message with enough identical body characters."),
    ]
    assert data.components(rows) == [["a", "b", "c"]]


@pytest.fixture
def prepared_refresh(corpus, tmp_path, monkeypatch):
    protected = [example("protected", "Protected body content here", group="reserve-family")]
    internal = SimpleNamespace(
        sha256=common.PROTOCOL["internal_manifest_sha256"],
        load=lambda split: protected if split == "test" else [],
    )
    monkeypatch.setattr(data, "FrozenDataset", lambda *args: internal)
    audit = [
        example(
            "audit-" + str(i),
            "Distinct inspected text " + chr(97 + i),
            label="phishing" if i % 2 else "legitimate",
            source="old",
        )
        for i in range(10)
    ]
    new = []
    for label in ("legitimate", "phishing"):
        for i in range(20):
            rid = label + "-" + str(i)
            new.append(
                example(
                    rid,
                    f"{label} sample alphabet {chr(65 + i)} unique",
                    label=label,
                    source="new-" + label,
                )
            )
    # A known reserve family must be excluded even without textual similarity.
    new.append(example("must-exclude", "Completely different topic", group="reserve-family"))
    holdout = [
        example("challenge-l", "A separate calendar event", group="zenodo-template-safe"),
        example(
            "challenge-p",
            "Provide your secret credential immediately",
            label="phishing",
            group="zenodo-template-phish",
        ),
    ]
    monkeypatch.setattr(data, "old_audit", lambda *args: (audit, [], [], {}))
    monkeypatch.setattr(
        data, "meajor", lambda *args: ([r for r in new if r.label == "legitimate"], {})
    )
    monkeypatch.setattr(
        data, "nazario", lambda *args: ([r for r in new if r.label == "phishing"], {})
    )
    monkeypatch.setattr(
        data, "challenge", lambda *args: (holdout, {r.example_id: "generated_v3" for r in holdout})
    )
    output = tmp_path / "prepared"
    manifest = data.prepare(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, output)
    reference = tmp_path / "reference.json"
    reference.write_bytes((output / "manifest.json").read_bytes())
    return output, reference, manifest


def test_prepare_protects_known_groups_and_inspected_audit(prepared_refresh):
    directory, reference, manifest = prepared_refresh
    study = data.FrozenStudy(directory, reference)
    assert manifest["exclusion_counts"]["related_to_protected_corpus"] == 1
    assert not any(r.example_id.startswith("audit") for r in study.load("test"))
    assert all(r.example_id.startswith("challenge") for r in study.load("challenge"))
    ids = [
        r.example_id for s in ("train", "validation", "test", "challenge") for r in study.load(s)
    ]
    assert len(set(ids)) == len(ids) and "must-exclude" not in ids


def test_refresh_files_are_individually_verified(prepared_refresh):
    directory, reference, _ = prepared_refresh
    (directory / "test.jsonl").write_bytes(b"PRIVATE text")
    study = data.FrozenStudy(directory, reference)
    assert study.load("train")
    with pytest.raises(DatasetError, match="integrity_mismatch"):
        study.load("test")


def freeze_corpus(corpus, tmp_path):
    directory = tmp_path / "study"
    directory.mkdir()
    partitions = {
        **corpus,
        "challenge": [
            example("challenge-a", "Please review your project agenda", group="ca"),
            example(
                "challenge-b", "Urgent password confirmation needed", label="phishing", group="cb"
            ),
        ],
    }
    manifest = {
        "protocol": common.PROTOCOL,
        "protocol_sha256": common.PROTOCOL_SHA256,
        "source": common.SOURCE,
        "source_sha256": common.SOURCE_SHA256,
        "groups": [],
        "partitions": {},
        "files": {},
    }
    for split, rows in partitions.items():
        rows = [
            r.model_copy(update={"split": "test" if split == "challenge" else split}) for r in rows
        ]
        payload = b"".join((r.model_dump_json() + "\n").encode() for r in rows)
        name = split + ".jsonl"
        (directory / name).write_bytes(payload)
        manifest["files"][name] = {"bytes": len(payload), "sha256": digest(payload)}
        manifest["partitions"][split] = cohort_stats(rows)
        manifest["groups"].extend(
            {"group_id": r.group_id, "members": [r.example_id], "split": split} for r in rows
        )
    reference = tmp_path / "reference.json"
    reference.write_bytes(json_bytes(manifest))
    (directory / "manifest.json").write_bytes(reference.read_bytes())
    return directory, reference


def test_train_never_opens_test_challenge_or_reserve(corpus, tmp_path):
    directory, reference = freeze_corpus(corpus, tmp_path)
    (directory / "test.jsonl").unlink()
    (directory / "challenge.jsonl").unlink()
    report = runner.train(directory, reference, tmp_path / "model")
    assert (
        report["test_rows_used"]
        == report["challenge_rows_used"]
        == report["reserve_rows_scored"]
        == 0
    )
    assert (tmp_path / "model/selection.json").exists()


@pytest.mark.parametrize("tamper", [False, True])
def test_evaluation_uses_only_heldout_and_exact_frozen_selection(
    corpus, tmp_path, monkeypatch, tamper
):
    old, _ = fit_baseline(
        corpus["train"], corpus["validation"], common.PROTOCOL["internal_manifest_sha256"]
    )
    save_model(old, tmp_path / "old")
    monkeypatch.setitem(common.PROTOCOL, "old_model_revision", old.revision)
    directory, reference = freeze_corpus(corpus, tmp_path)
    runner.train(directory, reference, tmp_path / "model")
    selection = tmp_path / "selection.json"
    selection.write_bytes(
        (tmp_path / "model/selection.json").read_bytes() + (b" " if tamper else b"")
    )
    (directory / "train.jsonl").unlink()
    (directory / "validation.jsonl").unlink()
    monkeypatch.setattr(runner, "fit_baseline", Mock(side_effect=AssertionError("No fitting")))
    if tamper:
        with pytest.raises(AuditError, match="selection_reference_mismatch"):
            runner.evaluate(
                directory,
                reference,
                tmp_path / "model",
                tmp_path / "old",
                selection,
                tmp_path / "evaluation",
            )
    else:
        report = runner.evaluate(
            directory,
            reference,
            tmp_path / "model",
            tmp_path / "old",
            selection,
            tmp_path / "evaluation",
        )
        assert report["reserve_rows_scored"] == 0
        for cohort in report["cohorts"].values():
            assert sum(cohort["paired_correctness"].values()) == cohort["rows"]


def test_refresh_cli_does_not_echo_exception_contents(tmp_path, monkeypatch, capsys):
    from phishguard.refresh import cli

    monkeypatch.setattr(cli, "train", Mock(side_effect=KeyError("PRIVATE email text")))
    assert main(["refresh", "train", "--output", str(tmp_path / "output")]) == 1
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.err + captured.out
    assert json.loads(captured.err)["code"] == "refresh_input_or_io_error"
