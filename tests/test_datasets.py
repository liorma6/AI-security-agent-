"""Offline data-pipeline checks using invented messages, never the public corpus."""

import io
import json
import random
import urllib.error
from itertools import combinations

import pytest
from pydantic import ValidationError

from phishguard.cli import main
from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets import preparation, source, verification
from phishguard.datasets.grouping import canonical, related_components, template
from phishguard.datasets.preparation import (
    assign_splits,
    deduplicate,
    ingest,
    json_bytes,
    prepare_source,
)
from phishguard.datasets.source import SOURCE, DatasetError, digest, fetch_source
from phishguard.datasets.verification import validate_separation, verify_dataset


def example(rid="sample", body="A small invented message.", **kwargs):
    return EmailExample(
        example_id=rid,
        email=EmailInput(subject=kwargs.pop("subject", ""), body=body),
        label=kwargs.pop("label", "legitimate"),
        source_id=SOURCE["source_id"],
        source_revision=SOURCE["revision"],
        license=SOURCE["license"],
        group_id=kwargs.pop("group_id", "unassigned"),
        **kwargs,
    )


@pytest.fixture
def tiny_source(tmp_path, monkeypatch):
    rows = []
    for label in (0, 1):
        for index in range(30):
            # Disjoint vocabulary prevents incidental template grouping.
            tag = chr(97 + label) + chr(97 + index // 26) + chr(97 + index % 26)
            rows.append(
                {
                    "Subject": f"Fixture {tag}",
                    "Body": f"Invented {tag} message for testing.",
                    "type": label,
                    "Language": "en",
                }
            )
    payload = json_bytes(rows)
    metadata = {"bytes": len(payload), "sha256": digest(payload)}
    monkeypatch.setitem(SOURCE["files"], "ephishLLM.json", metadata)
    path = tmp_path / "source.json"
    path.write_bytes(payload)
    return path, tmp_path / "prepared"


def test_ingestion_preserves_unicode_and_filters_language():
    body = "  Caf\u00e9\n<markup> is inert.\n"
    rows = [
        {"Subject": "  Test  ", "Body": body, "type": 1, "Language": "en"},
        {"Subject": "Other", "Body": "Other language", "type": 0, "Language": "it"},
    ]
    records, report = ingest(rows)
    assert records[0].email.body == body
    assert records[0].email.subject == "  Test  "
    assert records[0].label == "phishing"
    assert records[0].split == "unassigned"
    assert report["ingestion_exclusions"] == [{"source_row": 1, "reason": "other_language"}]


@pytest.mark.parametrize(
    "change",
    [
        {"type": True},
        {"type": "1"},
        {"type": 2},
        {"Language": None},
        {"extra": "secret"},
        {"Body": "  "},
        {"Body": "x" * 20_001},
        {"Subject": None},
        {"Body": "bad\x00text"},
    ],
)
def test_invalid_rows_are_excluded_without_content(change):
    row = {"Subject": "private", "Body": "PRIVATE-MARKER", "type": 0, "Language": "en"}
    row.update(change)
    records, report = ingest([row])
    assert not records
    assert report["ingestion_exclusions"][0]["source_row"] == 0
    assert "PRIVATE-MARKER" not in json.dumps(report)


def test_non_list_source_is_rejected():
    with pytest.raises(DatasetError, match="invalid_source_shape"):
        ingest({})


def test_exact_duplicates_keep_lowest_id_without_changing_text():
    original = example("a", "Caf\u00e9   NEWS\n")
    duplicate = example("b", "cafe\u0301 news")
    retained, exclusions = deduplicate([duplicate, original])
    assert retained == [original]
    assert exclusions == [{"example_id": "b", "reason": "exact_duplicate", "retained_id": "a"}]


def test_conflicting_labels_quarantine_all_copies():
    records, exclusions = deduplicate(
        [
            example("a", "Identical text"),
            example("b", "IDENTICAL TEXT", label="phishing"),
            example("c", "A separate message"),
        ]
    )
    assert [r.example_id for r in records] == ["c"]
    assert len(exclusions) == 2
    assert {e["reason"] for e in exclusions} == {"conflicting_exact_labels"}


def test_subject_groups_even_different_labelled_bodies():
    records = [
        example("a", "First message", subject="Monthly project meeting invitation"),
        example(
            "b",
            "Unrelated content",
            subject="MONTHLY  project meeting invitation",
            label="phishing",
        ),
        example("c", "Third message", subject="Hi"),
        example("d", "Fourth message", subject="Hi"),
    ]
    assert related_components(records) == [["a", "b"], ["c"], ["d"]]


def test_template_links_are_masked_but_not_followed():
    left = "Please review our attached agenda for the next meeting at https://example.invalid/a 123"
    right = "Please review our attached agenda for the next meeting at https://other.invalid/b 456"
    assert related_components([example("a", left), example("b", right)]) == [["a", "b"]]
    assert "url" in template(left)
    assert template("Send to a@example.invalid <<private>> [attachment] 25") == (
        "send to email placeholder placeholder number"
    )


def test_near_duplicates_use_transitive_components():
    words = [f"token{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(100)]
    second, third = words.copy(), words.copy()
    second[20] = "replacement"
    third[20], third[60] = "replacement", "changed"
    records = [
        example("a", " ".join(words)),
        example("b", " ".join(second)),
        example("c", " ".join(third)),
    ]
    assert related_components(records) == [["a", "b", "c"]]


def test_prefix_search_matches_brute_force_jaccard():
    rng = random.Random(71)
    vocabulary = [f"word{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(200)]
    records = []
    for family in range(8):
        base = rng.sample(vocabulary, 80)
        for variant in range(6):
            words = base.copy()
            for position in rng.sample(range(80), variant):
                words[position] = rng.choice(vocabulary)
            records.append(example(f"f{family}v{variant}", " ".join(words)))
    sets = {}
    for r in records:
        words = template(r.email.body).split()
        sets[r.example_id] = {tuple(words[i : i + 3]) for i in range(len(words) - 2)}
    expected = [{r.example_id} for r in records]
    for a, b in combinations(sets, 2):
        if len(sets[a] & sets[b]) / len(sets[a] | sets[b]) >= 0.9:
            ga = next(g for g in expected if a in g)
            gb = next(g for g in expected if b in g)
            if ga is not gb:
                ga.update(gb)
                expected.remove(gb)
    assert sorted(map(sorted, expected)) == related_components(records)


def test_parent_lineage_is_grouped_and_cycles_rejected():
    assert related_components(
        [example("parent", "Original"), example("child", "Changed", parent_id="parent")]
    ) == [["child", "parent"]]
    with pytest.raises(DatasetError, match="missing_parent"):
        related_components([example(parent_id="absent")])
    with pytest.raises(DatasetError, match="cyclic_lineage"):
        related_components([example("a", parent_id="b"), example("b", parent_id="a")])
    with pytest.raises(ValidationError):
        example("a", parent_id="a")


def test_grouped_split_is_reproducible_and_order_independent(tiny_source):
    path, _ = tiny_source
    records, _ = ingest(json.loads(path.read_bytes()))
    first = assign_splits(records, 42)
    assert first == assign_splits(list(reversed(records)), 42)
    assert first != assign_splits(records, 43)
    validate_separation(first)
    for split, ratio in preparation.SPLITS.items():
        assert abs(sum(r.split == split for r in first) - len(first) * ratio) <= 1


@pytest.mark.parametrize("seed", [-1, 2**32, True])
def test_invalid_seed_rejected(seed):
    with pytest.raises(DatasetError, match="invalid_seed"):
        assign_splits([], seed)


def test_degenerate_corpus_rejected():
    with pytest.raises(DatasetError, match="insufficient_independent_groups"):
        assign_splits([example()])


@pytest.mark.parametrize(
    "case,code",
    [
        ("duplicate_id", "duplicate_example_id"),
        ("exact", "duplicate_text"),
        ("subject", "related_examples_in_different_groups"),
        ("parent", "related_examples_in_different_groups"),
        ("group", "group_crosses_splits"),
    ],
)
def test_split_leakage_is_rejected(case, code):
    first = example("a", "First body", group_id="g-a", split="train")
    second = example("b", "Second body", group_id="g-b", split="test")
    if case == "duplicate_id":
        second = second.model_copy(update={"example_id": "a"})
    if case == "exact":
        second = second.model_copy(update={"email": first.email})
    if case == "subject":
        first = first.model_copy(
            update={"email": EmailInput(subject="Shared project meeting", body="a")}
        )
        second = second.model_copy(
            update={"email": EmailInput(subject="Shared project meeting", body="b")}
        )
    if case == "parent":
        second = second.model_copy(update={"parent_id": "a"})
    if case == "group":
        second = second.model_copy(update={"group_id": "g-a"})
    with pytest.raises(DatasetError, match=code):
        validate_separation([first, second])


def test_prepare_verify_roundtrip_and_frozen_reference(tiny_source):
    path, output = tiny_source
    manifest = prepare_source(path, output)
    reference = output.parent / "frozen.json"
    reference.write_bytes(json_bytes(manifest))
    assert verify_dataset(output, reference)["rows"] == 60
    other = output.parent / "second"
    prepare_source(path, other)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {
        p.name: p.read_bytes() for p in other.iterdir()
    }
    assert "Invented" not in reference.read_text()
    with pytest.raises(DatasetError, match="output_already_exists"):
        prepare_source(path, output)
    reference.write_bytes(b"{}")
    with pytest.raises(DatasetError, match="frozen_manifest_mismatch"):
        verify_dataset(output, reference)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("bytes", "partition_integrity_mismatch"),
        ("group", "membership_mismatch"),
        ("counts", "partition_counts_mismatch"),
        ("paths", "manifest_contract_mismatch"),
        ("malformed", "invalid_dataset_artifact"),
        ("seed", "manifest_contract_mismatch"),
    ],
)
def test_artifact_tampering_detected(tiny_source, mutation, code):
    path, output = tiny_source
    manifest = prepare_source(path, output)
    if mutation == "bytes":
        with (output / "train.jsonl").open("ab") as stream:
            stream.write(b" ")
    elif mutation == "group":
        manifest["groups"][0]["members"].append("fake")
    elif mutation == "counts":
        manifest["partitions"]["train"]["rows"] += 1
    elif mutation == "paths":
        manifest["files"]["../private"] = manifest["files"].pop("train.jsonl")
    elif mutation == "seed":
        manifest["seed"] = True
    (output / "manifest.json").write_bytes(
        b"PRIVATE-MARKER" if mutation == "malformed" else json_bytes(manifest)
    )
    with pytest.raises(DatasetError, match=code):
        verify_dataset(output)


def test_data_cli_errors_are_private(tmp_path, capsys):
    assert (
        main(
            [
                "data",
                "prepare",
                "--source",
                str(tmp_path / "PRIVATE-PATH"),
                "--output",
                str(tmp_path / "new-output"),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["code"] == "dataset_io_error"
    assert "PRIVATE" not in captured.err


def test_data_cli_prepare_and_verify(tiny_source, capsys):
    path, output = tiny_source
    assert main(["data", "prepare", "--source", str(path), "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "prepared"
    assert main(["data", "verify", "--directory", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["rows"] == 60


def test_fetch_downloads_only_pinned_files_and_reuses_cache(tmp_path, monkeypatch):
    requested = []
    payloads = {name: name.encode() for name in SOURCE["files"]}
    for name, payload in payloads.items():
        monkeypatch.setitem(
            SOURCE["files"], name, {"bytes": len(payload), "sha256": digest(payload)}
        )

    def fake_open(request, timeout):
        requested.append(request.full_url)
        response = io.BytesIO(payloads[request.full_url.rsplit("/", 1)[-1]])
        response.url = "https://cdn.example.invalid/fixed-source"
        return response

    monkeypatch.setattr(source.urllib.request, "urlopen", fake_open)
    assert fetch_source(tmp_path)["status"] == "verified"
    fetch_source(tmp_path)
    assert len(requested) == 2
    assert all(f"/resolve/{SOURCE['revision']}/" in url for url in requested)
    (tmp_path / "ephishLLM.json").write_bytes(b"corrupt")
    with pytest.raises(DatasetError, match="source_integrity_mismatch"):
        fetch_source(tmp_path)
    assert len(requested) == 2


@pytest.mark.parametrize(
    "failure,code",
    [
        ("network", "source_download_failed"),
        ("checksum", "source_integrity_mismatch"),
        ("http", "insecure_source_redirect"),
    ],
)
def test_failed_fetch_does_not_install_source(tmp_path, monkeypatch, failure, code):
    def fake_open(*args, **kwargs):
        if failure == "network":
            raise urllib.error.URLError("PRIVATE-MARKER")
        response = io.BytesIO(b"PRIVATE-MARKER")
        response.url = "http://example.invalid" if failure == "http" else "https://example.invalid"
        return response

    monkeypatch.setattr(source.urllib.request, "urlopen", fake_open)
    with pytest.raises(DatasetError, match=code) as caught:
        fetch_source(tmp_path)
    assert "PRIVATE" not in str(caught.value)
    assert not list(tmp_path.iterdir())


def test_oversized_artifact_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(verification, "MAX_ARTIFACT_BYTES", 4)
    (tmp_path / "manifest.json").write_bytes(b"12345")
    with pytest.raises(DatasetError, match="artifact_too_large"):
        verify_dataset(tmp_path)


def test_source_checksum_failure_prevents_output(tiny_source):
    path, output = tiny_source
    path.write_bytes(b"PRIVATE-MARKER")
    with pytest.raises(DatasetError, match="source_integrity_mismatch"):
        prepare_source(path, output)
    assert not output.exists()


def test_canonical_does_not_change_input_object():
    record = example(body="  MiXeD\nText  ")
    assert canonical(record.email.body) == "mixed text"
    assert record.email.body == "  MiXeD\nText  "
