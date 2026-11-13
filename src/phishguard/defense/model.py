"""Independent defended artifact; never overwrite or reinterpret the parent model."""

from safetensors.torch import load_file, save_file
from transformers import BertForSequenceClassification

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.defense.common import MODEL_ID, PROTOCOL, PROTOCOL_SHA256, DefenseError
from phishguard.finetune.common import SOURCE, SOURCE_SHA256, STUDY
from phishguard.finetune.model import (
    Detector,
    configuration,
    runtime,
    tokenizer,
    validate_weights,
)
from phishguard.finetune.model import (
    load_detector as load_parent,
)
from phishguard.pretrained.source import verify_file


def snapshot(directory):
    return {
        name: digest(read_bytes(directory / name, 64 * 1024 * 1024))
        for name in (
            "model.safetensors",
            "config.json",
            "vocab.txt",
            "manifest.json",
            "selection.json",
        )
    }


def parent(directory, selection_reference):
    detector = load_parent(directory)
    selection_payload = read_bytes(selection_reference)
    selection = parse_json(selection_payload)
    if (
        detector.manifest["model_revision"] != PROTOCOL["parent_revision"]
        or detector.manifest["threshold"] != PROTOCOL["parent_threshold"]
        or read_bytes(directory / "selection.json") != selection_payload
        or selection["manifest_sha256"] != digest(read_bytes(directory / "manifest.json"))
    ):
        raise DefenseError("defense_parent_identity_mismatch")
    return detector


def save_detector(
    detector,
    parent_directory,
    output,
    threshold,
    epoch,
    fingerprints,
    augmentation_sha256,
    review_sha256,
):
    if output.exists():
        raise DefenseError("output_already_exists")
    output.mkdir(parents=True, exist_ok=False)
    save_file(
        {k: v.detach().cpu().contiguous() for k, v in detector.network.state_dict().items()},
        output / "model.safetensors",
        metadata={"format": "pt"},
    )
    (output / "vocab.txt").write_bytes(read_bytes(parent_directory / "vocab.txt"))
    (output / "config.json").write_bytes(json_bytes(configuration().to_dict()))
    manifest = {
        "version": "1.0",
        "model_id": MODEL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "source_sha256": SOURCE_SHA256,
        "dataset_sha256": STUDY["dataset_sha256"],
        "parent_revision": PROTOCOL["parent_revision"],
        "threshold": threshold,
        "selected_epoch": epoch,
        "augmentation_manifest_sha256": augmentation_sha256,
        "preflight_review_sha256": review_sha256,
        "development_text_hashes": sorted(set(fingerprints)),
        "files": {
            name: {
                "bytes": (output / name).stat().st_size,
                "sha256": digest(read_bytes(output / name, 64 * 1024 * 1024)),
            }
            for name in ("model.safetensors", "config.json", "vocab.txt")
        },
    }
    manifest["model_revision"] = digest(json_bytes(manifest))
    payload = json_bytes(manifest)
    (output / "manifest.json").write_bytes(payload)
    selection = {
        k: manifest[k]
        for k in (
            "model_revision",
            "threshold",
            "selected_epoch",
            "protocol_sha256",
            "dataset_sha256",
            "augmentation_manifest_sha256",
            "preflight_review_sha256",
            "parent_revision",
        )
    }
    selection["manifest_sha256"] = digest(payload)
    (output / "selection.json").write_bytes(json_bytes(selection))
    return manifest, selection


class DefendedDetector(Detector):
    def predict(self, email):
        result = super().predict(email)
        result["prediction"]["model_id"] = MODEL_ID
        return result


def load_detector(directory, selection_reference=None):
    payload = read_bytes(directory / "manifest.json", 2 * 1024 * 1024)
    manifest = parse_json(payload)
    core = {k: v for k, v in manifest.items() if k != "model_revision"}
    if (
        digest(json_bytes(core)) != manifest.get("model_revision")
        or manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or manifest.get("source_sha256") != SOURCE_SHA256
        or manifest.get("dataset_sha256") != STUDY["dataset_sha256"]
        or manifest.get("parent_revision") != PROTOCOL["parent_revision"]
        or manifest.get("model_id") != MODEL_ID
        or type(manifest.get("threshold")) not in (int, float)
        or not 0 <= manifest["threshold"] <= 1
        or set(manifest.get("files", {})) != {"model.safetensors", "config.json", "vocab.txt"}
    ):
        raise DefenseError("defended_manifest_mismatch")
    selected_payload = read_bytes(directory / "selection.json")
    selection = parse_json(selected_payload)
    keys = (
        "model_revision",
        "threshold",
        "selected_epoch",
        "protocol_sha256",
        "dataset_sha256",
        "augmentation_manifest_sha256",
        "preflight_review_sha256",
        "parent_revision",
    )
    if (
        selection.get("manifest_sha256") != digest(payload)
        or any(selection.get(k) != manifest[k] for k in keys)
        or (selection_reference is not None and selected_payload != read_bytes(selection_reference))
    ):
        raise DefenseError("defended_selection_mismatch")
    for name, meta in manifest["files"].items():
        if type(meta["bytes"]) is not int or not 0 < meta["bytes"] <= 64 * 1024 * 1024:
            raise DefenseError("defended_artifact_size_invalid")
        verify_file(directory / name, meta)
    if (
        parse_json(read_bytes(directory / "config.json"))
        != parse_json(json_bytes(configuration().to_dict()))
        or manifest["files"]["vocab.txt"] != SOURCE["files"]["vocab.txt"]
    ):
        raise DefenseError("defended_configuration_mismatch")
    with runtime():
        network = BertForSequenceClassification(configuration())
        weights = load_file(directory / "model.safetensors", device="cpu")
        validate_weights(weights, network.state_dict())
        network.load_state_dict(weights, strict=True)
        network.eval()
    return DefendedDetector(tokenizer(directory), network, manifest)
