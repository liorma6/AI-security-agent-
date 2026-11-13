# PhishGuard implementation plan

Updated November 13, 2026. The [project book](project-book.md) defines the course scope, requirements, research protocol and equal Lior/Sharon ownership. The [stage log](stage-log.md) records completed work and actual checks.

Stages 0-3 are implemented at their stated scope: specification, Python foundation, dataset preparation and the trained/evaluated classical baseline. Stages 4-9 are not implemented. Complete one requested stage at a time, verify its acceptance criteria and commit it before starting the next stage. Student review and course approval remain separate from implementation status.

## Stages and acceptance criteria

| Stage | Deliverable and acceptance | Responsibility | Status |
| --- | --- | --- | --- |
| 0. Specification | Eight course chapters, PG01-PG10 requirements, STRIDE, UML, planned tests, learning record and balanced ownership; valid internal links and consistent status | Lior and Sharon review the AI-assisted drafts together | Draft prepared; verification recorded in stage log |
| 1. Python foundation and contracts | Select a compatible development environment; define email, prediction and artifact records; add small reviewed fixtures and input-validation tests; document runnable commands | Lior: contracts and setup. Sharon: validation cases and fixture review. W02 | Implemented and checked; student fixture review remains to be recorded |
| 2. Dataset preparation | Review source/license and labels; ingest and deduplicate; assign campaign/template groups where identifiable; freeze train/validation/test manifests; test group separation | Lior: provenance and ingestion. Sharon: labels, deduplication and split validator. W03 | Implemented and checked; individual student review remains open |
| 3. Classical baseline | Train TF-IDF plus logistic regression using training data only; save/load artifacts; select threshold on validation data; report held-out metrics and counts; test leakage and reproducibility | Lior: training and artifacts. Sharon: evaluation and leakage checks. W04 | Implemented, measured and reproduced; individual student review remains open |
| 4. Pretrained comparison | Select a task-compatible Hugging Face classifier; pin revision and verify label mapping; evaluate on the same dataset protocol and document resource conditions | Lior: model review and inference adapter. Sharon: label checks and comparative evaluation. W05 | Planned |
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

The selected dataset is the publisher-English subset of synthetic E-PhishLLM. Stage 3 froze and applied marker removal before training, recorded shortcut diagnostics, selected its threshold on validation only and evaluated the frozen baseline. See the [baseline report](baseline.md). Select model revisions and the compatible training environment before their respective model stages. Profile compute and input limits before demo release. Keep final test data independent of model, attack and defense tuning. A missing model must produce an explicit unavailable state rather than a fabricated score.
