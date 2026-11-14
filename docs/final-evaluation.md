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

Each new output contains aggregate `report.json`, text-free per-example `predictions.jsonl` and private local `bank.jsonl` with candidate text. No existing directory is overwritten. Large/raw artifacts stay ignored by Git. Measured results and independent verification are recorded below. The final submission package includes an updated project book, comparative report, reproduction/demo instructions and presentation; student review and course submission are separate from preparing those files.

## Measured results and interpretation

### Execution and clean comparison

Protocol, executable code and freeze manifest were committed and pushed at `77c4a17777d92abf653d7fd13746ba4e384eeb5a` before scoring or manually reviewing any reserve text. The freeze binds 96 source/reference files and 79 preserved model/data inputs. Both full runs record that clean code revision. All 703 messages in 432 groups were evaluated: 479 legitimate and 224 publisher-labeled phishing. Existing model weights, thresholds, preprocessing and input budgets remained unchanged; no final results selected a model or changed the demo default.

| Model | Accuracy | Phishing recall | False-positive rate | FN / FP |
| --- | --- | --- | --- | --- |
| Baseline v2 | 99.29% | 98.66% | 0.42% | 3 / 2 |
| Original BERT | 98.29% | 96.43% | 0.84% | 8 / 4 |
| Defended BERT | 98.15% | 96.43% | 1.04% | 8 / 5 |
| Pretrained DistilBERT | 95.16% | 89.73% | 2.30% | 23 / 11 |

These are frozen-threshold, source-conditioned results, not estimates of contemporary inbox accuracy. The reserve shares source families and years with development; class, source and era are confounded. Baseline v2 has the fewest errors here but its earlier challenge accuracy is 80.10% with 372 false alarms among 1,000 legitimate messages. Pretrained DistilBERT has 87.25% challenge accuracy but the lowest challenge phishing recall. Different datasets and error costs change the comparison. No universal winner or production-readiness claim follows.

Original and defended BERT truncate 384/703 messages to 256 tokens; pretrained DistilBERT truncates 204/703 to 512 tokens. The machine-readable report includes group-bootstrap intervals, per-source results and paired defense contrasts. The paired defended-minus-original clean accuracy interval spans zero (approximately -0.64 to +0.30 percentage points). This is descriptive uncertainty conditional on this corpus and heuristic grouping, not proof of equivalence.

The same seed-9042 bank contains 5,853 candidates. Each of the three trained current models uses 6,556 total queries, with at most 12 candidates plus one clean query per parent. No pretrained attack evaluation is claimed. Directed search includes the original in the minimum score, attacks phishing only and leaves legitimate messages clean. The denominator includes initially detected phishing without candidates.

| Model | Clean / directed FN | New misses / initially detected phishing | Candidate ASR |
| --- | --- | --- | --- |
| Baseline v2 | 3 / 3 | 0 / 221 | 0.00% |
| Original BERT | 8 / 13 | 5 / 216 | 2.31% |
| Defended BERT | 8 / 11 | 3 / 216 | 1.39% |

On the common 215 phishing messages initially detected by both BERT variants, the new-miss counts are 4 for original BERT and 3 for defended BERT. First-candidate corruption produces 0, 1 and 0 new phishing misses for baseline, original BERT and defended BERT respectively. These results support only the declared finite search and automatic edit constraints; the semantic and label review below is essential. A single seed, an easy source-matched cohort and no clean-only continued-training control cannot establish a general or causal defense advantage.

Two complete scoring runs produce identical prediction and candidate-bank bytes, metrics, intervals and selected review IDs. An independent verifier reconstructs all clean/fixed/directed confusion counts, source/operation ASR, eligibility, edit replay and query bounds. All 79 preserved files retain their hashes; neural tensors and thresholds remain unchanged. Reproduction is numerical verification, not a second independent dataset. See [final protocol and results](final-evaluation.md), [aggregate report](reports/final-evaluation.json) and [independent verification](reports/final-verification.json).

### Review and conclusions

The committed post-score selection yields 11 unique clean-error cases and three defended attack successes. AI-assisted inspection supports five benign-text patterns and marks six clean cases ambiguous, including missing message bodies, extraction placeholders, mixed-content padding and unknown sender/destination context. Clean inspection uses the redacted subject and up to 1,800 displayed body characters; it is not exhaustive full-message annotation. Primary publisher labels and all measured counts remain unchanged.

All three attack cases preserve the short original notification's apparent meaning after typographical edits. However, they are sharing/account notifications whose underlying phishing identity cannot be independently established from the available text. Thus **3/216 is publisher-label-dependent candidate ASR, not three independently confirmed malicious evasions**. The reviewed lower bound of successes with both supported phishing identity and preserved meaning is zero; this does not prove the messages benign or the defense secure. Independent student/human review remains open. The [text-free review record](reports/final-review.json) records each judgment without publishing email excerpts.

The project delivers a reproducible detector comparison, bounded robustness experiment, separate augmentation defense and working local demo. The high reserve accuracy does not erase poor challenge transfer or label uncertainty. Future research should acquire contemporary both-class data with independently reviewed labels, stronger campaign separation, multiple seeds and a clean-only continued-training control. The 703-message reserve is now consumed and cannot be reused as fresh evidence after tuning. New model or threshold decisions require a new held-out cohort.

The comparative report, English project book, reproduction/demo guide and 16-slide presentation are prepared. See the [submission package](submission.md) and [slide content with speaker notes](presentation.md). This completes the twelve planned implementation milestones (0-9 plus 4a/4b). Students must still review, understand and present their work and complete the actual course submission; those personal actions are not claimed as completed.

### Exact reproduction and preserved outputs

The initial runs used the clean preregistration commit `77c4a17`. Later documentation and independent-verifier changes do not alter the frozen 96 source/reference files. The runner still requires a clean committed tracked tree and all frozen hashes; never rewrite the freeze to make an incompatible run pass. Reproduction needs the exact pinned local artifacts, not merely any retrained model with similar scores. The verifier reads both original output directories by design:

```sh
uv run --frozen python scripts/verify_final.py
```

This checks recorded outputs without loading a model or changing data. New scoring repetitions must use unused directories. The private candidate banks and predictions stay local; [verification aggregates](reports/final-verification.json) provide digests for comparison. See the [reproduction and submission guide](submission.md) for prerequisite artifact preparation and limitations across hardware.
