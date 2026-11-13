# PhishGuard

PhishGuard is a course project on phishing-email classification and adversarial robustness. Its planned workflow compares a TF-IDF/logistic-regression baseline with Hugging Face classifiers, measures the effect of controlled text changes, and evaluates a defense. A local web demo will accept pasted email text and show a risk score and explanation.

## Current status

Stages 1-2 provide an installable Python package, strict data contracts, an offline JSON validator and a reproducible dataset-preparation pipeline with grouped training/validation/test splits. Classifiers, training, perturbation experiments and the web demo are **not implemented yet**. These commands do not classify new email or produce a risk score.

## Install

Use Python 3.11-3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.13 is the development default in `.python-version`; the local environment was verified with Python 3.13.16 and uv 0.13.1. The selected training libraries will be checked separately when model work begins.

From the repository root:

```sh
uv sync --locked
uv run --frozen phishguard --version
```

The first command creates an isolated `.venv` and installs versions recorded in `uv.lock`. Installation needs package downloads; subsequent validation is local and needs no account, API key, database or model download. To select Python 3.11 explicitly, add `--python 3.11` to both `uv sync` and `uv run`.

## Validate data

```sh
uv run --frozen phishguard validate email --file tests/fixtures/email.json
uv run --frozen phishguard validate example --file tests/fixtures/phishing-example.json
uv run --frozen phishguard validate artifact --file tests/fixtures/artifact.json
uv run --frozen phishguard validate prediction --file tests/fixtures/prediction.json
uv run --frozen phishguard validate prediction --file tests/fixtures/unavailable.json
```

Successful validation reports only metadata:

```json
{"status": "valid", "contract": "email", "schema_version": "1.0"}
```

Use `--file -` to read UTF-8 JSON from standard input. Invalid data exits with code 1 and a structured error on standard error; unreadable files or incorrect command usage exit with code 2. Input text is not printed or logged. The example messages and scores are invented test fixtures, not a research dataset or model results.

Print the structural JSON Schema with:

```sh
uv run --frozen phishguard schema email
```

For Python integration, use `validate_record` or `validate_json` from `phishguard.validation` and handle `ContractError`. See [contract rules and error handling](docs/contracts.md). The maximum combined subject/body text is 20,000 Unicode code points; the validator preserves text and rejects excess length instead of truncating it.

## Prepare the research dataset

```sh
uv run --frozen phishguard data fetch
uv run --frozen phishguard data prepare
uv run --frozen phishguard data verify --reference data/manifests/ephishllm-v1.json
```

The downloader retrieves a pinned public E-PhishLLM file and publisher license card, verifies their digests and caches them locally. No account or paid service is needed. Preparation and verification then run offline. The selected corpus is **synthetic**, with 11,502 English-flagged messages: 8,052 training, 1,725 validation and 1,725 test examples.

The raw and processed message files remain in ignored local `data/raw/` and `data/processed/` folders. Only a text-free split manifest is tracked in Git. Preparation refuses an existing output directory; see the [dataset guide](docs/dataset.md) for separate reproductions, options, label audit and limitations. Synthetic placeholders create a known shortcut that must be addressed before model training.

## Run checks and build

```sh
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen python scripts/check_documents.py
uv build
```

The offline tests cover contracts, malformed JSON, input limits, label mappings, threshold decisions, data ingestion, grouping, split leakage, frozen-file integrity, downloader failures and CLI privacy/errors. Documentation checks cover English content, local links, tables, eight required chapters and UML diagrams. GitHub Actions runs the checks on Windows and Linux with Python 3.11 and 3.13. These are foundation checks, not measurements of detection accuracy. Builds are written to the ignored `dist` directory.

## Documentation

- [Project book and system specification](docs/project-book.md)
- [Specification entry point](docs/specification.md)
- [Implementation plan](docs/implementation-plan.md)
- [Progress and verification log](docs/stage-log.md)
- [Implemented contracts](docs/contracts.md)
- [Dataset source, preparation and limits](docs/dataset.md)
- [Label sample audit](docs/dataset-label-audit.md)

The project book is the canonical specification. It distinguishes implemented behavior from future work. Training, evaluation and demo commands will be added when their implementations are available and verified.

## Planned deliverables

- A baseline detector and a fine-tuned small transformer, with reproducible evaluation.
- A comparison against a suitable pretrained Hugging Face classifier.
- A controlled text-perturbation runner and a robustness improvement experiment.
- A local pasted-email demo with model identity, score and explanation.
- A comparative report and final presentation.

## Data and models

No raw research emails or model checkpoints are included in Git. The reviewed source is pinned in the [source manifest](src/phishguard/datasets/source.json); the publisher declares MIT. Downloaded data remains on your local disk. [Fixture provenance](tests/fixtures/README.md) describes the separate invented unit-test examples. Keep credentials, private mail and large artifacts out of Git. Keep related messages and their derived variants in the same split. Dataset checks do not establish real-mail classification quality.

## Team

Lior and Sharon Elimelech share planned responsibility equally. The project book records the allocation, the reported two-week learning period and how actual contributions will be recorded as work proceeds.
