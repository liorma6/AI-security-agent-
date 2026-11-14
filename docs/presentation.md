# PhishGuard final presentation

English slide content and speaker notes; generated artifacts are stored locally in the project outputs directory.

## 1. PhishGuard

Phishing detection and controlled adversarial robustness

- Lior & Sharon Elimelech
- Final project presentation | November 14, 2026
- An academic research prototype with a local email demo.

Speaker notes: Introduce the research question and the two students. Development and documentation were AI-assisted; students must review and explain the implementation.

## 2. What are we testing?

Detection quality is only one part of the question.

- Can a classifier separate phishing from legitimate email?
- Can small constrained text changes turn a detection into a miss?
- Does augmentation improve robustness without unacceptable clean-data cost?
- Can we demonstrate the result while making uncertainty visible?

Speaker notes: Define a false negative as missed phishing and a false positive as a legitimate message flagged incorrectly. A passing test suite does not prove detection quality.

## 3. One pipeline, two separate workflows

Offline experiments produce frozen artifacts; the UI only runs inference.

- DATA: reviewed sources, inert extraction, deduplication and grouped splits.
- MODELS: classical baseline, pretrained comparison, fine-tuning and defense.
- EVALUATION: frozen clean inputs, bounded variants, metrics and verification.
- DEMO: paste text, select a model, inspect score, decision and evidence.

Speaker notes: Explain why no training, email transmission or link following is available from the demo. Discuss the trust boundaries in the STRIDE chapter.

## 4. Keep development separate from evidence

Groups and derived variants stay together.

| Partition | Messages | Purpose |
| --- | --- | --- |
| Training | 3,261 | Fit the current local models |
| Validation | 745 | Select checkpoints and thresholds |
| Retrospective benchmarks | 423 + 2,000 | Historical and mainly synthetic challenge |
| Final reserve | 703 / 432 groups | Frozen evaluation after all choices |

Speaker notes: The final reserve has 479 legitimate and 224 phishing messages. It was held out from local selection, but shares source families and years with development. It is not a new representative real-world inbox.

## 5. Four preserved candidates

Architecture and training history are different.

| Candidate | How obtained | Threshold | Text budget |
| --- | --- | --- | --- |
| Baseline v2 | TF-IDF + logistic regression | 0.31 | Full accepted text |
| Original BERT | Locally fine-tuned BERT-Tiny | 0.69 | 256 tokens |
| Defended BERT | Separate augmentation continuation | 0.07 | 256 tokens |
| HF DistilBERT | Existing pretrained phishing classifier | 0.45 | 512 tokens |

Speaker notes: The downloaded phishing classifier is distinct from the general BERT-Tiny encoder we fine-tuned. Thresholds were validation-selected, not tuned on the final reserve. Scores are not calibrated probabilities.

## 6. The evaluation was frozen first

Protocol and executable code committed before reserve scoring.

- Freeze commit: 77c4a17. It binds 96 source/reference files and 79 preserved inputs.
- All four models scored the same 703 clean messages with existing thresholds.
- The three trained candidates used the same seed-9042 attack bank.
- No refitting, relabeling, threshold changes or test-based model replacement.

Speaker notes: Show the protocol commit and final report in GitHub. Explain the clean-worktree gate, file hashes, development-overlap rejection and frozen post-score review selection.

## 7. Final clean results

703 held-out messages: 224 phishing and 479 legitimate.

| Model | Accuracy | Phishing recall | Missed phishing | False alarms |
| --- | --- | --- | --- | --- |
| Baseline v2 | 99.29% | 98.66% | 3 | 2 |
| Original BERT | 98.29% | 96.43% | 8 | 4 |
| Defended BERT | 98.15% | 96.43% | 8 | 5 |
| HF DistilBERT | 95.16% | 89.73% | 23 | 11 |

Speaker notes: Read counts as well as accuracy. Compare the two error types explicitly. These are source-conditioned held-out results; the same models behaved differently on the challenge dataset. Group-based intervals and per-source results are in the report.

## 8. Changing the dataset changes the result

Do not average different cohorts into one claimed product accuracy.

| Model | Historical accuracy | Challenge accuracy | Final reserve accuracy |
| --- | --- | --- | --- |
| Baseline v2 | 98.82% | 80.10% | 99.29% |
| Original BERT | 98.58% | 80.80% | 98.29% |
| Defended BERT | 98.82% | 80.80% | 98.15% |
| HF DistilBERT | 90.54% | 87.25% | 95.16% |

Speaker notes: The historical cohort has 423 messages; the challenge has 2,000 and is mainly generated; the reserve has 703 held-out messages. The pretrained classifier had 87.25% challenge accuracy but missed 136 of 1,000 phishing messages. Source and template effects matter.

## 9. Controlled evasion, not unrestricted attacks

A fixed, inspectable search budget.

- Three operations: duplicate a letter, swap internal letters, substitute a listed word.
- At most 3 changed words and 10% of body words; first 1,500 body characters only.
- Protect URLs, addresses, numbers, markup, capitalization and listed negations.
- 5,853 candidates; at most 12 candidates plus 1 clean query per message/model.
- Automatic constraints do not certify that every candidate preserves meaning.

Speaker notes: The generator never sees gradients or model scores. Each model scores the same finite candidate bank. Original messages are included in minimum-score selection; legitimate originals stay clean in directed-evasion metrics.

## 10. What happened under the fixed budget?

Candidate ASR counts newly evaded, initially detected phishing.

| Model | Clean recall | Attacked recall | New misses / detected | Candidate ASR |
| --- | --- | --- | --- | --- |
| Baseline v2 | 98.66% | 98.66% | 0 / 221 | 0.00% |
| Original BERT | 96.43% | 94.20% | 5 / 216 | 2.31% |
| Defended BERT | 96.43% | 95.09% | 3 / 216 | 1.39% |

Speaker notes: ASR is conditional: its denominator is initially detected phishing, including examples without candidates. It is not the percentage of all mail. Pretrained DistilBERT was not evaluated under attack. The three models each used 6556 total queries.

## 11. Did augmentation help?

A separate preserved checkpoint, evaluated without retuning.

- Original / defended candidate ASR: 2.31% / 1.39%.
- Common clean-detected phishing: 215; newly evaded original / defended: 4 / 3.
- Compare clean errors, fixed corruption and fresh search together.
- Continued training and augmentation are combined; no clean-only continuation control.
- One seed and one finite search cannot establish universal robustness.

Speaker notes: Use common eligibility to reduce the denominator mismatch. Explain the paired whole-group clean contrast and ASR uncertainty. Do not attribute every difference causally to augmentation.

## 12. Review errors without changing the test

A bounded, deterministic post-score review.

- Reviewed 11 unique clean cases and 3 attack cases.
- Publisher labels remain fixed in primary metrics, even when context is incomplete.
- All 3 attack edits preserve meaning; the original phishing identity is ambiguous.
- No independently confirmed malicious-evasion lower bound above zero.
- AI-assisted inspection is not exhaustive independent human annotation.

Speaker notes: The three reviewed defended successes are short sharing/account notifications. Their typos preserve meaning, but available text cannot independently confirm a phishing identity. Thus 3/216 is publisher-label-dependent candidate ASR. Keep labels unchanged and do not call these confirmed real-world malicious evasions. Raw text stays local. Explain nonidentifying clean-error themes from the review report. Distinguish a model mistake, missing evidence, and an uncertain publisher label. Students should independently review the bounded sample.

## 13. The local demonstration

Choose a model, paste English email text, inspect the result.

- 127.0.0.1:7860 | local inference
- Score, decision, model identity and truncation
- Baseline term contributions; labeled text indicators
- No link fetching, message delivery or saved submissions
- Not flagged does not mean safe

Speaker notes: Use invented public examples for the live demo. Show a normal result, a model change, the identity panel, an overlength error and Clear. Scores across models are not directly comparable.

## 14. Verification is part of the deliverable

Separate software correctness from model-quality evidence.

- 354 offline tests, including final-freeze and leakage guards.
- Two full final runs: identical prediction and candidate-bank bytes.
- Independent confusion / ASR / query recounts and unchanged 79 input files.
- Original neural tensors and all frozen thresholds remain unchanged.
- Windows + Linux CI; local demo and desktop/mobile browser checks.

Speaker notes: A complete repeated run demonstrates numerical reproducibility in this environment, not new independent statistical evidence. Reproduction instructions and all aggregate reports are versioned.

## 15. What the project establishes

A reproducible detection-and-robustness study with a working demo.

- Model quality depends on source, wording, threshold and the chosen error cost.
- A small controlled edit can expose a miss; finite resistance is not a guarantee.
- The final reserve is now consumed and must not become a tuning set.
- Next research: contemporary both-class data, independent labels, stronger grouped evaluation, multiple seeds and a clean-only defense control.

Speaker notes: Conclude using the measured results, not a claim of a production email gateway. Any future improvements need fresh held-out evidence. Discuss what an organization would still need before deployment.

## 16. Reproduce, review, present

Shared responsibility; transparent assistance.

- Lior: reproduction guide, local demonstration and packaging (W10: 5 units).
- Sharon Elimelech: comparative report, conclusions and presentation (W10: 5 units).
- Both students review the implementation and can explain the complete pipeline.
- AI-assisted code and documents; assigned ownership is not invented personal authorship.
- Repository: github.com/liorma6/AI-security-agent- | docs/submission.md

Speaker notes: Course submission and personal review remain human actions. Sources: supplied Project2_PhishGuard brief; frozen dataset/model manifests; scikit-learn and Hugging Face documentation; TextAttack method reference; final protocol and measured reports.
