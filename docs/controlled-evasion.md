# Stage 6 - Controlled offline evasion

This stage measures the preserved baseline v2 and fine-tuned BERT-Tiny under bounded text changes. The protocol is declared before benchmark variant generation/scoring. It includes no model fitting, threshold changes, augmentation, defense, live mailbox integration or stage-7 work. Measured results will be added after execution.

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

`preview` writes local training-only review pairs to `artifacts/evasion-preflight-v1/`. `prepare` writes local changed texts and a text-free manifest to `artifacts/evasion-variants-v1/`. The committed `data/manifests/evasion-variants-v1.json` will freeze that manifest before scoring; `verify` and `evaluate` require an exact reference match and regenerate all candidates to validate constraints/lineage. Evaluation writes text-free per-original/per-candidate scores and an aggregate report to `artifacts/evasion-evaluation-v1/`. Existing output directories are refused. Raw texts and large artifacts remain ignored by Git.

For a separate technical repetition use new paths, keeping the same frozen bank reference:

```sh
uv run --frozen phishguard evasion prepare --output artifacts/evasion-variants-reproduction-v1
uv run --frozen --extra pretrained phishguard evasion evaluate --bank artifacts/evasion-variants-reproduction-v1 --output artifacts/evasion-reproduction-v1
```

Repeat generation and complete scoring, compare candidate/prediction bytes, independently recount results and verify preserved model/data digests. Reproduction is not another independent evaluation cohort. Any later change to the threat model or budget requires a separately declared study, not overwriting these results.

W07 retains five planning units each: Lior leads transformations, lineage and budgeted runner; Sharon Elimelech leads validity review, paired metrics, fixtures and reproduction. Both review limitations. Initial implementation and experimental review are AI-assisted; actual personal review remains to be recorded.
