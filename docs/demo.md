# Local email demo

The stage-8 Gradio interface accepts an optional subject and a required email body, then shows a model score, thresholded decision, exact model identity, input-length status and evidence with limitations. It supports the preserved baseline v2, original BERT-Tiny, augmentation-trained BERT and pretrained DistilBERT. Original BERT is the initial view for continuity, not an empirically selected winner.

## Start and stop

From the repository root, with Python 3.11-3.13 and uv installed:

```sh
uv sync --locked --extra pretrained --extra demo
uv run --frozen --extra pretrained --extra demo phishguard demo
```

Open [the local demo](http://127.0.0.1:7860). Keep the terminal running; Ctrl+C stops the server. If the port is busy, use `phishguard demo --port 7861`. The host is fixed to `127.0.0.1`; there is no public sharing option. Inference needs no account, paid API, MongoDB or Docker. After package/model preparation, it runs locally.

Model weights and datasets are intentionally excluded from Git. A fresh checkout starts the UI, but selecting a missing model returns **Model unavailable**, never a fabricated score. Prepare the reviewed artifacts using the [baseline-refresh](baseline-refresh.md), [fine-tuning](finetuned.md), [defense](robustness-defense.md) and [pretrained](pretrained.md) guides. External DistilBERT additionally needs the separate [current comparison](current-comparison.md) validation selection. Existing prepared workspaces can run immediately. The application does not download or train anything when Analyze is pressed.

| Choice | Required local model | Frozen threshold | Token budget |
| --- | --- | --- | --- |
| Baseline v2 | `models/baseline-v2/` | 0.31 | Full accepted text after preprocessing |
| Original BERT | `models/finetuned-v1/` | 0.69 | First 256 tokens |
| Augmentation defense | `models/defended-v1/` | 0.07 | First 256 tokens |
| Pretrained DistilBERT | `models/pretrained/dima806-310a5602/` and `artifacts/pretrained-real-selection-v1/` | 0.45 | First 512 tokens |

Selections are checked against committed identities. Never replace the files of a running model: restart after an intentionally reviewed artifact change. Loaded models are cached in memory, while requests are serialized because neural runtime settings are process-wide. The bounded queue accepts at most eight waiting events. If interrupted or disconnected during analysis, reload the page before retrying.

## Understand a result

- The 0-100 display is the classifier score multiplied by 100, **not calibrated probability**. Decisions use the unrounded score and each model's own validation-selected threshold. Scores are not comparable across models.
- "Not flagged by this model" does not mean safe. These models were developed on English research data and have substantial transfer limitations. The UI makes no claim to authenticate senders or inspect links/attachments.
- Baseline evidence shows up to six largest absolute TF-IDF-times-coefficient terms in log-odds units. It also acknowledges the intercept and omitted terms. Learned associations are not proof of harmful intent.
- All models show a small fixed set of observable link/account/urgency/payment/markup indicators. These are text matches, not transformer attributions or a generated account of its reasoning. Indicators inspect the whole input even if a transformer truncates it; the distinction is displayed.
- The subject/body separator counts toward the 20,000-character combined limit. Empty, unusable or malformed text is rejected before model loading. Token truncation is separately disclosed; overlength character input is rejected rather than silently shortened by the service.

## Privacy and validation

The demo treats input as inert text and escapes feature/explanation output. It has no attachment input, email delivery, URL fetching, training or external inference route. Telemetry, public sharing, monitoring, MCP serving and PWA are disabled. System fonts avoid external font downloads. Private event endpoints, strict CORS, a 262,144-byte request-body cap, denied upload routes and blocked project-file serving reduce the local interface's exposure. This is not a multiuser hosting design.

PhishGuard does not persist submitted email or log it in its own handlers. Text exists in the browser and transient server/queue memory; Clear removes the displayed fields/result, not guaranteed memory erasure. Browser extensions, developer tools and operating-system memory are outside this guarantee. Use nonsensitive synthetic/public examples. Model failures use fixed messages without raw exception content.

Tests cover validation-before-load, exact length boundaries, allowlisted models, preserved thresholds, unavailable artifacts, private error messages, escaped output, signed feature contributions, truncation, queue/event configuration and upload/body limits. Actual browser checks exercise all four local models, empty input, HTML-like input, clear/reset and desktop/mobile layouts. Full-corpus model comparison is separate from software-test success. See [Gradio Blocks documentation](https://gradio.app/docs/gradio/blocks) and [file-access documentation](https://gradio.app/guides/file-access) for the framework controls.
