# PhishGuard specification

The [PhishGuard project book](project-book.md) is the canonical system specification and course submission source. It contains the eight required chapters: background, objectives, technical requirements, STRIDE, unit tests, conclusions, UML architecture and work plan.

Current status: stages 0-4 and additional checkpoints 4a/4b completed. Python contracts, reviewed data preparation, frozen grouped splits, baseline training/evaluation, safe model persistence, pretrained comparison, external generalization audit, real-mail data refresh, separately trained baseline v2 and local inference are available. See the [contract reference](contracts.md), [dataset guide](dataset.md), [baseline report](baseline.md), [pretrained comparison](pretrained.md), [generalization audit](generalization-audit.md) and [baseline refresh with limitations](baseline-refresh.md). Stage 5 has not started. Transformer fine-tuning, adversarial evaluation, defense and the web demo remain planned. The [stage log](stage-log.md) records completed checks and their scope.

Use the [implementation plan](implementation-plan.md) for stage order and acceptance criteria. Use the root [README](../README.md) for the capabilities and commands available in the current checkout. Update the project book as implementation proceeds; do not maintain a second competing specification here.
