# Foundation contracts - version 1.0

Stage 1 implements offline validation with [Pydantic strict models](https://docs.pydantic.dev/latest/concepts/strict_mode/). The public input boundaries are `validate_record` and `validate_json` in [validation.py](../src/phishguard/validation.py). Record definitions are in [contracts.py](../src/phishguard/contracts.py). Unknown fields and unsupported schema versions are rejected. Omitted `schema_version` defaults to `1.0`.

## Records

| CLI kind | Python record | Purpose |
| --- | --- | --- |
| `email` | `EmailInput` | Optional subject and required body, preserved as text |
| `example` | `EmailExample` | Email plus ID, label, source/version, license, group and split |
| `artifact` | `ModelArtifact` | Model identity/revision, digest, preprocessing version, label mapping, threshold and optional tokenizer reference |
| `prediction` | `Prediction` or `UnavailablePrediction` | An explicitly successful result or an unavailable state, selected by `status` |

These records do not train, download or load a model. Validating a prediction fixture checks its structure and arithmetic consistency, not the truth of a phishing decision. Artifact validation checks digest syntax; it does not verify a file's bytes or establish publisher trust. These behaviors belong to later stages.

## Input and text rules

- The body must contain a non-whitespace character. The subject defaults to an empty string.
- The combined text is `subject + "\n\n" + body` when the subject is nonempty, or just `body` otherwise. Its maximum length is 20,000 Unicode code points, including the separator. Emoji can comprise multiple code points; this is not a byte or token limit.
- Text, punctuation, line endings and whitespace are preserved. There is no trimming, Unicode normalization, HTML rendering, link fetching or automatic truncation. NUL and unpaired surrogate characters are rejected.
- JSON must be UTF-8 and at most 262,144 bytes. Object keys must be unique. NaN/Infinity literals are rejected. Container nesting is limited to 16 levels. The CLI reads at most the byte limit plus one before rejecting oversized input.
- Labels are `legitimate` or `phishing`. Splits are `unassigned`, `train`, `validation` or `test`. Stage 2 implements cross-record split/group and lineage checks; see the [dataset guide](dataset.md). Optional `parent_id` identifies a derived example's original/parent and cannot equal its own ID. Dataset-level validation rejects missing parents, cycles and group/split separation from parents. Existing records that omit it remain valid.
- Identifiers contain 1-128 ASCII letters/digits or `.`, `_`, `:`, `/`, `-`, starting with a letter/digit. Source/license/revision metadata is nonblank and bounded to 2,048 characters. Identifiers are not file paths and are never executed or opened.

The selected research subset uses the publisher's English flag. The validator accepts Unicode without claiming to detect the language or support multilingual classification. Tokenization and a token limit are not implemented in this stage.

## Prediction and artifact rules

`score` always refers to phishing. It must be a finite number in [0, 1], as must `threshold`. Boolean values and numeric strings are rejected. A successful result includes example ID, model ID/revision, threshold and finite nonnegative elapsed milliseconds. Its label must be `phishing` when `score >= threshold`, and `legitimate` otherwise. A score is not presented as a calibrated probability.

The artifact's label mapping must assign distinct indices 0 and 1 to the two labels. Either ordering is valid and preserved; a future inference adapter must use the recorded mapping. A tokenizer, if supplied, requires both name and revision. SHA-256 digests contain exactly 64 lowercase hexadecimal characters.

An unavailable result has `status: unavailable`, an optional model ID and one reason: `model_not_loaded`, `model_load_failed` or `manifest_mismatch`. It cannot contain a score, threshold, label or elapsed time. There is no fabricated fallback prediction.

## Public errors and privacy

The CLI reports success with the contract name and schema version only. It does not print the email or the supplied prediction. Invalid input produces `status: invalid` and a list of stable error codes. Raw values, unknown field names, parser excerpts and tracebacks are excluded from this public response. Unreadable input produces `status: error` with `input_unreadable`.

Use `ContractError.to_dict()` for public error responses. Do not log raw inputs, validated email records or Pydantic error internals in future integrations. No files, logs or network requests are created by the validation operation itself.

CLI exit codes: 0 = valid input/schema output; 1 = invalid input; 2 = unreadable file or invalid command usage. Structural JSON Schema can be printed with `phishguard schema KIND`. Cross-field rules such as combined text length and threshold/label agreement additionally require the Python validator.

## Verification and ownership

[Contract tests](../tests/test_contracts.py) and [CLI tests](../tests/test_cli.py) cover synthetic round trips, required provenance, reversed/malformed mappings, boundary scores, finite-number rules, malformed/bounded JSON, input limits and private error handling. [Fixture provenance](../tests/fixtures/README.md) distinguishes invented examples and scores from research data and measured predictions.

W02 assigns Lior the environment and contracts, and Sharon Elimelech the fixtures and validation checks, with mutual review. The current implementation was developed with AI assistance in this project session; assigned ownership does not assert that either student's individual review has already occurred.
