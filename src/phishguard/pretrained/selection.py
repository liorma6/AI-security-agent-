"""A digest-bound validation decision, separate from the external model weights."""

from pathlib import Path

from pydantic import ValidationError

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.model import Digest
from phishguard.contracts import LabelMapping, ModelArtifact, Record, Score, TokenizerReference
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.pretrained.source import (
    PROTOCOL,
    PROTOCOL_SHA256,
    SOURCE,
    SOURCE_SHA256,
    PretrainedError,
)


class Selection(Record):
    source_sha256: Digest
    protocol_sha256: Digest
    dataset_sha256: Digest
    baseline_revision: Digest
    threshold: Score
    validation_report_sha256: Digest


def save_selection(output: Path, selection: Selection, report: dict) -> None:
    if output.exists():
        raise PretrainedError("output_already_exists")
    payload = json_bytes(selection.model_dump())
    manifest = ModelArtifact(
        model_id=SOURCE["model_id"],
        model_revision=SOURCE["revision"],
        source=SOURCE["homepage"],
        artifact_sha256=digest(payload),
        preprocessing_version=PROTOCOL["preprocessing_version"],
        label_mapping=LabelMapping(**SOURCE["label_mapping"]),
        threshold=selection.threshold,
        tokenizer=TokenizerReference(name=SOURCE["model_id"], revision=SOURCE["revision"]),
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "validation-report.json").write_bytes(json_bytes(report))
    (output / "selection.json").write_bytes(payload)
    (output / "manifest.json").write_bytes(json_bytes(manifest.model_dump()))


def load_selection(directory: Path) -> Selection:
    try:
        manifest = ModelArtifact.model_validate(
            parse_json(read_bytes(directory / "manifest.json", 262144))
        )
        payload = read_bytes(directory / "selection.json", 262144)
        if digest(payload) != manifest.artifact_sha256:
            raise PretrainedError("selection_integrity_mismatch")
        selection = Selection.model_validate(parse_json(payload))
        if (
            selection.source_sha256 != SOURCE_SHA256
            or selection.protocol_sha256 != PROTOCOL_SHA256
            or manifest.model_id != SOURCE["model_id"]
            or manifest.model_revision != SOURCE["revision"]
            or manifest.source != SOURCE["homepage"]
            or manifest.threshold != selection.threshold
            or manifest.preprocessing_version != PROTOCOL["preprocessing_version"]
            or manifest.label_mapping.model_dump() != SOURCE["label_mapping"]
            or manifest.tokenizer
            != TokenizerReference(name=SOURCE["model_id"], revision=SOURCE["revision"])
            or digest(read_bytes(directory / "validation-report.json"))
            != selection.validation_report_sha256
        ):
            raise PretrainedError("selection_manifest_mismatch")
        return selection
    except ValidationError:
        raise PretrainedError("invalid_selection_artifact") from None
