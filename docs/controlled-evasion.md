# Stage 6 - Controlled offline evasion

This stage measures the preserved baseline v2 and fine-tuned BERT-Tiny under bounded text changes. The protocol is declared before benchmark variant generation/scoring. It includes no model fitting, threshold changes, augmentation, defense, live mailbox integration or stage-7 work. Execution, full repetition and independent verification are complete; measured results follow below.

## Threat model and limits

The simulated adversary can edit an existing email body and observe each local model's phishing score. Its goal is a below-threshold score for a publisher-phishing original that the same model initially detected. This is a score-access, finite candidate search, not a label-only or strongest-possible attack. Originals, labels and model identities remain fixed; no links are opened and no messages are sent.

The design separates transformations, constraints, a goal and a search policy, following the methodological decomposition in [Morris et al., TextAttack (EMNLP 2020)](https://aclanthology.org/2020.emnlp-demos.16/). It is our small deterministic implementation, not a reproduction of a published TextAttack/TextBugger attack or an installation of those frameworks. Automatic edit checks cannot establish semantic equivalence; descriptive sample review and explicit uncertainty are required.

The [executable protocol](../src/phishguard/evasion/protocol.json) fixes seed 42 and three transformation families:

- Duplicate one internal letter of a lowercase ASCII word of 6-20 letters.
- Swap two unequal adjacent internal letters, preserving the first/last letters.
- Apply one of ten explicit lexical replacements, such as please/kindly and verify/confirm. No generated paraphrases or external LLM calls.

Each candidate changes at most three words and at most 10% of the alphabetic body-word count, rounded down. A message with fewer than ten words has no allowed edit under this rule. Only words ending within the first 1,500 body characters are editable. The subject, URL/email/domain spans, numeric tokens, markup/entities, capitalized words and listed negation/control words are preserved. This policy does not authenticate links/senders or guarantee that all proper names and context-dependent meanings are recognized.

Four hash-ranked proposals per family use edit counts 1, 2, 3, 3, subject to the edit cap and available words. Proposals are interleaved by proposal number and family, independently of model outputs. Every candidate starts from the original; raw/cleaned no-ops, duplicate outputs and input-limit violations are discarded. There are at most 12 unique candidates and one clean prediction per original/model: at most 13 model queries. Score the same bank fully for both models, without early stopping, saliency probing or test-driven search changes. Tokenization is preprocessing, not an additional model query.

## Separation and fixed artifacts

Reuse the stage-5 423 historical benchmark rows and 2,000 challenge rows, including its full two-row reviewed-family exclusion. The frozen data and models are unchanged. Earlier outcomes and the stage-5 17-example post-score review are already known; these are retrospective research benchmarks, not untouched final tests. No new split regeneration is performed. Every variant records its parent, original group, source label, original split, cohort, seed, operation, edit offsets and content digests. The challenge retains its existing test split and separate challenge cohort.

Preflight inspection reads training rows only and scores no model. Bank preparation, verification and evaluation read only test/challenge files and frozen metadata. Evaluation rejects original/variant cleaned-text overlap with either model's development fingerprints. It does not open training, validation or reserve mail. The original 703-message reserve stays unscored and unreviewed until the separately frozen final protocol in stage 9. Stage-6 variants are not training examples for stage 7; that stage must separately generate training-only variants.

The baseline identity/threshold remain `a78643d919de806d170fec8cf303ac8be29e7866d0e30acb14650430009fe480` / 0.31. BERT-Tiny remains `2a49e59947fd081463a300c9b99d34e9ea609d6a671593c8f204cea02435d3d5` / 0.69, with its exact stage-5 selection reference. Evaluation verifies model files and in-memory neural tensors before/after inference. The original 256-token BERT limit remains in force; record candidates whose effective tokenized input is unchanged. Baseline inference retains full accepted text.

## Measurements and validity review

Report three separate views on each cohort:

1. Clean metrics, checked against stage 5 on identical IDs.
2. Fixed corruption: the first available candidate for every original, or the clean original if none. Both models receive exactly the same input. Report full class metrics, false alarms and paired correctness; this is a nonadaptive corruption comparison.
3. Directed evasion: choose the lowest phishing score among the original and its bank for phishing originals only; keep legitimate originals clean. Report conditional candidate ASR and full-cohort metrics, explaining that unchanged legitimate false-positive rate is by construction. Exact ties retain the original or earlier candidate.

Candidate ASR counts clean-detected phishing originals with any constraint-pass below-threshold candidate, divided by all clean-detected phishing originals, including those without an editable candidate. Report coverage, per-family/per-source counts, actual clean/candidate queries, and a separate comparison restricted to phishing originals detected by both models. Zero denominators are undefined, not zero performance. Whole-group bootstrap intervals use 1,000 resamples and seed 42; they do not correct source bias, uncertain labels or limited search strength.

Before scoring, inspect two deterministic training originals per class/family (up to 12 pairs), selecting the largest generated edit count for each. After scoring, inspect up to two deterministic successful candidates per cohort/model/family. Record accepted/ambiguous/invalid label preservation and reviewed IDs without changing the frozen protocol/models. Publish no raw excerpts. Candidate ASR remains explicitly conditional on automated constraints; the post-score report separately counts reviewed supported evasions as a lower bound. Unreviewed cases are not claimed semantically certified, and AI-assisted review is not invented student review.

Source/era confounding, old real-mail sources, synthetic challenge templates and unverified original-challenge provenance remain. A low measured ASR would mean this limited search found few failures, not that the model cannot be evaded. A high ASR would identify a problem under this protocol, not establish a real-world compromise.

## Local workflow and reproducibility

Use the existing environment with the `pretrained` extra and the completed stage-5 data/models. No new download or paid service is required.

```sh
uv run --frozen phishguard evasion preview
uv run --frozen phishguard evasion prepare
uv run --frozen phishguard evasion verify
uv run --frozen --extra pretrained phishguard evasion evaluate
```

`preview` writes local training-only review pairs to `artifacts/evasion-preflight-v1/`. `prepare` writes local changed texts and a text-free manifest to `artifacts/evasion-variants-v1/`. The committed `data/manifests/evasion-variants-v1.json` freezes that manifest before scoring; `verify` and `evaluate` require an exact reference match and regenerate all candidates to validate constraints/lineage. Evaluation writes text-free per-original/per-candidate scores and an aggregate report to `artifacts/evasion-evaluation-v1/`. Existing output directories are refused. Raw texts and large artifacts remain ignored by Git.

For a separate technical repetition use new paths, keeping the same frozen bank reference:

```sh
uv run --frozen phishguard evasion prepare --output artifacts/evasion-variants-reproduction-v1
uv run --frozen --extra pretrained phishguard evasion evaluate --bank artifacts/evasion-variants-reproduction-v1 --output artifacts/evasion-reproduction-v1
```

Repeat generation and complete scoring, compare candidate/prediction bytes, independently recount results and verify preserved model/data digests. Reproduction is not another independent evaluation cohort. Any later change to the threat model or budget requires a separately declared study, not overwriting these results.

W07 retains five planning units each: Lior leads transformations, lineage and budgeted runner; Sharon Elimelech leads validity review, paired metrics, fixtures and reproduction. Both review limitations. Initial implementation and experimental review are AI-assisted; actual personal review remains to be recorded.

## Executed verification and review commands

```sh
uv run --frozen python scripts/verify_evasion.py
uv run --frozen python scripts/review_evasion.py select
uv run --frozen python scripts/review_evasion.py verify
```

The independent verifier expects both complete runs, the stage-5 saved predictions and the unchanged historical files listed in the preservation manifest. It confirms this recorded local experiment; a fresh installation will not reproduce historical report timestamps byte-for-byte. The review selector writes text-free candidate IDs to a new local folder and refuses an existing folder. Review verification checks the committed contextual decisions against those deterministic IDs and computes distinct-original lower bounds. It does not automatically certify semantic validity or expose email content.

## Measured results and limitations

The stage-6 code/protocol and preservation fingerprints were committed at `593c1af` before experimental scoring. Twelve deterministic training-only examples were inspected without querying either model; all supported label preservation in the inspected contexts. The bank and review were frozen at `427685b` before scoring. Both full runs record that clean revision. Model weights/thresholds and the 703-message reserve were not changed.

The frozen bank contains 19,969 variants: 3,677 for 423 historical originals and 16,292 for 2,000 challenge originals. Eleven historical and five challenge originals have no candidate under the constraints; they remain in the metrics. Each model made 4,100 historical and 18,292 challenge predictions, including clean originals: 22,392 queries per model, 44,784 per complete comparison. The actual per-original maximum is 13. No extra model queries were used for per-family analysis or review.

| Measure | Historical baseline v2 | Historical BERT-Tiny | Challenge baseline v2 | Challenge BERT-Tiny |
| --- | --- | --- | --- | --- |
| Clean accuracy | 98.82% | 98.58% | 80.10% | 80.80% |
| Fixed-corruption accuracy | 98.82% | 98.58% | 80.20% | 80.25% |
| Phishing-only attacked accuracy | 98.82% | 98.35% | 79.70% | 76.05% |
| Clean phishing recall | 99.38% | 97.53% | 97.40% | 91.40% |
| Attacked phishing recall | 99.38% | 96.91% | 96.60% | 81.90% |
| Clean-detected phishing originals | 161 | 158 | 974 | 914 |
| Additional misses within budget | 0 | 1 | 8 | 95 |
| Constraint-pass candidate ASR | 0.00% | 0.63% | 0.82% | 10.39% |

Candidate ASR is conditional on automatic edit constraints, not exhaustive semantic certification. Its denominator differs from all phishing messages and from all emails. Existing clean misses are not counted as new evasions. Three initially detected historical phishing messages and five challenge messages per model have no candidate; omitting them would inflate the denominator-conditioned result. Their coverage is disclosed rather than hidden.

The same 909 challenge phishing originals are initially detected by both models. Within this common set, baseline evasion is 4/909 (0.44%) versus 91/909 (10.01%) for BERT-Tiny. Historical common eligibility is 157, with zero versus one evasion. Thus the observed challenge sensitivity difference persists when eligibility is aligned. It does not establish an architecture-wide ranking or general security superiority: the baseline still falsely flags 37.20% of legitimate clean challenge texts, versus 29.80% for BERT.

On challenge data, letter duplication finds 7 baseline and 69 BERT evasions; swaps find 5 and 83; lexical substitution finds zero and one. These sets overlap and must not be summed. Family coverage and actual queries differ; the restricted substitution dictionary has much lower coverage. The fixed-corruption view changes both classes without searching scores: challenge false-positive rates are 36.60% and 29.60%, and paired outcomes improve 21/worsen 19 baseline decisions and improve 23/worsen 34 BERT decisions. Directed-evasion results instead keep legitimate originals clean, so their unchanged false-positive rate is not evidence of robustness.

Whole-group 95% candidate-ASR intervals are 0.00-2.42% for the challenge baseline and 4.51-17.67% for BERT. Historical intervals are 0.00-0.00% and 0.00-2.27%. The baseline's zero-success bootstrap is degenerate: it is not a bound proving zero future failure probability. These intervals condition on this corpus, grouping, constraints and finite search; they do not address unseen attack families, semantic validity or source bias. No budget or threshold was increased after observing results.

A predetermined post-score sample contains ten successful variants from eight originals. Contextual AI-assisted review supported preservation of the original request/intent in all ten; no labels or outcomes were edited. The reviewed evidence covers two distinct challenge originals for baseline, five for BERT, and the single historical BERT evasion. Corresponding review-supported lower bounds are 2/974 (0.21%), 5/914 (0.55%) and 1/158 (0.63%); the larger candidate-ASR figures are not fully manually validated. Student review remains open. Observations include unchanged gift-card, invoice, document-login, transaction-check and tax-refund requests with small readable edits; raw excerpts remain local.

BERT's effective tokenized input is unchanged for 196 historical candidates, versus zero challenge candidates, under its preserved 256-token cap. Long-message truncation and the first-1,500-character edit region limit the experiment. Scoring all clean originals and candidates took 1.54 seconds on historical mail and 1.58 on the challenge for baseline; BERT took 17.19 and 17.41 seconds, including tokenization but excluding bank verification, model loading and disk I/O. These are total batch times, not single-email latency. The existing CPU runtime and four neural threads were used.

Repeated bank generation and full scoring produced byte-identical variants/manifests and predictions. An independent verifier recounted confusion, paired, ASR, coverage, source and query counts, replayed every edit and checked lineage. Clean scores match stage 5 exactly. All 67 preserved model/processed-data files remain byte-identical; reserve bytes were hashed without parsing. Software checks and research metrics are separate evidence.

Stage 6 establishes measured sensitivity under a limited offline threat model, not production readiness or a guarantee against evasion. Low baseline ASR does not remove its false-alarm problem. Stage 7 has not started: no defense or augmentation training was performed. Future defense development must use training-only originals/variants, preserve these fixed baselines and evaluation artifacts, and keep the final reserve independent of all choices.

Evidence: [protocol and commands](controlled-evasion.md), [training-only preflight review](reports/evasion-preflight-review.json), [evaluation](reports/evasion-evaluation.json), [independent verification](reports/evasion-verification.json), [post-score label review](reports/evasion-label-review.json), [reviewed lower bounds](reports/evasion-reviewed-evidence.json).
