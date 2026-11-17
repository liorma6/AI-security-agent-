# PhishGuard

**AI Phishing Detection and Adversarial Robustness**

**Team:** Lior Mashaich and Sharon Elimelech  
**Supervisor:** Zimon Roi  
**Institution:** HIT | **Course:** AB- Ai Security

## Problem

Convincing phishing emails can evade text classifiers, while excessive false alarms disrupt legitimate communication. High accuracy on one dataset may hide weak transfer to other sources or sensitivity to small wording changes.

## Solution

PhishGuard is a local research prototype that compares phishing detectors, tests bounded text changes and evaluates a training-data augmentation defense. Its web demo accepts pasted English email text and displays a score, decision, model identity and evidence with limitations.

## Product capabilities

- Compare a TF-IDF/logistic-regression baseline, fine-tuned BERT-Tiny, a separately defended BERT and a pretrained DistilBERT classifier.
- Keep related messages together and separate training, validation and evaluation.
- Test controlled typos, letter swaps and substitutions under a fixed query budget.
- Explain decisions through baseline feature contributions or clearly labeled text indicators; disclose truncation and unavailable models.

## Method and measured outcome

Current local models use 3,261 training and 745 validation messages. A final protocol was committed before scoring the 703-message reserve. Existing weights and thresholds were preserved, and two full runs produced identical predictions.

| Final reserve model | Accuracy | Missed phishing / false alarms |
| --- | --- | --- |
| Baseline v2 | 99.29% | 3 / 2 |
| Original BERT | 98.29% | 8 / 4 |
| Defended BERT | 98.15% | 8 / 5 |
| Pretrained DistilBERT | 95.16% | 23 / 11 |

The reserve contains 224 publisher-labeled phishing and 479 legitimate messages. Challenge accuracy was 80.10%-87.25%; model rankings and error costs vary by dataset. Augmentation gains were small and inconsistent. These results do not establish production-inbox accuracy.

## Technology and deliverables

Python, scikit-learn, PyTorch, Hugging Face Transformers, Gradio and GitHub. Inference runs locally on CPU. Deliverables include the demo, controlled-evasion script, comparative reports, eight-chapter project book, poster and PowerPoint. Software verification includes 354 passing offline tests; it is separate from model-quality evidence.

**Repository:** https://github.com/liorma6/AI-security-agent-  
**Status:** Implemented academic prototype | Updated November 17, 2026
