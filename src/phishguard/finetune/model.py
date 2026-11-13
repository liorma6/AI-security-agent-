"""Local safetensors-only BERT initialization, inference and artifact validation."""

import random
import time
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version

import numpy as np
import torch
from safetensors.torch import load_file, save, save_file
from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import Prediction
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.finetune.common import (
    MODEL_ID,
    PROTOCOL,
    PROTOCOL_SHA256,
    SOURCE,
    SOURCE_SHA256,
    STUDY,
    STUDY_SHA256,
    FineTuneError,
    verify_source,
)
from phishguard.pretrained.source import verify_file

LABELS = {0: "legitimate", 1: "phishing"}


@contextmanager
def runtime(seed=None):
    for package, expected in PROTOCOL["runtime"].items():
        if version(package).split("+")[0] != expected:
            raise FineTuneError("finetuning_runtime_mismatch")
    threads = torch.get_num_threads()
    deterministic = torch.are_deterministic_algorithms_enabled()
    torch.set_num_threads(PROTOCOL["numeric_threads"])
    torch.use_deterministic_algorithms(True)
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    try:
        yield
    finally:
        torch.set_num_threads(threads)
        torch.use_deterministic_algorithms(deterministic)


def configuration():
    config = BertConfig(
        **SOURCE["configuration"],
        num_labels=2,
        id2label=LABELS,
        label2id={v: k for k, v in LABELS.items()},
    )
    config._attn_implementation = PROTOCOL["attention"]
    return config


def tokenizer(directory):
    return BertTokenizerFast(
        vocab_file=str(directory / "vocab.txt"),
        do_lower_case=True,
        model_max_length=SOURCE["configuration"]["max_position_embeddings"],
        padding_side="right",
        truncation_side="right",
    )


def tensor_digest(state):
    return digest(save({k: v.detach().cpu().contiguous() for k, v in state.items()}))


def initialize(directory):
    verify_source(directory)
    network = BertForSequenceClassification(configuration())
    weights = load_file(directory / "model.safetensors", device="cpu")
    encoder = {k.removeprefix("bert."): v for k, v in weights.items() if k.startswith("bert.")}
    discarded = set(weights) - {"bert." + k for k in encoder}
    allowed = {
        "cls.predictions.bias",
        "cls.predictions.transform.LayerNorm.bias",
        "cls.predictions.transform.LayerNorm.weight",
        "cls.predictions.transform.dense.bias",
        "cls.predictions.transform.dense.weight",
        "cls.seq_relationship.bias",
        "cls.seq_relationship.weight",
    }
    if discarded != allowed:
        raise FineTuneError("unexpected_source_heads")
    validate_weights(encoder, network.bert.state_dict())
    network.bert.load_state_dict(encoder, strict=True)
    return Detector(tokenizer(directory), network)


def validate_weights(weights, expected):
    if set(weights) != set(expected) or any(
        weights[k].shape != expected[k].shape
        or weights[k].dtype != torch.float32
        or not torch.isfinite(weights[k]).all().item()
        for k in expected
    ):
        raise FineTuneError("invalid_finetuned_weights")


@dataclass
class Detector:
    tokenizer: BertTokenizerFast
    network: BertForSequenceClassification
    manifest: dict | None = None

    def encode(self, emails):
        texts = [preprocess(email.text) for email in emails]
        counts = [
            len(ids)
            for ids in self.tokenizer(
                texts,
                truncation=False,
                padding=False,
                return_attention_mask=False,
                return_token_type_ids=False,
                verbose=False,
            )["input_ids"]
        ]
        encoded = self.tokenizer(
            texts, truncation=True, max_length=PROTOCOL["max_tokens"], padding=False, verbose=False
        )
        return [{k: encoded[k][i] for k in encoded} for i in range(len(texts))], counts

    def batch(self, encoded):
        return self.tokenizer.pad(encoded, padding=True, return_tensors="pt", verbose=False)

    def score_encoded(self, encoded, labels=None, progress=None):
        self.network.eval()
        scores, loss = [], 0.0
        with torch.inference_mode():
            for start in range(0, len(encoded), PROTOCOL["batch_size"]):
                batch = encoded[start : start + PROTOCOL["batch_size"]]
                logits = self.network(**self.batch(batch)).logits
                if logits.shape != (len(batch), 2) or not torch.isfinite(logits).all().item():
                    raise FineTuneError("invalid_finetuned_output")
                scores.extend(torch.softmax(logits, dim=-1)[:, 1].tolist())
                if labels is not None:
                    loss += torch.nn.functional.cross_entropy(
                        logits,
                        torch.tensor(labels[start : start + len(batch)], dtype=torch.long),
                        reduction="sum",
                    ).item()
                if progress:
                    progress({"status": "scoring", "rows": len(scores), "total": len(encoded)})
        return scores, loss / len(encoded) if labels is not None else None

    def score(self, emails, progress=None):
        started = time.perf_counter()
        with runtime():
            encoded, counts = self.encode(emails)
            scores, _ = self.score_encoded(encoded, progress=progress)
        return {
            "scores": scores,
            "token_counts": counts,
            "elapsed_seconds": time.perf_counter() - started,
        }

    def predict(self, email):
        result = self.score([email])
        threshold = self.manifest["threshold"]
        score = result["scores"][0]
        return {
            "prediction": Prediction(
                example_id="local-input",
                model_id=MODEL_ID,
                model_revision=self.manifest["model_revision"],
                score=score,
                threshold=threshold,
                label="phishing" if score >= threshold else "legitimate",
                elapsed_ms=result["elapsed_seconds"] * 1000,
            ).model_dump(),
            "input": {
                "original_tokens": result["token_counts"][0],
                "used_tokens": min(result["token_counts"][0], PROTOCOL["max_tokens"]),
                "truncated": result["token_counts"][0] > PROTOCOL["max_tokens"],
            },
        }


def token_report(counts):
    return {
        "rows": len(counts),
        "max_tokens": PROTOCOL["max_tokens"],
        "truncated_rows": sum(n > PROTOCOL["max_tokens"] for n in counts),
        "maximum_original_tokens": max(counts, default=0),
        "mean_original_tokens": sum(counts) / len(counts) if counts else None,
    }


def save_detector(detector, source_directory, output, threshold, epoch, fingerprints):
    if output.exists():
        raise FineTuneError("output_already_exists")
    output.mkdir(parents=True, exist_ok=False)
    save_file(
        {k: v.detach().cpu().contiguous() for k, v in detector.network.state_dict().items()},
        output / "model.safetensors",
        metadata={"format": "pt"},
    )
    (output / "vocab.txt").write_bytes((source_directory / "vocab.txt").read_bytes())
    (output / "config.json").write_bytes(json_bytes(configuration().to_dict()))
    files = {
        name: {
            "bytes": (output / name).stat().st_size,
            "sha256": digest((output / name).read_bytes()),
        }
        for name in ("model.safetensors", "config.json", "vocab.txt")
    }
    manifest = {
        "version": "1.0",
        "model_id": MODEL_ID,
        "source_sha256": SOURCE_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "study_sha256": STUDY_SHA256,
        "dataset_sha256": STUDY["dataset_sha256"],
        "source_revision": SOURCE["revision"],
        "threshold": threshold,
        "selected_epoch": epoch,
        "files": files,
        "development_text_hashes": sorted(set(fingerprints)),
    }
    manifest["model_revision"] = digest(json_bytes(manifest))
    payload = json_bytes(manifest)
    (output / "manifest.json").write_bytes(payload)
    selection = {
        "model_revision": manifest["model_revision"],
        "manifest_sha256": digest(payload),
        "threshold": threshold,
        "selected_epoch": epoch,
        "protocol_sha256": PROTOCOL_SHA256,
        "study_sha256": STUDY_SHA256,
        "dataset_sha256": STUDY["dataset_sha256"],
    }
    (output / "selection.json").write_bytes(json_bytes(selection))
    return manifest, selection


def load_detector(directory):
    manifest = parse_json(read_bytes(directory / "manifest.json", 1024 * 1024))
    core = {k: v for k, v in manifest.items() if k != "model_revision"}
    if (
        digest(json_bytes(core)) != manifest.get("model_revision")
        or manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or manifest.get("source_sha256") != SOURCE_SHA256
        or manifest.get("study_sha256") != STUDY_SHA256
        or manifest.get("dataset_sha256") != STUDY["dataset_sha256"]
        or manifest.get("source_revision") != SOURCE["revision"]
        or manifest.get("model_id") != MODEL_ID
        or type(manifest.get("threshold")) not in (int, float)
        or not 0 <= manifest["threshold"] <= 1
        or set(manifest.get("files", {})) != {"model.safetensors", "config.json", "vocab.txt"}
    ):
        raise FineTuneError("finetuned_manifest_mismatch")
    for name, meta in manifest["files"].items():
        if type(meta["bytes"]) is not int or not 0 < meta["bytes"] <= 64 * 1024 * 1024:
            raise FineTuneError("finetuned_artifact_size_invalid")
        verify_file(directory / name, meta)
    if (
        parse_json(read_bytes(directory / "config.json"))
        != parse_json(json_bytes(configuration().to_dict()))
        or manifest["files"]["vocab.txt"] != SOURCE["files"]["vocab.txt"]
    ):
        raise FineTuneError("finetuned_configuration_mismatch")
    with runtime():
        network = BertForSequenceClassification(configuration())
        weights = load_file(directory / "model.safetensors", device="cpu")
        validate_weights(weights, network.state_dict())
        network.load_state_dict(weights, strict=True)
        network.eval()
    return Detector(tokenizer(directory), network, manifest)
