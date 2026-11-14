# Same-cohort pretrained comparison

The course assignment requires using a pretrained Hugging Face text classifier and comparing results. It does not literally specify identical message IDs; using identical evaluation inputs is our methodological requirement for a meaningful paired comparison. Stage 4 already compared the pretrained classifier and baseline v1 on the same 1,725 synthetic test messages. This extension compares the four current candidates on the later research cohorts before stage 8.

## Frozen method

Preserve the external DistilBERT revision, cased tokenizer, preprocessing, 512-token right truncation, float32 CPU inference, one numeric thread and batches of eight from [stage 4](pretrained.md). Never update its weights. On the 745-row real-mail-v2 validation partition only, select a separate threshold using the existing F1 grid and tie policy. Commit that selection before scoring benchmark text. Keep the earlier synthetic-validation selection unchanged.

Re-score baseline v2, the original fine-tuned BERT, the defended BERT and pretrained DistilBERT on exactly 423 historical and 2,000 challenge examples. Use the existing whole-family exclusion, grouping and labels. Preserve the three trained models and their thresholds. Report clean confusion counts, recall, false-positive rate, F1, per-source results, group-bootstrap intervals, paired correctness and truncation. Include pretrained 0.50 and old 0.05 thresholds as declared diagnostics, without selecting based on test results.

These are already-inspected retrospective cohorts. Upstream pretrained training membership is unknown, so overlap cannot be excluded. Different training histories and token limits prevent an architecture-controlled interpretation. This extension does not evaluate pretrained adversarial robustness. The 703-row final reserve remains unscored and unreviewed.

```sh
uv run --frozen --extra pretrained phishguard compare select
# Review and version the new selection.json as data/manifests/pretrained-real-selection-v1.json.
uv run --frozen --extra pretrained phishguard compare evaluate
```

Selection writes `artifacts/pretrained-real-selection-v1/`; evaluation writes `artifacts/comparison-v1/`. Existing outputs are refused. Reproduction uses `--output` and, for evaluation, `--selection` / `--selection-reference`. No model or dataset download is required after the earlier stages. Raw email and per-example predictions stay outside Git. Measured results follow.

## Measured results

**Historical cohort: 423 messages**

| Model | Threshold | Accuracy | Phishing recall | False-positive rate | Missed phishing | False alarms |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline v2 | 0.31 | 98.82% | 99.38% | 1.53% | 1 | 4 |
| Original BERT-Tiny | 0.69 | 98.58% | 97.53% | 0.77% | 4 | 2 |
| Augmentation defense | 0.07 | 98.82% | 98.15% | 0.77% | 3 | 2 |
| Pretrained DistilBERT | 0.45 | 90.54% | 95.68% | 12.64% | 7 | 33 |


**Challenge cohort: 2,000 messages**

| Model | Threshold | Accuracy | Phishing recall | False-positive rate | Missed phishing | False alarms |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline v2 | 0.31 | 80.10% | 97.40% | 37.20% | 26 | 372 |
| Original BERT-Tiny | 0.69 | 80.80% | 91.40% | 29.80% | 86 | 298 |
| Augmentation defense | 0.07 | 80.80% | 92.10% | 30.50% | 79 | 305 |
| Pretrained DistilBERT | 0.45 | 87.25% | 86.40% | 11.90% | 136 | 119 |

The pretrained model has the highest challenge accuracy and F1 and the fewest false alarms, but also misses the most phishing messages at the frozen thresholds. On the historical cohort it has lower accuracy and more errors of both kinds than the three trained candidates. On the 100-message challenge subset labeled original by its publisher, pretrained accuracy is only 68%; its original provenance remains unverified. The appropriate choice therefore depends on the evaluation domain and the cost of missed phishing versus false alarms; no deployment recommendation follows from these cohorts alone.

The pretrained threshold is 0.45, selected from 745 validation rows only; its weights are unchanged. All four candidates see identical benchmark IDs and labels, with the existing two-row family exclusion. The three preserved models reproduce their previous clean metrics exactly. The pretrained 512-token budget truncates 81/423 historical and 0/2,000 challenge messages. Default 0.50 and earlier 0.05 thresholds, per-source metrics, group-bootstrap intervals and paired counts are disclosed in the machine-readable report, not used to select a new model or threshold. These are retrospective benchmarks with source/era and synthetic-template limitations. External training membership is unknown, so upstream overlap cannot be excluded. This comparison does not establish pretrained adversarial robustness or a universally best model. The 703-message reserve remains unscored and unreviewed.

Protocol/code was committed at `dc7a699` before scoring validation; the separate threshold was committed at `9b34692` before benchmark inference. Reports disclose a dirty worktree because independent demo work was in progress; the comparison implementation and frozen method were unchanged. No training was performed. The earlier stage-4 selection is preserved.

[Aggregate report](reports/current-comparison.json), [validation report](reports/current-pretrained-validation.json) and [independent verification](reports/current-comparison-verification.json). The verifier independently reconstructs counts and IDs, matches all three previous clean results and checks 79 preserved model/data files. It does not claim a second full pretrained inference run. Run `uv run --frozen --extra pretrained python scripts/verify_current_comparison.py` to repeat those checks.
