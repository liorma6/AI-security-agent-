# Learning and contribution register

Updated November 17, 2026. Team: **Lior Mashaich and Sharon Elimelech**. Supervisor: **Zimon Roi**. Institution: **HIT**. Course: **AB- Ai Security**.

## Period and current evidence

The student confirmed the calendar period as **November 2026 through July 2027** on November 17, 2026. These are the agreed project-planning months; no exact institutional deadlines have been supplied. W01-W10 are work-package identifiers, not calendar week numbers.

The implementation, experiments and prepared submission documents already exist with their actual November repository history. The calendar below assigns student learning, code ownership, inspection, explanation and handoff of those outputs. It does not move completed experiments to later months or schedule new model fitting. Activities after the current date are planned; the calendar is not a retrospective attendance or work-hours record.

| Existing record | What it establishes | What remains unrecorded |
| --- | --- | --- |
| [Book section 1.1 and section 8.2](project-book.md) | A two-week crypto/TLS/AI learning period reported by the student; ten topic sessions organized with five review leads per student | Actual dates, individual notes and whether each proposed review session took place |
| [Book section 8.3](project-book.md) and [implementation plan](implementation-plan.md) | Ten packages, each assigning five responsibility units to each student; 50 units each overall | Personal completion dates, actual effort and individual review evidence |
| [Stage log](stage-log.md), source code and aggregate reports | Implemented AI-assisted software, executed checks and measured project results | An independent attribution of each code change or review to either student |
| This register and [editable contribution log](contribution-log.csv) | An explicit November-July schedule, individual deliverables and a common recording format | Planned rows become completed entries only when the actual date and supporting artifact are supplied |

The reported two-week learning period is retained as reported. November below is the proposed month for consolidating and reviewing those concepts; it does not assert that the original study happened on invented November dates.

## Fair allocation and review

Lior Mashaich and Sharon Elimelech each receive **50 of 100 planning units**. November contains W01 and W02, giving ten units to each student. Each remaining month contains one package, giving five units to each. These are relative responsibility weights, not hours already worked.

For each five-unit package, the suggested allocation per student is two units for the assigned code/system area, one for testing and peer review, one for learning and one for documentation or demonstration. For W01 the code/system component becomes concept exercises. Both students study every topic, inspect the other's area and give an explanation of the complete pipeline. Sharon Elimelech owns technical implementation areas as well as evaluation; Lior Mashaich also owns checks and documentation.

At the end of each month, compare actual recorded effort and unfinished work. If the workload differs, transfer a concrete remaining task and record the change. Equal planning weights alone do not prove equal actual effort. A Git author field or an AI-generated draft alone does not establish personal authorship.

## Monthly responsibilities and deliverables

All rows below are **planned student activities** as of November 17, 2026. Existing implementation artifacts are references to inspect, not evidence that the listed personal activity has happened.

| Month / package | Lior Mashaich | Sharon Elimelech | Shared learning and completion evidence |
| --- | --- | --- | --- |
| November 2026 / W01-W02 / 10 units each | Lead five foundation review sessions; explain requirements and component UML; inspect email/result contracts and CLI setup | Lead five foundation review sessions; explain STRIDE and sequence UML; inspect input validation, fixtures and error cases | Two-week foundation consolidation; Python/Git/pytest introduction; one individual study note and one reviewed contract/test walkthrough per student |
| December 2026 / W03 / 5 units each | Explain source/license manifests, ingestion and MIME/text extraction; inspect acquisition failure handling | Explain labels, deduplication, group assignment and split validation; inspect leakage checks | Dataset provenance and leakage; an ingestion map and a grouping/split checklist, cross-reviewed |
| January 2027 / W04 / 5 units each | Explain TF-IDF/logistic regression, fitting and artifact save/load; trace the baseline training runner | Explain confusion counts, precision/recall/F1, validation threshold selection and metric/leakage tests | Underfitting, overfitting and generalization; one training-pipeline note and one hand-worked metric example |
| February 2027 / W05 / 5 units each | Explain the pinned pretrained adapter, label mapping, external source/MIME repairs and separate baseline-v2 artifacts | Explain same-cohort comparison, relatedness boundaries, challenge false alarms and the disclosed inspection-boundary deviation | Hugging Face model cards, domain shift and source/label bias; a model/source audit and a comparison-limitations note |
| March 2027 / W06 / 5 units each | Explain BERT-Tiny fine-tuning, optimizer/seed settings, training runner and checkpoint identity | Explain tokenizer limits, validation-only checkpoint selection, evaluation and reproducibility checks | Tokenization, attention, transfer learning and truncation; an annotated training trace and a checkpoint/metric review |
| April 2027 / W07 / 5 units each | Explain bounded text transformations, parent/group lineage and query-budget enforcement | Explain validity review, candidate ASR denominators, paired comparison and evasion test fixtures | Controlled adversarial robustness and meaning preservation; a transformation walkthrough and an ASR/review worksheet using invented examples |
| May 2027 / W08 / 5 units each | Explain defended-model loading/inference, artifact separation and clean-performance costs | Explain training-only augmentation, defense training, validation selection and verification | Data augmentation, robustness trade-offs and experimental controls; a preservation/clean-cost note and an augmentation/defense explanation |
| June 2027 / W09 / 5 units each | Explain the Gradio UI, model registry, input limits and local startup/packaging | Explain feature contributions versus text indicators, error/privacy behavior and usability checks | Local web inference, privacy and explanation limits; one demo walkthrough and one desktop/mobile acceptance checklist |
| July 2027 / W10 / 5 units each | Explain the frozen final protocol and independent verification; finalize architecture/reproduction text and the demonstration recording segment | Explain final comparison, uncertainty and conclusions; finalize One Pager, graphs, presentation and the results recording segment | Scientific reporting and oral defense; two individual reflection notes, mutual presentation review, completed submission checklist and video/link when actually produced |

## November foundation sequence

Both students participate throughout. The ten relative sessions preserve the existing allocation from book section 8.2. No exact daily dates are asserted.

| Relative session | Topic | Review lead | Individual evidence to prepare |
| --- | --- | --- | --- |
| Week 1 / 1 | Cryptography, confidentiality, integrity and authentication | Lior Mashaich | Explain the three properties with project examples |
| Week 1 / 2 | Symmetric encryption and shared-key handling | Sharon Elimelech | Explain one shared key and its distribution problem |
| Week 1 / 3 | Asymmetric cryptography and public/private keys | Lior Mashaich | Compare public/private keys with a symmetric traffic key |
| Week 1 / 4 | Algorithms, ciphers and hash functions | Sharon Elimelech | Distinguish AES, TLS and hashing |
| Week 1 / 5 | HMAC, salt and password storage | Lior Mashaich | Distinguish message authentication, signatures and salted password hashing |
| Week 2 / 1 | TLS handshake and traffic protection | Sharon Elimelech | Draw the roles of authentication and traffic encryption |
| Week 2 / 2 | Certificates, CSR and certificate authorities | Lior Mashaich | Explain a certificate chain and domain binding |
| Week 2 / 3 | CRLs, revocation and expiry | Sharon Elimelech | Explain why a valid date alone is insufficient |
| Week 2 / 4 | Models, generative AI and Hugging Face | Lior Mashaich | Explain a model card, intended use and evaluation limits |
| Week 2 / 5 | AI agents, tools and recap | Sharon Elimelech | Explain why the current classifier demo is not an autonomous agent |

These are security foundations. The implemented PhishGuard product classifies email text; the learning topics do not imply that it implements TLS scanning, password storage or an autonomous agent.

## Code and report references for individual walkthroughs

| Package | Existing material to study and explain |
| --- | --- |
| W01-W02 | [Glossary and STRIDE](project-book.md), [contracts](contracts.md), [validation](../src/phishguard/validation.py), [CLI tests](../tests/test_cli.py) |
| W03 | [Dataset guide](dataset.md), [dataset verification](../src/phishguard/datasets/verification.py), [dataset tests](../tests/test_datasets.py) |
| W04 | [Baseline study](baseline.md), [model](../src/phishguard/baseline/model.py), [metrics](../src/phishguard/baseline/metrics.py), [baseline tests](../tests/test_baseline.py) |
| W05 | [Pretrained comparison](pretrained.md), [adapter](../src/phishguard/pretrained/adapter.py), [audit](generalization-audit.md), [refresh](baseline-refresh.md), [current comparison](current-comparison.md) |
| W06 | [Fine-tuning study](finetuned.md), [training](../src/phishguard/finetune/training.py), [evaluation](../src/phishguard/finetune/evaluation.py), [tests](../tests/test_finetune.py) |
| W07 | [Controlled evasion](controlled-evasion.md), [transformations](../src/phishguard/evasion/perturbations.py), [ASR metrics](../src/phishguard/evasion/metrics.py), [tests](../tests/test_evasion.py) |
| W08 | [Defense study](robustness-defense.md), [defense tests](../tests/test_defense.py), [independent verification tests](../tests/test_defense_verification.py) |
| W09 | [Demo guide](demo.md), [UI](../src/phishguard/demo/ui.py), [service](../src/phishguard/demo/service.py), [tests](../tests/test_demo.py) |
| W10 | [Frozen final protocol/results](final-evaluation.md), [verifier](../scripts/verify_final.py), [submission guide](submission.md), [presentation](presentation.md), [One Pager](one-pager.md) |

The final 703-message reserve is already consumed evaluation evidence. Learning exercises and reviews must preserve the existing models and thresholds; use invented fixtures for new exercises. This calendar does not authorize retraining on test outcomes or reusing the reserve as a fresh test.

## How completed personal entries are recorded

The [editable CSV](contribution-log.csv) contains eighteen planned entries: one per student per month. Actual dates, hours, evidence links and peer-review fields are initially empty. Blank fields mean not supplied, not zero effort. Change an entry's status only after recording the corresponding activity.

Each completed entry records: student; package; actual date; work actually performed; what was learned; artifact or commit; check performed and result; AI assistance; and peer review with an actual date when it occurs. Evidence can be a study note, an explanation recording, an annotated code review or the output of a check the student actually ran. A completed artifact existing in the repository is not a substitute for a personal walkthrough.

| Status | Meaning |
| --- | --- |
| Planned | Allocated activity; personal completion is not claimed |
| In progress | The student reports starting the activity; add the start date and partial evidence |
| Completed - self-reported | The student supplies the actual date, activity and evidence |
| Completed - peer reviewed | The other student records a review date, comments and any checked outcome |

For work already performed, enter its actual past date and describe it in the student's own words. Do not alter the repository chronology to fit this calendar. Keep personal identifiers and private email content out of the public evidence log.
