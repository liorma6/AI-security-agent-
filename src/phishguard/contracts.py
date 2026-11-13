"""Versioned records with strict types and cross-field validation.

Validation never loads a model, follows an email link or interprets message code.
Use validation.validate_record at input boundaries for redacted errors.
"""

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, TypeAdapter, model_validator

MAX_EMAIL_CHARACTERS = 20_000
Label = Literal["legitimate", "phishing"]
Split = Literal["unassigned", "train", "validation", "test"]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")]
Score = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


def _valid_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("NUL characters are not supported")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Text must be valid Unicode") from None
    return value


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Text must contain a non-whitespace character")
    return _valid_text(value)


MetadataText = Annotated[str, Field(min_length=1, max_length=2048), AfterValidator(_nonblank)]
EmailText = Annotated[str, Field(max_length=MAX_EMAIL_CHARACTERS), AfterValidator(_valid_text)]


class Record(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, hide_input_in_errors=True)
    schema_version: Literal["1.0"] = "1.0"


class EmailInput(Record):
    subject: EmailText = Field(default="", repr=False)
    body: EmailText = Field(repr=False)

    @property
    def text(self) -> str:
        """Preserve text; join a nonempty subject and body with two newlines."""
        return f"{self.subject}\n\n{self.body}" if self.subject else self.body

    @model_validator(mode="after")
    def check_message(self) -> Self:
        if not self.body.strip():
            raise ValueError("Email body must not be blank")
        if len(self.text) > MAX_EMAIL_CHARACTERS:
            raise ValueError("Combined email exceeds the character limit")
        return self


class EmailExample(Record):
    example_id: Identifier
    email: EmailInput = Field(repr=False)
    label: Label
    source_id: Identifier
    source_revision: MetadataText
    license: MetadataText
    group_id: Identifier
    split: Split = "unassigned"


class LabelMapping(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    legitimate: Annotated[int, Field(ge=0, le=1)]
    phishing: Annotated[int, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def distinct_indices(self) -> Self:
        if self.legitimate == self.phishing:
            raise ValueError("Binary labels must have distinct indices")
        return self


class TokenizerReference(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    name: MetadataText
    revision: MetadataText


class ModelArtifact(Record):
    model_id: Identifier
    model_revision: MetadataText
    source: MetadataText
    artifact_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    preprocessing_version: Identifier
    label_mapping: LabelMapping
    threshold: Score
    tokenizer: TokenizerReference | None = None


class Prediction(Record):
    status: Literal["ok"] = "ok"
    example_id: Identifier
    model_id: Identifier
    model_revision: MetadataText
    score: Score
    threshold: Score
    label: Label
    elapsed_ms: Annotated[float, Field(ge=0, allow_inf_nan=False)]

    @model_validator(mode="after")
    def decision_matches_score(self) -> Self:
        expected = "phishing" if self.score >= self.threshold else "legitimate"
        if self.label != expected:
            raise ValueError("Decision does not match the score and threshold")
        return self


class UnavailablePrediction(Record):
    status: Literal["unavailable"] = "unavailable"
    reason: Literal["model_not_loaded", "model_load_failed", "manifest_mismatch"]
    model_id: Identifier | None = None


PredictionResult = Annotated[Prediction | UnavailablePrediction, Field(discriminator="status")]
CONTRACTS = {
    "email": TypeAdapter(EmailInput),
    "example": TypeAdapter(EmailExample),
    "artifact": TypeAdapter(ModelArtifact),
    "prediction": TypeAdapter(PredictionResult),
}
