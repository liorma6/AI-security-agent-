# PhishGuard stage and verification log

Record only completed PhishGuard work and actual verification. The [implementation plan](implementation-plan.md) lists future stages; the [project book](project-book.md) defines requirements and ownership.

## Stage 0 - Initial specification - November 13, 2026

Prepared the eight-chapter project book for phishing-email detection and adversarial robustness. It defines the TF-IDF/logistic-regression baseline, pretrained comparison, small-transformer fine-tuning, controlled evasion, defense evaluation and local Gradio demo. Added six-category STRIDE analysis, component and sequence UML, a planned unit-test matrix and a reproducible experiment protocol.

Recorded the student-reported two-week security/AI learning period. Assigned Lior and Sharon Elimelech 50 planning units each, including concrete implementation, testing and review responsibilities. The documents are AI-assisted drafts for student review; named ownership does not claim that planned code has been written or personal review has occurred.

Implementation status: no selected dataset, trained classifier, training runner, perturbation harness, defense experiment or inference demo. No model-quality results or application-test pass counts are claimed.

Verification: `python scripts/check_documents.py` passed using Python 3.13.16. It checked 12 English UTF-8 project files, internal links, Markdown table structure, the eight required chapters and the two SVG diagrams. An independent content review checked PG01-PG10, U01-U12, W01-W10, all six STRIDE categories, truthful implementation status and equal ownership totals.

Local exports were generated from project-book revision 1.0. The PDF contains 16 pages. The Word file was reopened programmatically and contains eight chapter headings, nine tables and two embedded diagrams. Both exports passed English-content and scope checks. PDF text bounds were checked, and the STRIDE and ownership pages were visually reviewed. No classifier tests or model experiments were run because their implementations are pending.

Next functional stage: stage 1, Python foundation, email/result contracts and reviewed fixtures.

## Stage 1 - Python foundation and contracts - November 13, 2026

Implemented an installable `phishguard` Python package and offline validation CLI. Added strict version 1.0 email, labeled-example, artifact, successful-prediction and unavailable-prediction records. The foundation preserves email text, enforces combined character and JSON byte/depth limits, rejects duplicate keys and nonfinite scores, checks explicit label mappings and threshold decisions, and returns public errors without input text or arbitrary field names.

Added six synthetic JSON fixtures with documented provenance. Their labels, digest and prediction values are test data; no dataset selection or inference result is claimed. W02 assigns environment/contracts to Lior and fixtures/validation checks to Sharon Elimelech. This code was implemented with AI assistance in the project session; individual student review remains to be recorded.

Local verification used Windows, Python 3.13.16, uv 0.13.1, Pydantic 2.14.3, pytest 9.2.0 and Ruff 0.17.5. The 80 contract/CLI tests passed, as did lint, formatting and dependency-lock checks. Built a source distribution and wheel, installed the wheel into the environment, verified the console command and reran the 80 tests successfully against the installed package. Restored the editable development installation using the locked environment.

The JSON regression tests identified a difference between parser recursion limits and contract rejection. An explicit 16-level container limit now provides a stable `json_too_deep` response. Public CLI errors were checked for input leakage, and exact email-length boundaries include the subject/body separator and Unicode code points.

Documentation verification checks 31 English UTF-8 files, including source and fixtures, along with local links, tables, eight course chapters and UML. Updated the README, canonical book revision 1.1, contract reference and implementation status. The component diagram marks the implemented CLI/validator separately from planned modules. GitHub Actions is configured for Windows/Linux and Python 3.11/3.13; actual remote results are recorded after execution.

No training, model downloads, dataset acquisition, mailbox connection or network access occurs during validation. Stage 2 is next: licensed dataset selection, ingestion, deduplication and grouped splits. Stages 2-9 remain planned.

## Contribution record format

For each completed activity record the package ID, student, date, actual work, artifact or commit, peer review status and verification results. Reference the ownership plan without treating assigned responsibility as evidence of historical authorship.
