# PhishGuard - Initial Project Book

Revision 1.0 - November 13, 2026

Team: Lior and Sharon Elimelech. Course-aligned proposal based on Project2_PhishGuard.docx and the student's eight-chapter checklist.

Status: INITIAL PROJECT SPECIFICATION. The PhishGuard scope, requirements, threat model, architecture and work plan are documented. Dataset preparation, classification, training, adversarial evaluation and the demo are planned and not implemented. This book is the canonical specification; it will acquire implementation evidence and experimental results as each stage is completed.

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

No accuracy, recall or robustness result is claimed at this initial stage. Select thresholds using validation data. Report unsuccessful experiments and trade-offs instead of choosing conclusions in advance.

### 2.1 Experimental questions and metrics

Compare the baseline, the selected pretrained classifier, the fine-tuned model and its defended version. Report accuracy, phishing precision/recall/F1, legitimate-email false-positive rate, confusion matrices, class counts, inference time and resource conditions. Use the same held-out originals for paired clean/perturbed comparisons.

Attack success rate (ASR) is the fraction of eligible phishing originals correctly detected by the evaluated model for which at least one valid perturbation causes a legitimate prediction within the attack budget. Report numerator, denominator, valid-perturbation coverage and query counts. Different models may have different eligible sets; do not compare ASR numbers alone as if their denominators were identical.

For the defense comparison, report results on fixed saved variants and the same evaluation cohort, and separately report a fresh attack search against the defended model using the same budget. Keep attack tuning and defense training away from the final test set. Group an original email, duplicates, its campaign/template relatives where identifiable and all derived variants into one split. Fit TF-IDF and preprocessing statistics on training data only. [R10]

## 3. Technical requirements

### 3.1 Requirements from the supplied brief

All PG requirements below are planned and not yet implemented.

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

Start with English plain-text subject/body inputs, subject to dataset review. Raw MIME parsing, attachments, sender authentication, mailbox integration and multilingual claims are outside the first version. Choose and pin a Python/training-library combination after checking the selected model's requirements. Keep large checkpoints and datasets outside Git and record their provenance and digests in small manifests.

Select a public dataset after checking license, privacy, label semantics and overlap with evaluation sources. Select a pretrained classifier with relevant phishing/legitimate labels. A generic sentiment model cannot be evaluated by relabeling positive/negative sentiment as safe/phishing. A base encoder without a trained classification head also does not provide a ready phishing detector.

### 3.3 Quality, security and reproducibility requirements

| ID | Proposed requirement | Acceptance |
| --- | --- | --- |
| Q01 | Trace every dataset/model/experiment revision | Manifest with source revision, digest, seed, configuration and split IDs |
| Q02 | Prevent leakage | No group or derived variant crosses splits; training alone fits transformations |
| Q03 | Preserve email privacy | No raw pasted email logging or storage by default; licensed/redacted fixtures only |
| Q04 | Bound resource use | Proposed 20,000-character and 512-token limits, visible truncation, bounded concurrency and explicit failures; tune after profiling |
| Q05 | Treat email content as inert data | Render escaped text; do not open links, send mail or execute attachments/instructions |
| Q06 | Load reviewed model artifacts | Pin revisions, verify manifests and disable unreviewed remote code; avoid untrusted serialized executables |
| Q07 | Explain uncertainty | Display a model score, threshold and model identity; do not claim a calibrated probability without calibration evidence |
| Q08 | Keep training/evaluation distinct from the demo | Offline runner owns training and perturbation; UI cannot invoke arbitrary scripts |
| Q09 | Reproduce a clean run | Document installation, test command, data preparation and evaluation with resource limits |

### 3.4 Data design

| Record | Required information |
| --- | --- |
| EmailExample | ID, reviewed text, binary label, source, license reference, group ID and split |
| ModelArtifact | Model/tokenizer revisions, label mapping, preprocessing configuration, manifest digest and threshold |
| Perturbation | Original ID, operation, seed, budget/query count, changed text and validity review |
| Prediction | Example/variant ID, model revision, score, decision, threshold and elapsed time |
| ExperimentRun | Dataset/split versions, compared models, defense configuration, metric counts and artifact references |

Separate model indicators from factual claims about the sender. A baseline explanation can show influential TF-IDF features; a transformer explanation needs a declared attribution or indicator method and limitations. Generated prose is optional and cannot replace measurement.

## 4. STRIDE threat analysis

This is a proposed threat model for PhishGuard. The controls and checks below are not implemented merely because they are described here. STRIDE provides six categories for analyzing system threats. The specific threats, priorities and controls below are design judgments for this project. [R11]

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

The repository currently contains the PhishGuard specification and implementation plan. Documentation verification checks the required chapter structure, local links and project consistency. The [stage log](stage-log.md) records actual completed checks and their scope.

No phishing-classifier unit tests or model-quality measurements exist yet. Add tests alongside each implemented module. A documentation check is not an inference test, and a planned test is not a passing test.

### 5.2 Planned PhishGuard unit-test matrix

All tests below are planned. Use small offline fixtures with fixed seeds; expensive model training and full-corpus evaluation belong to separate integration/experiment checks.

| ID | Unit and input | Expected result | Owner |
| --- | --- | --- | --- |
| U01 | Empty, whitespace and malformed email input | A structured validation error; no inference call | Lior |
| U02 | Exact length limit and one character above it | Accepted at the boundary; rejected above it; truncation is explicit | Sharon |
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

Run a tiny prepare/train/save/load/predict cycle and verify schema, label mapping and reproducibility within declared numerical tolerance. Test the actual selected classifier on a small reviewed fixture set. Exercise the pasted-email UI and failure states without sending email or fetching message links. Validate the complete attack/defense evaluation on frozen splits and compare metrics to independently computed counts.

Keep unit-test pass counts separate from model-quality measurements. A passing test suite cannot establish that the detector generalizes to real mail.

## 6. Summary and conclusions

PhishGuard will combine phishing-email classification with a controlled adversarial robustness experiment. The specification defines the dataset, baseline, pretrained comparison, fine-tuning, perturbation, defense and demonstration work required to answer the research questions.

The proposed solution is a modular Python experiment with a simple local Gradio demo and versioned artifact manifests. Evaluation must distinguish performance on clean messages, performance under controlled changes, and the cost or benefit of the chosen defense.

This initial book contains the required eight chapters, a STRIDE analysis, UML design, test plan and equal ownership allocation. It contains no claimed detector accuracy, trained-model result or completed defense. Those conclusions must follow measured experiments.

Open implementation decisions are the licensed dataset, confirmed language coverage, pretrained checkpoint, compatible training environment and practical compute budget. The next stage establishes the Python development environment, email/result contracts and small reviewed fixtures; dataset preparation and the baseline then follow in the [implementation plan](implementation-plan.md).

## 7. Architecture - UML

The following UML diagrams describe the proposed PhishGuard design. They specify intended modules and interactions; the application components have not been implemented.

### 7.1 UML component diagram

![Proposed PhishGuard UML component diagram](diagrams/phishguard-components.svg)

Rectangles marked component are software components; rectangles marked artifact are files. Dashed open-arrow dependencies point from a component to the component/artifact it uses. The demo depends on shared inference and explanation modules. The offline runner depends on data preparation, trainers, the perturbation harness and evaluation. All use reviewed versioned artifacts. These are logical Python modules within the application.

The Gradio UI calls a Python inference function. Offline training can run on a workstation or Colab; exported reviewed artifacts feed local inference. Model/dataset downloads occur in the reviewed preparation workflow, not in response to pasted message instructions.

### 7.2 UML sequence diagram

![Proposed pasted-email inference UML sequence diagram](diagrams/phishguard-sequence.svg)

The sequence shows one accepted request: validate input, obtain a prediction from a preloaded reviewed model, derive the declared explanation and return a result. A UML alternative fragment covers invalid input. Dashed arrows are replies; vertical dashed lines are lifelines. This interaction performs no training, email transmission or link following.

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

Relative milestones avoid inventing semester dates. Attach submission dates when the course calendar is available. W01's learning is user-reported and its evidence collation remains open. W02's specification draft exists; its code contracts, fixtures and student review remain planned. Implementation in W03-W10 has not started.

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

The specification, STRIDE table, proposed UML, planned tests and ownership schedule are present. These documents are AI-assisted drafts for both students to review. No dataset preparation, classifier, training pipeline, perturbation harness or demo implementation is claimed as complete.

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
