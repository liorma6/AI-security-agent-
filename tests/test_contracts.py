import json

import pytest

from phishguard.contracts import CONTRACTS, MAX_EMAIL_CHARACTERS
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json, validate_record


@pytest.mark.parametrize(
    "kind,name",
    [
        ("email", "email"),
        ("example", "legitimate-example"),
        ("example", "phishing-example"),
        ("artifact", "artifact"),
        ("prediction", "prediction"),
        ("prediction", "unavailable"),
    ],
)
def test_fixture_round_trip(kind, name, fixture_data):
    record = validate_record(kind, fixture_data(name))
    restored = validate_json(kind, record.model_dump_json().encode())
    assert restored == record


@pytest.mark.parametrize(
    "payload",
    [
        {},
        None,
        [],
        {"body": ""},
        {"body": " \t\r\n"},
        {"body": 12},
        {"body": True},
        {"body": "text", "subject": None},
        {"body": "text", "attachments": []},
        {"body": "text", "schema_version": "2.0"},
        {"body": "bad\x00text"},
        {"body": "bad\ud800text"},
    ],
)
def test_invalid_email_rejected(payload):
    with pytest.raises(ContractError):
        validate_record("email", payload)


def test_text_is_preserved_and_not_interpreted():
    text = (
        "  Caf\u00e9 \U0001f512\r\n<script>alert('example')</script>\t\nhttps://example.invalid  "
    )
    record = validate_record("email", {"subject": "Example", "body": text})
    assert record.body == text
    assert record.text == f"Example\n\n{text}"
    assert text not in repr(record)


@pytest.mark.parametrize("subject", ["", "Subject"])
def test_combined_character_limit(subject):
    separator_length = 2 if subject else 0
    body = "\U0001f512" * (MAX_EMAIL_CHARACTERS - len(subject) - separator_length)
    record = validate_record("email", {"subject": subject, "body": body})
    assert len(record.text) == MAX_EMAIL_CHARACTERS
    with pytest.raises(ContractError):
        validate_record("email", {"subject": subject, "body": body + "a"})


def test_escaped_unicode_boundary_fits_json_limit():
    data = json.dumps({"body": "\U0001f512" * MAX_EMAIL_CHARACTERS}).encode()
    assert len(data) < MAX_JSON_BYTES
    assert len(validate_json("email", data).body) == MAX_EMAIL_CHARACTERS


@pytest.mark.parametrize(
    "field,value",
    [
        ("label", "spam"),
        ("label", 1),
        ("split", "development"),
        ("group_id", ""),
        ("source_revision", " "),
        ("license", ""),
        ("example_id", "not an identifier"),
    ],
)
def test_example_requires_provenance_and_explicit_labels(field, value, fixture_data):
    payload = fixture_data("legitimate-example")
    payload[field] = value
    with pytest.raises(ContractError):
        validate_record("example", payload)


@pytest.mark.parametrize(
    "mapping",
    [
        {"legitimate": 0, "phishing": 0},
        {"legitimate": 0},
        {"legitimate": False, "phishing": 1},
        {"legitimate": "0", "phishing": 1},
        {"legitimate": 0, "phishing": 2},
        {"legitimate": 0, "phishing": 1, "spam": 2},
    ],
)
def test_invalid_label_mapping_rejected(mapping, fixture_data):
    payload = fixture_data("artifact")
    payload["label_mapping"] = mapping
    with pytest.raises(ContractError):
        validate_record("artifact", payload)


def test_reversed_mapping_is_preserved(fixture_data):
    payload = fixture_data("artifact")
    payload["label_mapping"] = {"legitimate": 1, "phishing": 0}
    record = validate_record("artifact", payload)
    assert record.label_mapping.phishing == 0
    assert record.label_mapping.legitimate == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_sha256", "not-a-digest"),
        ("model_revision", ""),
        ("threshold", 1.1),
        ("tokenizer", {"name": "fixture"}),
        ("preprocessing_version", ""),
    ],
)
def test_invalid_artifact_metadata_rejected(field, value, fixture_data):
    payload = fixture_data("artifact")
    payload[field] = value
    with pytest.raises(ContractError):
        validate_record("artifact", payload)


@pytest.mark.parametrize(
    "score,label", [(0, "legitimate"), (0.499, "legitimate"), (0.5, "phishing"), (1, "phishing")]
)
def test_prediction_threshold_boundary(score, label, fixture_data):
    payload = fixture_data("prediction")
    payload.update(score=score, label=label)
    record = validate_record("prediction", payload)
    assert record.label == label
    assert record.model_revision == "fixture-v1"


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", -0.1),
        ("score", 1.1),
        ("score", float("nan")),
        ("score", float("inf")),
        ("score", True),
        ("score", "0.75"),
        ("threshold", float("nan")),
        ("threshold", False),
        ("threshold", -1),
        ("label", "legitimate"),
        ("elapsed_ms", -1),
        ("elapsed_ms", float("inf")),
        ("elapsed_ms", True),
        ("model_id", ""),
    ],
)
def test_invalid_prediction_rejected(field, value, fixture_data):
    payload = fixture_data("prediction")
    payload[field] = value
    with pytest.raises(ContractError):
        validate_record("prediction", payload)


def test_unavailable_cannot_contain_a_score(fixture_data):
    payload = fixture_data("unavailable")
    assert validate_record("prediction", payload).status == "unavailable"
    payload["score"] = 0.0
    with pytest.raises(ContractError):
        validate_record("prediction", payload)


@pytest.mark.parametrize(
    "data,code",
    [
        (b'{"body":"a","body":"b"}', "duplicate_json_key"),
        (b'{"nested":{"secret":1,"secret":2}}', "duplicate_json_key"),
        (b'{"body":NaN}', "invalid_json"),
        (b'{"body":Infinity}', "invalid_json"),
        (b"\xff", "invalid_json"),
        (b"{", "invalid_json"),
        (b" " * (MAX_JSON_BYTES + 1), "input_too_large"),
        (b"[" * 2000 + b"]" * 2000, "json_too_deep"),
    ],
)
def test_malformed_json_is_bounded_and_rejected(data, code):
    with pytest.raises(ContractError) as error:
        validate_json("email", data)
    assert error.value.issues[0].code == code


def test_errors_never_echo_private_values_or_unknown_field_names():
    marker = "PRIVATE-EMAIL-MARKER"
    payload = {"body": marker, marker: {"nested": marker}}
    with pytest.raises(ContractError) as error:
        validate_record("email", payload)
    assert marker not in str(error.value)
    assert marker not in json.dumps(error.value.to_dict())
    assert error.value.to_dict() == {"status": "invalid", "issues": [{"code": "extra_forbidden"}]}


def test_unknown_contract_has_structured_error():
    with pytest.raises(ContractError) as error:
        validate_record("unknown", {})
    assert error.value.issues[0].code == "unknown_contract"


@pytest.mark.parametrize("kind", CONTRACTS)
def test_schema_is_json_serializable_and_versioned(kind):
    schema = json.loads(json.dumps(CONTRACTS[kind].json_schema()))
    assert "schema_version" in json.dumps(schema)
    assert "additionalProperties" in json.dumps(schema)
