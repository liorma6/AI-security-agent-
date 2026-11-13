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

Documentation verification checked 31 English UTF-8 files, including source and fixtures, along with local links, tables, eight course chapters and UML. Updated the README, canonical book revision 1.1, contract reference and implementation status. The component diagram marks the implemented CLI/validator separately from planned modules.

All four GitHub Actions combinations passed: Windows/Linux with Python 3.11/3.13. Each ran locked installation, lint/format checks, the 80 tests, documentation validation, distribution build and a CLI fixture check. [Verified implementation](https://github.com/liorma6/AI-security-agent-/commit/70f280fce5664b30377c0f9f17382bf15a90eb0a) and [verification run](https://github.com/liorma6/AI-security-agent-/actions/runs/43419224477).

Regenerated the local English Word and PDF book from revision 1.1. The PDF contains 17 pages; the Word document contains eight chapter headings, nine tables and two diagrams. PDF text bounds and language were checked, and the test-matrix and architecture pages were visually reviewed. These export checks do not imply model-quality verification.

No training, model downloads, dataset acquisition, mailbox connection or network access occurs during validation. Stage 2 is next: licensed dataset selection, ingestion, deduplication and grouped splits. Stages 2-9 remain planned.

## Stage 2 - Dataset preparation - November 13, 2026

Implemented PhishGuard 0.2.0 with pinned E-PhishLLM source acquisition, preserved-text ingestion, explicit label mapping, invalid-row exclusions, exact/conflicting-label deduplication, conservative template/near-duplicate grouping and seeded grouped train/validation/test splits. Added optional parent lineage to the example contract and checks for missing/cyclic/cross-group parents. The pipeline neither trains a model nor opens email links.

Reviewed the authors' source card and MIT declaration at revision `dda1f1e0b155206a4f84915bf117012f960bdafe`. The source and card are hash/size verified and stored locally outside Git. The retained corpus contains 11,502 publisher-English synthetic messages in 10,564 groups: 8,052 train, 1,725 validation and 1,725 test. Excluded 5,114 other-language rows. No selected invalid rows, normalized exact duplicates or conflicting exact labels were found. The text-free frozen manifest is tracked; raw and processed email content is ignored.

The deterministic 24-row AI-assisted label review found 17 text-compatible and seven context-dependent examples, retaining all source labels. Corpus inspection found synthetic angle-bracket markers in 3,609 phishing and zero legitimate messages. The dataset guide and book record this shortcut and require label-independent marker removal before stage 3 training, with training/validation diagnostics and no final-test tuning. This is a synthetic benchmark, with no claim of real-mail generalization, complete campaign independence or fully validated labels.

Local acceptance: 124 tests passed on Windows/Python 3.13.16, including 44 new data checks. Verified the near-duplicate index against a brute-force comparison on an offline fixture; tested conflicting labels, group/parent leakage, deterministic splits, artifact tampering, corrupt downloads, cache reuse, output preservation and privacy. Lint, formatting, dependency-lock and 41-file English documentation checks passed. Built the source distribution and wheel, verified the bundled source manifest, and reran all 124 tests plus full-corpus verification against the installed wheel. Restored the editable locked installation.

Fetched the public source through the implemented downloader into a fresh cache and prepared a second output. It matched the committed reference and all partition digests byte-for-byte. Frozen manifest SHA-256: `e2d33ec1688236caced98bcbb8440c16b49282e9614f7e42110274d610beae2d`. These checks establish the documented data invariants, not classifier accuracy.

Updated the operational README, dataset guide, sample audit, project-book revision 1.2, contracts and component UML. W03 assigns provenance/ingestion to Lior and labels/deduplication/split validation to Sharon Elimelech with equal planning weight. Code and initial review were AI-assisted; no completed individual student review is asserted.

All four GitHub Actions combinations passed: Windows/Linux with Python 3.11/3.13. Each ran locked installation, lint/format checks, the 124 tests, documentation validation, package build and a CLI fixture check. [Verified implementation](https://github.com/liorma6/AI-security-agent-/commit/af9df084f276e85538c8c34b956b49180c36c483) and [verification run](https://github.com/liorma6/AI-security-agent-/actions/runs/43422755491).

Regenerated the local English Word and PDF books from revision 1.2. The PDF has 17 pages; Word has eight chapter headings, nine tables and two embedded UML diagrams. Both exports passed language/content checks, PDF text stayed within page bounds, and the dataset/architecture pages were visually reviewed. Distribution inspection confirmed that neither the source archive nor wheel contains raw or processed research emails.

Next functional stage: stage 3, TF-IDF/logistic regression with training-only feature fitting and the documented shortcut mitigation. Stages 0-2 are implemented; stages 3-9 remain planned.

## Stage 3 - Baseline protocol freeze - November 13, 2026

Implemented the classical baseline runner, safe JSON artifacts, separate evaluation and private inference CLI. The fixed protocol specifies marker removal, training-only TF-IDF/logistic-regression fitting, validation-only threshold selection and independent final evaluation. The initial 172 offline tests passed, including 48 baseline checks. This entry precedes research-corpus training; no measured research accuracy is claimed yet. W04 assigns training/artifacts to Lior and evaluation/leakage checks to Sharon Elimelech, with AI assistance and individual student review still open.

## Stage 3 - Classical baseline results - November 13, 2026

Completed research training and final evaluation under the protocol committed at `3cd54fb3cfaffc38acaaf75ac7d61afefb5f5c78`, with a clean working tree recorded for both runs. Trained on 8,052 messages using 30,000 word unigram/bigram TF-IDF features and L2 logistic regression. Only training data fitted vocabulary, IDF and coefficients. Validation selected threshold 0.44 using the declared F1 objective; final-test text was not opened during training. Complete synthetic markers were removed identically for all inputs without changing source records.

Final-test counts on 1,725 messages: TP=891, FP=19, TN=807, FN=8. Accuracy=98.43%, phishing precision=97.91%, recall=99.11%, F1=98.51%, legitimate false-positive rate=2.30%. The training-majority comparator scored 52.12% accuracy and 100% false-positive rate. These are synthetic-benchmark measurements, not real-inbox or adversarial results. The lower selected threshold trades fewer misses for more false alarms, as recorded in the validation comparison.

The marker-only rule achieved 80.81% validation accuracy before cleanup, demonstrating the source shortcut. Zero complete markers remained in transformed training/validation data. This diagnostic does not prove removal of all synthetic cues or quantify a raw-model ablation. Context-dependent source labels and incomplete campaign identity remain limitations.

Independent retraining produced byte-identical model/manifest files and identical final-test prediction bytes. Independently recounted confusion values agreed. Numerical reconstruction from validated JSON matched scikit-learn scores exactly locally, within the required 1e-12 tolerance. Model digest: `a526bb2de383bbeb46282a6c2f0f8bca375310397945319d8b2e5d161f435703`. No test-driven changes were made to the protocol, parameters or threshold. Aggregate training, test and reproduction reports are committed under docs/reports; learned model state and per-example predictions remain in ignored local folders.

Verification: 175 offline tests passed locally (80 foundation, 44 dataset, 51 baseline), including non-convergence, no test-file access during training, train-only IDF/vocabulary, exact confusion arithmetic, cleaned-text leakage, malformed/tampered model state and private inference. Lint and formatting passed. CPU environment: Windows AMD64, Python 3.13.16, scikit-learn 1.9.1, NumPy 2.5.4, SciPy 1.18.1, one requested numerical-library thread. Measured fit/validation computation was 3.02 seconds and test batch scoring was 0.311 seconds, excluding the overhead described in the baseline guide.

Updated book revision 1.3, README startup commands, baseline guide, implementation plan, contracts and UML to distinguish implemented baseline inference from the pending web demo, explanation and advanced experiments. W04 ownership remains evenly allocated: Lior leads training/artifacts; Sharon Elimelech leads metrics, threshold selection and leakage/reproducibility checks. The implementation and reports are AI-assisted; individual student review remains open.

Built source and wheel distributions, confirmed that the protocol is bundled and learned models/raw email are excluded, and reran all 175 tests against the installed wheel. Loaded the research model through the installed console command and obtained the same fixture prediction. Restored the locked editable environment. Dependency-lock and 55-file English documentation checks passed.

All four GitHub Actions combinations passed: Windows/Linux with Python 3.11/3.13, each running locked installation, lint/format checks, 175 tests, documentation checks, package build and a CLI fixture. [Verified stage implementation and results](https://github.com/liorma6/AI-security-agent-/commit/d622b06d4ed1f49253eaf36e96fe1c4d9fc65c4c) and [verification run](https://github.com/liorma6/AI-security-agent-/actions/runs/43439235239).

Regenerated the local English Word and PDF project books from revision 1.3. The PDF contains 18 pages. Word contains the eight required chapter headings, ten tables and two embedded diagrams. Exported language/content and PDF page bounds passed checks; the measured-results and architecture pages were visually reviewed. The saved local model is available for offline prediction, while Git retains the implementation, protocol, aggregate results and documentation.

Next functional stage: stage 4, reviewed pretrained Hugging Face classifier comparison. Stages 0-3 are implemented; six stages (4-9) remain.

## Contribution record format

For each completed activity record the package ID, student, date, actual work, artifact or commit, peer review status and verification results. Reference the ownership plan without treating assigned responsibility as evidence of historical authorship.

## Stage 4 - protocol frozen before corpus evaluation

Date: November 13, 2026. Selected the pinned two-class external DistilBERT, reviewed its card/configuration and recorded tokenizer reconstruction and unknown upstream membership. Implemented verified public downloads, local safetensors inference, validation-only threshold selection, paired final-test comparison and private CLI output. Added 26 offline checks (201 total passed locally), including an actual tiny random transformer, tokenizer truncation, label direction, digest failures, unchanged weights and selection/test boundaries. The full reviewed checkpoint loaded and scored the invented email fixture locally. These checks are software evidence, not model-quality results. Full-corpus validation and final-test comparison are pending at this protocol checkpoint. AI-assisted code and documentation; W05 assigns Lior the source/model adapter and Sharon the mapping/comparison checks. Individual student review has not been asserted.
