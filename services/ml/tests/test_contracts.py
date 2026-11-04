import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS = Path(__file__).resolve().parents[3] / "packages" / "contracts"
SCHEMA = json.loads((CONTRACTS / "schemas" / "contracts.schema.json").read_text("utf-8"))
VALID = json.loads((CONTRACTS / "examples" / "valid.json").read_text("utf-8"))
INVALID = json.loads((CONTRACTS / "examples" / "invalid.json").read_text("utf-8"))
Draft202012Validator.check_schema(SCHEMA)


def test_all_declared_formats_have_installed_checkers():
    def formats(value):
        if isinstance(value, dict):
            if "format" in value:
                yield value["format"]
            for child in value.values():
                yield from formats(child)
        elif isinstance(value, list):
            for child in value:
                yield from formats(child)

    assert set(formats(SCHEMA)) <= set(FormatChecker().checkers)


def validator(name):
    return Draft202012Validator(
        {"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]},
        format_checker=FormatChecker(),
    )


@pytest.mark.parametrize("name,value", VALID.items())
def test_valid_contracts(name, value):
    validator(name).validate(value)


@pytest.mark.parametrize("example", INVALID, ids=[item["name"] for item in INVALID])
def test_invalid_contracts(example):
    assert not validator(example["schema"]).is_valid(example["value"])
