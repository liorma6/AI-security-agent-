# Stage 5 - Fine-tuned small transformer

This stage trains a small transformer for phishing classification and compares it with the preserved baseline v2. It does not start stage 6: no perturbations, evasion search, adversarial augmentation or defense training. The following protocol is declared before research fitting and benchmark scoring. The measured results below are now complete; the original protocol and model-selection freezes are preserved in Git.

## Source and scope

The starting encoder is [Google BERT-Tiny](https://huggingface.co/google/bert_uncased_L-2_H-128_A-2/tree/30b0a37ccaaa32f332884b96992754e246e48c5f), revision `30b0a37ccaaa32f332884b96992754e246e48c5f`, with publisher Apache-2.0 declaration. Attribution: Google BERT Miniatures; Turc et al., *Well-Read Students Learn Better* (2019). This English uncased model has two encoder layers, hidden width 128 and two attention heads. A two-class head gives 4,386,178 trainable parameters. Its small size allows reproducible CPU training in the existing local environment; the assignment gives DistilBERT as an example, not a required architecture. BERT-Mini was reviewed but its main revision lacked a safetensors artifact; no pickle checkpoint conversion or GPU-environment change was needed for the selected model.

The [source manifest](../src/phishguard/finetune/source.json) pins the card, configuration, vocabulary and safetensors weights (about 18 MB total). Downloads use HTTPS verification and bounded streaming, validate sizes/digests and never replace existing verified files. Loading instantiates the known local BERT implementation, verifies exact encoder tensor names/shapes/dtypes, discards the original pretraining heads and initializes a new legitimate/phishing head. Every encoder and classifier parameter is fine-tuned. It is a general pretrained encoder, not an existing phishing detector or the stage-4 DistilBERT classifier. No remote model code, pickle weights, email transmission or message-link access is used.

Upstream pretraining membership is unavailable, so complete upstream non-overlap cannot be proven. No distillation teacher is used. Small capacity, source/era bias, publisher processing and truncation limit interpretation. The comparison is pretrained-and-fine-tuned BERT versus our classical baseline; it does not isolate architecture from pretraining and input representation.

## Frozen data and review registry

Reuse the exact [real-mail-v2 manifest](../data/manifests/real-mail-v2.json), digest `6f9a757dc2444607312ff9719a9f4f2a2ece5a2808231d28e8dfdb42a17159bb`: 3,261 training and 745 validation messages. No split regeneration, new labeling or synthetic training rows. The original baseline v1, baseline v2, stage-4 pretrained model and all old dataset/report files remain preserved.

The [study policy](../src/phishguard/finetune/study.json) records the 16 earlier provisional-training review IDs and binds their trace. It excludes the entire historical benchmark group containing reviewed `meajor-trec7-081259`, including its relative `meajor-trec7-082202`. That leaves 423 historical benchmark rows in 339 groups. Both compared models receive exactly those same rows. The earlier 425-row report and 424-row sensitivity are historical evidence and are not overwritten. The separate challenge remains 2,000 rows in 91 groups; 1,900 are templated synthetic text and 100 original records have unverified provenance.

Both benchmark cohorts have already been scored in stage 4b. They are retrospective comparisons, not fresh final tests. They never enter gradient updates, epoch selection or threshold selection. The original 703-message reserve is unopened by training/evaluation and receives no scores. Before final stage-9 use, freeze all detector/threshold/attack/defense decisions and the final evaluation protocol; report the reserve without using it to select or retune a model. Its source/era bias will remain. Technical reproduction is not an additional independent test.

## Fixed training and selection

- One configuration and random seed 42. CPU float32, four numerical threads, deterministic PyTorch algorithms and a separate seeded shuffle generator. No hyperparameter sweep or test-driven retries.
- Five epochs; batch size 16; AdamW learning rate 0.00005, betas 0.9/0.999, epsilon 1e-8; weight decay 0.01 except bias/LayerNorm weights. Ten-percent linear warmup followed by linear decay, gradient norm clipped at 1.0. All encoder/head weights update on training rows only.
- Reuse frozen subject/body and baseline marker removal. Fixed uncased WordPiece tokenizer; right truncation to 256 tokens including special tokens and dynamic padding. Count original lengths and every truncated row, rather than silently discarding long emails. The baseline retains its full accepted text; report that difference.
- Select the epoch with minimum mean validation cross-entropy, with earliest-epoch exact ties. At that epoch select the threshold with the existing validation-only phishing-F1 grid/ties. Report the fixed 0.50 threshold as a predeclared diagnostic. No train-plus-validation refit.
- Save only safetensors, configuration, vocabulary and text-free manifests/fingerprints. Verify reload scores and prove selected encoder weights differ from the source encoder. Commit the model identity and validation-selected threshold before benchmark scoring.

The [executable protocol](../src/phishguard/finetune/protocol.json) freezes these choices. A repeated identical-seed run verifies execution reproducibility, not variability across random seeds or operating systems. The base language model already has pretrained vocabulary/weights; task-specific updates use only the declared training split.

## Evaluation and verification

Compare with the exact baseline-v2 digest `a78643d919de806d170fec8cf303ac8be29e7866d0e30acb14650430009fe480` and threshold 0.31. Report confusion counts, accuracy, precision/recall/F1, legitimate false-positive rate, balanced accuracy, source/origin subgroups, paired correctness, whole-group 95% bootstrap intervals (1,000 resamples, seed 42), token truncation and resource/timing conditions. Do not merge historical and challenge results into one headline score. Neither high accuracy nor high phishing recall alone establishes useful generalization.

After weights/thresholds are frozen and all benchmarks scored, inspect a deterministic bounded sample of transformer false positives, false negatives and correct controls. Record observations without changing the selected model or threshold. Repeat the fixed training and scoring once and independently recount saved predictions. Verify all preserved baseline/data/reserve digests. Software checks use invented tiny neural fixtures and test actual encoder updates, leakage/read boundaries, family exclusion, validation selection, deterministic training, safe artifacts, label mapping, truncation, source verification and private CLI errors.

W06 maintains equal assigned responsibility: Lior leads the training runner, local environment and checkpoint artifacts; Sharon Elimelech leads tokenization/data boundaries, comparison, reproduction and error analysis. Both review conclusions and explain limitations. Implementation and initial experimental review are AI-assisted; completed individual student authorship is not asserted.

## Run locally

After preparing real-mail-v2 and baseline v2 using the [refresh guide](baseline-refresh.md):

```sh
uv sync --locked --extra pretrained
uv run --frozen --extra pretrained phishguard finetune fetch
uv run --frozen --extra pretrained phishguard finetune verify
uv run --frozen --extra pretrained phishguard finetune train
uv run --frozen --extra pretrained phishguard finetune evaluate
uv run --frozen --extra pretrained phishguard finetune predict --file tests/fixtures/email.json
```

The verified download is about 18 MB. Training fine-tunes all weights of Google's BERT-Tiny encoder and a new phishing head locally on CPU; it needs no account or paid API. The existing `pretrained` extra supplies the shared neural runtime. Training writes `models/finetuned-v1/`; comparison writes `artifacts/finetuned-evaluation-v1/`. Existing output directories are refused. The [fine-tuning guide](finetuned.md) covers separate reproduction, the frozen selection reference, hardware limits and model provenance. Exact comparison requires the committed selected model identity; training on a different platform can differ numerically and must not silently replace the reference.

Training uses 3,261 rows only; 745 validation rows select epoch 5 and threshold 0.69. It never reads benchmark/reserve text. Comparison uses the unchanged baseline v2 at 0.31 on identical inputs, excluding the entire earlier reviewed family. Historical accuracy is **98.82% baseline / 98.58% transformer** across 423 rows. On the mainly synthetic 2,000-row challenge, accuracy is **80.10% / 80.80%**, false-positive rate **37.20% / 29.80%**, and phishing recall **97.40% / 91.40%**. Fewer false alarms come with more missed phishing; this is not a general model-quality victory or production-ready filter. The previously scored cohorts are retrospective benchmarks, while 703 reserve messages remain unscored.

Inference right-truncates to 256 tokens with explicit length metadata. It does not save or transmit pasted text. All raw data, model weights and per-example predictions stay local; text-free reports, source/protocol manifests and the selected identity are versioned. Stage 6 has not started.

## Reproduce without replacing artifacts

```sh
uv run --frozen --extra pretrained phishguard finetune train --output models/finetuned-reproduction-v1
uv run --frozen --extra pretrained phishguard finetune evaluate --model models/finetuned-reproduction-v1 --output artifacts/finetuned-reproduction-v1
uv run --frozen python scripts/verify_finetuning.py
uv run --frozen python scripts/review_finetuned_errors.py
```

The evaluator requires the committed [selection reference](../data/manifests/finetuned-v1-selection.json); it refuses a different checkpoint or threshold. Full research runs were executed on Windows/Python 3.13.16 with the pinned CPU runtime. Identical seeds are not a guarantee of cross-platform byte identity. For a separately declared new experiment, commit a new selection reference before scoring and supply it with `--selection-reference`; retain this study's artifacts and reports. Never adjust a reference just to accept an accidental mismatch or tune after seeing benchmark scores.

The verifier expects the earlier stage-4b comparison artifacts, preserved baseline/source/data files, and both stage-5 runs at the paths above. It hashes reserve bytes for integrity without parsing its content. The error-review command selects text-free IDs only; the already completed local excerpt review and its observations are documented in the book/report. No private email text is published.

## Measured results and model limitations

Protocol/code were committed at `91314b9` before fitting; selected artifact/threshold at `de53248` before benchmark scoring. Both initial reports record clean commits. The one declared seed/configuration ran all five epochs. Mean validation cross-entropy fell from 0.22198 to 0.07340; the predeclared rule selected epoch 5 and validation threshold 0.69. Training accuracy is 99.63%; validation accuracy 98.26%, with four false alarms and nine missed phishing records. The threshold is an experimental F1 choice, not a calibrated probability or company blocking policy.

| Measure | Historical baseline v2 | Historical BERT-Tiny | Challenge baseline v2 | Challenge BERT-Tiny |
| --- | --- | --- | --- | --- |
| Rows | 423 | 423 | 2,000 | 2,000 |
| Threshold | 0.31 | 0.69 | 0.31 | 0.69 |
| Accuracy | 98.82% | 98.58% | 80.10% | 80.80% |
| Balanced accuracy | 98.93% | 98.38% | 80.10% | 80.80% |
| Phishing precision | 97.58% | 98.75% | 72.36% | 75.41% |
| Phishing recall | 99.38% | 97.53% | 97.40% | 91.40% |
| Phishing F1 | 98.47% | 98.14% | 83.03% | 82.64% |
| Legitimate false-positive rate | 1.53% | 0.77% | 37.20% | 29.80% |
| TP / FP / TN / FN | 161 / 4 / 257 / 1 | 158 / 2 / 259 / 4 | 974 / 372 / 628 / 26 | 914 / 298 / 702 / 86 |

The historical comparison excludes the entire previously reviewed family before stage-5 scoring: two legitimate rows, leaving 261 legitimate and 162 phishing messages in 339 groups. Earlier 425/424-row reports remain intact. The transformer makes one additional total error. On the challenge it removes 74 false alarms but adds 60 missed phishing messages, a net 14 additional correct predictions out of 2,000. Paired outcomes favor BERT alone on 120 challenge rows and baseline alone on 106. This is a trade-off, not an overall superior detector; phishing F1 declines slightly. The baseline remains available without automatic replacement.

The 1,900 generated challenge rows have 81.05% baseline versus 81.74% transformer accuracy. On the 100 original records of unverified provenance, accuracy is 62% versus 63%; transformer false alarms remain 37/77 legitimate records, and both models detect all 23 phishing-labeled records. At the predeclared diagnostic threshold 0.50, transformer challenge accuracy is 80.10%, recall 92.60% and false-positive rate 32.40%. That diagnostic did not change the selected 0.69 threshold.

Whole-group 95% accuracy intervals are 97.55-99.75% for the historical baseline and 97.19-99.55% for the transformer; challenge intervals are 70.51-88.18% and 71.61-88.61%. These 1,000 seeded group resamples describe conditional uncertainty. They do not establish a significant improvement, correct source bias or make 91 challenge groups independent contemporary inboxes. Existing source/era confounding, synthetic templates and publisher-label uncertainty remain.

Token truncation affects 1,545/3,261 training, 379/745 validation and 202/423 historical benchmark rows, versus zero challenge rows. Three of four historical transformer misses are truncated, but this association is not evidence that truncation caused them. The short challenge's errors cannot be explained by the length cap. A deterministic post-score review inspected 17 excerpts: five historical errors, six challenge errors and six correct controls. Historical false alarms involve ordinary account/setup messages; misses include promotional/context-dependent content and a markup-heavy account lure. Challenge false alarms include routine document/travel messages; misses include gift-card, invoice and secure-message lures. Correct controls contain overlapping topics, so no simple keyword rule or causal explanation is established. Labels, weights and threshold stayed unchanged; excerpts remain local and review is AI-assisted.

Initial fit/validation work took 263.15 seconds on the local Ryzen 5 3600X CPU with four neural threads, Python 3.13.16, PyTorch 2.15.0+cpu and Transformers 4.57.6. Historical/challenge batched scoring took 1.285/1.084 seconds for BERT and 0.150/0.080 seconds for baseline v2, excluding imports, loading and disk I/O. These are amortized batch timings, not single-request latency or a memory benchmark. No cloud service, GPU runtime change or paid inference was used.

A complete repeated same-seed training/scoring run produced byte-identical selected weights, manifests, validation history and predictions. Independent recounts matched class, subgroup, paired and default-threshold results; prior model/data/source files and reserve bytes remained unchanged. This verifies reproducibility in the same environment, not robustness across seeds/platforms. Stage 5 supplies the required fine-tuned detector and honest comparison; it does not resolve generalization or measure adversarial robustness. Stage 6 has not started.

Evidence: [fine-tuning guide and model limitations](finetuned.md), [training report](reports/finetuned-training.json), [paired evaluation](reports/finetuned-evaluation.json), [independent verification](reports/finetuned-verification.json), [text-free error review](reports/finetuned-error-review.json).
