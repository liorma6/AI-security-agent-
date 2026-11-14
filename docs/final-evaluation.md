# Stage 9 - Preregistered final evaluation

This protocol is fixed **before scoring or manually inspecting the 703 reserved messages**. The packaged [protocol](../src/phishguard/final_protocol.json) states all experimental choices. A committed freeze manifest binds that protocol, executable source, prior selections and unchanged artifacts. The CLI refuses a dirty tracked worktree, an uncommitted freeze, changed files, development overlap or mismatched reserve membership. No training command is involved.

## Population and fixed decisions

Use all 703 existing reserve messages in their 432 heuristic groups: 479 legitimate SpamAssassin messages and 224 Nazario phishing messages (116 from 2024, 108 from 2025). Membership, labels, preprocessing, source/license provenance and original bytes are already pinned by the stage-4a manifest. Do not drop difficult examples, relabel errors or resplit. The on-disk reserve keeps its original unassigned split; the runner creates a temporary test-role view solely for the existing perturbation library.

Clean comparison includes baseline v2 at 0.31, original BERT at 0.69, defended BERT at 0.07 and pretrained DistilBERT at 0.45. All weights and selections are preserved. The earlier baseline v1 and synthetic pretrained selection remain archived. Existing full-text/256-token/512-token limits and CPU adapters remain unchanged. Neither the model used by default in the demo nor any threshold will change because of the final results.

Report confusion counts, accuracy, balanced accuracy, phishing precision/recall/F1, legitimate false-positive rate, source breakdowns and truncation. Use existing 1,000-resample whole-group 95% bootstrap intervals with seed 42. Add a paired defended-minus-original BERT clean contrast over the same resampled groups. These are descriptive corpus-conditional intervals, not an adjusted universal-superiority test. Sources containing only one class have undefined denominators reported as null.

## Controlled robustness

Compare the three trained current candidates using one new seed-9042 bank under the unchanged stage-6 operations/constraints. Up to twelve candidate queries plus one clean query per parent/model are permitted. No adaptive generation, gradients, extra probing or early stopping. Both classes receive the same generated candidates and models receive identical texts. Keep parent/group lineage. Original and candidate exact preprocessed overlap with local development fingerprints aborts the run, rather than silently excluding rows.

First-candidate corruption measures both-class degradation. Directed phishing-only search takes the minimum score including the original and leaves legitimate mail clean. Candidate ASR divides newly evaded phishing by **all initially detected phishing**, including parents without candidates. Report common eligibility, per-family/source results, parent-selected transfer, actual queries and effective token no-ops. Pretrained DistilBERT is included in clean comparison only; this stage makes no claim about its adversarial robustness.

Automatic edit constraints do not prove semantic preservation. Only after all scores are fixed, select the bounded error/attack sample specified in the protocol by deterministic hashes. Record AI-assisted supported/ambiguous/invalid judgments without changing primary labels or results. Raw text and excerpts stay local. Reviewed valid successes provide a limited lower bound, not certification of all generated variants.

## Verification, failure and interpretation

Run the complete frozen evaluation twice into separate new directories. Independently reconstruct confusion counts and query/ASR denominators; compare prediction/bank bytes, file digests and in-memory neural weights. A numerical repeat is not a second independent dataset. Require all 79 preserved file identities from stage 8, plus the current pretrained selection and committed references. The ordinary test suite uses invented fixtures and never opens the real reserve.

On an integrity, membership or development-overlap failure, stop without publishing a selected subset as the full reserve. Fix only a disclosed implementation defect, record whether any outcome was visible, and retain the originally frozen experimental choices. Any later model/threshold/attack tuning requires a new external cohort; these 703 examples are no longer untouched evidence once scored.

The reserve is independent of local model-selection outcomes but belongs to the same source families as earlier audits. Legitimate mail is historical and phishing is recent, so class, era and source remain confounded. Upstream pretrained training membership is unknown. Campaign grouping and labels are imperfect. The defense combines continued training and augmentation without a clean-only continuation control or multi-seed study. No production-ready spam-filter or calibrated-risk claim is supported by this study alone.

## Commands and outputs

After the freeze manifest has been committed:

```sh
uv run --frozen --extra pretrained phishguard final evaluate
uv run --frozen --extra pretrained phishguard final evaluate --output artifacts/final-evaluation-repeat-v1
```

Each new output contains aggregate `report.json`, text-free per-example `predictions.jsonl` and private local `bank.jsonl` with candidate text. No existing directory is overwritten. Large/raw artifacts stay ignored by Git. Measured results, verification, error review and final conclusions will be added after evaluation. The final submission package includes an updated project book, comparative report, reproduction/demo instructions and presentation; student review and course submission are separate from preparing those files.
