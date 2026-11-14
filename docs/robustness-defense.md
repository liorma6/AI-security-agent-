# Stage 7 - Separate augmentation defense

This stage preserves all earlier models and trains a separate BERT-Tiny continuation with perturbed training copies. The [packaged protocol](../src/phishguard/defense/protocol.json) is fixed before development-copy generation and training. Implementation, real training/comparison, complete reproduction and independent verification are complete. Stage 8 is outside this stage.

## Method and data boundaries

Continue the exact stage-5 BERT-Tiny checkpoint, rather than replace it. Keep the same tokenizer, 256-token limit, float32 CPU runtime and four numerical threads. Fix seed 42, three epochs, batch 16, AdamW learning rate 0.00002, weight decay 0.01, gradient clipping 1.0 and linear 10% warmup/decay before fitting. All encoder/head parameters update. This is one configuration; no benchmark-driven hyperparameter search is allowed.

The frozen 3,261 training parents each contribute one clean and one copied view. The copy is a deterministic stage-6 constrained perturbation or the unchanged original if no candidate exists. This gives equal weight to each parent and each view without overweighting messages with more possible edits. Both legitimate and phishing labels are retained. Training generation uses seed 101. A separate seed-102 copy for each of 745 validation parents is used only for selection, never for gradient updates. Existing groups/splits and the stage-5 full reviewed-family exclusion remain.

Generate at most twelve candidates per development parent, with unchanged three-family edits, protected spans, first-1,500-character limit, at most three words and 10% word-edit cap. Choose the lowest SHA256 rank of `choice:variant_id`, independent of scores. Freeze the copy manifest and review before fitting. Two selected training pairs per class/family are sampled deterministically for contextual review; an ambiguous or invalid decision blocks fitting. This review is bounded, AI-assisted evidence rather than exhaustive human certification. Raw originals/copies stay local. Augmentation development views are checked for train/validation overlap and conflicting cleaned-text labels.

Select the epoch with lowest cross-entropy on the equal clean/perturbed validation mixture; exact ties select the earlier epoch. At that checkpoint, use only clean validation phishing F1 to select the threshold using the existing frozen grid/ties. Record validation metrics for each view and original parent. Freeze the selected artifact/threshold before benchmark scoring. Original 0.69 and default 0.50 thresholds are prespecified diagnostics, not alternative choices selected using test results.

The new model is saved under `models/defended-v1/` with its own identity, parent revision, augmentation/review digests and development fingerprints. Source loading uses known local BERT code and safetensors only. Previous artifacts are never overwritten. Training opens training/validation mail only. Evaluation opens historical/challenge mail only and text-free metadata, rejecting development overlap. The 703-message reserve remains unscored and unreviewed; integrity checks hash bytes without parsing it.

## Comparison after model selection

Evaluate baseline v2, unchanged stage-5 BERT and the new defense on the same 423 historical and 2,000 challenge parents. These are known retrospective research benchmarks, not an untouched final test. Source/era confounding, mainly templated challenge data and uncertain publisher labels remain.

Use two separately reported candidate banks:

- Fixed: the exact committed stage-6 bank. Report clean metrics, first-candidate corruption on both classes, parent-BERT-selected transfer inputs and each model's own worst-of-budget search.
- Fresh: generate a seed-43 bank after checkpoint/threshold selection, under the same constraints and at most twelve candidates plus one clean prediction per parent/model. Select against each model's own fresh scores. Some candidate texts may coincide with the fixed bank; disclose that overlap. A fresh seed does not create new independent email data.

No early stopping, hidden queries, saliency probing or score-guided candidate generation is used. Each model receives the same bank and budget. Do not combine both banks into a nominal 13-query attack: each bank is its own comparison, with clean predictions counted separately. Per-family and diagnostic metrics reuse existing scores without extra queries.

Report clean accuracy, precision/recall/F1, false-positive rate and clean-performance changes; candidate ASR with all clean-detected phishing in its denominator, including no-candidate parents; common eligibility for all three models and for the original/defended BERT pair; source results, whole-group intervals, exact query counts, token-input no-ops and resource times. Directed phishing-only metrics leave legitimate originals clean by construction. Fixed-first corruption changes both classes. Parent-selected transfer chooses the lowest score under the original BERT, including the original itself, and evaluates that same input under all models.

After scoring, review up to two deterministic successful fresh-search defense variants per cohort/family. Report supported, ambiguous and invalid cases without retuning; count reviewed supported distinct parents separately as a lower bound. Automatic constraints do not prove semantic equivalence. A finite, model-independent candidate search is not a strongest-attack or certified-robustness claim.

The experiment combines continued fitting and augmentation. Without a clean-only continued-training control, it cannot attribute any change solely to augmentation. One fixed seed and same-environment reproduction do not estimate multi-seed variability. More robust behavior need not improve clean performance or deployment suitability. The distinction between augmentation and adversarial training follows [Morris et al., TextAttack (EMNLP 2020)](https://aclanthology.org/2020.emnlp-demos.16/); this implementation does not install or reproduce a TextAttack recipe.

## Local workflow

Use the existing `pretrained` environment and completed stages 5/6. No extra model download, API account or paid service is required. These implemented commands refuse existing output directories:

```sh
uv run --frozen phishguard defense prepare
uv run --frozen --extra pretrained phishguard defense train
uv run --frozen phishguard defense prepare-fresh
uv run --frozen --extra pretrained phishguard defense evaluate
uv run --frozen --extra pretrained phishguard defense predict --file tests/fixtures/email.json
```

Between preparation and training, commit `artifacts/defense-augmentation-v1/manifest.json` as `data/manifests/defense-augmentation-v1.json` and the text-free contextual decisions as `docs/reports/defense-preflight-review.json`. The training command enforces exact manifest/content and reviewed IDs. After training, commit the new `selection.json` as `data/manifests/defended-v1-selection.json`. After fresh preparation, commit its manifest as `data/manifests/defense-fresh-bank-v1.json` before benchmark inference. Never substitute new artifacts for those identities after scoring.

For full same-environment reproduction use new destinations and the same frozen references:

```sh
uv run --frozen phishguard defense prepare --output artifacts/defense-augmentation-reproduction-v1
uv run --frozen --extra pretrained phishguard defense train --augmentation artifacts/defense-augmentation-reproduction-v1 --output models/defended-reproduction-v1
uv run --frozen phishguard defense prepare-fresh --output artifacts/defense-fresh-bank-reproduction-v1
uv run --frozen --extra pretrained phishguard defense evaluate --model models/defended-reproduction-v1 --fresh-bank artifacts/defense-fresh-bank-reproduction-v1 --output artifacts/defense-reproduction-v1
uv run --frozen python scripts/verify_defense.py
uv run --frozen python scripts/review_defense.py select
uv run --frozen python scripts/review_defense.py verify
```

The verifier independently checks preserved files, repeated preparation/weights/selection/predictions, earlier fixed-bank scores, confusion/ASR/common/transfer/query counts and repeated group intervals. It expects local artifacts from both complete runs. The review selector writes text-free IDs to a new local folder; contextual review is a separate step before verification. Prediction returns model identity, score/decision and truncation metadata without saving/echoing the email.

W08 retains five planning units each: Lior leads defended inference, integration and clean-cost comparison; Sharon Elimelech leads training-only augmentation, defense training and verification. Both review interpretation. Implementation and initial review are AI-assisted; actual student contributions/review must be recorded when performed. Stage 8 has not started.

## Measured outcome

Stage 7 continues the preserved stage-5 checkpoint into a separate artifact. Code/protocol were frozen at `b1b6bb7`, and development-copy membership plus pre-fit review at `550f438`. The initial training report records clean commit `550f438`. Three epochs were declared in advance; validation selected epoch 1 and clean-validation F1 selected threshold 0.07. No historical/challenge score influenced epoch or threshold selection. The original model and baseline remain unchanged and available.

The 3,261 training parents contribute 6,522 fit views: one original plus one deterministic copy each. Of those copies, 3,193 contain constrained changes and 68 are clean fallbacks. All 745 validation parents similarly provide clean and separate perturbed views for checkpoint selection, with 13 clean fallbacks; none are fitted. Twelve selected training pairs were reviewed before fitting, with supported contextual preservation and explicit grammar/quoted-identifier caveats. Source labels are retained without claiming independent authenticity verification.

| Measure - 2,000-row challenge | Baseline v2 | Original BERT-Tiny | Defended BERT-Tiny |
| --- | --- | --- | --- |
| Threshold | 0.31 | 0.69 | 0.07 |
| Clean accuracy | 80.10% | 80.80% | 80.80% |
| Clean phishing recall | 97.40% | 91.40% | 92.10% |
| Clean legitimate false-positive rate | 37.20% | 29.80% | 30.50% |
| Clean phishing F1 | 83.03% | 82.64% | 82.75% |
| Clean TP / FP / TN / FN | 974 / 372 / 628 / 26 | 914 / 298 / 702 / 86 | 921 / 305 / 695 / 79 |
| Fixed-bank candidate ASR | 8/974 (0.82%) | 95/914 (10.39%) | 98/921 (10.64%) |
| Fresh-search candidate ASR | 10/974 (1.03%) | 95/914 (10.39%) | 93/921 (10.10%) |
| Fresh-search phishing-only accuracy | 79.60% | 76.05% | 76.15% |
| Fresh-search phishing-only recall | 96.40% | 81.90% | 82.80% |
| Fixed-bank first-corruption accuracy | 80.20% | 80.25% | 80.70% |
| Parent-selected fixed-bank transfer accuracy | 79.95% | 76.05% | 75.95% |

Relative to the original BERT, defended clean challenge accuracy changes by +0.00 percentage points, recall by +0.70 points and false-positive rate by +0.70 points. Counts, not a single headline accuracy, expose the cost of the defense. On the common 910 clean-detected challenge phishing parents, fresh-search successes are 92 for original BERT and 84 for the defense. This common denominator controls the different initial detection sets, but does not correct corpus bias.

Historical clean accuracy is 98.82% / 98.58% / 98.82% for baseline/original/defended BERT. Historical fresh candidate ASR is 0/161 (0.00%) / 0/158 (0.00%) / 2/159 (1.26%). These 423 historical rows preserve the original two-row reviewed-family exclusion. The challenge is still mainly synthetic, with only 91 groups and uncertain provenance for its 100 original records. Both cohorts are already-inspected retrospective benchmarks, not a fresh final test.

The fixed bank has 19,969 variants; the fresh seed-43 bank has 19,970. Of the fresh variants, 1,094 have the same parent/text as a fixed candidate. Fresh search means newly seeded candidate ranking and selection against each model's own scores; it does not imply disjoint messages or entirely new text. Each bank independently uses at most twelve candidates plus one clean prediction per parent/model. Do not pool the banks into a nominal 13-query attack. First-corruption metrics perturb both classes; directed phishing-only views leave legitimate originals clean by definition. Parent-selected transfer scores the same input chosen by the original BERT under all models.

Defended fresh challenge candidate-ASR group-bootstrap interval is 4.51%-17.02%. This is a 1,000-resample, seed-42 whole-group interval conditional on these cohorts and finite constraints. Candidate ASR includes no-candidate clean detections and assumes contextual label preservation under automatic constraints. A deterministic post-score review inspected 7 successful fresh variants; it remains bounded AI-assisted evidence, not exhaustive human certification. The challenge reviewed-supported lower bound is 4/921, reported separately from all candidate successes. The sample contains six supported variants from five originals and one ambiguous historical example with an uninformative extracted body. Its publisher label and automatic candidate count remain unchanged; it is excluded from reviewed-supported evidence. See the review for all decisions.

The old 0.69 threshold and default 0.50 are prespecified diagnostics only; the selected threshold stays 0.07. At 0.69 the defense's clean challenge accuracy is 82.30% and fresh candidate ASR is 117/884 (13.24%). Continued fitting and augmentation were not separated by a clean-only continuation control, so observed differences cannot be attributed solely to augmentation. One seed and this limited model-independent search do not establish universal robustness or deployment readiness.

Full repeated preparation, training and scoring produced byte-identical copies, selected model files, fresh bank and predictions, with identical validation history. Independent recounts match confusion, ASR, shared eligibility, transfer and query counts; the original fixed-bank model scores match stage 6 exactly. All 75 preserved model/data/stage-6 artifact files remain unchanged. Reserve integrity is checked by hashing, without parsing or scoring any of its 703 messages. Training/evaluation have separate read boundaries. Evidence: [defense protocol and commands](robustness-defense.md), [training](reports/defense-training.json), [comparison](reports/defense-evaluation.json), [verification](reports/defense-verification.json), [pre-fit review](reports/defense-preflight-review.json), [post-score review](reports/defense-label-review.json).

The defense does not consistently improve robustness: aggregate fixed-bank challenge ASR rises slightly, fresh-search ASR falls slightly, and historical fresh evasion increases. Common-eligible challenge counts improve modestly, while clean accuracy stays unchanged and false alarms increase. This is a completed defense experiment, not evidence for automatically replacing the original model. Stage 7 is complete at this experimental scope. Stage 8 has not started. Final stage-9 evaluation requires a separately frozen protocol after all model, threshold, attack and defense decisions; do not use reserve outcomes for further tuning.

Resource conditions: the first full fit/validation run took 414.59 seconds on the existing Ryzen 5 3600X CPU with four neural threads. The first comparison overlapped the separately fixed reproduction-training process, so its recorded times are instrumentation, not a controlled speed benchmark. Reproduction verifies result bytes rather than elapsed-time equality. Zero-event bootstrap intervals can degenerate to zero and do not establish zero future risk.
