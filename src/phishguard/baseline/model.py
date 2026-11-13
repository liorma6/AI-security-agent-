"""Fit the baseline and persist only validated numerical/text JSON state."""

import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Self

import numpy as np
import sklearn
from pydantic import Field, ValidationError, model_validator
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from phishguard.baseline.common import (
    MODEL_ID,
    PROTOCOL,
    PROTOCOL_SHA256,
    BaselineError,
    parse_json,
    read_bytes,
)
from phishguard.baseline.metrics import select_threshold
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import (
    EmailExample,
    EmailInput,
    LabelMapping,
    ModelArtifact,
    Prediction,
    Record,
    Score,
)
from phishguard.datasets.grouping import canonical, related_components
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import DatasetError, digest

Finite = Annotated[float, Field(allow_inf_nan=False)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Term = Annotated[str, Field(min_length=1, max_length=20_000)]


class ModelState(Record):
    kind: Literal["tfidf-logistic-regression"] = MODEL_ID
    protocol_sha256: Digest
    dataset_sha256: Digest
    sklearn_version: Literal["1.9.1"]
    terms: Annotated[list[Term], Field(min_length=1, max_length=30_000)] = Field(repr=False)
    idf: Annotated[
        list[Annotated[float, Field(ge=1, allow_inf_nan=False)]], Field(max_length=30_000)
    ]
    coefficients: Annotated[list[Finite], Field(max_length=30_000)]
    intercept: Finite
    threshold: Score
    label_mapping: LabelMapping
    training_majority: Literal[0, 1]
    development_text_hashes: Annotated[list[Digest], Field(min_length=1, max_length=100_000)]

    @model_validator(mode="after")
    def consistent_dimensions(self) -> Self:
        if (
            len(self.terms) != len(self.idf)
            or len(self.terms) != len(self.coefficients)
            or len(set(self.terms)) != len(self.terms)
            or self.label_mapping.model_dump() != PROTOCOL["label_mapping"]
            or self.protocol_sha256 != PROTOCOL_SHA256
            or len(set(self.development_text_hashes)) != len(self.development_text_hashes)
        ):
            raise ValueError("Inconsistent baseline state")
        return self


def vectorizer(**kwargs) -> TfidfVectorizer:
    settings = dict(PROTOCOL["vectorizer"])
    settings["ngram_range"] = tuple(settings["ngram_range"])
    return TfidfVectorizer(**settings, dtype=np.float64, **kwargs)


@dataclass
class Baseline:
    state: ModelState
    transform: TfidfVectorizer

    @classmethod
    def from_state(cls, state: ModelState) -> "Baseline":
        transform = vectorizer(vocabulary={term: i for i, term in enumerate(state.terms)})
        transform.idf_ = np.asarray(state.idf, dtype=np.float64)
        return cls(state, transform)

    def scores(self, emails: list[EmailInput]) -> list[float]:
        if not emails:
            return []
        texts = [preprocess(email.text) for email in emails]
        with threadpool_limits(limits=PROTOCOL["threads"]):
            matrix = self.transform.transform(texts)
            scores = expit(matrix @ np.asarray(self.state.coefficients) + self.state.intercept)
        if not np.isfinite(scores).all():
            raise BaselineError("nonfinite_prediction")
        return scores.tolist()

    @property
    def revision(self) -> str:
        return digest(json_bytes(self.state.model_dump()))

    def predict(self, email: EmailInput) -> Prediction:
        started = time.perf_counter()
        score = self.scores([email])[0]
        elapsed = (time.perf_counter() - started) * 1000
        return Prediction(
            example_id="local-input",
            model_id=MODEL_ID,
            model_revision=self.revision,
            score=score,
            threshold=self.state.threshold,
            label="phishing" if score >= self.state.threshold else "legitimate",
            elapsed_ms=elapsed,
        )


def check_training_boundary(train: list[EmailExample], validation: list[EmailExample]) -> None:
    if (
        not train
        or not validation
        or any(r.split != "train" for r in train)
        or any(r.split != "validation" for r in validation)
        or {r.label for r in train} != {"legitimate", "phishing"}
        or {r.label for r in validation} != {"legitimate", "phishing"}
    ):
        raise BaselineError("invalid_training_partitions")
    combined = train + validation
    by_id = {r.example_id: r for r in combined}
    try:
        components = related_components(combined)
    except DatasetError:
        raise BaselineError("training_data_leakage") from None
    groups = {}
    for record in combined:
        previous = groups.setdefault(record.group_id, record.split)
        if previous != record.split:
            raise BaselineError("training_data_leakage")
    if any(len({by_id[rid].split for rid in component}) > 1 for component in components):
        raise BaselineError("training_data_leakage")
    if {text_hash(r.email) for r in train} & {text_hash(r.email) for r in validation}:
        raise BaselineError("preprocessed_text_leakage")


def text_hash(email: EmailInput) -> str:
    return digest(canonical(preprocess(email.text)).encode("utf-8"))


def fit_baseline(train: list[EmailExample], validation: list[EmailExample], dataset_sha256: str):
    check_training_boundary(train, validation)
    train_text = [preprocess(r.email.text) for r in train]
    validation_text = [preprocess(r.email.text) for r in validation]
    y_train = [PROTOCOL["label_mapping"][r.label] for r in train]
    y_validation = [PROTOCOL["label_mapping"][r.label] for r in validation]
    transform = vectorizer()
    classifier = LogisticRegression(**PROTOCOL["classifier"])
    started = time.perf_counter()
    try:
        with threadpool_limits(limits=PROTOCOL["threads"]), warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            matrix = transform.fit_transform(train_text)
            classifier.fit(matrix, y_train)
            validation_matrix = transform.transform(validation_text)
            scores = classifier.predict_proba(validation_matrix)[:, 1].tolist()
    except ConvergenceWarning:
        raise BaselineError("training_not_converged") from None
    except ValueError:
        raise BaselineError("training_failed") from None
    if classifier.classes_.tolist() != [0, 1]:
        raise BaselineError("unexpected_label_mapping")
    threshold, candidates = select_threshold(y_validation, scores)
    majority = int(sum(y_train) > len(y_train) / 2)
    state = ModelState(
        protocol_sha256=PROTOCOL_SHA256,
        dataset_sha256=dataset_sha256,
        sklearn_version=sklearn.__version__,
        terms=transform.get_feature_names_out().tolist(),
        idf=transform.idf_.tolist(),
        coefficients=classifier.coef_[0].tolist(),
        intercept=float(classifier.intercept_[0]),
        threshold=threshold,
        label_mapping=LabelMapping(**PROTOCOL["label_mapping"]),
        training_majority=majority,
        development_text_hashes=sorted({text_hash(r.email) for r in train + validation}),
    )
    baseline = Baseline.from_state(state)
    restored_scores = baseline.scores([r.email for r in validation])
    max_error = max(abs(a - b) for a, b in zip(scores, restored_scores, strict=True))
    if max_error > 1e-12:
        raise BaselineError("restored_score_mismatch")
    details = {
        "validation_scores": scores,
        "threshold_candidates": candidates,
        "fit_and_validation_seconds": time.perf_counter() - started,
        "iterations": int(classifier.n_iter_[0]),
        "feature_count": len(state.terms),
        "roundtrip_max_absolute_score_error": max_error,
        "zero_feature_validation_rows": int(
            np.count_nonzero(validation_matrix.getnnz(axis=1) == 0)
        ),
    }
    return baseline, details


def save_model(baseline: Baseline, directory: Path) -> ModelArtifact:
    if directory.exists():
        raise BaselineError("output_already_exists")
    payload = json_bytes(baseline.state.model_dump())
    manifest = ModelArtifact(
        model_id=MODEL_ID,
        model_revision=digest(payload),
        source=f"dataset-sha256:{baseline.state.dataset_sha256}",
        artifact_sha256=digest(payload),
        preprocessing_version=PROTOCOL["preprocessing_version"],
        label_mapping=baseline.state.label_mapping,
        threshold=baseline.state.threshold,
    )
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "model.json").write_bytes(payload)
    (directory / "manifest.json").write_bytes(json_bytes(manifest.model_dump()))
    return manifest


def load_model(directory: Path) -> Baseline:
    try:
        manifest = ModelArtifact.model_validate(
            parse_json(read_bytes(directory / "manifest.json", 262144))
        )
        payload = read_bytes(directory / "model.json")
        if digest(payload) != manifest.artifact_sha256:
            raise BaselineError("artifact_integrity_mismatch")
        state = ModelState.model_validate(parse_json(payload))
        if (
            manifest.model_id != MODEL_ID
            or manifest.model_revision != digest(payload)
            or manifest.source != f"dataset-sha256:{state.dataset_sha256}"
            or manifest.preprocessing_version != PROTOCOL["preprocessing_version"]
            or manifest.label_mapping != state.label_mapping
            or manifest.threshold != state.threshold
            or manifest.tokenizer is not None
            or sklearn.__version__ != state.sklearn_version
        ):
            raise BaselineError("artifact_manifest_mismatch")
        return Baseline.from_state(state)
    except FileNotFoundError:
        raise BaselineError("artifact_missing") from None
    except ValidationError:
        raise BaselineError("invalid_model_state") from None
