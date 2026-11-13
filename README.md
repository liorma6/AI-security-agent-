# PhishGuard

PhishGuard is a course project on phishing-email classification and adversarial robustness. Its planned workflow compares a TF-IDF/logistic-regression baseline with Hugging Face classifiers, measures the effect of controlled text changes, and evaluates a defense. A local web demo will accept pasted email text and show a risk score and explanation.

## Current status

This repository contains the initial specification, proposed UML architecture, STRIDE threat analysis, test plan and development milestones. Dataset preparation, classifiers, training, perturbation experiments and the web demo are **not implemented yet**. There is no application start command or trained model to download at this stage.

## Check the documentation

Python 3.11 or later is sufficient. No third-party packages, accounts or API keys are required for the current checks.

From the repository root, run:

```sh
python scripts/check_documents.py
```

The command checks English content, local document links, Markdown table structure, the eight required project-book chapters and both UML diagrams. GitHub Actions runs the same checks. These checks validate the documentation; they are not classifier tests or evidence of model accuracy.

## Documentation

- [Project book and system specification](docs/project-book.md)
- [Specification entry point](docs/specification.md)
- [Implementation plan](docs/implementation-plan.md)
- [Progress and verification log](docs/stage-log.md)

The project book is the canonical specification. It distinguishes existing documentation from planned application behavior. Installation, training, evaluation and demo commands will be added here when their implementations are available and verified.

## Planned deliverables

- A baseline detector and a fine-tuned small transformer, with reproducible evaluation.
- A comparison against a suitable pretrained Hugging Face classifier.
- A controlled text-perturbation runner and a robustness improvement experiment.
- A local pasted-email demo with model identity, score and explanation.
- A comparative report and final presentation.

## Data and models

No dataset or checkpoint is included. Review licenses, provenance, privacy and label meanings before selecting them. Keep raw or private email, credentials and large model artifacts out of Git. Keep related messages and all their derived variants in the same data split.

## Team

Lior and Sharon Elimelech share planned responsibility equally. The project book records the allocation, the reported two-week learning period and how actual contributions will be recorded as work proceeds.
