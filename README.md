# PhishGuard

PhishGuard is a course project on phishing-email classification and adversarial robustness. It compares a TF-IDF/logistic-regression baseline, a reviewed Hugging Face classifier and a locally fine-tuned small transformer. A bounded offline experiment measures the effect of controlled text changes. A separately trained augmentation defense is compared with the preserved models. A local Gradio demo accepts pasted email text and shows a model score, decision and evidence with limitations.

## Current status

PhishGuard provides validated email records, reproducible grouped data splits, a trained TF-IDF/logistic-regression baseline and local prediction commands. Training learns from the training split only; validation selects the threshold. A pinned pretrained DistilBERT classifier, same-test comparison, external generalization audit and separately trained real-mail baseline v2 are available. Stage 5 adds reproduced BERT-Tiny fine-tuning and a preserved-baseline comparison. Stage 6 adds fixed-bank controlled evasion with unchanged models, explicit budgets and bounded semantic review. Stage 7 adds a separately trained augmentation defense and fixed/fresh robustness comparisons. Stage 8 adds the local four-model demo and extends the pretrained comparison to the same current historical/challenge cohorts. Final evaluation and presentation remain pending.

## Install

Use Python 3.11-3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.13 is the development default in `.python-version`; the local environment was verified with Python 3.13.16 and uv 0.13.1. The baseline uses scikit-learn 1.9.1 with numerical dependencies pinned in `uv.lock`. The optional pretrained extra pins PyTorch 2.15.0 (CPU on Windows/Linux), Transformers 4.57.6 and safetensors 0.8.0.

From the repository root:

```sh
uv sync --locked
uv run --frozen phishguard --version
```

The first command creates an isolated `.venv` and installs versions recorded in `uv.lock`. Installation needs package downloads; subsequent validation is local and needs no account, API key, database or model download. To select Python 3.11 explicitly, add `--python 3.11` to both `uv sync` and `uv run`.

## Run the local demo

With the reviewed model artifacts prepared using the guides below:

```sh
uv sync --locked --extra pretrained --extra demo
uv run --frozen --extra pretrained --extra demo phishguard demo
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860). Choose a model, paste an English email and select **Analyze email**. Ctrl+C stops the server; use `--port 7861` if needed. A missing model produces an explicit unavailable message. Weights are intentionally excluded from Git, so a fresh checkout needs artifact preparation before inference. No paid API, database or Docker is needed.

The interface shows model identity, its validation-selected threshold, token truncation and an evidence-based explanation. Scores are not calibrated probabilities and a low score does not establish safety. Input stays local; links are not opened and messages are not saved by PhishGuard. See the [demo guide](docs/demo.md) for artifact paths, privacy boundaries and explanation methods. The [current four-model comparison](docs/current-comparison.md) reports identical-cohort results; it does not rank pretrained adversarial robustness.

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

The raw and processed message files remain in ignored local `data/raw/` and `data/processed/` folders. Only a text-free split manifest is tracked in Git. Preparation refuses an existing output directory; see the [dataset guide](docs/dataset.md) for separate reproductions, options, label audit and limitations. The baseline removes complete synthetic angle-bracket markers from model input while preserving the original records.

## Train, evaluate and predict

```sh
uv run --frozen phishguard baseline train
uv run --frozen phishguard baseline evaluate
uv run --frozen phishguard baseline predict --file tests/fixtures/email.json
```

Run these after dataset preparation. Training writes the model and training report to `models/baseline-v1/`; evaluation loads that model and writes final-test results to `artifacts/baseline-test-v1/`. Both directories stay local and are ignored by Git. Existing outputs are never overwritten; see [separate reproduction commands](docs/baseline.md).

To check your own message, supply a UTF-8 JSON file with `body` and optional `subject`, or use `--file -` for JSON standard input. Prediction returns the score, threshold, decision and model identity without saving or echoing the email. It uses the trained local model; no network or paid API is involved. A missing/invalid model returns `unavailable` with no score. This score is not a calibrated probability or proof that a message is safe.

The frozen synthetic test set produced **98.43% accuracy, 99.11% phishing recall and 2.30% legitimate false-positive rate**. The unchanged model scored **92.86% accuracy, 88.70% recall and 5.19% false-positive rate** on a later external audit. This drop limits interpretation of the synthetic score. The external sources differ by class and era, so neither result establishes contemporary-inbox or adversarial performance. [Baseline protocol](docs/baseline.md) and [external audit](docs/generalization-audit.md).

## Use the pretrained classifier

```sh
uv sync --locked --extra pretrained
uv run --frozen --extra pretrained phishguard pretrained fetch
uv run --frozen --extra pretrained phishguard pretrained verify
uv run --frozen --extra pretrained phishguard pretrained predict --file tests/fixtures/email.json
```

The first use downloads a pinned public DistilBERT checkpoint (about 263 MB of weights); inference then runs locally on CPU without an API key or sending email content to a service. The pretrained prediction contains the score/decision plus token-length and truncation metadata. Input over 512 model tokens is right-truncated and explicitly marked. The normal email character limit still applies.

After preparing the dataset and baseline, reproduce the comparison with:

```sh
uv run --frozen --extra pretrained phishguard pretrained select
uv run --frozen --extra pretrained phishguard pretrained evaluate
uv run --frozen --extra pretrained phishguard pretrained predict --selection artifacts/pretrained-selection-v1 --file tests/fixtures/email.json
```

Selection uses validation only and freezes the threshold before final-test evaluation. Without `--selection`, prediction uses 0.50. Existing output directories are preserved; use new `--output` paths for repeated experiments. Model files and per-example predictions stay in ignored local folders. See [model provenance, commands, comparison and limitations](docs/pretrained.md).

On the same synthetic test set, pretrained accuracy was **61.16% at threshold 0.50** and **59.83% at the validation-selected threshold 0.05**, versus **98.43% for the corpus-trained baseline**. This is a transfer comparison; upstream training overlap is unknown, and none of these measurements establish real-mail or adversarial performance.

## Audit generalization on external email

After internal dataset preparation and baseline training:

```sh
uv run --frozen phishguard audit fetch
uv run --frozen phishguard audit prepare
uv run --frozen phishguard audit internal
uv run --frozen phishguard audit evaluate
```

The downloader verifies pinned Nazario phishing and SpamAssassin legitimate-mail archives (about 36.4 MB). Review the [source terms and limitations](docs/generalization-audit.md) before downloading. Messages stay local. Offline preparation extracts inert MIME text, filters language, removes duplicates and groups relatives. The committed manifest binds 1,639 audit messages and 703 reserved messages. The evaluator loads the exact baseline and threshold, scores only the audit partition and does not open the reserve file. It performs no training.

Results go to ignored `artifacts/generalization-internal-v1/` and `artifacts/generalization-external-v1/`; existing outputs are refused. Aggregate published reports include confusion counts, balanced accuracy, per-source metrics and group-bootstrap uncertainty. See [reproduction commands and interpretation](docs/generalization-audit.md). The inspected audit cohort is development evidence for future decisions; the reserve remains unscored.

## Re-evaluate the baseline with improved data

After the original dataset, baseline and external audit are prepared:

```sh
uv run --frozen phishguard refresh diagnose
uv run --frozen phishguard refresh fetch
uv run --frozen phishguard refresh prepare
uv run --frozen phishguard refresh train
uv run --frozen phishguard refresh evaluate
uv run --frozen phishguard baseline predict --model models/baseline-v2 --file tests/fixtures/email.json
```

Review the [source terms, protocol and reproduction guide](docs/baseline-refresh.md). New verified downloads total about 211.7 MB. Preparation adds reviewed historical legitimate/phishing mail, repairs specific extraction artifacts, removes declared publisher placeholders and protects earlier held-out groups. Training writes a separate model to `models/baseline-v2/`; results go to `artifacts/real-mail-v2-evaluation/`. Original data/model files are preserved. The 703-message reserve remains unscored. Existing outputs are refused; the guide provides separate reproduction paths.

On the 425-row historical benchmark, v1/v2 accuracy is 82.59%/98.82%; on the separate 2,000-row, mainly synthetic challenge it is 66.00%/80.10%. V2 still falsely flags 37.20% of legitimate challenge texts. Historical source families also occur in v2 development, and one previously reviewed message is disclosed in that test; the 424-row post-hoc sensitivity remains 98.82%. The challenge's 100 original records have unverified provenance and only 62% v2 accuracy. These are bounded research benchmarks, not production or universal accuracy claims. Stage 5 excludes that reviewed message and its full family for the subsequent comparison below.

## Fine-tune and compare the small transformer

After preparing real-mail-v2 and baseline v2 with the commands above:

```sh
uv sync --locked --extra pretrained
uv run --frozen --extra pretrained phishguard finetune fetch
uv run --frozen --extra pretrained phishguard finetune verify
uv run --frozen --extra pretrained phishguard finetune train
uv run --frozen --extra pretrained phishguard finetune evaluate
uv run --frozen --extra pretrained phishguard finetune predict --file tests/fixtures/email.json
```

The verified download is about 18 MB. Training fine-tunes all weights of Google's BERT-Tiny encoder and a new phishing head locally on CPU; it needs no account or paid API. The existing `pretrained` extra supplies the shared neural runtime. Training writes `models/finetuned-v1/`; comparison writes `artifacts/finetuned-evaluation-v1/`. Existing output directories are refused. The [fine-tuning guide](docs/finetuned.md) covers separate reproduction, the frozen selection reference, hardware limits and model provenance. Exact comparison requires the committed selected model identity; training on a different platform can differ numerically and must not silently replace the reference.

Training uses 3,261 rows only; 745 validation rows select epoch 5 and threshold 0.69. It never reads benchmark/reserve text. Comparison uses the unchanged baseline v2 at 0.31 on identical inputs, excluding the entire earlier reviewed family. Historical accuracy is **98.82% baseline / 98.58% transformer** across 423 rows. On the mainly synthetic 2,000-row challenge, accuracy is **80.10% / 80.80%**, false-positive rate **37.20% / 29.80%**, and phishing recall **97.40% / 91.40%**. Fewer false alarms come with more missed phishing; this is not a general model-quality victory or production-ready filter. The previously scored cohorts are retrospective benchmarks, while 703 reserve messages remain unscored.

Inference right-truncates to 256 tokens with explicit length metadata. It does not save or transmit pasted text. All raw data, model weights and per-example predictions stay local; text-free reports, source/protocol manifests and the selected identity are versioned. Stage-6 measurements follow below.

## Measure controlled evasion

After completing stage-5 data/model preparation:

```sh
uv run --frozen phishguard evasion preview
uv run --frozen phishguard evasion prepare
uv run --frozen phishguard evasion verify
uv run --frozen --extra pretrained phishguard evasion evaluate
```

The training-only preview scores no model. Preparation creates a deterministic local bank of bounded typos, letter swaps and lexical substitutions. Verification regenerates the bank and requires the committed manifest. Evaluation compares the unchanged baseline v2 and BERT-Tiny on the same variants, with at most 12 candidate predictions plus one clean prediction per original/model. Existing outputs are refused. See the [evasion guide](docs/controlled-evasion.md) for paths, reproduction and the fixed threat model. There is no new download, API key or model training.

The measured bank contains 19,969 variants for 2,423 benchmark originals. On the mainly synthetic challenge, constraint-pass candidates evade **8/974 (0.82%)** initially detected phishing messages for baseline v2 and **95/914 (10.39%)** for BERT. On the common 909 initially detected originals, counts are **4/909 versus 91/909**. These are candidate-ASR measurements under automatic constraints; only a bounded semantic sample was reviewed. They are not percentages of all email or guarantees against other attacks. The historical benchmark yields zero/one new misses. Known-cohort, source, template and truncation limitations remain; baseline's clean challenge false-positive rate is still 37.20%.

Models, thresholds and earlier data are preserved. The 703-message reserve remains unscored. Variants, original text and detailed predictions stay in ignored local artifact folders; only text-free manifests, reviews and aggregate reports enter Git. The separate stage-7 defense is described below.

## Train and compare the augmentation defense

After completing stages 5/6 and reviewing the [defense protocol](docs/robustness-defense.md):

```sh
uv run --frozen phishguard defense prepare
uv run --frozen --extra pretrained phishguard defense train
uv run --frozen phishguard defense prepare-fresh
uv run --frozen --extra pretrained phishguard defense evaluate
uv run --frozen --extra pretrained phishguard defense predict --file tests/fixtures/email.json
```

The guide explains the committed augmentation/review/selection references enforced between commands, and separate paths for reproductions. Training continues the preserved BERT checkpoint into `models/defended-v1/`, using training-only clean/copied views. Validation alone selects its checkpoint and threshold (0.07). Evaluation compares three models on the fixed stage-6 bank and a separately seeded equal-budget bank. All previous models remain available; no new download or paid API is needed. Existing outputs are refused.

On the mainly synthetic challenge, original/defended clean accuracy is **80.80%/80.80%**, phishing recall **91.40%/92.10%**, and false-positive rate **29.80%/30.50%**. Fresh-search candidate ASR is **95/914 (10.39%)/93/921 (10.10%)**. ASR is conditional on automatic constraints and a partial semantic review. These known-cohort results do not establish universal robustness or production readiness. The 703-message reserve remains unscored. The local demo is available above; final evaluation remains separate.

## Run checks and build

```sh
uv run --frozen --extra pretrained --extra demo pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen python scripts/check_documents.py
uv build
```

The 310 offline tests cover contracts, malformed JSON, input limits, mappings, thresholds, data ingestion/grouping, leakage, artifact integrity, downloader failures and CLI privacy. They include tiny training/save/load checks, a random local transformer, MIME/archive handling and frozen external evaluation without reserve access or fitting. Refresh checks add extraction repairs, ham-only ingestion, protected groups, placeholder cleanup and separate training/evaluation file boundaries. Fine-tuning checks add actual encoder updates, deterministic selection/reload, reviewed-family exclusion and separate fitting/evaluation read boundaries. Evasion tests add protected edit spans, lineage/replay, query caps, zero/empty cases, ASR denominators and scoring without training files or updates. Defense tests add training-only augmentation/review gates, separate artifacts, validation selection, deterministic repetition and fixed/fresh inference without development files. Documentation checks cover English content, local links, tables, eight required chapters and UML diagrams. GitHub Actions runs Windows/Linux with Python 3.11/3.13. CI installs the pretrained extra; core-only installations skip its tests. Research-corpus metrics are separate from software tests. Builds are written to ignored `dist/`.

## Documentation

- [Project book and system specification](docs/project-book.md)
- [Specification entry point](docs/specification.md)
- [Implementation plan](docs/implementation-plan.md)
- [Progress and verification log](docs/stage-log.md)
- [Implemented contracts](docs/contracts.md)
- [Dataset source, preparation and limits](docs/dataset.md)
- [Label sample audit](docs/dataset-label-audit.md)
- [Classical baseline and measured results](docs/baseline.md)
- [Pretrained classifier comparison](docs/pretrained.md)
- [Generalization audit and external results](docs/generalization-audit.md)
- [External pre-score label review](docs/external-label-audit.md)
- [Data refresh, baseline v2 and remaining limits](docs/baseline-refresh.md)
- [Fine-tuned transformer, reproduction and measured trade-offs](docs/finetuned.md)
- [Controlled evasion, budgets and measured limits](docs/controlled-evasion.md)
- [Augmentation defense, fixed/fresh comparisons and limits](docs/robustness-defense.md)

The project book is the canonical specification. It distinguishes implemented behavior from future work. The commands above cover data preparation, training/evaluation, pretrained comparison, generalization audits, controlled evasion, augmentation defense and the local demo. See the [demo guide](docs/demo.md) and [current four-model results](docs/current-comparison.md).

## Remaining deliverables

- Final evaluation under a separately frozen protocol, updated comparative conclusions and submission materials.
- Final presentation and student review of the completed implementation.

## Data and models

No raw research emails or model checkpoints are included in Git. The internal synthetic source is pinned in its [source manifest](src/phishguard/datasets/source.json), with a publisher MIT declaration. The [external source manifest](src/phishguard/audit/source.json) separately records Nazario CC BY 4.0 attribution and SpamAssassin's research-use terms retaining sender copyright. The [refresh source manifest](src/phishguard/refresh/source.json) pins MeAJOR ham, historical Nazario phishing and the separate Zenodo challenge with publisher CC BY 4.0 declarations. Downloaded data remains on your disk. [Fixture provenance](tests/fixtures/README.md) describes invented test examples. Keep credentials, private mail and large artifacts out of Git; keep detected relatives and derived variants together. Dataset checks do not establish classification quality.

## Team

Lior and Sharon Elimelech share planned responsibility equally. The project book records the allocation, the reported two-week learning period and how actual contributions will be recorded as work proceeds.
