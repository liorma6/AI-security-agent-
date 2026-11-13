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

## Reproduce

Prepare the internal dataset and baseline using the README first. From the repository root:

```sh
uv run --frozen phishguard audit fetch
uv run --frozen phishguard audit prepare
uv run --frozen phishguard audit internal
uv run --frozen phishguard audit evaluate
```

The fetch command uses operating-system certificate verification and digest checks. Preparation runs offline; its generated manifest must exactly match the committed [external manifest](../data/manifests/external-mail-v1.json) when evaluation loads it. Existing output directories are refused. Use separate paths for a repeat:

```sh
uv run --frozen phishguard audit prepare --output data/processed/external-mail-reproduction
uv run --frozen phishguard audit evaluate --dataset data/processed/external-mail-reproduction --output artifacts/generalization-external-reproduction
uv run --frozen python scripts/verify_generalization.py
```

The independent verifier recounts predictions, compares preparation/prediction bytes, verifies the model digest and hashes reserve bytes without parsing or scoring them. It writes the text-free verification report. Downloads are about 36.4 MB; all message files remain in ignored local folders. Aggregate reports are committed. Source files changing at the publisher cause an integrity error, not silent adoption of new data.

## Measured results - November 13, 2026

Protocol/code freeze: `385b881563fcc22ded9b3ccc1a03485445109980`. Cohort and pre-score review freeze: `09165d3b40a46cc84504356789bcd8bc499c5249`. Internal and external reports record the latter clean commit. Model weights, vocabulary, preprocessing and threshold remained unchanged.

The 2,534 mailbox records yielded 2,342 eligible unique messages. Exclusions: 74 not confidently English, 31 undecodable, 11 invalid/overlong, five over the raw-message bound, one mailbox system record, 69 exact duplicates and one external message related to the internal corpus. No conflicting exact labels were found. Preparation retained 1,596 legitimate and 746 phishing messages. The fixed allocation produced 1,639 audit messages in 1,003 groups (1,117 legitimate / 522 phishing) and 703 reserve messages in 432 groups (479 legitimate / 224 phishing). No detected group crosses audit/reserve; the reserve was not scored or manually reviewed.

The [pre-score sample review](external-label-audit.md) found context-dependent labels and an uninformative plain-text MIME placeholder. Those messages were kept. The review is not a whole-corpus ground-truth validation.

| Measure | Internal synthetic test | External audit |
| --- | --- | --- |
| Rows | 1,725 | 1,639 |
| Accuracy | 98.43% | 92.86% |
| Balanced accuracy | 98.40% | 91.75% |
| Phishing precision | 97.91% | 88.87% |
| Phishing recall | 99.11% | 88.70% |
| Phishing F1 | 98.51% | 88.78% |
| Legitimate false-positive rate | 2.30% | 5.19% |
| TP / FP / TN / FN | 891 / 19 / 807 / 8 | 463 / 58 / 1,059 / 59 |

The external missed-phishing rate is 11.30% (59/522). Accuracy alone hides the class mix: always predicting legitimate would score 68.15% here. Balanced accuracy averages phishing recall and legitimate specificity, giving the two classes equal weight. Whole-group bootstrap 95% intervals: accuracy 91.31-94.33%, balanced accuracy 89.78-93.57%, recall 85.09-91.79%, false-positive rate 3.74-6.81% (1,000 resamples, seed 42). These intervals are conditional on this sample and heuristic grouping.

Per-source phishing recall: Nazario 2024, 194/221 = 87.78%; Nazario 2025, 269/301 = 89.37%. Legitimate false-positive rate: easy ham, 52/959 = 5.42%; hard ham, 6/158 = 3.80%. Each source contains one class, so source-specific precision is not evidence of deployment precision. No input had an all-zero TF-IDF vector. Scoring took 0.532 seconds for the batch (0.325 ms per email amortized), on Windows/Python 3.13.16 with one numerical-library thread, excluding loading/imports/I/O.

## Internal diagnosis and conclusions

Frozen training accuracy is 99.32%, validation 98.67% and test 98.43%. The training-to-test gap is 0.88 percentage points. The original grouping rule found zero cross-split components; the broader audit found one train/test relation through a normalized subject. Excluding that one test message as a post-hoc sensitivity check leaves 98.43% on 1,724 messages. This is not a replacement test set, and the heuristic cannot prove semantic/campaign independence.

Feature associations show source-specific cues: `download` occurs in 668 phishing versus two legitimate training messages; `invoice` in 430 versus zero; `training` in three versus 315. After fixed preprocessing, HTTP-URL patterns occur in 204 legitimate training messages and zero phishing messages. Such patterns justify concern about source shortcuts but do not establish their causal contribution to errors. No feature was removed or retuned based on this diagnosis.

The external decline is evidence of a generalization gap under source/era/extraction differences. It does not isolate excessive training, prove that more training caused overfitting, or estimate contemporary company-inbox performance. The 98.43% internal score must not be presented as universal accuracy. The baseline remains a useful reproducible comparator; it has not been validated as a production security filter.

Independent preparation produced byte-identical audit/reserve files and manifest. Repeated evaluation produced byte-identical predictions and identical metrics/bootstrap intervals; an independent recount matched every confusion count. The baseline digest is unchanged. Full-precision evidence: [internal audit](reports/generalization-internal.json), [external audit](reports/generalization-external.json), [verification](reports/generalization-verification.json).

## Work-plan decision

Stage 4a is complete. Stage 5 has not started. Before future training, declare the training sources, label/extraction policy, validation objective and fresh final-evaluation protocol. The now-inspected audit cohort is development evidence; do not tune on it and later call its score unseen-test performance. The untouched reserve can support a future precommitted evaluation, but cannot remove source/era confounding. More representative contemporary data containing both classes remains desirable for stronger claims.

W05 assigns Lior external provenance, downloads and MIME extraction; Sharon Elimelech owns overlap/group separation, label-review checks, metrics and uncertainty. Both share interpretation and review, with the existing equal planning weights. Implementation, experiments and initial review are AI-assisted; completed individual student review is not asserted.
