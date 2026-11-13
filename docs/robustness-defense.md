# Stage 7 - Separate augmentation defense

This stage preserves all earlier models and trains a separate BERT-Tiny continuation with perturbed training copies. The [packaged protocol](../src/phishguard/defense/protocol.json) is fixed before development-copy generation and training. Implementation checks precede real experiments; measured outcomes will be added after execution. Stage 8 is outside this stage.

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
