"""Local-only, explicitly mapped, bounded CPU inference on reviewed safetensors."""

import time
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import torch
from transformers import BertTokenizerFast, DistilBertConfig, DistilBertForSequenceClassification

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import EmailInput, Prediction
from phishguard.pretrained.source import PROTOCOL, SOURCE, PretrainedError, verify_source


def phishing_index(id2label: dict) -> int:
    if (
        not isinstance(id2label, dict)
        or len(id2label) != 2
        or any(type(key) not in (str, int) for key in id2label)
        or any(not isinstance(value, str) for value in id2label.values())
    ):
        raise PretrainedError("incompatible_label_mapping")
    normalized = {str(key): value for key, value in id2label.items()}
    if set(normalized) != {"0", "1"} or set(normalized.values()) != {
        "SAVE EMAIL",
        "PHISHING EMAIL",
    }:
        raise PretrainedError("incompatible_label_mapping")
    return next(int(key) for key, value in normalized.items() if value == "PHISHING EMAIL")


def phishing_scores(logits: torch.Tensor, id2label: dict) -> list[float]:
    index = phishing_index(id2label)
    if logits.ndim != 2 or logits.shape[1] != 2 or not torch.isfinite(logits).all().item():
        raise PretrainedError("invalid_model_output")
    return torch.softmax(logits, dim=-1)[:, index].tolist()


@dataclass
class ScoredBatch:
    scores: list[float]
    token_counts: list[int]
    elapsed_seconds: float

    def token_report(self) -> dict:
        return {
            "max_tokens": PROTOCOL["max_tokens"],
            "rows": len(self.token_counts),
            "truncated_rows": sum(n > PROTOCOL["max_tokens"] for n in self.token_counts),
            "maximum_original_tokens": max(self.token_counts, default=0),
            "mean_original_tokens": sum(self.token_counts) / len(self.token_counts)
            if self.token_counts
            else None,
        }


@dataclass
class PretrainedClassifier:
    tokenizer: BertTokenizerFast
    network: DistilBertForSequenceClassification

    def score(self, emails: list[EmailInput], progress=None) -> ScoredBatch:
        started = time.perf_counter()
        scores, counts = [], []
        self.network.eval()
        old_threads = torch.get_num_threads()
        torch.set_num_threads(PROTOCOL["numeric_threads"])
        try:
            with torch.inference_mode():
                for start in range(0, len(emails), PROTOCOL["batch_size"]):
                    batch = emails[start : start + PROTOCOL["batch_size"]]
                    text = [preprocess(email.text) for email in batch]
                    unbounded = self.tokenizer(
                        text,
                        padding=False,
                        truncation=False,
                        return_attention_mask=False,
                        return_token_type_ids=False,
                        verbose=False,
                    )
                    counts.extend(len(ids) for ids in unbounded["input_ids"])
                    encoded = self.tokenizer(
                        text,
                        padding=True,
                        truncation=True,
                        max_length=PROTOCOL["max_tokens"],
                        return_tensors="pt",
                        return_token_type_ids=False,
                        verbose=False,
                    )
                    logits = self.network(**encoded).logits
                    if logits.shape[0] != len(batch):
                        raise PretrainedError("invalid_model_output")
                    scores.extend(phishing_scores(logits, self.network.config.id2label))
                    if progress is not None:
                        progress(len(scores), len(emails))
        finally:
            torch.set_num_threads(old_threads)
        return ScoredBatch(scores, counts, time.perf_counter() - started)

    def predict(self, email: EmailInput, threshold: float = 0.5) -> dict:
        result = self.score([email])
        score = result.scores[0]
        prediction = Prediction(
            example_id="local-input",
            model_id=SOURCE["model_id"],
            model_revision=SOURCE["revision"],
            score=score,
            threshold=threshold,
            label="phishing" if score >= threshold else "legitimate",
            elapsed_ms=result.elapsed_seconds * 1000,
        )
        return {
            "prediction": prediction.model_dump(),
            "input": {
                "original_tokens": result.token_counts[0],
                "used_tokens": min(result.token_counts[0], PROTOCOL["max_tokens"]),
                "truncated": result.token_counts[0] > PROTOCOL["max_tokens"],
            },
        }


def load_classifier(directory: Path) -> PretrainedClassifier:
    verify_source(directory)
    for package, expected in PROTOCOL["runtime"].items():
        if version(package).split("+")[0] != expected:
            raise PretrainedError("incompatible_model_runtime")
    raw = parse_json(read_bytes(directory / "config.json", 262144))
    if (
        raw.get("architectures") != [SOURCE["architecture"]]
        or raw.get("id2label") != SOURCE["id2label"]
        or raw.get("max_position_embeddings") != PROTOCOL["max_tokens"]
        or raw.get("model_type") != "distilbert"
        or raw.get("vocab_size") != 28996
    ):
        raise PretrainedError("incompatible_model_config")
    phishing_index(raw["id2label"])
    config = DistilBertConfig.from_dict(raw)
    try:
        tokenizer = BertTokenizerFast(
            vocab_file=str(directory / "vocab.txt"),
            do_lower_case=False,
            strip_accents=None,
            model_max_length=PROTOCOL["max_tokens"],
            padding_side="right",
            truncation_side="right",
        )
        if len(tokenizer) != config.vocab_size or tokenizer.convert_tokens_to_ids(
            ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
        ) != [0, 100, 101, 102, 103]:
            raise PretrainedError("incompatible_tokenizer")
        network, loading = DistilBertForSequenceClassification.from_pretrained(
            str(directory),
            config=config,
            local_files_only=True,
            use_safetensors=True,
            trust_remote_code=False,
            output_loading_info=True,
            attn_implementation=PROTOCOL["attention"],
            dtype=torch.float32,
        )
        if any(
            loading.get(key)
            for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")
        ):
            raise PretrainedError("incomplete_model_weights")
        network.to("cpu")
        network.eval()
        network.requires_grad_(False)
    except PretrainedError:
        raise
    except (ValueError, RuntimeError, OSError):
        raise PretrainedError("model_load_failed") from None
    return PretrainedClassifier(tokenizer, network)
