# Classical phishing baseline

Stage 3 implements and evaluates TF-IDF plus logistic regression. The protocol and code were committed before research-corpus training at [3cd54fb](https://github.com/liorma6/AI-security-agent-/commit/3cd54fb3cfaffc38acaaf75ac7d61afefb5f5c78); both initial training and final evaluation recorded a clean working tree. The [packaged protocol](../src/phishguard/baseline/protocol.json) is the machine-readable specification.

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

## Measured results - November 13, 2026

Trained on 8,052 messages with 30,000 TF-IDF features. LIBLINEAR converged in nine iterations. Validation selected threshold **0.44**; the model was then frozen before final-test evaluation. No protocol, hyperparameter or threshold was changed after viewing test results.

| Metric | Validation, selected 0.44 | Final test, frozen 0.44 |
| --- | --- | --- |
| Rows | 1,725 | 1,725 |
| Accuracy | 98.67% | 98.43% |
| Phishing precision | 98.56% | 97.91% |
| Phishing recall | 98.89% | 99.11% |
| Phishing F1 | 98.72% | 98.51% |
| Legitimate false-positive rate | 1.57% | 2.30% |
| TP / FP / TN / FN | 889 / 13 / 813 / 10 | 891 / 19 / 807 / 8 |

At the default threshold 0.50, validation had five false alarms and 19 misses; at the selected 0.44 it had 13 false alarms and ten misses. The declared F1 objective accepted more false alarms to reduce misses. This threshold is a research choice, not a validated operating policy for a company. Selecting a stricter operational policy would require a new declared validation-only procedure.

The training-majority comparator always predicts phishing. On the final set it achieved 52.12% accuracy, 100% recall and 100% false-positive rate, illustrating why recall alone is insufficient. Exact counts, full-precision values and all threshold candidates are in the [training report](reports/baseline-training.json) and [test report](reports/baseline-test.json).

The marker-only diagnostic detected 2,500 training and 568 validation phishing rows with zero legitimate matches. It achieved 80.81% validation accuracy without learning any language patterns, confirming the source shortcut. After preprocessing, no complete synthetic markers remained in those inputs. This is not an ablation quantifying how much a raw-text trained classifier would improve or degrade, and does not remove all dataset bias.

Execution used Windows AMD64, Python 3.13.16, scikit-learn 1.9.1, NumPy 2.5.4 and SciPy 1.18.1 on CPU, requesting one numerical-library thread; the machine reports 12 logical CPUs. Fit/validation computation took 3.02 seconds after input/boundary preprocessing. A final-test batch of 1,725 emails took 0.311 seconds (0.180 ms amortized per email), excluding imports, model loading and file I/O. This is not single-request latency or a service throughput benchmark; no peak-memory measurement is claimed.

Independent retraining produced byte-identical model and manifest files, identical validation results, and identical final-test prediction bytes. Test confusion counts were also recomputed independently from the predictions. The deterministic test rerun was a reproduction check, not retuning. See the [reproduction evidence](reports/baseline-reproduction.json). Cross-platform tests use numerical tolerances; byte identity across different environments is not promised.

Model SHA-256: `a526bb2de383bbeb46282a6c2f0f8bca375310397945319d8b2e5d161f435703`. The full model stays in the ignored local model directory, since its vocabulary is learned from the corpus. Git contains aggregate results and reproduction metadata only.

## Verification and responsibility

The offline tests exercise train-only vocabulary/IDF fitting, no test-file access during training, deterministic fitting, threshold arithmetic, group/parent/cleaned-text leakage, hand-calculated confusion counts, malformed/tampered model files, numerical round trips, private inference and explicit unavailable states. Tests use invented messages; they are separate from benchmark-quality results.

W04 assigns training/artifacts to Lior and metrics, threshold selection and leakage checks to Sharon Elimelech, with equal planning weight and mutual review. Implementation is AI-assisted; individual student review remains to be recorded. Conclusions apply only to the synthetic source labels and the frozen experimental protocol, not to real inboxes or robustness against adversarial messages.
