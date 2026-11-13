# PhishGuard implementation plan

Updated November 13, 2026. The [project book](project-book.md) defines the course scope, requirements, research protocol and equal Lior/Sharon ownership. The [stage log](stage-log.md) records completed work and actual checks.

Stages 0-4 and the additional stage 4a generalization checkpoint are complete at their stated scope: six completed milestones out of eleven including the checkpoint. Five stages (5-9) remain. Stage 5 has not started. Complete one requested stage at a time, verify its acceptance criteria and commit it before starting the next stage. Student review and course approval remain separate from implementation status.

## Stages and acceptance criteria

| Stage | Deliverable and acceptance | Responsibility | Status |
| --- | --- | --- | --- |
| 0. Specification | Eight course chapters, PG01-PG10 requirements, STRIDE, UML, planned tests, learning record and balanced ownership; valid internal links and consistent status | Lior and Sharon review the AI-assisted drafts together | Draft prepared; verification recorded in stage log |
| 1. Python foundation and contracts | Select a compatible development environment; define email, prediction and artifact records; add small reviewed fixtures and input-validation tests; document runnable commands | Lior: contracts and setup. Sharon: validation cases and fixture review. W02 | Implemented and checked; student fixture review remains to be recorded |
| 2. Dataset preparation | Review source/license and labels; ingest and deduplicate; assign campaign/template groups where identifiable; freeze train/validation/test manifests; test group separation | Lior: provenance and ingestion. Sharon: labels, deduplication and split validator. W03 | Implemented and checked; individual student review remains open |
| 3. Classical baseline | Train TF-IDF plus logistic regression using training data only; save/load artifacts; select threshold on validation data; report held-out metrics and counts; test leakage and reproducibility | Lior: training and artifacts. Sharon: evaluation and leakage checks. W04 | Implemented, measured and reproduced; individual student review remains open |
| 4. Pretrained comparison | Select a task-compatible Hugging Face classifier; pin revision and verify label mapping; evaluate on the same dataset protocol and document resource conditions | Lior: model review and inference adapter. Sharon: label checks and comparative evaluation. W05 | Implemented and measured; individual student review remains open |
| 4a. Generalization audit | Freeze the existing baseline; audit internal relatives and shortcuts; evaluate publisher-labeled external phishing/ham; reserve separate groups without scoring; report limitations and uncertainty | Lior: provenance, downloads and MIME extraction. Sharon: overlap/split checks, label review and metrics. Shared W05 review | Completed: 1,639 external evaluations, 703 unscored reserve messages, reproduced results; student review open |
| 5. Fine-tuned detector | Fine-tune a small transformer; record tokenizer, configuration, seeds, environment and artifact manifest; evaluate clean performance and investigate errors | Lior: training runner. Sharon: tokenization, reproducibility and error analysis. W06 | Planned |
| 6. Controlled evasion | Implement bounded typos, character swaps and substitutions; trace variants to originals; review label preservation; report paired clean/attacked results and attack budgets | Lior: perturbations and query budget. Sharon: validity review, fixtures and metrics. W07 | Planned |
| 7. Robustness defense | Train with reviewed training-only perturbations or another declared defense; compare clean cost, fixed variants and fresh equal-budget attacks without tuning on final test data | Lior: defended inference and clean-performance comparison. Sharon: augmentation and defense training. W08 | Planned |
| 8. Local demo | Provide Gradio email-paste interface, score, decision, model identity and evidence-based explanation; verify limits, error states, escaped output and privacy; document startup | Lior: UI integration and packaging. Sharon: explanations, privacy and usability checks. W09 | Planned |
| 9. Final evaluation and submission | Reproduce experiments; complete measured conclusions and current UML; deliver comparative report, runnable demo and final presentation | Lior: reproduction guide and demonstration. Sharon: comparative report and presentation. Both review all outputs. W10 | Planned |

The two-week security/AI learning record is W01 in the project book. Python, text processing and evaluation study continue alongside stages 1-3. Planning weights are 50 units per student; they are not assertions of logged hours or completed code.

## Stage completion procedure

1. Identify the stage requirements and the small set of acceptance checks before changing code.
2. Work on a focused stage branch, such as `stage/01-foundation`.
3. Implement the scope and run meaningful module tests, adding integration or experiment checks when required.
4. Record actual commands, results, limitations and student contributions in the stage log. Keep unit-test results separate from model performance.
5. Update the book, diagrams and README to match implemented capabilities. Keep datasets, raw private mail, checkpoints and secrets outside Git.
6. Review the changes, commit and publish through the normal repository workflow. Start the next stage only when requested.

## Decisions to resolve during implementation

The selected dataset is the publisher-English subset of synthetic E-PhishLLM. Stage 3 froze and applied marker removal before training, recorded shortcut diagnostics, selected its threshold on validation only and evaluated the frozen baseline. See the [baseline report](baseline.md) and completed [pretrained comparison](pretrained.md). Stage 4 pinned the external checkpoint, reviewed label/tokenizer compatibility, froze validation decisions and evaluated the identical test IDs. Select the fine-tuning configuration before stage 5 training. Profile compute and input limits before demo release. Keep final test data independent of model, attack and defense tuning. A missing model must produce an explicit unavailable state rather than a fabricated score.

## Stage 4a outcome and next-stage gate

The [generalization audit](generalization-audit.md) measured the unchanged baseline at 92.86% external accuracy, 91.75% balanced accuracy, 88.70% phishing recall and 5.19% legitimate false-positive rate. Internal accuracy was 98.43%; the audit supports a generalization concern without isolating its cause as excessive training. The original grouping passed; a broader check found one additional train/test subject relation. No data, model weights, features or threshold were changed to improve results.

Before any stage-5 training, freeze the training-source and extraction/label policies, validation objective and a fresh final-evaluation protocol. The inspected audit cohort is now development evidence; future tuning cannot treat it as unseen final data. Keep the 703 reserve messages unscored until a separately committed final protocol is ready. Their source/era confounding remains; more representative contemporary data containing both classes is desirable. No additional data collection, fine-tuning, evasion or defense work is claimed here. Stage 5 requires the next requested stage.

Stage 4a is part of W05 and preserves the book's 50/50 planning allocation. Lior leads external provenance/MIME handling; Sharon Elimelech leads relatedness, partitions, metrics and label-review verification. Both review limitations and can explain the outcome. AI assistance is recorded; individual student authorship/review must be logged when actually performed.
