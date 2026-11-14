# PhishGuard implementation plan

Updated November 14, 2026. The [project book](project-book.md) defines the course scope, requirements, research protocol and equal Lior/Sharon ownership. The [stage log](stage-log.md) records completed work and actual checks.

Stages 0-8 and additional checkpoints 4a/4b are complete at their stated scope: eleven completed milestones out of twelve including both checkpoints. Stage 9 (final evaluation and submission) is in progress: its protocol is being committed before reserve scoring. Complete one requested stage at a time, verify its acceptance criteria and commit it before starting the next stage. Student review and course approval remain separate from implementation status.

## Stages and acceptance criteria

| Stage | Deliverable and acceptance | Responsibility | Status |
| --- | --- | --- | --- |
| 0. Specification | Eight course chapters, PG01-PG10 requirements, STRIDE, UML, planned tests, learning record and balanced ownership; valid internal links and consistent status | Lior and Sharon review the AI-assisted drafts together | Draft prepared; verification recorded in stage log |
| 1. Python foundation and contracts | Select a compatible development environment; define email, prediction and artifact records; add small reviewed fixtures and input-validation tests; document runnable commands | Lior: contracts and setup. Sharon: validation cases and fixture review. W02 | Implemented and checked; student fixture review remains to be recorded |
| 2. Dataset preparation | Review source/license and labels; ingest and deduplicate; assign campaign/template groups where identifiable; freeze train/validation/test manifests; test group separation | Lior: provenance and ingestion. Sharon: labels, deduplication and split validator. W03 | Implemented and checked; individual student review remains open |
| 3. Classical baseline | Train TF-IDF plus logistic regression using training data only; save/load artifacts; select threshold on validation data; report held-out metrics and counts; test leakage and reproducibility | Lior: training and artifacts. Sharon: evaluation and leakage checks. W04 | Implemented, measured and reproduced; individual student review remains open |
| 4. Pretrained comparison | Select a task-compatible Hugging Face classifier; pin revision and verify label mapping; evaluate on the same dataset protocol and document resource conditions | Lior: model review and inference adapter. Sharon: label checks and comparative evaluation. W05 | Implemented and measured; individual student review remains open |
| 4a. Generalization audit | Freeze the existing baseline; audit internal relatives and shortcuts; evaluate publisher-labeled external phishing/ham; reserve separate groups without scoring; report limitations and uncertainty | Lior: provenance, downloads and MIME extraction. Sharon: overlap/split checks, label review and metrics. Shared W05 review | Completed: 1,639 external evaluations, 703 unscored reserve messages, reproduced results; student review open |
| 4b. Data refresh and baseline re-evaluation | Diagnose old errors; review new sources/labels; protect held-out groups; train separate real-mail baseline v2; freeze and compare historical/challenge results; reproduce and disclose limitations | Lior: sources, ingestion, extraction and model artifacts. Sharon: quality/group boundaries, evaluation, review trace and reproduction. W05 | Implemented, measured and reproduced; remaining false alarms and one inspection-boundary deviation disclosed; student review open |
| 5. Fine-tuned detector | Fine-tune a small transformer; record tokenizer, configuration, seeds, environment and artifact manifest; evaluate clean performance and investigate errors | Lior: training runner, environment and checkpoint artifacts. Sharon: tokenization/data boundaries, comparison, reproduction and error analysis. W06 | Implemented and measured: BERT-Tiny, validation-only selection, preserved baseline and byte-identical reproduction; student review open |
| 6. Controlled evasion | Implement bounded typos, character swaps and substitutions; trace variants to originals; review label preservation; report paired clean/attacked results and attack budgets | Lior: transformations, lineage and query-budget runner. Sharon: validity review, fixtures, paired/ASR metrics and reproduction. W07 | Implemented and measured: 19,969 frozen variants, unchanged models, explicit conditional ASR and bounded review; student review open |
| 7. Robustness defense | Train with reviewed training-only perturbations or another declared defense; compare clean cost, fixed variants and fresh equal-budget attacks without tuning on final test data | Lior: defended inference and clean-performance comparison. Sharon: augmentation and defense training. W08 | Implemented and reproduced: separate defended model, validation-only selection and fixed/fresh comparison; student review open |
| 8. Local demo | Provide Gradio email-paste interface, score, decision, model identity and evidence-based explanation; verify limits, error states, escaped output and privacy; document startup | Lior: UI integration and packaging. Sharon: explanations, privacy and usability checks. W09 | Implemented and checked: four local models, grounded explanations, privacy/error states and desktop/mobile browser checks; student review open |
| 9. Final evaluation and submission | Reproduce experiments; complete measured conclusions and current UML; deliver comparative report, runnable demo and final presentation | Lior: reproduction guide and demonstration. Sharon: comparative report and presentation. Both review all outputs. W10 | In progress: protocol frozen before reserve scoring; no outcomes yet |

The two-week security/AI learning record is W01 in the project book. Python, text processing and evaluation study continue alongside stages 1-3. Planning weights are 50 units per student; they are not assertions of logged hours or completed code.

## Stage completion procedure

1. Identify the stage requirements and the small set of acceptance checks before changing code.
2. Work on a focused stage branch, such as `stage/01-foundation`.
3. Implement the scope and run meaningful module tests, adding integration or experiment checks when required.
4. Record actual commands, results, limitations and student contributions in the stage log. Keep unit-test results separate from model performance.
5. Update the book, diagrams and README to match implemented capabilities. Keep datasets, raw private mail, checkpoints and secrets outside Git.
6. Review the changes, commit and publish through the normal repository workflow. Start the next stage only when requested.

## Decisions to resolve during implementation

The original selected dataset is the publisher-English subset of synthetic E-PhishLLM. Stage 4b adds a separate frozen real-mail-v2 development dataset and challenge without overwriting it. Stage 3 froze and applied marker removal before training, recorded shortcut diagnostics, selected its threshold on validation only and evaluated the frozen baseline. See the [baseline report](baseline.md) and completed [pretrained comparison](pretrained.md). Stage 4 pinned the external checkpoint, reviewed label/tokenizer compatibility, froze validation decisions and evaluated the identical test IDs. Stage 5 froze the fine-tuning configuration before training and selected the checkpoint/threshold before benchmark scoring. Profile compute and input limits before demo release. Keep final test data independent of model, attack and defense tuning. A missing model must produce an explicit unavailable state rather than a fabricated score.

## Stage 4a outcome

The [generalization audit](generalization-audit.md) measured the unchanged baseline at 92.86% external accuracy, 91.75% balanced accuracy, 88.70% phishing recall and 5.19% legitimate false-positive rate. Internal accuracy was 98.43%; the audit supports a generalization concern without isolating its cause as excessive training. The original grouping passed; a broader check found one additional train/test subject relation. No data, model weights, features or threshold were changed to improve results.

Before any stage-5 training, freeze the training-source and extraction/label policies, validation objective and a fresh final-evaluation protocol. The inspected audit cohort is now development evidence; future tuning cannot treat it as unseen final data. Keep the 703 reserve messages unscored until a separately committed final protocol is ready. Their source/era confounding remains; more representative contemporary data containing both classes is desirable. Stage 4b subsequently added reviewed data and retrained the classical baseline as described below. The subsequently requested stage 5 is recorded below.

Stage 4a is part of W05 and preserves the book's 50/50 planning allocation. Lior leads external provenance/MIME handling; Sharon Elimelech leads relatedness, partitions, metrics and label-review verification. Both review limitations and can explain the outcome. AI assistance is recorded; individual student authorship/review must be logged when actually performed.

## Stage 4b outcome and next-stage gate

The [data refresh](baseline-refresh.md) is complete: 3,261 training and 745 validation rows, a frozen 425-row historical benchmark, and a separate 2,000-row challenge. Baseline v2 uses the same classical algorithm; validation selects threshold 0.31. Historical accuracy improves from 82.59% to 98.82%, while challenge accuracy improves from 66% to 80.10%. Challenge false-positive rate remains 37.20%; its 100 original records of unverified provenance obtain only 62% accuracy. Original v1/data and all 703 reserve rows remain unchanged and unscored. Repeated preparation, fit, predictions and independent counts match.

One provisional-training review row moved into the historical test after regrouping. Its disclosed post-hoc exclusion leaves 424 rows and unchanged rounded v2 accuracy; this does not create a new independent final test. Preserve the review trace and carry all reviewed IDs into a development-only registry before future split regeneration. Retain current scored cohorts as research benchmarks, not untouched final evidence.

These stage-4b gates were carried into stage 5: freeze the model/data/validation policy before fitting, protect reviewed families and keep final evaluation separate from later detector, attack and defense choices. Do not use test/challenge or reserve outcomes to select hyperparameters. Seek contemporary both-class data for stronger claims; the current source/era and publisher-processing limits remain. No production-readiness claim is supported.

W05 remains equally allocated: Lior leads source review, ingestion, extraction and model persistence; Sharon Elimelech leads data quality, relatedness/split checks, metrics, inspection-boundary trace and reproduction. Both review conclusions. This is assigned responsibility for AI-assisted work, not a claim that either student has already personally completed or reviewed each item.

## Stage 5 outcome and next-stage gate

The [fine-tuned detector](finetuned.md) is complete. A pinned Google BERT-Tiny encoder and new classification head were trained on the same 3,261-row development training split; 745 validation rows alone selected epoch 5 and threshold 0.69. Baseline v1/v2 and the earlier pretrained model remain unchanged. The reviewed-ID registry excludes the full two-row historical family, so both models compare on the same 423 historical and 2,000 challenge rows. All 703 reserve messages remain unscored and unreviewed.

Historical baseline/transformer accuracy is 98.82%/98.58%; challenge accuracy is 80.10%/80.80%. The transformer reduces challenge false alarms from 37.20% to 29.80%, but recall drops from 97.40% to 91.40% and F1 declines slightly. Same-seed retraining and rescoring reproduce selected artifacts/predictions exactly; independent recounts agree. Seventeen deterministic post-score excerpts support bounded error analysis without changing labels or the frozen model. These are retrospective research benchmarks and do not establish deployment readiness.

W06 preserves five planning units per student: Lior leads the training runner, environment/configuration and artifact handling; Sharon Elimelech leads tokenization, data boundaries, paired metrics, reproduction and error analysis. Both review results. AI-assisted implementation and review are recorded without inventing completed individual student authorship.

The subsequently requested stage 6 freezes perturbation/query bounds, retains parent/group lineage, reviews label preservation and separates attack development from final evaluation, as recorded below. Do not retune the stage-5 checkpoint/threshold after seeing these benchmarks. The final stage-9 reserve protocol must freeze all detector, attack and defense decisions before scoring; the reserve must not become a model-selection set. After stage 5, controlled evasion was the next requested milestone. Its completed outcome follows; defense, demo and final submission remain.

## Stage 6 outcome and next-stage gate

The [controlled-evasion experiment](controlled-evasion.md) is complete. Protocol/code `593c1af` precedes scoring; training-only preflight and the 19,969-variant bank were frozen at `427685b`. Both models retain their exact stage-5 identities and thresholds. All 2,423 historical/challenge originals remain in their original groups/splits; variants inherit lineage, with no training, validation or reserve mail read during scoring. The prior two-row family exclusion remains. The 703-message reserve is unscored and unreviewed.

Constraint-pass candidate ASR is 0/161 versus 1/158 on historical mail and 8/974 versus 95/914 on the challenge for baseline/BERT. The common 909 challenge phishing originals yield 4 versus 91 evasions. These conditional figures are distinct from overall accuracy and from exhaustive semantic validation. Twelve training-only pairs and ten successful benchmark variants were contextually reviewed with AI assistance. Complete repeated bank/scoring runs are byte-identical, independent counts agree, and all 67 preserved model/processed-data files are unchanged. The 292-test suite covers the new bounds and separation rules.

W07 remains five planning units each. Lior leads transformations, parent/group/split lineage and the budgeted runner. Sharon Elimelech leads label-preservation review, paired/ASR metrics, fixtures and independent reproduction. Both review conclusions; personal student work/review is recorded only when actually performed.

The subsequently requested stage 7 implements these gates: training-only copies with pre-fit sample review, validation-only selection, preserved original checkpoints and clean/fixed/fresh comparisons. Existing scored cohorts stay retrospective benchmarks. Before stage 9, freeze all detector, threshold, attack and defense choices and the final reserve protocol; do not retune on final outcomes. Stage 7 is recorded below; stages 8 (local demo) and 9 (final evaluation/submission) remain.

## Stage 7 outcome and next-stage gate

The [augmentation defense](robustness-defense.md) is complete. Three declared epochs continued the exact original BERT into a separate model; validation selected epoch 1 and threshold 0.07. Training uses 6,522 clean/copied views of 3,261 training parents only. All original models, data and stage-6 artifacts remain unchanged; 703 reserve messages remain unscored/unreviewed.

Challenge original/defended clean accuracy is 80.80%/80.80%, recall 91.40%/92.10% and false-positive rate 29.80%/30.50%. Fixed-bank candidate ASR is 95/914 (10.39%) versus 98/921 (10.64%); fresh-search ASR is 95/914 (10.39%) versus 93/921 (10.10%). Candidate ASR is conditional on automatic constraints and bounded review, not exhaustive semantic certification. Known cohorts, source/template bias and the absence of a clean-only continued-training control limit causal and deployment claims.

Full repeated preparation, training and evaluation are byte-identical; independent counts and preserved-file checks pass. W08 keeps five units each: Lior leads defended inference/integration and clean-cost comparison; Sharon Elimelech leads augmentation, defense training and verification. Both review interpretation; AI assistance and open student review remain explicit.

The subsequently requested stage 8 implements the local demo and extends the current pretrained comparison, as recorded below. Before stage 9, freeze all detector, threshold, attack and defense choices and the final reserve protocol. Do not retune using final outcomes.

## Stage 8 outcome and final-stage gate

The [local demo](demo.md) is implemented and browser-checked with all four preserved models. It provides validation-selected decisions, exact identities, token truncation, linear feature contributions for the baseline and clearly labeled text indicators for the transformers. It runs only on loopback, does not persist submitted email and refuses uploads, oversized requests and project-file serving. The original BERT starting view is a continuity choice, not a new model-quality winner.

The [comparison extension](current-comparison.md) addresses the course's pretrained-result comparison on the same 423 historical and 2,000 challenge messages. A separate threshold of 0.45 was fixed from validation alone before scoring; no weights changed. Independent counts match, the three old clean results reproduce and 79 prior model/data files remain byte-identical. All 703 reserve messages stay unscored/unreviewed.

The 340-test suite passes locally. Actual browser checks cover the four models, invalid/overlength/HTML-like input, truncation, clear/reset, mobile layout and blocked routes; no external browser requests were observed. The book and operational guides are updated. W09 stays five units each: Lior owns UI/model integration and packaging; Sharon Elimelech owns explanation methods, privacy/error tests and usability review. The W05 comparison extension remains shared review. AI assistance is recorded; neither student's personal review is invented.

Stage 9 is the only remaining milestone. Before touching the reserve, commit the final model/threshold/attack/defense and evaluation protocol. Then execute that frozen evaluation without retuning, finish the comparative conclusions and submission materials, and prepare the final presentation. Stage 8 does not perform that final evaluation or guarantee production accuracy.
