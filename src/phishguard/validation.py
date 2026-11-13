"""JSON and record validation with input-free boundary errors."""

import json
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from phishguard.contracts import CONTRACTS

MAX_JSON_BYTES = 262_144
MAX_JSON_DEPTH = 16


@dataclass(frozen=True)
class ValidationIssue:
    code: str


class ContractError(ValueError):
    """Contains stable error codes only, never input values or arbitrary keys."""

    def __init__(self, *codes: str):
        self.issues = tuple(ValidationIssue(code) for code in dict.fromkeys(codes))
        super().__init__("Input validation failed")

    def to_dict(self) -> dict[str, Any]:
        return {"status": "invalid", "issues": [asdict(issue) for issue in self.issues]}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("duplicate_json_key")
        value[key] = item
    return value


def _reject_constant(_: str) -> None:
    raise ContractError("invalid_json")


def read_json(data: bytes) -> Any:
    if len(data) > MAX_JSON_BYTES:
        raise ContractError("input_too_large")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except RecursionError:
        raise ContractError("json_too_deep") from None
    except (UnicodeDecodeError, ValueError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("invalid_json") from None
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if isinstance(item, (dict, list)):
            if depth > MAX_JSON_DEPTH:
                raise ContractError("json_too_deep")
            children = item.values() if isinstance(item, dict) else item
            pending.extend((child, depth + 1) for child in children)
    return value


def validate_record(kind: str, payload: Any) -> BaseModel:
    if kind not in CONTRACTS:
        raise ContractError("unknown_contract")
    try:
        return CONTRACTS[kind].validate_python(payload)
    except (ValidationError, RecursionError) as error:
        if isinstance(error, RecursionError):
            raise ContractError("invalid_structure") from None
        # Field names and custom messages can contain private, user-supplied text.
        codes = [item["type"] for item in error.errors(include_input=False, include_context=False)]
        raise ContractError(*codes) from None


def validate_json(kind: str, data: bytes) -> BaseModel:
    return validate_record(kind, read_json(data))
