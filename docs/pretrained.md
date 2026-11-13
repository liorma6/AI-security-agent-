# Pretrained classifier comparison

## Model selected before evaluation

Use `dima806/phishing-email-detection`, revision `310a5602280486e01dd60e37230980cfcc327b41`, a two-class DistilBERT checkpoint. The publisher model card declares Apache-2.0; the repository has no separate license file. Its configuration explicitly maps class 0 to `SAVE EMAIL` (the publisher spelling, interpreted as non-phishing) and class 1 to `PHISHING EMAIL`. Generic, missing or extra labels are rejected.

The checkpoint was selected for its email task, explicit two-class mapping, declared license and manageable CPU size before measuring our validation or final-test scores. The model card points to the author's Kaggle notebook, but its full training membership and preprocessing were not independently available. Do not claim verified absence of overlap with our corpus. Publication chronology alone cannot prove independence. A larger BERT-large checkpoint would cost more resources; a four-class email/URL checkpoint would require additional label aggregation. No candidate was selected using our final-test results.

The [source manifest](../src/phishguard/pretrained/source.json) pins all four downloaded files and their byte sizes/SHA-256 digests: card, configuration, vocabulary and safetensors weights (263,144,680 bytes for weights). Pickle-based weight/training files are excluded. The downloader checks HTTPS, size and digest before publishing a file, reuses verified files and refuses corrupt existing files. Downloads are public and need no token or paid API. Email inference is local and does not send messages to Hugging Face.

## Tokenizer and inference protocol

The publisher supplies `vocab.txt` but not a complete tokenizer bundle. Reconstruct `BertTokenizerFast` with that vocabulary, case preserved, normal cased accent handling, right padding and right truncation. These choices follow the declared `distilbert-base-cased` base tokenizer configuration, pinned in the source manifest. Verify vocabulary size 28,996 and special-token IDs. This reconstruction is a documented limitation rather than a claim that the original training tokenizer was fully recovered.

The [frozen protocol](../src/phishguard/pretrained/protocol.json) uses the same subject/body joining, artificial-marker removal and whitespace normalization as the baseline. Tokenize at most 512 tokens including special tokens; count original lengths and report every truncated input without dropping rows. Keep weights unchanged, use evaluation and inference modes, CPU float32, eager attention, batches of eight and one numerical-library thread. Only local reviewed safetensors are loaded; remote code is disabled and missing/unexpected/mismatched keys fail instead of creating a new classification head.

Compare the published baseline with both the external model's fixed 0.50 threshold and a separately validation-selected threshold. The selection grid and F1/tie rules match stage 3. `select` opens only validation data, saves its decision and report digests, and binds the decision to the reviewed model, tokenizer/protocol, frozen dataset and baseline revision. `evaluate` loads that decision without selecting another threshold and checks the baseline against its published report on exactly the same test IDs. It records confusion counts, paired correctness, token truncation and timings. A digest is an integrity check, not proof of trusted authorship.

The baseline was trained on this corpus, while the external model was trained elsewhere: this comparison measures ready-made transfer versus a corpus-trained baseline, not the isolated effect of neural architecture. Scores are uncalibrated. Neither synthetic benchmark accuracy nor this comparison establishes real-inbox reliability or adversarial robustness.

## Run locally

First prepare the frozen dataset and train/evaluate the baseline as described in the [README](../README.md). Install the optional pinned inference dependencies:

```sh
uv sync --locked --extra pretrained
uv run --frozen --extra pretrained phishguard pretrained fetch
uv run --frozen --extra pretrained phishguard pretrained verify
uv run --frozen --extra pretrained phishguard pretrained select
uv run --frozen --extra pretrained phishguard pretrained evaluate
uv run --frozen --extra pretrained phishguard pretrained predict --file tests/fixtures/email.json
uv run --frozen --extra pretrained phishguard pretrained predict --selection artifacts/pretrained-selection-v1 --file tests/fixtures/email.json
```

Runtime: PyTorch 2.15.0, Transformers 4.57.6 and safetensors 0.8.0. The lockfile uses the official CPU wheel index on Windows/Linux. This stage does not require CUDA. Core contracts/data/baseline commands can run without the `pretrained` extra. Use that extra for the full 201-test suite; core-only installations skip the pretrained module tests.

Default checkpoint directory: `models/pretrained/dima806-310a5602`. Selection output: `artifacts/pretrained-selection-v1`. Test output: `artifacts/pretrained-test-v1`. All remain ignored locally. Commands refuse existing experiment outputs. For a repeat, choose a new `--output` directory; use `--selection` to choose an existing frozen decision. Dataset/reference/model/baseline/report paths have explicit options; see `--help`.

Prediction accepts the existing UTF-8 email JSON contract (or stdin with `--file -`) and returns a nested `prediction` plus original/used token counts and a truncation flag. Without `--selection`, it uses threshold 0.50. It does not store/echo the message or open its links. An unavailable model has no fabricated score. Selection and evaluation show only processed row counts on stderr. Implementation/protocol commit `50172afacad72af4e6afa8596e56044c8bd48f1f` preceded validation and final-test scoring. Both reports record a clean working tree.

## Sources reviewed

- [Publisher card at the pinned revision](https://huggingface.co/dima806/phishing-email-detection/blob/310a5602280486e01dd60e37230980cfcc327b41/README.md)
- [Publisher configuration and explicit labels](https://huggingface.co/dima806/phishing-email-detection/blob/310a5602280486e01dd60e37230980cfcc327b41/config.json)
- [Declared base model tokenizer settings](https://huggingface.co/distilbert/distilbert-base-cased/blob/6ea81172465e8b0ad3fddeed32b986cdcdcffcf0/tokenizer_config.json)
- [Transformers DistilBERT documentation](https://huggingface.co/docs/transformers/v4.57.3/en/model_doc/distilbert)
- [Transformers model loading](https://huggingface.co/docs/transformers/v4.57.3/en/main_classes/model)
- [PyTorch installation](https://pytorch.org/get-started/locally/)

## Measured results

| Measure | Classical baseline | Pretrained at 0.50 | Pretrained selected |
| --- | --- | --- | --- |
| Threshold | 0.44 | 0.50 | 0.05 |
| Accuracy | 98.43% | 61.16% | 59.83% |
| Phishing precision | 97.91% | 58.76% | 57.32% |
| Phishing recall | 99.11% | 85.43% | 89.77% |
| Phishing F1 | 98.51% | 69.63% | 69.96% |
| Legitimate false-positive rate | 2.30% | 65.25% | 72.76% |
| True positives / false positives | 891 / 19 | 768 / 539 | 807 / 601 |
| True negatives / false negatives | 807 / 8 | 287 / 131 | 225 / 92 |

Validation selected threshold 0.05; the test set contains 899 phishing and 826 legitimate messages. Pretrained right truncation affected 0 test rows, with maximum original length 345. CPU scoring took 457.82 seconds, versus 0.275 seconds for the recomputed baseline, excluding model loading. See the [project book](project-book.md) for interpretation and resource limits, [validation evidence](reports/pretrained-validation.json), [test evidence](reports/pretrained-test.json), and [independent counts/reload verification](reports/pretrained-reproduction.json). The latter is not a repeated full-corpus transformer run. No settings were changed after test outcomes were inspected.
