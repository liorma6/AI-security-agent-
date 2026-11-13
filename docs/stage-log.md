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

## Stage 4 - pretrained comparison results - November 13, 2026

Completed the protocol frozen at `50172afacad72af4e6afa8596e56044c8bd48f1f` with unchanged external DistilBERT weights. Both reports record a clean working tree. Validation selected 0.05; final evaluation used the same 1,725 IDs as stage 3 and independently reproduced baseline metrics before comparing. Test accuracy: baseline 98.43%, pretrained fixed 61.16%, pretrained selected 59.83%. Selected pretrained confusion: {'fn': 92, 'fp': 601, 'tn': 225, 'tp': 807}. 0 test inputs were right-truncated; none were dropped. The published reports contain all precision/recall/F1/FPR values, paired correctness, source/protocol digests and resource conditions.

Independently recounted every confusion/paired count from local saved predictions. Reload/repeatability checks used invented fixtures, including a long input, and verified unchanged reviewed weights; this was not a second full-corpus evaluation. Unknown upstream membership, reconstructed tokenizer, source/domain differences and synthetic-only data limit inference. No model selection, retuning or fine-tuning followed final-test results.

The 201 offline tests passed locally. Built source and wheel packages and confirmed the source/protocol resources are included. Updated book revision 1.4, component UML, operational README, guides and stage statuses. W05 assigns source/license/inference integration to Lior and mapping/evaluation checks to Sharon Elimelech; both share review responsibility, with individual student review still open. Code, experiments and documentation were AI-assisted.

Stages 0-4 are complete at their stated scope; five stages (5-9) remain. Next: stage 5, training-only transformer fine-tuning and held-out clean evaluation.

All four GitHub Actions jobs passed for the frozen implementation: Windows/Linux with Python 3.11/3.13, each running all 201 tests, locked optional dependencies, lint/format, document checks and package build. [Protocol and implementation](https://github.com/liorma6/AI-security-agent-/commit/50172afacad72af4e6afa8596e56044c8bd48f1f); [verification run](https://github.com/liorma6/AI-security-agent-/actions/runs/43447596056). All 201 tests also passed when importing the installed wheel. A deliberately unavailable optional dependency produced a structured unavailable result while core validation and source verification continued to work.

Regenerated the local English Word and PDF books from revision 1.4. The PDF has 19 pages; Word has eight chapter headings, 11 tables and two embedded UML diagrams. Language/content and PDF page bounds passed validation. The comparative-results table and updated component architecture were visually reviewed. Both distribution formats exclude raw research messages and model checkpoints. The local exports are saved in the project outputs directory outside Downloads.

## Stage 4a - protocol checkpoint - November 13, 2026

Added the requested generalization audit before stage 5. The exact baseline artifact, threshold, extraction rules, source digests, language filter, relatedness heuristic, external audit/reserve partition, label-review sample and evaluation metrics are fixed in the packaged protocol. Publisher sources are Nazario phishing (2024/2025, CC BY 4.0) and SpamAssassin easy/hard legitimate mail (2003, publisher research-use terms). Source/era confounding is explicit. Raw messages remain local. No new model has been trained and no stage-5 work has started.

The 26 new offline checks passed, covering MIME/HTML handling, archive traversal, deterministic grouping, exclusion of relatives from every internal split, frozen model/threshold enforcement, verified TLS downloads and evaluation without reserve access or fitting. Public source downloads succeeded with certificate and digest verification enabled. Corpus preparation, sample review and scoring follow this protocol checkpoint; no external accuracy is claimed here. Lior/Sharon W05 assignments remain balanced, with AI assistance and individual student review still open.

## Stage 4a - completed generalization audit - November 13, 2026

Protocol/code freeze: `385b881563fcc22ded9b3ccc1a03485445109980`. Prepared the external cohort, reviewed the predetermined 16 audit examples before scores and committed membership/review at `09165d3b40a46cc84504356789bcd8bc499c5249`. Both internal and external reports record this clean commit. No weights, vocabulary, preprocessing or threshold were changed; stage 5 has not started.

From 2,534 publisher mailbox records, 2,342 eligible unique messages remained after declared quality/duplicate/overlap exclusions. Audit: 1,639 messages in 1,003 groups (522 phishing / 1,117 legitimate). Reserve: 703 in 432 groups (224 phishing / 479 legitimate), with no model scoring or manual content review. Preparation read all inputs for language/quality/grouping; integrity checks only hash reserve bytes. The pre-score sample review retained publisher labels, including three context-dependent phishing examples and one uninformative plain MIME placeholder. The raw messages remain ignored local files.

Frozen baseline external counts: TP=463, FP=58, TN=1,059, FN=59. Accuracy 92.86%, balanced accuracy 91.75%, phishing precision 88.87%, recall 88.70%, F1 88.78%, legitimate false-positive rate 5.19%. The whole-group 95% bootstrap accuracy interval is 91.31-94.33%; recall is 85.09-91.79%. This measures transfer to a source/era-confounded corpus, not contemporary inbox prevalence, calibrated probabilities or adversarial robustness. The baseline's unchanged synthetic test accuracy is 98.43%.

Internal train/validation/test accuracy: 99.32/98.67/98.43%. The declared grouping found zero cross-split components. A broader diagnostic found one additional train/test subject relation; the post-hoc sensitivity subset remains 98.43% on 1,724 messages. Coefficients and text-pattern frequencies suggest source cues but do not prove causal dependence. The audit supports a generalization gap without proving excessive training caused it. No result-driven feature removal or tuning occurred.

Independent preparation reproduced the manifest and both partitions byte for byte. Repeated frozen scoring reproduced predictions, metrics and bootstrap intervals exactly. `scripts/verify_generalization.py` independently recounted confusion values, checked prediction IDs against audit-only membership and verified the unchanged baseline digest and reserve integrity. Aggregate reports are under docs/reports; local predictions contain IDs/labels/scores but no email text. External batch scoring took 0.532 seconds on CPU with one numerical-library thread, excluding loading/imports/I/O.

All 227 offline tests passed locally, with lint/format and English document checks. Updated the operational README, audit/label-review guides, project-book revision 1.4a, contracts, component UML and implementation plan. Stages 0-4 plus checkpoint 4a are complete; stages 5-9 remain. Future training must freeze its data/validation/final-evaluation policy first. The inspected audit is development evidence; the 703 reserve messages remain unscored and retain their source limitations.

W05's equal planning allocation includes Lior's external provenance/download/MIME responsibilities and Sharon Elimelech's label/relatedness/split/metrics responsibilities, with shared interpretation and peer review. Code, experiments and initial document/sample review were AI-assisted. Individual student contribution/review is not invented.

Built wheel/source distributions and verified bundled audit source/protocol resources and exclusion of raw/processed mail, learned models and private experiment folders. All 227 tests also passed against the installed wheel. That check exposed one test using the default experiment-output folder after real evaluation had created it; the test now uses its own temporary output, with no change to the audited implementation, model or results. The locked editable environment was restored.

Regenerated the local English revision-1.4a Word and PDF books. The PDF has 22 pages; Word has the eight required chapter headings, 12 tables and two embedded UML diagrams. Content/language and PDF page-bound checks passed. The external-results page and component UML were visually reviewed. Local exports remain in the project's outputs folder outside Downloads. Stage 5 remains unstarted.

All four GitHub Actions combinations passed: Windows/Linux with Python 3.11/3.13, including all 227 tests, locked installation, lint/format, documentation validation and package build. [Verified stage-4a implementation and results](https://github.com/liorma6/AI-security-agent-/commit/9032bb9f05f4171f9d4b6fea6a70d24fd429e9ae); [verification run](https://github.com/liorma6/AI-security-agent-/actions/runs/43457279731).

## November 13, 2026 - Stage 4b data refresh and baseline re-evaluation

Implemented the requested additional data/baseline checkpoint; stage 5 was not started. Version 0.4.2 adds `refresh fetch/diagnose/prepare/train/evaluate`, pinned sources, targeted MIME/rooted-HTML repairs, explicit publisher-placeholder cleanup, protected grouped splits, a separately persisted baseline v2 and fixed comparison reports. Raw mail, vocabulary/model weights and predictions stay local. All original files and the 703-message reserve remain preserved; reserve machine access is solely overlap/integrity checking, without manual review or scoring.

Diagnosed all 117 old errors using full-text indicator profiles and excerpt triage plus 24 deterministic correct controls. Reviewed sources and retained publisher labels; MeAJOR contributes only TREC ham, never generic spam as phishing. New historical Nazario mail supplies phishing; Zenodo v3 is a separate mainly templated challenge with an explicitly unverified 100-record original subset. Source review and experiments are AI-assisted, not invented individual student authorship.

Chronology: protocol/code `622b9e0`; provisional data `31d632a`; first training stopped before fitting on the leakage guard. Pre-fit corrections `941a4b7` unite original/broader groups and remove declared anonymization placeholders. Corrected data `818372e` binds 3,261 training / 745 validation / 425 historical test / 2,000 challenge rows. Model/threshold freeze `8d519e9` precedes first held-out scoring. Initial successful training and evaluation record clean commits. V2 model digest is `a78643d919de806d170fec8cf303ac8be29e7866d0e30acb14650430009fe480`; threshold 0.31 comes only from validation F1.

Historical v1/v2 accuracy: 82.59%/98.82%; challenge: 66.00%/80.10%. V2 challenge FPR is still 37.20%, and accuracy on the 100 original records is only 62%. The historical cohort shares source families with development. A trace of the 16 provisional-training excerpt-review IDs found one moved into the corrected historical test; this deviation is disclosed. Excluding it post-hoc leaves 424 rows and 98.82% v2 accuracy, not a fresh independent final test. No weights/thresholds changed after scoring. Existing cohorts remain research benchmarks and further generalization claims are unsupported.

Repeated full preparation, fitting and evaluation produced byte-identical partitions, manifest, model and predictions. The independent verifier matched confusion, subgroup and paired counts and repeated intervals; it also checked original internal files, v1 digest and reserve bytes. Full results, exclusions, source limitations and review trace are linked from the refresh guide and book revision 1.4b. The work plan now records seven completed milestones out of twelve, with stages 5-9 remaining. W05 ownership remains five planning units per student, with actual individual review still open.

All 249 tests passed locally on Python 3.13.16 and again against the installed wheel. Locked dependencies, lint/format and English documentation checks passed; v2 CLI prediction was exercised. Wheel/source distributions were built, packaged refresh source/protocol resources were verified, and raw/processed mail, weights and private artifacts were excluded. The editable environment was restored.

Regenerated the English revision-1.4b local Word/PDF books. The PDF has 25 pages; Word has eight required chapter headings, 14 tables and two embedded UML diagrams. Language, content and PDF page bounds passed; the new comparison pages and component UML were visually reviewed. Exports remain in the project outputs folder outside Downloads.

All four GitHub Actions combinations passed for the completed implementation/results commit: Windows/Linux with Python 3.11/3.13, including the 249 tests, locked installation, lint/format, documentation validation and package build. [Verified stage-4b implementation and results](https://github.com/liorma6/AI-security-agent-/commit/42e7d7e882ef292af450c9db1054c7d2a8d6d3da); [verification run](https://github.com/liorma6/AI-security-agent-/actions/runs/43511565440).
