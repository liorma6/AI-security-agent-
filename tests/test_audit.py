"""Invented email archives verify external preparation and frozen evaluation boundaries."""

import io
import json
import random
import ssl
import tarfile
from email.message import EmailMessage
from itertools import combinations
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from phishguard.audit import common, data, mime, runner
from phishguard.audit.common import AuditError
from phishguard.audit.similarity import relations
from phishguard.baseline.common import BaselineError
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.model import fit_baseline, save_model
from phishguard.cli import main
from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets.grouping import template
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import DatasetError, digest


def email_bytes(body="An invented project message for this unit test.", subject="Meeting"):
    message = EmailMessage()
    message["Subject"] = subject
    message["X-Spam-Status"] = "PRIVATE-MARKER"
    message.set_content(body)
    return message


def test_mime_prefers_plain_text_and_never_reads_attachment():
    message = email_bytes()
    message.add_alternative("<p>Other representation</p>", subtype="html")
    message.add_attachment(
        b"PRIVATE-ATTACHMENT",
        maintype="application",
        subtype="octet-stream",
        filename="payload.exe",
    )
    parsed, diagnostics = mime.extract(message.as_bytes())
    assert parsed.subject == "Meeting" and "invented project" in parsed.body
    assert "PRIVATE" not in parsed.text and not diagnostics["html_body"]


def test_html_is_inert_text_and_subject_flags_removed():
    message = email_bytes(
        """<html><head><title>SECRET</title></head><body>
        <script>SECRET_NETWORK()</script><style>SECRET_CSS</style><!--SECRET-->
        <p>Review <a href="https://never-follow.invalid">the report</a>.</p>
        <img src="https://never-fetch.invalid/pixel"></body></html>""",
        "[SPAM] [PHISHING] Review",
    )
    message.replace_header("Content-Type", 'text/html; charset="utf-8"')
    parsed, diagnostics = mime.extract(message.as_bytes())
    assert parsed.subject == "Review" and "the report" in parsed.body
    assert "SECRET" not in parsed.body and "https://" not in parsed.body
    assert diagnostics["html_body"] and diagnostics["subject_flag_removed"]


@pytest.mark.parametrize(
    "kind,code",
    [
        ("large", "raw_message_too_large"),
        ("system", "mailbox_system_record"),
        ("binary", "no_inline_text"),
        ("long", "invalid_or_overlong_email"),
        ("bad_encoding", "undecodable_text"),
    ],
)
def test_unusable_messages_are_counted_not_silently_truncated(kind, code):
    message = email_bytes()
    if kind == "system":
        message.replace_header("Subject", "DON'T DELETE THIS MESSAGE -- FOLDER INTERNAL DATA")
    if kind == "binary":
        message = EmailMessage()
        message.set_content(b"secret", maintype="application", subtype="octet-stream")
    if kind == "long":
        message.set_content("long text " * 3000)
    payload = message.as_bytes()
    if kind == "large":
        payload = b"x" * (common.PROTOCOL["raw_message_bytes"] + 1)
    if kind == "bad_encoding":
        payload = b"Subject: Broken\nContent-Type: text/plain; charset=utf-8\n\n\xff\xfe"
    with pytest.raises(AuditError, match=code):
        mime.extract(payload)


def test_language_filter_is_repeatable_and_does_not_learn():
    english = EmailInput(
        body="Please review the report for our upcoming project meeting. Thank you for your help."
    )
    french = EmailInput(
        body=(
            "Bonjour, voici le compte rendu de notre reunion. "
            "Merci de lire ce document et de me donner votre avis."
        )
    )
    assert mime.english(english) is True
    assert mime.english(english) is True
    assert mime.english(french) is False


def archive_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:bz2") as archive:
        for name, payload, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(payload) if kind == tarfile.REGTYPE else 0
            archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../0001." + "a" * 32, tarfile.REGTYPE),
        ("/0001." + "a" * 32, tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
    ],
)
def test_archive_paths_and_links_never_extracted(tmp_path, name, kind):
    path = tmp_path / "archive.bz2"
    path.write_bytes(archive_bytes([(name, b"invented", kind)]))
    with pytest.raises(AuditError, match="unsafe_archive_member"):
        list(mime.messages(path, "tar-bz2"))
    assert list(tmp_path.iterdir()) == [path]


def row(rid, body, label="legitimate", source="fixture", subject=""):
    return EmailExample(
        example_id=rid,
        email=EmailInput(subject=subject, body=body),
        label=label,
        source_id=source,
        source_revision="a" * 64,
        license="invented fixture",
        group_id="unassigned",
    )


def test_similarity_index_matches_bruteforce_at_broader_threshold():
    rng = random.Random(42)
    base = ["word" + chr(97 + i) for i in range(24)]
    rows = []
    for i in range(30):
        words = base.copy()
        for _ in range(i % 8):
            words[rng.randrange(len(words))] = "unique" + chr(97 + i)
        rows.append(row(f"r{i}", " ".join(words)))
    _, edges = relations(rows, 0.7)
    actual = {frozenset((a, b)) for a, b, reason, _ in edges if reason == "near_body"}

    def shingles(record):
        words = template(record.email.body).split()
        return set(zip(words, words[1:], words[2:], strict=False))

    expected = {
        frozenset((a.example_id, b.example_id))
        for a, b in combinations(rows, 2)
        if len(shingles(a) & shingles(b)) / len(shingles(a) | shingles(b)) >= 0.7
    }
    assert actual == expected


def test_transitive_relatives_cannot_cross_audit_reserve():
    rows = [
        row("a", "Shared body text long enough to identify a duplicate."),
        row(
            "b",
            "Shared body text long enough to identify a duplicate.",
            subject="Common subject line",
        ),
        row("c", "A different body entirely", subject="Re: Common subject line"),
    ]
    groups, _ = relations(rows)
    assert groups == [["a", "b", "c"]]


@pytest.fixture
def external_fixture(tmp_path, monkeypatch, prepared):
    internal, reference = prepared
    monkeypatch.setitem(common.PROTOCOL, "internal_manifest_sha256", digest(reference.read_bytes()))
    monkeypatch.setattr(data, "english", lambda _: True)
    cache = tmp_path / "cache"
    cache.mkdir()
    sources = {}
    for label in ("legitimate", "phishing"):
        entries = []
        for i in range(6):
            body = (
                ("agenda workshop" if label == "legitimate" else "verify password urgent")
                + " external"
                + chr(97 + i)
            )
            payload = email_bytes(body, subject=label + chr(97 + i)).as_bytes()
            entries.append((f"mail/{i:04d}." + f"{i:032x}", payload, tarfile.REGTYPE))
        raw = archive_bytes(entries)
        name = label + ".tar.bz2"
        (cache / name).write_bytes(raw)
        sources[name] = {
            "kind": "tar-bz2",
            "label": label,
            "source_id": label,
            "license": "invented fixture",
            "sha256": digest(raw),
            "bytes": len(raw),
        }
    monkeypatch.setitem(common.SOURCE, "files", sources)
    output = tmp_path / "external"
    manifest = data.prepare(cache, internal, reference, output)
    frozen = tmp_path / "external-reference.json"
    frozen.write_bytes((output / "manifest.json").read_bytes())
    return output, frozen, manifest


def test_preparation_reserve_is_separate_and_reproducible(external_fixture, tmp_path):
    output, reference, manifest = external_fixture
    rows, _, _ = data.load_audit(output, reference)
    assert manifest["reserve_scored"] is False and manifest["partitions"]["reserve"]["rows"] > 0
    audit_groups = {r.group_id for r in rows}
    reserve = [
        EmailExample.model_validate_json(line)
        for line in (output / "reserve.jsonl").read_bytes().splitlines()
    ]
    assert not audit_groups & {r.group_id for r in reserve}
    all_rows = rows + reserve
    groups = [g["members"] for g in manifest["groups"]]
    original, _ = data.partition(all_rows, groups)
    repeated, _ = data.partition(list(reversed(all_rows)), list(reversed(groups)))
    assert original == repeated
    (output / "reserve.jsonl").unlink()
    assert data.load_audit(output, reference)[0] == rows


def test_external_evaluation_does_not_fit_or_open_reserve(
    external_fixture, corpus, tmp_path, monkeypatch
):
    output, reference, manifest = external_fixture
    model, _ = fit_baseline(
        corpus["train"], corpus["validation"], common.PROTOCOL["internal_manifest_sha256"]
    )
    path = tmp_path / "model"
    save_model(model, path)
    monkeypatch.setitem(common.PROTOCOL, "baseline_revision", model.revision)
    monkeypatch.setitem(common.PROTOCOL, "baseline_threshold", model.state.threshold)
    # Fixture manifest must describe the exact test protocol after fixture model binding.
    manifest["protocol"] = common.PROTOCOL
    reference.write_bytes(json_bytes(manifest))
    (output / "manifest.json").write_bytes(reference.read_bytes())
    (output / "reserve.jsonl").unlink()
    from sklearn.linear_model import LogisticRegression

    def no_fit(*args, **kwargs):
        raise AssertionError("Frozen audit must not train")

    monkeypatch.setattr(LogisticRegression, "fit", no_fit)
    before = (path / "model.json").read_bytes()
    report = runner.evaluate_external(output, reference, path, tmp_path / "result")
    assert report["reserve_rows_scored"] == 0 and report["weights_updated"] is False
    assert before == (path / "model.json").read_bytes()
    predictions = [
        json.loads(line)
        for line in (tmp_path / "result/predictions.jsonl").read_bytes().splitlines()
    ]
    assert report["metrics"]["accuracy"] == sum(
        r["label"] == r["decision"] for r in predictions
    ) / len(predictions)
    assert all("body" not in r and "subject" not in r for r in predictions)
    with pytest.raises(AuditError, match="output_already_exists"):
        runner.evaluate_external(output, reference, path, tmp_path / "result")


def test_wrong_model_is_rejected_before_external_files(tmp_path):
    with pytest.raises(BaselineError, match="artifact_missing"):
        runner.evaluate_external(tmp_path, tmp_path, tmp_path / "absent", tmp_path / "result")


def test_corrupt_external_partition_is_rejected(external_fixture):
    output, reference, _ = external_fixture
    (output / "audit.jsonl").write_bytes(b"PRIVATE-MARKER")
    with pytest.raises(DatasetError, match="source_integrity_mismatch"):
        data.load_audit(output, reference)


def test_group_bootstrap_repeatable_and_perfect_case():
    rows = [
        row(f"r{i}", f"Invented text {i}", label="phishing" if i % 2 else "legitimate").model_copy(
            update={"group_id": f"g{i}"}
        )
        for i in range(20)
    ]
    scores = [float(i % 2) for i in range(20)]
    result = runner.intervals(rows, scores, 0.5)
    assert result == runner.intervals(rows, scores, 0.5)
    assert result["intervals"]["accuracy"]["lower"] == 1
    assert result["intervals"]["false_positive_rate"]["upper"] == 0


def test_audit_cli_redacts_input_failures(tmp_path, capsys):
    assert (
        main(
            [
                "audit",
                "evaluate",
                "--model",
                str(tmp_path / "PRIVATE-MARKER"),
                "--output",
                str(tmp_path / "result"),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "PRIVATE" not in captured.out + captured.err
    assert json.loads(captured.err)["code"] == "artifact_missing"


def test_prepare_excludes_relatives_of_every_internal_split(external_fixture, prepared, tmp_path):
    internal, reference = prepared
    dataset = FrozenDataset(internal, reference)
    entries = []
    for i, split in enumerate(("train", "validation", "test")):
        original = dataset.load(split)[0]
        payload = email_bytes(original.email.body, original.email.subject or "").as_bytes()
        entries.append((f"{i:04d}." + "b" * 32, payload, tarfile.REGTYPE))
    raw = archive_bytes(entries)
    name = "overlap.tar.bz2"
    (tmp_path / "cache" / name).write_bytes(raw)
    common.SOURCE["files"][name] = {
        "kind": "tar-bz2",
        "label": "phishing",
        "source_id": "overlap",
        "license": "invented fixture",
        "sha256": digest(raw),
        "bytes": len(raw),
    }
    manifest = data.prepare(tmp_path / "cache", internal, reference, tmp_path / "overlap")
    assert manifest["exclusion_counts"]["related_to_internal_corpus"] == 3
    assert not any(
        rid.startswith("external-overlap")
        for group in manifest["groups"]
        for rid in group["members"]
    )


@pytest.mark.parametrize(
    "field,value", [("baseline_revision", "0" * 64), ("baseline_threshold", 0.123)]
)
def test_frozen_model_identity_and_threshold_are_enforced(
    corpus, tmp_path, monkeypatch, field, value
):
    model, _ = fit_baseline(corpus["train"], corpus["validation"], "a" * 64)
    path = tmp_path / "model"
    save_model(model, path)
    monkeypatch.setitem(common.PROTOCOL, "baseline_revision", model.revision)
    monkeypatch.setitem(common.PROTOCOL, "baseline_threshold", model.state.threshold)
    monkeypatch.setitem(common.PROTOCOL, "internal_manifest_sha256", "a" * 64)
    monkeypatch.setitem(common.PROTOCOL, field, value)
    with pytest.raises(AuditError, match="frozen_baseline_mismatch"):
        runner.evaluate_external(
            tmp_path / "absent", tmp_path / "absent", path, tmp_path / "result"
        )


@pytest.mark.parametrize("case", ["valid", "digest", "oversize", "redirect"])
def test_verified_fetch_is_bounded_and_preserves_tls_validation(tmp_path, monkeypatch, case):
    payload = b"invented archive"
    metadata = {
        "bytes": len(payload),
        "sha256": digest(payload),
        "url": "https://publisher.invalid/file",
    }
    monkeypatch.setitem(common.SOURCE, "files", {"archive": metadata})
    received = (
        payload
        if case not in {"digest", "oversize"}
        else b"X" * (len(payload) + (case == "oversize"))
    )
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = received
    response.url = "http://insecure.invalid" if case == "redirect" else metadata["url"]
    opener = SimpleNamespace(open=Mock(return_value=response))
    build = Mock(return_value=opener)
    monkeypatch.setattr(common.urllib.request, "build_opener", build)
    if case == "valid":
        assert common.fetch(tmp_path)["status"] == "verified"
        common.fetch(tmp_path)
        assert opener.open.call_count == 1  # Verified cache, no second download.
    else:
        with pytest.raises(
            AuditError,
            match=(
                "insecure_source_redirect"
                if case == "redirect"
                else "external_source_integrity_mismatch"
            ),
        ):
            common.fetch(tmp_path)
        assert not (tmp_path / "archive").exists()
    context = build.call_args.args[1]._context
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    if case != "redirect":
        response.read.assert_called_once_with(len(payload) + 1)
