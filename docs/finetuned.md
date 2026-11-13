# Stage 5 - Fine-tuned small transformer

This stage trains a small transformer for phishing classification and compares it with the preserved baseline v2. It does not start stage 6: no perturbations, evasion search, adversarial augmentation or defense training. The following protocol is declared before research fitting and benchmark scoring. Results follow after measurement.

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
