# Stage 4a - Generalization audit

This additional checkpoint investigates whether the high internal score transfers to external email. It does not train a model or start stage 5. The exact stage-3 TF-IDF/logistic-regression artifact and its threshold of 0.44 are frozen in the [protocol](../src/phishguard/audit/protocol.json). The original synthetic test result remains a same-source benchmark, not a real-inbox accuracy claim.

## Sources and interpretation

The [source manifest](../src/phishguard/audit/source.json) pins public publisher URLs, byte counts and SHA-256 digests. Phishing messages come from Jose Nazario's 2024 and 2025 personal-inbox archives. His [README](https://monkey.org/~jose/phishing/README.txt) describes manual classification and possible errors; the [license](https://monkey.org/~jose/phishing/LICENSE.txt) is CC BY 4.0. Attribution: Jose Nazario, phishing email corpus; local modifications consist of MIME extraction, language filtering, deduplication and grouping.

Legitimate messages come from SpamAssassin's February 2003 `easy_ham_2` and `hard_ham` archives. The [publisher README](https://spamassassin.apache.org/old/publiccorpus/readme.html) offers the corpus for filtering research/testing while retaining the original authors' copyrights; it does not supply a standardized data license. This is not an Apache software-license claim. Raw messages stay local and are not redistributed in the repository. General spam is not relabeled as phishing.

Source and era are confounded with class: recent phishing versus older legitimate email. Labels are publisher judgments, not independently verified ground truth. The combined corpus is a cross-source stress test, not a sample of contemporary inbox prevalence. English filtering and input limits further restrict the population represented. Bootstrap intervals cannot correct these biases.

## Frozen procedure

1. Verify the source files. Parse subject and inline MIME text offline, preferring plain text and otherwise extracting inert HTML text. Ignore attachments, embedded messages and non-subject headers; never render HTML or follow message links. Remove leading classification flags from subjects. Reject unusable/overlong messages rather than truncate.
2. Accept only confident English text using fixed language profiles and seed. Record every rejection by ID and reason, without publishing message content.
3. Collapse exact model-input duplicates and exclude conflicting exact labels. Group exact bodies, sufficiently long normalized subjects, templates and body word-trigram Jaccard similarity of at least 0.70, including transitive relatives. Exclude any external component touching any internal train, validation or test record.
4. Allocate whole groups to a 70% audit / 30% reserve target by class using the fixed seed. Freeze the text-free manifest before inference. Preparation necessarily reads all messages for quality and grouping; evaluation reads only `audit.jsonl`. The reserve receives no model scores or manual content review.
5. Review a deterministic sample of eight audit messages per class before predictions, reporting ambiguity without changing labels or excluding difficult messages.
6. Recheck the original internal grouping and report a broader, exploratory similarity diagnostic, train/validation/test gaps and coefficient/pattern associations. Do not refit or change features.
7. Score every eligible external audit message with the frozen baseline and threshold. Report confusion counts, class metrics, balanced accuracy, per-source results, group-bootstrap intervals and exclusions. Independently recount predictions and verify unchanged model artifacts.

The original 0.90 grouping rule and broader 0.70 diagnostic serve different purposes. Broader matches can include unrelated messages; their presence alone is not proof of leakage. Once inspected, the audit cohort is development evidence. Any future final use of the reserve requires a separately frozen protocol, and the reserve still shares the same source/era limitations.

## Status

The audit implementation and protocol are being frozen before corpus preparation and scoring. Results will be added after execution. Stage 5 remains unstarted. W05 assigns Lior the external-source/MIME pipeline and Sharon Elimelech the group separation, metrics and review checks, with equal responsibility and shared review. Implementation and initial review are AI-assisted; completed individual student review is not asserted.
