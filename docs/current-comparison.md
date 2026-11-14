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

Selection writes `artifacts/pretrained-real-selection-v1/`; evaluation writes `artifacts/comparison-v1/`. Existing outputs are refused. Reproduction uses `--output` and, for evaluation, `--selection` / `--selection-reference`. No model or dataset download is required after the earlier stages. Raw email and per-example predictions stay outside Git. Results will be recorded after measurement.
