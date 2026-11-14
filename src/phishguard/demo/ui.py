"""Loopback Gradio UI with no upload, remote assets, telemetry or stored examples."""

import os
from pathlib import Path

from phishguard.demo.service import DEFAULT_MODEL, IDLE, MODELS, DemoService

CSS = """
.gradio-container {max-width:1180px !important;margin:auto !important;}
#hero {padding:32px 4px 20px;border-bottom:1px solid #cad8d5;margin-bottom:22px;}
#hero h1 {font-size:42px;letter-spacing:-1.8px;margin:8px 0;color:#153e38;}
.eyebrow {font-size:11px;font-weight:750;letter-spacing:1.5px;color:#376b61;}
#hero p {max-width:720px;font-size:17px;line-height:1.65;color:#45625b;}
.result {border:1px solid #c8d8d2;border-top:4px solid #357c6b;border-radius:14px;
padding:26px;background:#fcfefd;min-height:390px;color:#183e35;}
.result h2 {font-size:27px;letter-spacing:-.6px;margin:12px 0;line-height:1.2;}
.result h3 {font-size:16px;margin:22px 0 8px;}
.result p,.result li {font-size:14px;line-height:1.65;}
.result ul {padding-left:22px;}
.result .score {font-size:52px;line-height:1.25;font-weight:750;
letter-spacing:-2px;margin-top:20px;}
.result .score small {font-size:20px;letter-spacing:0;font-weight:400;color:#60766e;}
.result.flagged {border-top-color:#b77c31;}
.result.notice {border-top-color:#b77c31;min-height:180px;}
.result .muted {color:#60766e;}
.result .revision {overflow-wrap:anywhere;font-family:monospace;font-size:12px;}
.result details {margin-top:22px;border-top:1px solid #dce5e1;padding-top:15px;}
#privacy {padding:18px 4px;color:#546960;font-size:13px;line-height:1.7;}
@media(max-width:650px){#hero h1{font-size:34px}.result{padding:20px;min-height:240px}}
"""


class LocalRequestGuard:
    """Bound request bodies before parsing; the pasted-text demo needs no upload route."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"].rstrip("/").endswith(("/upload", "/upload_progress")):
            return await self.reject(send, 403)
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            events, size = [], 0
            while True:
                event = await receive()
                if event["type"] == "http.disconnect":
                    return
                size += len(event.get("body", b""))
                if size > 262_144:
                    return await self.reject(send, 413)
                events.append(event)
                if not event.get("more_body", False):
                    break

            async def replay():
                return events.pop(0) if events else await receive()

            return await self.app(scope, replay, send)
        return await self.app(scope, receive, send)

    @staticmethod
    async def reject(send, status):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send(
            {"type": "http.response.body", "body": b"Request not accepted by this local text demo."}
        )


def build_demo(service=None):
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    os.environ["GRADIO_RUN_HISTORY"] = "False"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import gradio as gr

    service = service or DemoService()
    with gr.Blocks(analytics_enabled=False, title="PhishGuard | Email research demo") as demo:
        gr.HTML(
            '<header id="hero"><span class="eyebrow">PHISHGUARD / LOCAL RESEARCH DEMO</span>'
            "<h1>A closer look at suspicious email.</h1><p>Explore what four phishing "
            "classifiers see in the same message. Read the score alongside its evidence "
            "and limitations.</p></header>"
        )
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=320):
                model = gr.Dropdown(
                    [(name, key) for key, name in MODELS.items()],
                    value=DEFAULT_MODEL,
                    label="Choose a model",
                    allow_custom_value=False,
                    info="Original BERT is the starting view, not a claim that it is best.",
                )
                subject = gr.Textbox(label="Subject (optional)", placeholder="Email subject")
                body = gr.Textbox(
                    label="Email body",
                    lines=12,
                    max_lines=18,
                    placeholder="Paste email text here. Use public or synthetic examples "
                    "without personal information.",
                    info="English text - 20,000 characters combined, including subject separator.",
                )
                with gr.Row():
                    analyze = gr.Button("Analyze email", variant="primary")
                    clear = gr.Button("Clear", variant="secondary")
            with gr.Column(scale=1, min_width=320):
                result = gr.HTML(IDLE, elem_id="analysis-result")
        gr.HTML(
            '<div id="privacy"><strong>Local by design.</strong> Inference runs on this computer. '
            "PhishGuard does not save submitted email, open links, send email or call an external "
            "model API. Text exists in browser/server memory during use; Clear removes the "
            "displayed input and result, not a guarantee of secure memory erasure. "
            "Use nonsensitive examples. This is a research demonstration, "
            "not a mail-security service.</div>"
        )
        controls = [subject, body, model, analyze, clear]

        def begin():
            return [gr.update(interactive=False) for _ in controls] + [
                '<div class="result" role="status"><h2>Analyzing locally...</h2><p>The first '
                "request may take longer while the selected model loads.</p></div>"
            ]

        def finish(subject_value, body_value, model_value):
            output = service.render(subject_value, body_value, model_value)
            return [gr.update(interactive=True) for _ in controls] + [output]

        start = analyze.click(
            begin, outputs=controls + [result], queue=False, api_visibility="private"
        )
        start.then(
            finish,
            inputs=[subject, body, model],
            outputs=controls + [result],
            concurrency_limit=1,
            concurrency_id="inference",
            api_visibility="private",
        )
        clear.click(
            lambda: ("", "", IDLE),
            outputs=[subject, body, result],
            queue=False,
            api_visibility="private",
        )
        for component in (subject, body, model):
            component.input(lambda: IDLE, outputs=result, queue=False, api_visibility="private")
    return demo.queue(max_size=8, default_concurrency_limit=1, api_open=False)


def launch_options(root, port):
    from starlette.middleware import Middleware

    return {
        "server_name": "127.0.0.1",
        "server_port": port,
        "share": False,
        "inbrowser": False,
        "show_error": False,
        "strict_cors": True,
        "enable_monitoring": False,
        "mcp_server": False,
        "pwa": False,
        "ssr_mode": False,
        "max_threads": 4,
        "max_file_size": 1,
        "allowed_paths": [],
        "blocked_paths": [str(root.resolve())],
        "footer_links": [],
        "state_session_capacity": 8,
        "app_kwargs": {"middleware": [Middleware(LocalRequestGuard)]},
        "css": CSS,
    }


def launch(port=7860, root=Path(".")):
    demo = build_demo(DemoService(root))
    import gradio as gr

    return demo.launch(
        **launch_options(root, port),
        theme=gr.themes.Soft(
            primary_hue="emerald",
            neutral_hue="slate",
            font=["Segoe UI", "Arial", "sans-serif"],
            font_mono=["Consolas", "monospace"],
        ),
    )
