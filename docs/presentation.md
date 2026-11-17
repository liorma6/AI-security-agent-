# PhishGuard final presentation

English slide content and speaker notes; generated artifacts are stored locally in the project outputs directory.

## 1. PhishGuard

Phishing detection and controlled adversarial robustness

- Lior Mashaich & Sharon Elimelech
- Supervisor: Zimon Roi
- HIT | AB- Ai Security | November 17, 2026
- An academic research prototype with a local email demo.

Speaker notes: Introduce the research question and the two students. Development and documentation were AI-assisted; students must review and explain the implementation.

## 2. What are we testing?

Detection quality is only one part of the question.

- Can a classifier separate phishing from legitimate email?
- Can small constrained text changes turn a detection into a miss?
- Does augmentation improve robustness without unacceptable clean-data cost?
- Can we demonstrate the result while making uncertainty visible?

Speaker notes: Define a false negative as missed phishing and a false positive as a legitimate message flagged incorrectly. A passing test suite does not prove detection quality.

## 3. Requirements: data and detectors

PG01-PG05 | Specification requirements mapped to evidence.

| ID | Requirement | Evidence |
| --- | --- | --- |
| PG01 | Learn the foundations | Learning record; personal evidence remains open |
| PG02 | Collect and prepare data | Pinned sources, grouped splits and manifests |
| PG03 | Classical ML baseline | TF-IDF + logistic regression; preserved v1/v2 |
| PG04 | Pretrained HF comparison | Pinned DistilBERT; identical evaluation IDs |
| PG05 | Fine-tune a transformer | BERT-Tiny; validation selection and full repeat |

Speaker notes: Map these rows to project-book section 3.18. Distinguish implemented artifacts from each student's remaining learning evidence. The external phishing classifier and the general encoder we fine-tuned are different models.

## 4. Requirements: evaluation and product

PG06-PG10 | Explain both delivered behavior and its limits.

| ID | Requirement | Evidence |
| --- | --- | --- |
| PG06 | Controlled text evasion | Three edit families, lineage and query caps |
| PG07 | Measure degradation | Clean/fixed/directed results and candidate ASR |
| PG08 | Evaluate a defense | Training-only augmentation; inconsistent gains |
| PG09 | Pasted-email web demo | Local UI, score, evidence and checked error states |
| PG10 | Report and presentation | Frozen final report, project book and this deck |

Speaker notes: The defense requirement is implemented and measured. Do not present it as a guaranteed improvement. The One Pager, poster, source and links handoff support the additional submission checklist.

## 5. One pipeline, two separate workflows

Offline experiments produce frozen artifacts; the UI only runs inference.

- DATA: reviewed sources, inert extraction, deduplication and grouped splits.
- MODELS: classical baseline, pretrained comparison, fine-tuning and defense.
- EVALUATION: frozen clean inputs, bounded variants, metrics and verification.
- DEMO: paste text, select a model, inspect score, decision and evidence.

Speaker notes: Explain why no training, email transmission or link following is available from the demo. Discuss the trust boundaries in the STRIDE chapter.

## 6. How the components communicate

Separate inference, research workflows and frozen artifacts.


![How the components communicate](../assets/architecture-overview.png)

Speaker notes: Use the component overview for an oral explanation. The detailed component and sequence UML are in chapter 7. The demo does not expose training or arbitrary model paths. The application uses versioned local files, not a user database.

## 7. Keep development separate from evidence

Groups and derived variants stay together.

| Partition | Messages | Purpose |
| --- | --- | --- |
| Training | 3,261 | Fit the current local models |
| Validation | 745 | Select checkpoints and thresholds |
| Retrospective benchmarks | 423 + 2,000 | Historical and mainly synthetic challenge |
| Final reserve | 703 / 432 groups | Frozen evaluation after all choices |

Speaker notes: The final reserve has 479 legitimate and 224 phishing messages. It was held out from local selection, but shares source families and years with development. It is not a new representative real-world inbox.

## 8. Four preserved candidates

Architecture and training history are different.

| Candidate | How obtained | Threshold | Text budget |
| --- | --- | --- | --- |
| Baseline v2 | TF-IDF + logistic regression | 0.31 | Full accepted text |
| Original BERT | Locally fine-tuned BERT-Tiny | 0.69 | 256 tokens |
| Defended BERT | Separate augmentation continuation | 0.07 | 256 tokens |
| HF DistilBERT | Existing pretrained phishing classifier | 0.45 | 512 tokens |

Speaker notes: The downloaded phishing classifier is distinct from the general BERT-Tiny encoder we fine-tuned. Thresholds were validation-selected, not tuned on the final reserve. Scores are not calibrated probabilities.

## 9. The evaluation was frozen first

Protocol and executable code committed before reserve scoring.

- Freeze commit: 77c4a17. It binds 96 source/reference files and 79 preserved inputs.
- All four models scored the same 703 clean messages with existing thresholds.
- The three trained candidates used the same seed-9042 attack bank.
- No refitting, relabeling, threshold changes or test-based model replacement.

Speaker notes: Show the protocol commit and final report in GitHub. Explain the clean-worktree gate, file hashes, development-overlap rejection and frozen post-score review selection.

## 10. Final clean results

703 held-out messages: 224 phishing and 479 legitimate.

| Model | Accuracy | Phishing recall | Missed phishing | False alarms |
| --- | --- | --- | --- | --- |
| Baseline v2 | 99.29% | 98.66% | 3 | 2 |
| Original BERT | 98.29% | 96.43% | 8 | 4 |
| Defended BERT | 98.15% | 96.43% | 8 | 5 |
| HF DistilBERT | 95.16% | 89.73% | 23 | 11 |

Speaker notes: Read counts as well as accuracy. Compare the two error types explicitly. These are source-conditioned held-out results; the same models behaved differently on the challenge dataset. Group-based intervals and per-source results are in the report.

## 11. Changing the dataset changes the result

Do not average different cohorts into one claimed product accuracy.


![Changing the dataset changes the result](../assets/accuracy-by-cohort.png)

Speaker notes: The historical cohort has 423 messages; the challenge has 2,000 and is mainly generated; the reserve has 703 held-out messages. The pretrained classifier had 87.25% challenge accuracy but missed 136 of 1,000 phishing messages. Source and template effects matter.

## 12. Different errors have different costs

Challenge cohort | 1,000 phishing and 1,000 legitimate messages.


![Different errors have different costs](../assets/challenge-error-tradeoff.png)

Speaker notes: Read the two error counts separately. The pretrained classifier misses 136 phishing but produces 119 false alarms. The baseline misses 26 but produces 372 false alarms. The challenge is mainly synthetic; this is not an inbox forecast.

## 13. Controlled evasion, not unrestricted attacks

A fixed, inspectable search budget.

- Three operations: duplicate a letter, swap internal letters, substitute a listed word.
- At most 3 changed words and 10% of body words; first 1,500 body characters only.
- Protect URLs, addresses, numbers, markup, capitalization and listed negations.
- 5,853 candidates; at most 12 candidates plus 1 clean query per message/model.
- Automatic constraints do not certify that every candidate preserves meaning.

Speaker notes: The generator never sees gradients or model scores. Each model scores the same finite candidate bank. Original messages are included in minimum-score selection; legitimate originals stay clean in directed-evasion metrics.

## 14. What happened under the fixed budget?

Candidate ASR counts newly evaded, initially detected phishing.

| Model | Clean recall | Attacked recall | New misses / detected | Candidate ASR |
| --- | --- | --- | --- | --- |
| Baseline v2 | 98.66% | 98.66% | 0 / 221 | 0.00% |
| Original BERT | 96.43% | 94.20% | 5 / 216 | 2.31% |
| Defended BERT | 96.43% | 95.09% | 3 / 216 | 1.39% |

Speaker notes: ASR is conditional: its denominator is initially detected phishing, including examples without candidates. It is not the percentage of all mail. Pretrained DistilBERT was not evaluated under attack. The three models each used 6556 total queries.

## 15. Did augmentation help?

A separate preserved checkpoint, evaluated without retuning.

- Original / defended candidate ASR: 2.31% / 1.39%.
- Common clean-detected phishing: 215; newly evaded original / defended: 4 / 3.
- Compare clean errors, fixed corruption and fresh search together.
- Continued training and augmentation are combined; no clean-only continuation control.
- One seed and one finite search cannot establish universal robustness.

Speaker notes: Use common eligibility to reduce the denominator mismatch. Explain the paired whole-group clean contrast and ASR uncertainty. Do not attribute every difference causally to augmentation.

## 16. Review errors without changing the test

A bounded, deterministic post-score review.

- Reviewed 11 unique clean cases and 3 attack cases.
- Publisher labels remain fixed in primary metrics, even when context is incomplete.
- All 3 attack edits preserve meaning; the original phishing identity is ambiguous.
- No independently confirmed malicious-evasion lower bound above zero.
- AI-assisted inspection is not exhaustive independent human annotation.

Speaker notes: The three reviewed defended successes are short sharing/account notifications. Their typos preserve meaning, but available text cannot independently confirm a phishing identity. Thus 3/216 is publisher-label-dependent candidate ASR. Keep labels unchanged and do not call these confirmed real-world malicious evasions. Raw text stays local. Explain nonidentifying clean-error themes from the review report. Distinguish a model mistake, missing evidence, and an uncertain publisher label. Students should independently review the bounded sample.

## 17. The interface contract

Documentation wireframe of implemented behavior, not an earlier design artifact.


![The interface contract](../assets/ui-wireframe.png)

Speaker notes: Walk through model selection, optional subject, body, Analyze and Clear. Explain the Ready, Analyzing, Result, Validation error and Model unavailable states. This is a schematic, while the following images are actual browser captures.

## 18. The local demonstration

Choose a model, paste English email text, inspect the result.

- 127.0.0.1:7860 | local inference
- Score, decision, model identity and truncation
- Baseline term contributions; labeled text indicators
- No link fetching, message delivery or saved submissions
- Not flagged does not mean safe

![The local demonstration](../assets/demo.png)

Speaker notes: Use invented public examples for the live demo. Show a normal result, a model change, the identity panel, an overlength error and Clear. Scores across models are not directly comparable.

## 19. The same demo on mobile

Actual stage-8 Chromium capture of the empty ready state.

- The form and result stack vertically on a narrow screen.
- The same four model choices and validation rules apply.
- The result area is ready; no prediction is shown in this capture.
- Clear resets the displayed form and result.

![The same demo on mobile](../assets/demo-mobile.png)

Speaker notes: This is the recorded browser screenshot, not a generated mockup. Open the full resolution image or live UI to inspect small text. The form is empty and contains no email content. No new browser-verification run is claimed here.

## 20. Verification is part of the deliverable

Separate software correctness from model-quality evidence.

- 354 offline tests, including final-freeze and leakage guards.
- Two full final runs: identical prediction and candidate-bank bytes.
- Independent confusion / ASR / query recounts and unchanged 79 input files.
- Original neural tensors and all frozen thresholds remain unchanged.
- Windows + Linux CI; local demo and desktop/mobile browser checks.

Speaker notes: A complete repeated run demonstrates numerical reproducibility in this environment, not new independent statistical evidence. Reproduction instructions and all aggregate reports are versioned.

## 21. Problems found and responses

The research record includes unsuccessful results and boundary corrections.

- Source shift: add external audits and report each cohort separately.
- Reviewed-family overlap: disclose it and exclude the whole family for later comparisons.
- Long emails: disclose token truncation instead of hiding discarded content.
- Small defense gains: retain clean-cost comparisons and state the missing control.

Speaker notes: The two-row historical exclusion is documented, not erased. Better source-matched accuracy does not remove challenge weaknesses. A clean-only continued-training control and new independent labels remain future research.

## 22. What the project establishes

A reproducible detection-and-robustness study with a working demo.

- Model quality depends on source, wording, threshold and the chosen error cost.
- A small controlled edit can expose a miss; finite resistance is not a guarantee.
- The final reserve is now consumed and must not become a tuning set.
- Next research: contemporary both-class data, independent labels, stronger grouped evaluation, multiple seeds and a clean-only defense control.

Speaker notes: Conclude using the measured results, not a claim of a production email gateway. Any future improvements need fresh held-out evidence. Discuss what an organization would still need before deployment.

## 23. Submission materials and demonstration

A traceable handoff for review, reproduction and presentation.

- One Pager, eight-chapter specification and English PowerPoint with notes.
- Measured reports, graphs, screenshots, interface wireframe and poster.
- GitHub source, source-only ZIP and local installation/demo instructions.
- Personal learning/review evidence and actual course submission remain open.

Speaker notes: Repository: https://github.com/liorma6/AI-security-agent-. Use docs/submission.md and docs/submission-review.md. No recorded/published YouTube link exists in the verified package. Research datasets and learned weights are excluded from the code ZIP.

## 24. Reproduce, review, present

Shared responsibility; transparent assistance.

- Lior Mashaich: reproduction guide, local demonstration and packaging (W10: 5 units).
- Sharon Elimelech: comparative report, conclusions and presentation (W10: 5 units).
- Both students review the implementation and can explain the complete pipeline.
- AI-assisted code and documents; assigned ownership is not invented personal authorship.
- Repository: github.com/liorma6/AI-security-agent- | docs/submission.md

Speaker notes: Course submission and personal review remain human actions. Sources: supplied Project2_PhishGuard brief; frozen dataset/model manifests; scikit-learn and Hugging Face documentation; TextAttack method reference; final protocol and measured reports.
