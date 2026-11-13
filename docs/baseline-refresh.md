# Stage 4b - Data refresh and baseline re-evaluation

This bounded study addresses the stage-4a generalization gap. It retains baseline v1, the original synthetic corpus and the 703-message reserve. It trains a separate TF-IDF/logistic-regression baseline v2; stage 5 and transformer fine-tuning are outside this stage. The protocol below is declared before fitting and new held-out scoring. The completed measurements and their limitations follow below.

## Diagnosis and source review

All 117 errors from the previously scored external audit receive automatic full-text indicator profiles and subject/body excerpt triage. A deterministic sample of 24 correctly classified messages is a control. Excerpts are not a complete ground-truth audit. False positives include technical/list discussions, account administration, newsletters and promotional mail. False negatives include account/delivery lures, unrelated padding, short or context-dependent messages and unusable plain-text alternatives. Several publisher-phishing labels require missing sender/link context; labels are retained, not changed to match predictions. Indicators overlap and do not establish causes.

The [new source manifest](../src/phishguard/refresh/source.json) pins six files by byte count and SHA-256. Attribution and source restrictions remain attached to every processed record. Raw texts, model vocabularies and predictions stay local.

- [MeAJOR v2.0](https://zenodo.org/records/18471483), Cardoso, Vitorino, Mendes, Maia and Praca, publisher CC BY 4.0. The downloaded CSV actually contains only TREC 2005/2006/2007 sources, despite the broader landing-page description. Use only label `0.0` (ham); exclude every `1.0` row. Generic spam is not phishing ground truth. Use subject/body only, excluding engineered features and sender identifiers. Take at most 600 publisher-English rows per source by fixed hash, then apply the seeded language filter. The mail is historical; archive dates are not authenticated.
- [Jose Nazario's phishing corpus](https://monkey.org/~jose/phishing/), `phishing3.mbox`, publisher CC BY 4.0. Add at most 1,800 eligible historical phishing messages, circa 2007. MIME extraction and language filtering precede deterministic hash sampling. This brings phishing closer to the ham era without eliminating source/class confounding. The publisher warns that labels can contain mistakes.
- [Phishing validation emails v3](https://zenodo.org/records/23954793), Miltchev, Rangelov and Genchev, publisher CC BY 4.0. This separate challenge contains 2,000 short English texts: 1,900 generated from templates and 100 original records. Although the README describes inbox/SMS messages, the data dictionary marks original provenance unverified. Never train on this source. Bind CSV rows to the metadata and keep declared templates together; report generated and original subsets separately.

The previously inspected Nazario 2024/2025 and SpamAssassin audit messages become development-only data under their [existing terms](generalization-audit.md). No newly verified contemporary English corpus containing both legitimate and phishing mail was established. This stage improves training coverage but cannot justify contemporary-inbox performance claims. Publisher licenses are recorded, not an independent rights/authenticity audit; no raw mail is redistributed.

## Frozen procedure

1. Retain all original files and model v1. Restrict extraction repairs to whole plain placeholders (`normal`, `no-reply`, the known HTML-viewing notice) with a valid inline HTML alternative, and rooted HTML accidentally stored as plain text. Extract visible text without links, rendering or attachments. Preserve valid original MIME text if repair is unusable. Ordinary prose/code quotations and the core baseline preprocessing remain unchanged; Unicode attack normalization is not implemented.
2. Deduplicate exact cleaned inputs, excluding conflicting exact labels. Use transitive 0.70 body-trigram, subject, template and exact-text relations, augmented by known prior group IDs and declared challenge templates. Exclude candidate components connected to any of the 11,502 original synthetic rows or the 703 reserved messages. The reserve is machine-read solely for overlap protection: no manual inspection, training or prediction.
3. Groups containing inspected audit messages can enter only training/validation, targeting 80/20. Newly sourced historical groups target 70/15/15 training/validation/test with source/label balancing. Exclude challenge groups connected to development/protected data; all remaining challenge rows stay held out. Targets are approximate because whole groups are indivisible. No replacement sampling after exclusions.
4. Freeze code/protocol, then the text-free data manifest before fitting. Train on real-mail training data only with the unchanged baseline algorithm/hyperparameters. Learn vocabulary/IDF/weights from training; choose the threshold by the existing validation F1 rule. No original synthetic rows enter v2 training. Freeze the saved model digest and threshold in a committed selection reference before test/challenge scoring.
5. Compare baseline v1 and v2 on identical prepared historical test inputs and, separately, challenge inputs. Report class counts, confusion matrices, accuracy, balanced accuracy, precision, recall, F1, false-positive rate, source/origin subgroups, group-bootstrap intervals and paired correctness. Reuse the fixed 1,000 whole-group resamples with seed 42. Do not tune after seeing results or combine challenge and historical scores into a headline number.
6. Repeat preparation/training/scoring under the fixed protocol for reproducibility, independently recount predictions, and verify unchanged original model/reserve hashes. These scored cohorts are stage-4b benchmarks; neither becomes an untouched final project test. Final reserve use requires a later precommitted policy covering subsequent model/attack/defense decisions.

Executable [protocol](../src/phishguard/refresh/protocol.json). Ownership within W05 remains five planning units each: Lior leads source review, ingestion, extraction and separate model persistence; Sharon Elimelech leads grouping, data checks, evaluation and reproduction. Both review interpretation. AI-assisted implementation is distinct from completed individual student authorship.

## Pre-fit quality corrections

The first training attempt stopped in the leakage guard before fitting any weights: eight development components shared literal subjects that the broader normalized-subject length rule missed. Preparation now unions both original and broader rules, with a regression test. The provisional manifest is superseded before scoring, without resetting history. A 16-message development excerpt review (two per source) also exposed MeAJOR entity placeholders. The explicit placeholder-type list is now removed from all candidate sources before grouping/model input, with unusable inputs excluded; protected files are compared through the same mapping in memory only. This is corpus-artifact cleanup, not adversarial defense. Original raw mail stays unchanged. Remaining publisher redaction/style differences still limit source independence. No new test/challenge predictions existed when these corrections were made.

## Reproduce locally

Prepare the original internal dataset, baseline v1 and stage-4a audit first, using the README. No paid service or account is required. Fetching the six new pinned files requires about 211.7 MB; subsequent work is offline. Existing output folders are refused.

```sh
uv run --frozen phishguard refresh diagnose
uv run --frozen phishguard refresh fetch
uv run --frozen phishguard refresh prepare
uv run --frozen phishguard refresh train
uv run --frozen phishguard refresh evaluate
uv run --frozen phishguard baseline predict --model models/baseline-v2 --file tests/fixtures/email.json
```

Preparation must reproduce the committed [data manifest](../data/manifests/real-mail-v2.json). Training reads only train/validation and writes `models/baseline-v2/`. Evaluation verifies the committed [selection reference](../data/manifests/baseline-v2-selection.json), loads only test/challenge, and compares both models on identical prepared inputs. It does not open the reserve, train or validation file. To reproduce without overwriting:

```sh
uv run --frozen phishguard refresh prepare --output data/processed/real-mail-v2-reproduction
uv run --frozen phishguard refresh train --dataset data/processed/real-mail-v2-reproduction --output models/baseline-v2-reproduction
uv run --frozen phishguard refresh evaluate --dataset data/processed/real-mail-v2-reproduction --model models/baseline-v2-reproduction --output artifacts/real-mail-v2-reproduction
uv run --frozen python scripts/verify_refresh.py
```

The verifier independently recounts saved predictions, including subgroups and paired correctness, compares both complete preparations and model/prediction bytes, and checks original model/data/reserve integrity without parsing reserve text. A different runtime or changed publisher file can produce an integrity/reproduction failure rather than silently accepting a new experiment. Default `baseline predict` still selects v1; explicitly select `models/baseline-v2` for this separate candidate.

## Prepared data and freezes

Final protocol/code correction: `941a4b7`; corrected data freeze: `818372e`; model/threshold freeze before held-out scoring: `8d519e9`. Initial training records the clean corrected-data commit; initial evaluation records the clean model-freeze commit. The failed preliminary training stopped before fitting; no test-driven model search followed.

MeAJOR ingestion examined 108,685 records, rejected 48,035 non-ham/unknown-source rows, 311 not publisher-English and two invalid inputs, then selected 1,800 by fixed hash; 16 failed the seeded language filter, leaving 1,784. Nazario yielded 1,404 eligible records from 2,279 (528 decoding failures, 251 language failures, 87 invalid/overlong, nine without inline text). These counts describe eligibility, not label accuracy. No excluded row was replaced to improve scores.

The 1,639 old audit records plus 3,188 additional real-mail-derived candidates and 2,000 challenge records yielded 6,431 retained rows after 355 exact cleaned-input duplicates and 41 protected-corpus relatives were excluded. No conflicting exact labels were found. The old audit received 35 extraction repairs: four plain-placeholder HTML fallbacks and 31 rooted-HTML cleanups. The new historical phishing archive had 12 rooted-HTML cleanups. Declared redaction tokens were removed from 1,730 MeAJOR candidates and 14 Nazario candidates before deduplication. Source anonymization/style differences remain even after marker removal.

| Partition | Rows | Legitimate | Phishing | Groups | Role |
| --- | --- | --- | --- | --- | --- |
| Training | 3,261 | 2,091 | 1,170 | 2,339 | Fit vocabulary, IDF and weights |
| Validation | 745 | 479 | 266 | 533 | Select threshold only |
| Historical test | 425 | 263 | 162 | 340 | New rows from sources also represented in v2 development |
| Separate challenge | 2,000 | 1,000 | 1,000 | 91 | Untrained source; mainly templated text |
| Original reserve | 703 | 479 | 224 | 432 | Unchanged; no scoring or manual review |

Training accuracy is 99.57%; validation accuracy is 97.85%. Validation selects threshold 0.31, with eight false positives and eight false negatives. The model retains 30,000 features and converged in eight solver iterations. This is our locally trained classical model, not a Hugging Face checkpoint. Core hyperparameters were unchanged; data composition, corpus cleanup and selected threshold changed together, so the comparison does not isolate their individual causal effects.

## Measured comparison

| Measure | Historical v1 | Historical v2 | Challenge v1 | Challenge v2 |
| --- | --- | --- | --- | --- |
| Rows | 425 | 425 | 2,000 | 2,000 |
| Threshold | 0.44 | 0.31 | 0.44 | 0.31 |
| Accuracy | 82.59% | 98.82% | 66.00% | 80.10% |
| Balanced accuracy | 84.39% | 98.93% | 66.00% | 80.10% |
| Phishing precision | 70.95% | 97.58% | 59.84% | 72.36% |
| Phishing recall | 91.98% | 99.38% | 97.30% | 97.40% |
| Phishing F1 | 80.11% | 98.47% | 74.11% | 83.03% |
| Legitimate false-positive rate | 23.19% | 1.52% | 65.30% | 37.20% |
| TP / FP / TN / FN | 149 / 61 / 202 / 13 | 161 / 4 / 259 / 1 | 973 / 653 / 347 / 27 | 974 / 372 / 628 / 26 |

Paired historical outcomes: v2 alone correctly classifies 72 rows, v1 alone three, both correctly 348 and both incorrectly two. Challenge outcomes: v2 alone 326, v1 alone 44, both correctly 1,276 and both incorrectly 354. V2's 95% whole-group bootstrap accuracy interval is 97.63-99.76% on historical data and 70.51-88.18% on the challenge. The latter's 91 transitive/template groups make uncertainty much larger than a naive 2,000-independent-message calculation. Bootstrap does not remove source bias.

On the 1,900 generated challenge rows, accuracy rises from 66.32% to 81.05%, and FPR falls from 66.41% to 36.19%. On the 100 original records of unverified provenance (77 legitimate, 23 phishing), accuracy is only 60% versus 62%, with 40 versus 38 false alarms; both detect all 23 publisher-phishing rows. This small subset is not verified contemporary email and does not support a broad deployment claim.

### Inspection-boundary deviation and sensitivity

A later trace of the 16 provisional-training review IDs found that regrouping moved one reviewed MeAJOR message into the frozen historical test. Fifteen stayed in training; none entered the challenge. That is a review-boundary deviation: the 425-row cohort is held out from fitting but cannot be called wholly untouched by development inspection. Both models classified the affected legitimate message correctly. A disclosed post-hoc exclusion leaves 424 rows: v1 accuracy 82.55%, v2 98.82%, with the same 61 versus four false positives and 13 versus one false negatives. This sensitivity check is not a new independent final test, and no model/threshold was retuned. The [review-boundary record](reports/refresh-review-boundary.json) preserves all IDs and counts. Future splitting must carry an explicit reviewed-ID registry through every regeneration.

## Interpretation and next-stage gate

Data refresh substantially improves the baseline on this historical benchmark and on the aggregate challenge. It does not resolve generalization: the challenge still produces 372 false alarms among 1,000 legitimate texts, and the original-record subset barely improves. The historical test shares source families with v2 development, source/class/era and publisher preprocessing remain confounded, and one reviewed row is disclosed above. The new 98.82% must not replace the old 98.43% as a universal accuracy claim. The old 92.86% audit and new 425-row benchmark are different cohorts and cannot form a direct before/after comparison.

Stage 4b is complete as a measured data/baseline study, not as a production-readiness milestone. Baseline v2 remains a separate research candidate. Stage 5 has not started. Before a requested fine-tuning stage, freeze its training/validation and reviewed-ID policy, continue reporting current scored cohorts as benchmarks, and precommit a final evaluation policy covering later model/attack/defense choices. Seek contemporary data containing both classes for stronger claims; do not repeatedly tune against the 703-message reserve. No threshold was raised after the challenge to hide false positives.

The complete repeated preparation, fit and evaluation produced byte-identical partitions, manifest, model and predictions, identical group intervals, and independently matching class/subgroup/paired counts. Baseline v1, the original synthetic files and the 703 reserved messages remain unchanged. Published evidence: [error profiles](reports/refresh-error-diagnosis.json), [training](reports/refresh-training.json), [evaluation](reports/refresh-evaluation.json), [independent verification](reports/refresh-verification.json).
