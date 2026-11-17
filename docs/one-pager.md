# PhishGuard

**Organization:** HIT | **Course:** AB- Ai Security

**Team:** Lior Mashaich and Sharon Elimelech

**Supervisor:** Zimon Roi

**Project coordination:** Lior Mashaich and Sharon Elimelech

**Student IDs:** Supplied privately for local submission exports; omitted from the public repository.

## Main points

AI phishing detection and controlled adversarial robustness. Four detectors, reproducible comparisons and a local email-analysis demo.

## Problem

Phishing wording changes, while excessive false alarms disrupt legitimate communication. Strong accuracy on one dataset may hide weak generalization or sensitivity to small text changes.

## Solution

Compare classical and transformer detectors, test bounded text perturbations and evaluate an augmentation defense. Present each model's decision, score, identity and explanation limits through a local web interface.

## The methodology

Grouped data separation: 3,261 training and 745 validation messages. Select thresholds on validation only; freeze before evaluating 703 reserve messages. Compare external cohorts, repeat the final run and independently verify counts. Preserve earlier models.

## System domain

English email-text classification and academic AI-security research. Local CPU inference; no mailbox connection, link following, attachment execution or automatic blocking.

## Modules

Data preparation; TF-IDF/logistic-regression baseline; pretrained DistilBERT; fine-tuned BERT-Tiny; training-only augmentation defense; controlled perturbations; evaluation and local demo.

## Interfaces

Gradio browser UI: optional subject, email body and four model choices. CLI: data, training and evaluation workflows. Pinned Hugging Face/data downloads during setup; inference stays local.

## Description of system components

Python orchestrates file-based datasets and reports. Scikit-learn provides the baseline; PyTorch and Transformers provide neural models. A verified model registry connects frozen artifacts to Gradio. GitHub stores public code and aggregate evidence.

## Defining the goals of the project

Measure detection and false alarms; compare a ready-made classifier with locally trained models; measure controlled evasion and defense costs; prevent evaluation leakage; provide a reproducible, explainable demonstration with explicit limitations.

## Summary and Conclusions

Final-reserve accuracy ranges from 95.16% to 99.29%; challenge accuracy is 80.10%-87.25%. Rankings depend on the cohort and error cost. Augmentation gains are small and inconsistent. Two final runs agree; these results do not establish production-inbox accuracy.

Repository: https://github.com/liorma6/AI-security-agent-

Updated November 17, 2026. The supplied course template determines the one-page layout and Calibri typography. Institutional artwork is retained as supplied. Student identifiers are local submission fields, not public source content.
