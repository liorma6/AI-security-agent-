# PhishGuard reproduction and submission package

All twelve implementation milestones (0-9 and checkpoints 4a/4b) are complete at their stated scope. This package supports student review and presentation; it does not claim that a course submission or independent personal review has occurred. Repository content and prepared documents are in English.

## Deliverable map

| Item | Canonical source | Prepared local export |
| --- | --- | --- |
| Eight-chapter project book | [Project book](project-book.md) | PhishGuard-Initial-Project-Book.docx and .pdf, revision 1.9 |
| Final protocol and comparative report | [Final evaluation](final-evaluation.md) | Included in the book and slides |
| Machine-readable evidence | [Results](reports/final-evaluation.json), [verification](reports/final-verification.json), [review](reports/final-review.json) | Text-free aggregates; raw messages remain private |
| Presentation and speaker notes | [16-slide source](presentation.md), [builder](../scripts/build_presentation.py) | PhishGuard-Final-Presentation.pptx, .html and .pdf |
| Runnable demonstration | [Startup and privacy guide](demo.md) | Local four-model pasted-email interface |
| Work allocation and evidence | [Implementation plan](implementation-plan.md), [stage log](stage-log.md) | Lior/Sharon equal planned responsibility; AI assistance disclosed |

The filenames containing Initial are retained for continuity; their content is the final revision. Local exports are stored in the project's outputs directory, outside Downloads. Generated binaries, research emails and learned model weights are intentionally excluded from Git. The English presentation builder uses only public aggregate reports and an invented-message screenshot.

## Reproduction levels

1. Software verification: install the locked dependencies, run offline tests, documentation validation and package build. No research email or model download is needed for fixture tests.
2. Numerical experiment verification: run the independent recount scripts against existing local artifacts. Final verification compares both complete runs and checks all preserved hashes.
3. Full reconstruction: follow the source, dataset, baseline, pretrained, refresh, fine-tuning, evasion and defense guides in order. Downloads require network access and review of each source's terms. Training can be numerically different on another runtime/hardware; similar metrics do not establish byte-identical artifact identity. The final runner refuses identities that differ from the committed freeze.

```sh
uv sync --locked --extra pretrained --extra demo
uv run --frozen --extra pretrained --extra demo pytest
uv run --frozen python scripts/check_documents.py
uv build
uv run --frozen python scripts/verify_final.py
```

The last command requires both completed local final-run directories; a fresh Git checkout does not contain them. Follow [final evaluation commands](final-evaluation.md) only after restoring the exact pinned artifacts, with a clean committed tree and new output directories. Never change the freeze or retune a model to match expected results. A repeat is not a new test population. [Dataset preparation](dataset.md), [baseline](baseline.md), [pretrained classifier](pretrained.md), [external data](generalization-audit.md), [real-mail refresh](baseline-refresh.md), [fine-tuning](finetuned.md), [controlled evasion](controlled-evasion.md), [defense](robustness-defense.md) and [current comparison](current-comparison.md) document the prerequisite chain.

## Demonstration walkthrough

```sh
uv run --frozen --extra pretrained --extra demo phishguard demo
```

Open http://127.0.0.1:7860. Use invented examples such as a routine meeting reminder and an invented urgent-account message; neither has a guaranteed outcome. Select each available model, analyze the same text, and explain its score, threshold, decision and identity. Show baseline feature contributions versus the transformers' explicitly labeled surface indicators. Show empty-input rejection, a long accepted message's truncation warning and Clear. Explain that overlength input is rejected, submitted text is not stored by the app and embedded links are not opened. A low score is not evidence of safety. Stop the server with Ctrl+C after the demonstration.

## Interpretation students must be able to explain

- Training fits weights; validation selects checkpoints/thresholds; the final reserve is used only after freezing those decisions.
- The four candidates are a local classical baseline, original fine-tuned BERT, separately augmented BERT and an existing downloaded DistilBERT phishing classifier.
- Clean accuracy, phishing recall, false alarms and conditional candidate ASR answer different questions. Count denominators matter.
- The baseline's 99.29% final accuracy coexists with 80.10% challenge accuracy. Source/era/label bias and synthetic templates limit generalization.
- The three defended attack successes preserve text meaning but their original phishing identity remains ambiguous. Report publisher-dependent candidate ASR, not confirmed real-world compromise.
- Two identical full runs and 354 passing fixture tests support reproducibility/software checks; they do not prove future detection quality.

## Ownership and final human actions

W10 assigns five planning units to each student. Lior leads reproduction instructions, architecture/test documentation and demo packaging. Sharon Elimelech leads comparative results, conclusions and slide assembly. Both review the complete code and selected error cases, add genuine learning/contribution evidence and dates, rehearse explanations and perform the actual course submission. These are assigned responsibilities for AI-assisted work, not invented individual authorship or approvals. No additional model tuning is part of the completed project; future changes require fresh held-out evidence.
