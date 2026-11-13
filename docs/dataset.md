# Research dataset: E-PhishLLM v1

Stage 2 prepares an English-flagged subset of **synthetic** emails. It provides reproducible research input, not evidence of real-mail detection quality. The [stage-3 baseline](baseline.md) is now trained and evaluated on this frozen dataset; the data-quality checks below remain distinct from model measurements.

## Source, license and provenance

The source is the authors' [pajola/e-phishGen dataset](https://huggingface.co/datasets/pajola/e-phishGen), accompanying [E-PhishGen: Unlocking Novel Research in Phishing Email Detection](https://doi.org/10.1145/3733799.3762967). The paper describes profile-driven generation. The released email file contains subject, body, language flag and binary type; it does not supply profile/campaign IDs.

The [pinned publisher card](https://huggingface.co/datasets/pajola/e-phishGen/blob/dda1f1e0b155206a4f84915bf117012f960bdafe/README.md) declares MIT and defines `type=0` as legitimate and `type=1` as phishing. This is the publisher's license declaration; the release has no separate LICENSE file. We preserve the card alongside the downloaded data and retain attribution in the [packaged source manifest](../src/phishguard/datasets/source.json). We do not claim an independent legal or privacy audit.

- Revision: `dda1f1e0b155206a4f84915bf117012f960bdafe`.
- File: `ephishLLM.json`, 12,275,474 bytes.
- File SHA-256: `56420b143e30343f6db723c3716e10abec9f72a67ba99ae2cc7c3a87b547f51f`.
- Card SHA-256: `76242889ff357e4fd89fa678e926ad4a68d31b72394c03019dd936ba3d2c8030`.
- Selection date: November 13, 2026. The Kaggle-derived `zefang-liu/phishing-email-dataset` was considered but not selected: sampled positives included generic advertising/spam, which weakens the intended phishing-versus-legitimate interpretation.

## Reproduce locally

From the repository root after `uv sync --locked`:

```sh
uv run --frozen phishguard data fetch
uv run --frozen phishguard data prepare
uv run --frozen phishguard data verify --reference data/manifests/ephishllm-v1.json
```

Only `fetch` accesses the network. It downloads the two fixed publisher files over HTTPS, verifies pinned sizes/digests, and reuses an already verified cache. No account, API key, mailbox or paid service is required. Email links are never opened. A corrupt cache raises `source_integrity_mismatch` without replacing the file.

Raw files are stored under `data/raw/ephishllm/<revision>/`. Prepared files are `data/processed/ephishllm-v1/{train,validation,test}.jsonl` plus `manifest.json`. These are ordinary local disk files and are ignored by Git. The repository retains the text-free [frozen manifest](../data/manifests/ephishllm-v1.json), which lists source row IDs, groups, split membership, exclusions, counts and file digests. It contains no email text.

Preparation refuses an existing destination, so a rerun cannot silently replace frozen data. To reproduce separately:

```sh
uv run --frozen phishguard data prepare --output data/processed/reproduction-check
uv run --frozen phishguard data verify --directory data/processed/reproduction-check --reference data/manifests/ephishllm-v1.json
```

`--source PATH`, `--cache PATH` and `--seed INTEGER` are supported. A different seed creates a different experiment and will not match the committed reference. Without `--reference`, verification checks local consistency only; using the committed reference additionally checks the exact approved manifest. Errors use fixed codes, never message contents: exit 1 for integrity/validation errors, exit 2 for file-access or command-usage errors.

## Preparation rules

1. Verify source bytes before parsing. Accept the exact four-column schema and integer labels 0/1. Select the publisher's `Language=en` flag. This is not independent language detection; some subjects may contain another language.
2. Validate subject/body with the existing email contract. Preserve the original accepted text; do not silently truncate, relabel or rewrite it. Invalid rows receive a metadata-only exclusion reason.
3. Detect identical combined text after NFKC, case-folding and whitespace collapse. Keep the lowest stable ID for same-label duplicates. Quarantine every member of a conflicting-label duplicate set.
4. Link records with identical normalized subjects of at least 15 characters and three words. Also link equal body templates of at least ten words after masking bracketed placeholders, URLs, email addresses and digits.
5. Link near-body pairs whose word-trigram sets have Jaccard similarity at least 0.90. A deterministic frequency-ordered prefix index finds candidates; the final comparison is exact. Transitive closure and declared parent links define groups. This is a conservative similarity heuristic, not verified campaign identification.
6. Assign complete groups to target ratios 70%/15%/15%, seed 42. Larger groups are assigned first, with seeded hash tie ordering and class-wise balancing. Ratios are approximate because groups remain intact. Both labels must appear in every split.
7. Write validated records, digests, counts and membership. Verify integrity, unique IDs/text, source metadata, group separation, related-record grouping, parent existence and acyclic lineage. Final test data is reserved for evaluation after decisions are frozen.

Grouping normalization never replaces the email text. Its corpus-wide frequency ordering is only a deduplication search optimization; no TF-IDF vocabulary, model or learned feature transformation is fitted. Later derived variants must carry `parent_id` and inherit their original's group/split in separate experiment artifacts; frozen originals must remain unchanged.

## Executed data-quality results

The pinned source has 16,616 rows. Filtering excluded 5,114 non-English-flagged rows and retained 11,502. No selected row violated the email contract. No normalized exact duplicates or conflicting exact labels were found. There are 10,564 groups, including 325 multi-message groups; the largest has 40 messages.

| Split | Legitimate | Phishing | Total | Groups |
| --- | --- | --- | --- | --- |
| Train | 3,854 | 4,198 | 8,052 | 7,395 |
| Validation | 826 | 899 | 1,725 | 1,585 |
| Test | 826 | 899 | 1,725 | 1,584 |
| Total | 5,506 | 5,996 | 11,502 | 10,564 |

Two independent local preparations, one using a fresh download through the implemented downloader, produced identical manifest and partition bytes. Frozen manifest SHA-256: `e2d33ec1688236caced98bcbb8440c16b49282e9614f7e42110274d610beae2d`. These are data-integrity results, not model metrics.

## Label review and limits

The [sample audit](dataset-label-audit.md) covers 24 deterministically selected rows, 12 per class, reviewed with AI assistance. Twelve legitimate examples and five phishing examples were compatible with their labels from their visible wording; seven phishing examples required missing sender/link/attachment context. Labels were retained, not silently corrected. Compatibility is not authentication of the sender, proof of intent or a full-corpus accuracy estimate. Student review remains open.

The corpus contains a substantial shortcut: `<<` placeholders occur in **3,609 phishing messages and zero legitimate messages**. Some placeholder names explicitly describe malicious content. Raw-text accuracy could reward detection of a generation artifact. **Implemented in stage 3:** a precommitted label-independent policy removes complete `<<...>>` spans from model input, preserves originals and records training/validation shortcut diagnostics. Any raw-text comparison must be clearly identified as artifact-sensitive. Do not use final-test outcomes to choose preprocessing.

Additional limits are synthetic writing style, possible label ambiguity, missing profile IDs, mixed-language subjects, and semantic relatives that the similarity heuristic misses. Group separation is verified for the declared rules only. There is no independent real-inbox evaluation or assurance of no overlap with a future pretrained model's training set. Later reports must state these limits; deployment-quality claims would require separately licensed real-message evaluation.

## Verification and ownership

[Dataset tests](../tests/test_datasets.py) use invented offline examples. They cover invalid source rows, unchanged text, deduplication/conflicts, transitive grouping, a brute-force comparison of the near-duplicate search, seeded splits, lineage leakage, tampered artifacts, output preservation, downloader failures/cache checks and private CLI errors. CI does not download the research corpus.

W03 assigns provenance/ingestion to Lior and label review/deduplication/split validation to Sharon Elimelech, with equal planning weight and mutual review. Implementation and the initial sample audit were AI-assisted in this project session. This allocation does not claim completed individual student review.
