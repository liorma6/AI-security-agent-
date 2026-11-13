# Classical phishing baseline

Stage 3 implements TF-IDF plus logistic regression. This document first records the protocol before research-corpus training; measured results are added only after execution. The [packaged protocol](../src/phishguard/baseline/protocol.json) is the machine-readable specification.

## Protocol fixed before evaluation

- Use the frozen E-PhishLLM v1 manifest and existing 8,052 / 1,725 / 1,725 grouped splits. Preserve source text and labels.
- Remove complete synthetic `<<...>>` spans including their contents, for every label. Collapse whitespace; leave other text unchanged. Reject inputs with no word tokens. This addresses the documented marker shortcut but does not establish absence of all synthetic artifacts.
- Fit TF-IDF vocabulary and IDF weights on training data only: lowercase word unigrams/bigrams, minimum document frequency 2, at most 30,000 features, sublinear term frequency, smoothed IDF and L2 normalization. [TF-IDF reference](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html).
- Fit binary logistic regression on training data only, legitimate=0 and phishing=1: LIBLINEAR, L2 regularization (`l1_ratio=0`), C=1, tolerance 1e-8, maximum 2,000 iterations, seed 42, no class weighting and one numeric-library thread. Stop with an error on non-convergence. [Estimator reference](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
- Choose a decision threshold using validation only: maximize phishing F1 over 0.05 through 0.95 in increments of 0.01. Tie-break by fewer false positives, then nearest to 0.50, then higher threshold. Keep the default-0.50 validation metrics for comparison. No model hyperparameter search or combined training/validation refit.
- Record training/validation marker counts and the marker-presence-only rule as a shortcut diagnostic. No raw-text classifier is selected using the final test set.
- Freeze and save the model before a separate final-test command. Report confusion counts, accuracy, phishing precision/recall/F1 and legitimate false-positive rate. Include a constant predictor using the training majority class. Undefined metric denominators produce null, not invented zeros.

Training never opens `test.jsonl`; a unit test removes that file before training to verify this boundary. The frozen manifest pins its expected hash and membership without exposing its content to fitting. Cleaned-text fingerprints additionally reject exact overlap between development and final-test messages. The similarity/campaign limitations of stage 2 still apply.

## Persistence, inference and privacy

The model is saved as bounded, strictly validated JSON: ordered terms, IDF values, coefficients, intercept, label mapping, threshold, protocol/data digests and development-text hashes. No pickle/joblib object is deserialized. A separate artifact manifest pins the model-file digest and cross-checks metadata. This avoids executable serialized objects; a digest is an integrity check, not publisher authentication. [Persistence risks](https://scikit-learn.org/stable/model_persistence.html).

Loading reconstructs TF-IDF with its fixed vocabulary/IDF and computes the logistic sigmoid. Tests compare these scores against scikit-learn and a saved/reloaded model within 1e-12. scikit-learn is pinned to 1.9.1; the loader rejects unsupported model/runtime versions and inconsistent states.

Inference accepts the existing JSON email contract. It returns the model score, chosen threshold, label, identity and measured scoring time without logging or saving pasted email. Missing/invalid models return an explicit unavailable result without a fabricated score. Inputs containing only removed markers or punctuation are rejected. If valid word tokens are all outside the vocabulary, the trained intercept supplies the score; this is not evidence that such an email is safe.

The score is uncalibrated. Threshold selection is not probability calibration. HTML and links remain inert text. Explanations, adversarial robustness and the web UI are later stages.

## Local commands

After the README installation and dataset preparation steps:

```sh
uv run --frozen phishguard baseline train
uv run --frozen phishguard baseline evaluate
uv run --frozen phishguard baseline predict --file tests/fixtures/email.json
```

Training writes `models/baseline-v1/model.json`, `manifest.json` and `training-report.json`. Evaluation writes `artifacts/baseline-test-v1/report.json` and text-free per-example predictions. These directories are ignored by Git. The measured aggregate reports are published under `docs/reports/` after execution. Neither command overwrites an existing output directory.

For a separate reproducibility check, use `baseline train --output models/baseline-reproduction`, then `baseline evaluate --model models/baseline-reproduction --output artifacts/baseline-reproduction`. Both accept `--dataset PATH` and `--reference PATH`; the model must reference that same frozen dataset digest. Prediction accepts `--model PATH` and `--file -` for JSON standard input. Exit codes: 0 success, 1 validation/model error or unavailable prediction, 2 file-access/usage error.

## Verification and responsibility

The offline tests exercise train-only vocabulary/IDF fitting, no test-file access during training, deterministic fitting, threshold arithmetic, group/parent/cleaned-text leakage, hand-calculated confusion counts, malformed/tampered model files, numerical round trips, private inference and explicit unavailable states. Tests use invented messages; they are separate from benchmark-quality results.

W04 assigns training/artifacts to Lior and metrics, threshold selection and leakage checks to Sharon Elimelech, with equal planning weight and mutual review. Implementation is AI-assisted; individual student review remains to be recorded. Conclusions apply only to the synthetic source labels and the frozen experimental protocol, not to real inboxes or robustness against adversarial messages.
