# PhishGuard - Initial Project Book

Revision 1.4 - November 13, 2026 - Pretrained comparison

Team: Lior and Sharon Elimelech. Course-aligned proposal based on Project2_PhishGuard.docx and the student's eight-chapter checklist.

Status: STAGE 4 PRETRAINED COMPARISON IMPLEMENTED AND EVALUATED. The specification, contracts, frozen grouped dataset, baseline and reviewed pretrained inference/comparison are available. Transformer fine-tuning, adversarial experiments, defense and the web demo remain planned. This book is the canonical specification; implementation evidence and experimental results are added as each stage is completed.

## 1. Background

Phishing emails attempt to persuade recipients to disclose information or perform a harmful action. Text classifiers can help flag suspicious messages, but changes to wording, spelling or characters can alter model predictions even when the harmful intent remains. This project studies that gap between apparent test performance and robustness under controlled text changes.

The supplied brief describes a company receiving many emails and needing both a detector and evidence about whether it can be bypassed. The academic deliverable is a reproducible comparison of detection and robustness, plus a simple demonstration. It is not a production mail gateway and will not send emails, collect credentials or test against real recipients.

### 1.1 Foundations studied over two weeks

The students report studying the concepts below over a two-week period. Exact calendar dates and individual study artifacts were not supplied. Section 8 organizes that reported learning without inventing dates, completed exercises or individual authorship. Crypto and TLS knowledge supplies security background; Python, text preprocessing, TF-IDF and model evaluation remain additional task-specific foundations.

| Concept | Meaning | Relevance and limitation |
| --- | --- | --- |
| Cryptography | Methods for confidentiality, integrity, authentication and signatures; encryption is one part of the field. | Explains security properties, not whether a message is persuasive or fraudulent. |
| Symmetric encryption | The communicating parties use a shared secret for encryption/decryption. | Efficient protection of data; key establishment and handling remain important. |
| Asymmetric cryptography | Uses a public/private key pair; particular schemes support signatures, encryption or key agreement. | These are distinct operations; one algorithm need not support all of them. |
| Symmetric and asymmetric keys | A shared secret differs from a public/private pair. TLS commonly uses asymmetric mechanisms for authentication/key establishment and symmetric traffic keys. | TLS 1.3 also supports pre-shared-key modes; certificate-based authentication is not universal. [R1] |
| Algorithm and cipher | An algorithm is a procedure. A cipher is an encryption/decryption algorithm, such as AES. | TLS is a protocol combining cryptographic mechanisms, not a single cipher. |
| Hash function | Produces a fixed-size digest for algorithms such as SHA-256. It is not reversible encryption. | Useful for artifact and dataset identifiers. An unkeyed digest alone does not authenticate a sender. [R2] |
| HMAC | A message authentication code combining a hash function and a shared secret. | Supports integrity and shared-key authentication; it is not a publicly verifiable digital signature. [R3] |
| Salt | A per-password random value stored with a password-hashing result. It need not be secret. | Use a dedicated, costed password-hashing scheme; ordinary SHA-256 alone is unsuitable. No login system is required for the initial local demo. [R4] |
| TLS | Establishes an authenticated, confidential channel with integrity protection; a handshake establishes parameters and keys. | Protects transport. It cannot establish that email content is benign. [R1] |
| Digital certificate | An X.509 structure binding identity information to a public key, usually signed by a CA. | A common issuance flow uses a key pair and CSR; validation includes identity, validity and a trusted chain. [R5] |
| CA | A certificate authority issues/signs certificates under an identity-validation policy. | Trust anchors depend on the selected client/application trust store. [R5] |
| CRL | A signed list of certificates revoked before their normal expiry. | It is published by a CA or authorized issuer. Revocation and expiry are distinct concepts in the security learning record. [R5] |
| Model | A learned mapping used to predict labels or scores from inputs. | Review data, label meanings, intended use and measured performance; a score is not a guarantee. [R6] |
| AI agent | A model-based system using tools/actions to pursue an objective. | An autonomous agent is not required by the PhishGuard brief; the classifier can be a bounded function. [R7] |
| Generative AI | Models that generate content such as text, code, images or audio. | An LLM rewriter is optional in the brief. It is not needed for the first attack harness or a grounded explanation. [R8] |
| Hugging Face | A platform and ecosystem for models, datasets, libraries and learning material. | Study the LLM course before the agents course, and inspect model/dataset cards and licenses. [R6-R8] |

### 1.2 Terminology for this project

TF-IDF converts text into weighted features; logistic regression supplies the required classic-ML classifier. A transformer is a neural architecture used by many pretrained language models. Fine-tuning updates an existing model for the target task. Adversarial evasion changes an input to induce an incorrect prediction while retaining its relevant label. Robustness is evaluated under a declared threat model and attack budget, rather than assumed from clean accuracy. [R6, R9]

## 2. Work objectives

The main objective is to build a phishing-email detector and measure how controlled text perturbations affect it, then evaluate a defense. The final demonstration accepts pasted email text and returns a phishing score, a decision, model identity and an explanation tied to observable evidence.

| Objective | Acceptance evidence |
| --- | --- |
| Establish a reproducible dataset | Licensed source manifest, label definition, deduplication and frozen grouped train/validation/test splits |
| Build the required baseline | TF-IDF plus logistic regression, reproducible configuration and held-out metrics |
| Compare a pretrained Hugging Face classifier | Documented checkpoint, revision, compatible label mapping and comparison on the same test protocol |
| Fine-tune a small transformer | Training configuration, seeds, checkpoint manifest and evaluation; DistilBERT is a proposed candidate |
| Measure evasion | Offline perturbation harness, validity review, fixed budget and paired clean/perturbed predictions |
| Evaluate a defense | Training-only augmentation or another declared defense, with clean and attacked evaluations |
| Deliver an understandable demo and report | Pasted-email workflow, bounded input, evidence-based explanation and comparative presentation |

Stages 3-4 provide measured baseline/pretrained comparisons and error counts in chapter 6. Robustness and real-inbox generalization have not been measured. Thresholds are selected using validation data only; report trade-offs and unsuccessful experiments without choosing conclusions in advance.

### 2.1 Experimental questions and metrics

Compare the baseline, the selected pretrained classifier, the fine-tuned model and its defended version. Report accuracy, phishing precision/recall/F1, legitimate-email false-positive rate, confusion matrices, class counts, inference time and resource conditions. Use the same held-out originals for paired clean/perturbed comparisons.

Attack success rate (ASR) is the fraction of eligible phishing originals correctly detected by the evaluated model for which at least one valid perturbation causes a legitimate prediction within the attack budget. Report numerator, denominator, valid-perturbation coverage and query counts. Different models may have different eligible sets; do not compare ASR numbers alone as if their denominators were identical.

For the defense comparison, report results on fixed saved variants and the same evaluation cohort, and separately report a fresh attack search against the defended model using the same budget. Keep attack tuning and defense training away from the final test set. Group an original email, duplicates, its campaign/template relatives where identifiable and all derived variants into one split. Fit TF-IDF and preprocessing statistics on training data only. [R10]

## 3. Technical requirements

### 3.1 Requirements from the supplied brief

The PG requirements describe the complete assignment. Stages 1-4 supply the environment, contracts, PG02 dataset evidence, the trained/evaluated PG03 baseline and the PG04 pretrained comparison. PG09 has local CLI inference; its web UI and explanation remain pending. No completed robustness experiment is claimed. PG01's task-specific learning continues alongside implementation. The remaining end-to-end acceptance evidence is planned.

| ID | Requirement | Verification |
| --- | --- | --- |
| PG01 | Learn Python, phishing and text classification | Learning notes and a small reproducible preprocessing exercise |
| PG02 | Collect public phishing and legitimate email data | Provenance, license, label audit and frozen split manifest |
| PG03 | Implement TF-IDF plus logistic regression | Training/inference command and baseline evaluation |
| PG04 | Use a pretrained Hugging Face text classifier for comparison | Checkpoint metadata, task-compatible labels and comparison report |
| PG05 | Fine-tune a small transformer | Repeatable run configuration and saved model artifact |
| PG06 | Implement controlled email-text evasion | Typo, character-swap and substitution variants with traceable originals; optional rephrasing |
| PG07 | Measure degradation under attack | Paired predictions, clean/attacked metrics and ASR with denominators |
| PG08 | Improve robustness and evaluate again | Documented defense and independent evaluation of benefits and costs |
| PG09 | Provide a simple pasted-email web demo | Risk score, explanation, model version, empty/error/length-limit states |
| PG10 | Deliver comparative report and presentation | Reproducible experiment report, demo instructions and final slides |

The brief lists Python, Hugging Face Transformers/Datasets, scikit-learn, Google Colab, Gradio/Streamlit and GitHub. DistilBERT is an example, and LLM-assisted rewriting is explicitly optional. The required final deliverables are baseline and fine-tuned detectors with a demo, a controlled adversarial script, a comparative report and a presentation.

### 3.2 Proposed implementation choices

Use a modular Python pipeline with a Gradio demo. Keep dataset preparation, feature extraction, training, perturbation, evaluation and inference separate. Use local versioned files for manifests and aggregate results. The offline experiment pipeline prepares reviewed artifacts; the demo loads a selected artifact for inference. Container packaging may be added when it makes the completed demo easier to reproduce.

The selected input is the publisher-English subset of E-PhishLLM, with plain-text subject/body fields. Raw MIME parsing, attachments, sender authentication, mailbox integration and multilingual claims are outside the first version. The foundation supports Python 3.11-3.13; local development uses Python 3.13.16, uv 0.13.1 and a locked dependency environment. It uses Pydantic for strict record validation, pytest for tests and Ruff for code checks. The baseline uses scikit-learn 1.9.1 and locked numerical dependencies on CPU. The pretrained runtime pins PyTorch 2.15.0, Transformers 4.57.6 and safetensors 0.8.0, with offline CI checks on Windows/Linux and Python 3.11/3.13. Full research-checkpoint scoring was measured locally on Windows. Keep large checkpoints and datasets outside Git and record provenance and digests in small manifests.

Stage 2 selected the synthetic E-PhishLLM public dataset with a pinned publisher MIT declaration, explicit label mapping and a documented sample audit. No independent real-inbox evaluation is available. Stage 4 selected a pretrained classifier with explicit phishing/legitimate labels and documented source limitations. A generic sentiment model cannot be evaluated by relabeling positive/negative sentiment as safe/phishing. A base encoder without a trained classification head also does not provide a ready phishing detector.

### 3.3 Quality, security and reproducibility requirements

| ID | Proposed requirement | Acceptance |
| --- | --- | --- |
| Q01 | Trace every dataset/model/experiment revision | Manifest with source revision, digest, seed, configuration and split IDs |
| Q02 | Prevent leakage | No group or derived variant crosses splits; training alone fits transformations |
| Q03 | Preserve email privacy | No raw pasted email logging or storage by default; licensed/redacted fixtures only |
| Q04 | Bound resource use | Implemented 20,000-code-point combined email and 262,144-byte JSON limits, with rejection and no truncation; pretrained inference enforces 512 tokens with disclosed truncation and batches of eight; web concurrency controls remain planned |
| Q05 | Treat email content as inert data | Render escaped text; do not open links, send mail or execute attachments/instructions |
| Q06 | Load reviewed model artifacts | Pin revisions, verify manifests and disable unreviewed remote code; avoid untrusted serialized executables |
| Q07 | Explain uncertainty | Display a model score, threshold and model identity; do not claim a calibrated probability without calibration evidence |
| Q08 | Keep training/evaluation distinct from the demo | Offline runner owns training and perturbation; UI cannot invoke arbitrary scripts |
| Q09 | Reproduce a clean run | Document installation, test command, data preparation and evaluation with resource limits |

### 3.4 Data design

| Record | Required information |
| --- | --- |
| EmailExample | ID, preserved text, source label, source/license, group ID, split and optional parent ID |
| ModelArtifact | Model/tokenizer revisions, label mapping, preprocessing configuration, manifest digest and threshold |
| Perturbation | Original ID, operation, seed, budget/query count, changed text and validity review |
| Prediction | Example/variant ID, model revision, score, decision, threshold and elapsed time |
| ExperimentRun | Dataset/split versions, compared models, defense configuration, metric counts and artifact references |

Separate model indicators from factual claims about the sender. A baseline explanation can show influential TF-IDF features; a transformer explanation needs a declared attribution or indicator method and limitations. Generated prose is optional and cannot replace measurement.

Stage 1 implements EmailInput, EmailExample, ModelArtifact, Prediction and UnavailablePrediction. [Contract details](contracts.md) define required fields, strict types, preserved text, explicit label mapping, finite scores and threshold/label consistency. Stage 3 supplies baseline inference and separately verifies model bytes, dimensions, mapping, threshold, runtime version and protocol digest before use. The contract-only validator still checks record structure without loading model files. Perturbation and ExperimentRun remain future designs. Synthetic fixtures document provenance and use unassigned splits; they are not a selected research dataset.

### 3.5 Implemented dataset preparation

The source is the authors' E-PhishLLM release, revision `dda1f1e0b155206a4f84915bf117012f960bdafe`, with a publisher-declared MIT license. It contains synthetic emails, not real inbox observations. Type 0 means legitimate and type 1 means phishing. Source digests, attribution, commands, quality results and limitations are maintained in the [dataset guide](dataset.md). [R12]

Of 16,616 source rows, 11,502 are flagged English and retained; 5,114 other-language rows are excluded. No selected row violates the input contract; normalized exact duplicates and conflicting exact labels number zero. Similarity/template grouping produces 10,564 groups, including 325 multi-message groups, with a largest group of 40. The seed-42 split contains 8,052 training messages (3,854 legitimate / 4,198 phishing), 1,725 validation messages (826 / 899) and 1,725 final-test messages (826 / 899).

Grouping combines normalized exact text, sufficiently long identical subjects, masked body templates and exact word-trigram Jaccard similarity of at least 0.90. Connected relatives and declared parent links remain together. These rules reduce detectable overlap but cannot establish complete campaign independence because the source supplies no campaign/profile IDs. Original accepted text remains unchanged. Stage 3 fits its TF-IDF vocabulary and IDF weights on the training partition only.

The [24-example label audit](dataset-label-audit.md) found 17 text-compatible and seven context-dependent examples. It was AI-assisted and is not a full label validation or completed student review. Labels remain the publisher's. A corpus-wide shortcut is also present: synthetic angle-bracket markers occur in 3,609 phishing messages and no legitimate messages. Before research training, stage 3 froze and applied label-independent removal of complete synthetic markers and their contents. Training/validation diagnostics confirm zero complete markers remain after this transformation. Do not tune preprocessing using final-test performance. Synthetic style, missing context and possible semantic overlap limit later conclusions.

The public source and processed JSONL files are kept on the local disk outside Git tracking. The repository stores a text-free frozen split manifest. A second preparation from a fresh verified download produced identical partition and manifest bytes. CLI verification checks file digests, membership, counts, provenance, unique IDs/text, similarity groups and parent lineage; the committed reference additionally anchors the expected bytes.

### 3.6 Implemented classical baseline

The baseline transforms each subject/body into word unigram/bigram TF-IDF features and fits logistic regression, with legitimate=0 and phishing=1. The fixed configuration uses a maximum of 30,000 features, minimum document frequency 2, sublinear term frequency, smoothed IDF, L2 normalization and L2-regularized logistic regression (C=1, LIBLINEAR, seed 42). All fitted vocabulary, IDF values and coefficients come from training data only. [R9, R13]

The versioned protocol was committed before research training. Training reads the train/validation partitions only; it does not open the final-test file. Validation selects the threshold maximizing phishing F1 on a fixed 0.05-0.95 grid with 0.01 increments and declared tie-breaks. There is no hyperparameter search or train+validation refit. The frozen model is evaluated in a separate command. Source digests and cleaned-text fingerprints reject inconsistent artifacts and exact cross-partition overlap.

The model is stored as strictly validated JSON vocabulary, numerical weights, threshold and provenance, with a separate SHA-256 manifest. Loading reconstructs scoring without deserializing executable objects. Missing or invalid artifacts return explicit errors/unavailable results. Inference neither saves pasted email nor follows its links. Model scores are not calibrated probabilities. [R14]

The [baseline guide](baseline.md) contains verified commands, the complete protocol, measured reports and limitations. Chapter 6 records the observed result; later transformer and robustness experiments remain separate work.

### 3.7 Implemented pretrained adapter and comparison

Stage 4 uses the externally trained two-class DistilBERT `dima806/phishing-email-detection`, pinned to revision `310a5602280486e01dd60e37230980cfcc327b41`. The publisher card declares Apache-2.0. Explicit configuration labels map `SAVE EMAIL` to legitimate and `PHISHING EMAIL` to phishing; generic/extra labels fail. The full upstream training manifest is unavailable, so no verified non-overlap claim is made. [R15]

The source manifest verifies card/configuration/vocabulary/safetensors bytes. The local loader disables remote code, rejects incomplete classification heads and reconstructs a cased tokenizer from the supplied vocabulary and pinned base-tokenizer settings. Input uses the baseline's marker removal; token lengths and right truncation at 512 are disclosed. Weights stay fixed. Validation-only threshold selection is separate from final evaluation and bound by digests to model, dataset and baseline versions. Evaluation checks identical test IDs and reproduces the published baseline counts before comparing predictions.

The [pretrained guide](pretrained.md) records selection reasons, source limitations, commands and CPU resource conditions. This comparison is implemented; fine-tuning those or other weights is a separate stage.

## 4. STRIDE threat analysis

This threat model covers the intended PhishGuard system. Stage 1 implements bounded, strict input validation and input-free public errors. Stage 2 adds pinned source/file integrity, frozen splits, lineage checks and controlled source-only downloading. Stage 3 adds train-only fitting, held-out threshold selection, numerical JSON model validation, artifact digest checks and input-private prediction. Stage 4 adds reviewed safetensors-only loading, explicit model labels, checked tokenizer reconstruction, token/batch limits and digest-bound validation decisions. The broader controls below remain planned unless linked to implemented evidence in the stage log. STRIDE provides six categories for analyzing system threats. The specific threats, priorities and controls below are design judgments for this project. [R11]

### 4.1 Assets, actors and trust boundaries

Protect email content, labels and split integrity, model artifacts, credentials used for downloads, predictions, experiment manifests and compute availability. Actors are the local analyst, student researcher, an untrusted email author and external model/dataset publishers. The controlled perturbation runner represents the adversary only inside the experiment.

Boundary B1 separates pasted text from the UI/inference code. B2 separates external dataset/model downloads from reviewed local artifacts. B3 separates training data from validation/test data. B4 separates the demo process from filesystem secrets and offline training privileges. The initial deployment is loopback-only; shared hosting introduces an additional authentication and transport boundary that must be reviewed before publication.

| Category | Scenario and impact | Proposed mitigation | Verification and owner |
| --- | --- | --- | --- |
| S - Spoofing | A forged sender display name or a model result is treated as proof of identity; a shared demo could accept an unauthorized user. | Explain that text classification does not authenticate senders. Keep local operation; require authentication before shared deployment. | Verify result wording and local binding; test access controls if shared hosting is added. Lior leads, Sharon reviews. |
| T - Tampering | A dataset label/split or model artifact is altered, poisoning training or invalidating evaluation. | Review provenance, pin revisions and digests, freeze grouped splits, track label edits, keep test data outside training. | Reject manifest mismatch and group overlap. Sharon leads, Lior reviews. |
| R - Repudiation | A reported result cannot be traced to the model, data, configuration or perturbation that produced it. | Record run IDs, manifests, seeds, versions and aggregate counts without raw email content. | Reproduce a tiny reference run and trace every reported metric. Logs provide traceability, not guaranteed non-repudiation. Lior leads, Sharon reviews. |
| I - Information disclosure | Pasted email contains private information and is leaked through logs, saved examples or an external LLM request. | Disable raw-input logging/persistence, redact public fixtures and avoid external inference by default. | Use a unique test marker and verify it is absent from logs/files/outbound requests. Sharon leads, Lior reviews. |
| D - Denial of service | Oversized text, repeated requests or unrestricted attack loops exhaust CPU, GPU or memory. | Bound characters/tokens, inference concurrency, time and attack queries; return clear limit errors. | Boundary/over-limit tests, exhausted-budget test and measured resource checks. Lior leads, Sharon reviews. |
| E - Elevation of privilege | An untrusted checkpoint, dataset script or email instruction executes code or invokes privileged tools. | Use reviewed artifacts, disable remote code, avoid arbitrary paths/commands and treat text as data. Use a non-root container if deployed in Docker. | Reject unknown paths/artifacts and ensure email text never triggers execution or networking. Sharon leads, Lior reviews. |

### 4.2 Model evasion and residual risk

STRIDE does not replace the adversarial ML experiment. The perturbation harness specifically measures false negatives under bounded, label-preserving changes. Label preservation must be reviewed: changing a phishing request into a harmless message is not a successful evasion. Report invalid or ambiguous variants separately.

Residual risks include dataset bias, incomplete campaign grouping, novel attack styles, attribution limitations, poisoning that escapes provenance checks and false confidence in a score. A successful defense experiment supports claims only for the measured datasets, budgets and attack families. The demo provides decision support and does not automatically block mail or claim that a message is safe.

## 5. Unit tests

### 5.1 Current verification status

The repository contains the specification, contracts, dataset pipeline, classical baseline and pretrained comparison. The 201 automated tests passed locally on Python 3.13.16: 80 foundation, 44 dataset, 51 baseline and 26 pretrained checks. They cover the synthetic examples, input length and Unicode preservation, malformed/oversized/deep JSON, provenance, label mapping, score/threshold consistency and private CLI errors. Dataset checks additionally cover invalid rows, conflicting labels, similarity grouping, reproducibility, cross-split relatives, parent cycles, tampering, downloader failures and private errors. A brute-force comparison verifies the near-duplicate search on a generated fixture. Documentation checks cover chapter structure, English text, links and tables. The [stage log](stage-log.md) records verification details and CI evidence.

Baseline tests cover train-only vocabulary/IDF fitting, threshold selection, exact metric counts, non-convergence, leakage, JSON model integrity, save/load numerical agreement and private predictions. Measured research-corpus results appear in chapter 6 and the linked reports. Passing tests and measured benchmark accuracy are distinct evidence.

### 5.2 Planned PhishGuard unit-test matrix

The matrix below describes the final test goals. Stage 1 implements the input-validation parts of U01/U02, text-preservation part of U03, metadata-mapping part of U06, record-level threshold checks in U07, unavailable-result shape in U11 and CLI privacy part of U12. Stage 2 adds U03 grouping and U04 duplicate/derived-lineage separation checks. Stage 3 implements U05 feature leakage checks, baseline mapping/loading in U06/U11, actual thresholded inference in U07, classification metrics in U10 and baseline CLI privacy in U12. Stage 4 adds transformer label direction, actual tiny-transformer inference, unchanged-weight checks, token truncation, safetensors loading policy, validated selection and comparison checks for U06/U07/U10/U11/U12. Perturbations, ASR and HTML output remain pending. Use small offline fixtures; full-corpus evaluation belongs to separate experiment checks.

| ID | Unit and input | Expected result | Owner |
| --- | --- | --- | --- |
| U01 | Empty, whitespace and malformed email input | A structured validation error; no inference call | Lior |
| U02 | Exact length limit and one character above it | Accepted at the boundary; rejected above it without truncation | Sharon |
| U03 | Unicode, punctuation and template duplicates | Stable preprocessing/group IDs; no silent label-changing cleanup | Lior |
| U04 | Duplicate and derived variant across splits | Split validator rejects leakage | Sharon |
| U05 | Validation-only token in a tiny corpus | Token absent from the training-fitted TF-IDF vocabulary | Lior |
| U06 | Tokenizer/model with reversed or missing label mapping | Mapping is validated or rejected; never silently interpreted | Sharon |
| U07 | Fixed model scores around the threshold | Correct decision and bounded score; model/threshold metadata retained | Lior |
| U08 | Seeded typo/swap operation and zero edit budget | Reproducible variant; no changes at zero budget | Sharon |
| U09 | Exhausted query budget and no valid variants | Termination with exact counts and an explicit no-result status | Lior |
| U10 | Hand-calculated confusion matrix and ASR, including zero denominator | Exact metric counts; undefined values remain explicit | Sharon |
| U11 | Model manifest mismatch or load failure | Structured unavailable/error result; no fabricated score | Lior |
| U12 | HTML-like email text and a privacy marker | Escaped explanation/output; no raw-content logging | Sharon |

For U10, a fixture with TP=3, FP=1, TN=4 and FN=2 must produce accuracy 0.7, precision 0.75, recall 0.6 and F1 approximately 0.6667. If two of four eligible correctly detected phishing originals are evaded, ASR is 0.5. A zero eligible denominator must be reported as undefined with count zero.

### 5.3 Integration and experiment checks

Implemented a tiny train/save/load/predict/evaluate cycle on invented fixtures. Numerical round-trip agreement is checked within 1e-12. An independent full-corpus retraining produced identical model, manifest and test-prediction bytes; confusion counts were separately recomputed. Student review of fixtures remains open. Stage 4 adds frozen external-checkpoint loading, complete validation/test runs, independent count reconstruction and reload/repeatability checks on invented messages. CI uses a tiny random local transformer and never downloads research weights. Future checks cover fine-tuning, the pasted-email UI and the complete attack/defense evaluation.

Keep unit-test pass counts separate from model-quality measurements. A passing test suite cannot establish that the detector generalizes to real mail.

## 6. Summary and conclusions

PhishGuard now has a working classical detector, a measured pretrained comparison, reproducible data preparation, strict contracts and local inference for both classifiers. The broader project still aims to fine-tune a transformer, measure controlled evasion, evaluate a defense and provide a web demo.

### 6.1 Measured baseline result

Stage 3 trained on 8,052 synthetic messages and selected threshold 0.44 on 1,725 validation messages before evaluating 1,725 final-test messages. The model uses 30,000 features and converged in nine solver iterations. No settings were tuned after viewing final-test outcomes.

| Measure | Validation | Final test |
| --- | --- | --- |
| Accuracy | 98.67% | 98.43% |
| Phishing precision | 98.56% | 97.91% |
| Phishing recall | 98.89% | 99.11% |
| Phishing F1 | 98.72% | 98.51% |
| Legitimate false-positive rate | 1.57% | 2.30% |
| True positives / false positives | 889 / 13 | 891 / 19 |
| True negatives / false negatives | 813 / 10 | 807 / 8 |

Thus, 891 of 899 phishing-labeled test messages were detected and eight were missed; 19 of 826 legitimate-labeled messages were falsely flagged. The training-majority comparator, which always predicts phishing, obtained 52.12% accuracy and 100% false-positive rate. At validation threshold 0.50 there were five false alarms and 19 misses; choosing 0.44 reduced misses to ten while increasing false alarms to 13. The F1 objective explicitly accepts that trade-off; the threshold is not yet a validated company operating policy.

### 6.2 Reproducibility, resources and limits

The initial run and an independent retraining produced identical model, manifest and final-test prediction bytes in the same environment. Confusion counts were independently recounted. Execution used Windows AMD64, Python 3.13.16 and scikit-learn 1.9.1 on CPU with one requested numerical-library thread. Fit/validation computation took 3.02 seconds after preprocessing/boundary checks. The test scoring batch took 0.311 seconds, or 0.180 ms amortized per email, excluding loading, imports and I/O. This is not single-request latency or a peak-memory benchmark.

The marker-only rule reached 80.81% validation accuracy, demonstrating an artificial source cue. Complete synthetic markers were removed before training and inference, and none remained in transformed training/validation inputs. This removes that declared cue without proving removal of all generation artifacts. The benchmark is synthetic, labels sometimes require missing sender/link/attachment context, and grouping cannot establish complete campaign independence. High benchmark accuracy therefore does not establish real-mail reliability or adversarial robustness.

Detailed, full-precision evidence is in the [training report](reports/baseline-training.json), [test report](reports/baseline-test.json) and [reproduction report](reports/baseline-reproduction.json). No real-inbox, fine-tuning or defense result is claimed. The stage 4 comparison follows below.

### 6.3 Measured pretrained comparison

Stage 4 selected `dima806/phishing-email-detection` before corpus evaluation and kept its external weights unchanged. Validation selected threshold 0.05 on the same 1,725 validation messages using the baseline's F1 grid/tie policy. At that threshold, validation accuracy was 58.14%. The selected 0.05 threshold is the lower boundary of the predeclared grid; the grid was not expanded. Maximizing F1 increased recall but also increased false alarms and reduced validation accuracy relative to 0.50. This threshold is an experimental decision, not an acceptable operational false-alarm policy. The code and protocol were committed at `50172afacad72af4e6afa8596e56044c8bd48f1f` before measurement; both validation and final-test reports record a clean working tree.

The comparison uses the same 1,725 final-test IDs (899 phishing / 826 legitimate). Baseline scores were recomputed and their metrics matched the published stage 3 report. No model, threshold or preprocessing was changed in response to final-test results.

| Measure | Classical baseline | Pretrained at 0.50 | Pretrained selected |
| --- | --- | --- | --- |
| Threshold | 0.44 | 0.50 | 0.05 |
| Accuracy | 98.43% | 61.16% | 59.83% |
| Phishing precision | 97.91% | 58.76% | 57.32% |
| Phishing recall | 99.11% | 85.43% | 89.77% |
| Phishing F1 | 98.51% | 69.63% | 69.96% |
| Legitimate false-positive rate | 2.30% | 65.25% | 72.76% |
| True positives / false positives | 891 / 19 | 768 / 539 | 807 / 601 |
| True negatives / false negatives | 807 / 8 | 287 / 131 | 225 / 92 |

The pretrained model did not outperform the baseline on this benchmark under the declared F1 objective. This measures an externally trained ready-made model versus a baseline fitted to our training split; it does not establish that one architecture is universally better. Missing upstream training membership means data overlap cannot be ruled out. The publisher card is brief, and its tokenizer was reconstructed from the supplied vocabulary and declared cased base model. Domain differences, synthetic writing style and missing email context limit the result.

No test input exceeded 512 tokens; none was truncated or excluded. Original token length reached 345. On CPU with one numerical-library thread, pretrained scoring took 457.82 seconds (265.40 ms per email amortized); the baseline rerun took 0.275 seconds. Pretrained scoring includes tokenization and uses batches of eight. Loading/imports/disk I/O are excluded; timings are not single-request latency or peak-memory measurements. Runtime versions are PyTorch 2.15.0+cpu, Transformers 4.57.6 and safetensors 0.8.0.

Aggregate evidence: [validation report](reports/pretrained-validation.json), [same-test comparison](reports/pretrained-test.json) and [verification/reload report](reports/pretrained-reproduction.json). The verification independently recounts confusion/paired counts from saved predictions and checks repeated loading/scoring on invented fixtures; it is not a second full-corpus transformer evaluation. Fine-tuning, evasion and defense measurements remain future work. Stage 5 will fine-tune a small transformer using training data only.

## 7. Architecture - UML

The component UML marks implemented baseline training, pretrained comparison, both local inference adapters, reviewed artifacts, contracts and dataset preparation. The sequence diagram remains the target web-demo interaction: both classifiers provide CLI prediction, while the UI and explanation are planned.

### 7.1 UML component diagram

![Proposed PhishGuard UML component diagram](diagrams/phishguard-components.svg)

Rectangles marked component are software components; rectangles marked artifact are files. Dashed open-arrow dependencies point from a component to the component/artifact it uses. Green components/artifacts are implemented: CLI, validator, preparation, frozen data, experiment runner, model artifacts, both inference adapters and reports. The CLI calls the selected local scorer; the offline runner separates baseline fitting, external-model threshold selection and final evaluation. Pale components are planned: web UI, explanation and advanced experiments. These are logical Python modules within the application.

The planned Gradio UI will call the Python inference function. Offline training can run on a workstation or Colab; exported reviewed artifacts feed local inference. Model/dataset downloads occur in the reviewed preparation workflow, not in response to pasted message instructions.

### 7.2 UML sequence diagram

![Proposed pasted-email inference UML sequence diagram](diagrams/phishguard-sequence.svg)

The target sequence shows one accepted demo request: validate input, obtain a prediction from a preloaded reviewed model, derive the declared explanation and return a result. A UML alternative fragment covers invalid input. Dashed arrows are replies; vertical dashed lines are lifelines. This interaction performs no training, email transmission or link following.

The editable SVG files are the diagram sources. Update them when the implemented design changes and verify that component responsibilities match the code and its tests.

## 8. Work plan

### 8.1 Reporting rules and equal allocation

The PhishGuard plan in section 8.3 assigns Lior and Sharon Elimelech equal estimated responsibility: 50 planning units each, 100 total. Each work package allocates five units to each person. These are planning weights, not measured working hours. Rebalance responsibilities as actual effort becomes clear and keep the total responsibility balanced.

Named ownership is an assignment of implementation, testing and explanation responsibility. It does not assert that planned code has already been written. Both students review each other's work, understand the full pipeline and record actual contributions with dates and artifacts. Development and documentation may use AI assistance; students remain responsible for validating and explaining the results.

### 8.2 Two-week learning record

Status: completed learning period as reported by the student. Calendar dates and supporting study artifacts remain to be supplied. The session grouping and review leads below organize that report; they do not assert an independently verified daily schedule or a completed exercise.

| Relative session | Topics studied | Review lead | Shared record to attach |
| --- | --- | --- | --- |
| Week 1, session 1 | Cryptography, confidentiality, integrity and authentication | Lior | Agreed glossary notes |
| Week 1, session 2 | Symmetric encryption and shared-key handling | Sharon Elimelech | Symmetric-key explanation |
| Week 1, session 3 | Asymmetric cryptography, public/private keys and their relation to symmetric keys | Lior | Key-role comparison |
| Week 1, session 4 | Algorithms/ciphers and hash functions | Sharon Elimelech | AES/TLS/hash distinction |
| Week 1, session 5 | HMAC, salt and password-storage principles | Lior | HMAC/signature/salt comparison |
| Week 2, session 1 | TLS handshake, traffic encryption and authentication | Sharon Elimelech | Annotated TLS explanation |
| Week 2, session 2 | X.509 certificates, CSR and certificate authorities | Lior | Certificate-chain notes |
| Week 2, session 3 | CRLs, revocation and limits of certificate-based trust | Sharon Elimelech | Revocation/expiry comparison |
| Week 2, session 4 | Models, generative AI, Hugging Face and LLM-course introduction | Lior | Model-card review notes |
| Week 2, session 5 | AI agents, tools and agents-course introduction; recap | Sharon Elimelech | Classifier/agent distinction |

Both students participate in all topics. Each has five review-lead sessions. Python, pandas/data handling, text labels, TF-IDF, logistic regression, leakage and evaluation receive an additional foundation milestone; they are not retrospectively included in the reported crypto/TLS learning period.

### 8.3 Two-semester milestones and ownership

Relative milestones avoid inventing semester dates. Attach submission dates when the course calendar is available. W01's learning is user-reported and its evidence collation remains open. W02's specification, environment, contracts and synthetic fixtures are implemented and checked; the students' individual review remains to be recorded. W03 dataset preparation is implemented and checked, with individual student review still open. W04 baseline training, artifacts, evaluation and reproduction are implemented; student review remains open. W05 pretrained source review, adapter, mapping checks and comparative evaluation are implemented and measured; student review remains open. W06-W10 implementation has not started.

| Package / period | Lior - 5 units | Sharon Elimelech - 5 units | Completion evidence |
| --- | --- | --- | --- |
| W01 / two learning weeks | Review five sessions and consolidate crypto/key notes | Review five sessions and consolidate TLS/AI notes | Shared learning record and individual evidence |
| W02 / Semester A foundation | Maintain requirements and component UML; implement email/result contracts | Maintain STRIDE, sequence UML and test matrix; implement validation fixtures | Reviewed book, runnable contracts and tiny fixtures |
| W03 / Semester A data | Source/license manifest and dataset ingestion | Label audit, deduplication and grouped split validator | Frozen dataset manifest; each reviews the other's output |
| W04 / Semester A baseline | TF-IDF/logistic-regression training and save/load pipeline | Baseline metrics, threshold selection and leakage tests | Reproducible baseline and reviewed report |
| W05 / Semester A comparison | Pretrained-model selection, card/license review and inference adapter | Label/domain compatibility checks and comparative evaluation | Same-protocol comparison and semester checkpoint |
| W06 / Semester B detector | Fine-tuning script, environment and configuration | Tokenization/training-data checks, reproducibility and error analysis | Reviewed small-transformer checkpoint and model card |
| W07 / Semester B evasion | Bounded perturbation operations and query-budget harness | Label-preservation review, paired metrics and attack test fixtures | Offline attack artifact set and baseline degradation report |
| W08 / Semester B defense | Integrate defended inference and measure clean-performance costs | Implement training-only adversarial augmentation and defense training | Fixed-variant and fresh-search comparison under equal budgets |
| W09 / Semester B demo | Pasted-email UI, input limits and local packaging | Evidence-based explanation, privacy/error tests and usability review | Demonstrable classifier with model identity and limitations |
| W10 / final submission | Reproduction guide, architecture/test chapters and demo walkthrough | Comparative experiment report, conclusions and presentation assembly | Both review all materials and present their work |

Totals: Lior 10 x 5 = 50 units; Sharon Elimelech 10 x 5 = 50 units. The asymmetry of roles within each package is balanced by review, experiments and later integration work. Both must understand and be able to demonstrate the full pipeline.

### 8.4 Contribution evidence and stage completion

The specification, STRIDE table, UML, test plan and ownership schedule are present. Stage 1 adds working contracts and an offline validator. Stage 2 adds pinned-source acquisition, a sample label audit, deduplication, frozen grouped splits and dataset tests. The documents, code and initial audit were developed with AI assistance for both students to review. Stage 3 adds the trained baseline, safe model artifacts, measured evaluation and local inference. Stage 4 adds a reviewed pretrained transformer, paired comparison and local inference. Transformer fine-tuning, perturbation/defense experiments and the web demo remain incomplete.

Lior owns the input/result contracts, dataset ingestion, baseline training, model adapters, fine-tuning runner, perturbation operations and demo integration listed in section 8.3. Sharon Elimelech owns validation fixtures, dataset quality and splits, evaluation and leakage checks, tokenization/reproducibility checks, perturbation validity, defense training and explanation/privacy checks. Each implementation package also includes tests and peer review; the weights in section 8.3 include that work.

For every completed contribution record the package ID, student, actual activity, date, artifact or commit, peer review and check results in the [stage log](stage-log.md). Keep assigned ownership, implemented behavior and completed personal review distinct. Update this book and its UML when behavior changes, and add measured conclusions after the experiments.

### 8.5 References and assignment provenance

The primary course reference is the student-supplied Project2_PhishGuard.docx, titled Project 2 - PhishGuard: AI Phishing Detection & Adversarial Robustness. The eight-chapter structure and reported learning topics follow the course-book checklist supplied by the student. External references support definitions and methods; project-specific threats, limits and allocations are design choices. The assignment document is retained locally as the course reference.

- [R1 - IETF RFC 8446: TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446)
- [R2 - NIST FIPS 180-4: Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
- [R3 - IETF RFC 2104: HMAC](https://www.rfc-editor.org/rfc/rfc2104)
- [R4 - NIST SP 800-63B-4: authentication and password verifiers](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [R5 - IETF RFC 5280: X.509 certificates and CRLs](https://www.rfc-editor.org/rfc/rfc5280)
- [R6 - Hugging Face: text classification and fine-tuning](https://huggingface.co/docs/transformers/tasks/sequence_classification)
- [R7 - Hugging Face: what is an agent?](https://huggingface.co/learn/agents-course/unit1/what-are-agents)
- [R8 - Hugging Face LLM course](https://huggingface.co/learn/llm-course/chapter1/1)
- [R9 - scikit-learn: TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [R10 - scikit-learn: common pitfalls and data leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- [R11 - Microsoft: STRIDE threat categories](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)

- [R12 - E-PhishGen: author dataset and source card](https://huggingface.co/datasets/pajola/e-phishGen)

- [R13 - scikit-learn: LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)
- [R14 - scikit-learn: model persistence](https://scikit-learn.org/stable/model_persistence.html)

- [R15 - Pinned pretrained phishing classifier card/configuration](https://huggingface.co/dima806/phishing-email-detection/tree/310a5602280486e01dd60e37230980cfcc327b41)
