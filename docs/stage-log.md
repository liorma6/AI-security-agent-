# PhishGuard stage and verification log

Record only completed PhishGuard work and actual verification. The [implementation plan](implementation-plan.md) lists future stages; the [project book](project-book.md) defines requirements and ownership.

## Stage 0 - Initial specification - November 13, 2026

Prepared the eight-chapter project book for phishing-email detection and adversarial robustness. It defines the TF-IDF/logistic-regression baseline, pretrained comparison, small-transformer fine-tuning, controlled evasion, defense evaluation and local Gradio demo. Added six-category STRIDE analysis, component and sequence UML, a planned unit-test matrix and a reproducible experiment protocol.

Recorded the student-reported two-week security/AI learning period. Assigned Lior and Sharon Elimelech 50 planning units each, including concrete implementation, testing and review responsibilities. The documents are AI-assisted drafts for student review; named ownership does not claim that planned code has been written or personal review has occurred.

Implementation status: no selected dataset, trained classifier, training runner, perturbation harness, defense experiment or inference demo. No model-quality results or application-test pass counts are claimed.

Verification: `python scripts/check_documents.py` passed using Python 3.13.16. It checked 12 English UTF-8 project files, internal links, Markdown table structure, the eight required chapters and the two SVG diagrams. An independent content review checked PG01-PG10, U01-U12, W01-W10, all six STRIDE categories, truthful implementation status and equal ownership totals.

Local exports were generated from project-book revision 1.0. The PDF contains 16 pages. The Word file was reopened programmatically and contains eight chapter headings, nine tables and two embedded diagrams. Both exports passed English-content and scope checks. PDF text bounds were checked, and the STRIDE and ownership pages were visually reviewed. No classifier tests or model experiments were run because their implementations are pending.

Next functional stage: stage 1, Python foundation, email/result contracts and reviewed fixtures.

## Contribution record format

For each completed activity record the package ID, student, date, actual work, artifact or commit, peer review status and verification results. Reference the ownership plan without treating assigned responsibility as evidence of historical authorship.
