"""Demo boundaries, privacy, rendering and the actual Gradio event wiring."""

import asyncio
from types import SimpleNamespace

import pytest

from phishguard.contracts import EmailInput, Prediction
from phishguard.demo.service import DemoService, feature_evidence, indicators, render_result
from phishguard.demo.ui import LocalRequestGuard, build_demo, launch_options


def fake_model(score=0.7, threshold=0.69, truncated=False):
    def predict(email, *args):
        return {
            "prediction": Prediction(
                example_id="fixture",
                model_id="fixture",
                model_revision="a" * 64,
                score=score,
                threshold=threshold,
                label="phishing" if score >= threshold else "legitimate",
                elapsed_ms=1.0,
            ).model_dump(),
            "input": {
                "original_tokens": 500 if truncated else 10,
                "used_tokens": 256 if truncated else 10,
                "truncated": truncated,
            },
        }

    return SimpleNamespace(predict=predict)


@pytest.mark.parametrize(
    "subject,body",
    [
        ("", ""),
        ("", "   "),
        ("", "!?"),
        ("", "<<marker>>"),
        ("", "a" * 20001),
        ("x", "a" * 19998),
        ("", "word\x00"),
        (None, "words"),
    ],
)
def test_invalid_input_never_loads_model(subject, body):
    service = DemoService(loader=lambda _: pytest.fail("must validate first"))
    assert service.analyze(subject, body, "finetuned")["status"] == "invalid"


@pytest.mark.parametrize("key", ["https://example.invalid/model", "../models", None, []])
def test_model_allowlist(key):
    assert DemoService().analyze("", "ordinary words", key)["status"] == "invalid"


def test_inclusive_length_boundary_and_model_cache():
    loaded = []

    def loader(key):
        loaded.append(key)
        return fake_model(), 0.69

    service = DemoService(loader=loader)
    for _ in range(2):
        assert service.analyze("x", "a" * 19997, "finetuned")["status"] == "ok"
    assert loaded == ["finetuned"]
    assert not hasattr(service, "emails")


def test_exception_redaction(capsys):
    marker = "PRIVATE_SENTINEL_NEVER_LOG"

    def fail(_):
        raise RuntimeError(marker)

    result = DemoService(loader=fail).render("", marker, "pretrained")
    assert "Model unavailable" in result and "No score" in result
    assert marker not in result
    assert marker not in str(capsys.readouterr())


def test_missing_artifacts_are_unavailable(tmp_path):
    assert (
        DemoService(root=tmp_path).analyze("", "sample words", "baseline_v2")["status"]
        == "unavailable"
    )


def test_mismatched_threshold_rejected():
    service = DemoService(loader=lambda _: (fake_model(), 0.5))
    assert service.analyze("", "sample words", "finetuned")["status"] == "unavailable"


def test_actual_score_decision_and_truncation_are_displayed():
    result = DemoService(loader=lambda _: (fake_model(truncated=True), 0.69)).render(
        "", "ordinary message", "finetuned"
    )
    assert "70.0" in result and "Potential phishing" in result
    assert "TRUNCATED" in result and "256 of 500" in result
    assert "not a calibrated probability" in result
    assert "not evidence of malicious intent" in result


def test_not_flagged_is_not_called_safe():
    result = DemoService(loader=lambda _: (fake_model(score=0.1), 0.69)).render(
        "", "ordinary message", "finetuned"
    )
    assert "Not flagged by this model" in result
    assert "can miss phishing" in result


def test_html_like_email_is_inert_and_features_are_escaped():
    service = DemoService(loader=lambda _: (fake_model(), 0.69))
    result = service.analyze("", '<script>alert("sentinel")</script> ordinary email', "finetuned")
    assert result["status"] == "ok"
    result["features"] = [("<img src=x onerror=alert(1)>", 0.2)]
    rendered = render_result(result)
    assert "<img" not in rendered and "<script" not in rendered
    assert "&lt;img" in rendered
    assert "sentinel" not in rendered


def test_linear_explanation_uses_real_signed_contributions():
    matrix = SimpleNamespace(indices=[0, 1, 2], data=[0.5, 0.25, 0.75])
    model = SimpleNamespace(
        state=SimpleNamespace(terms=["first", "second", "third"], coefficients=[2, -8, 0.2]),
        transform=SimpleNamespace(transform=lambda _: matrix),
    )
    values = feature_evidence(model, EmailInput(body="sample words"))
    assert values[:2] == [("second", -2.0), ("first", 1.0)]
    assert values[2][1] == pytest.approx(0.15)


def test_observations_do_not_fetch_links():
    result = indicators(EmailInput(body="Urgent payment at https://example.invalid"))
    assert len(result) == 3
    assert "No destination was opened" in result[0]


def test_launch_is_local_and_does_not_expose_artifact_paths(tmp_path):
    options = launch_options(tmp_path, 7860)
    assert options["server_name"] == "127.0.0.1"
    assert options["share"] is options["show_error"] is options["enable_monitoring"] is False
    assert options["mcp_server"] is options["pwa"] is False
    assert options["strict_cors"] is True
    assert options["allowed_paths"] == []
    assert options["blocked_paths"] == [str(tmp_path.resolve())]


def test_gradio_wiring_is_private_bounded_and_has_no_upload_components():
    demo = build_demo(DemoService(loader=lambda _: (fake_model(), 0.69)))
    try:
        assert demo.analytics_enabled is False
        assert demo._queue.max_size == 8
        assert all(fn.api_visibility == "private" for fn in demo.fns.values())
        assert not any(
            type(x).__name__ in {"File", "UploadButton", "Image"} for x in demo.blocks.values()
        )
        inference = next(fn for fn in demo.fns.values() if fn.concurrency_id == "inference")
        assert inference.concurrency_limit == 1
        assert len(inference.inputs) == 3 and len(inference.outputs) == 6
    finally:
        demo.close()


@pytest.mark.parametrize(
    "path,size,status", [("/gradio_api/upload", 0, 403), ("/api", 262145, 413), ("/api", 100, 200)]
)
def test_guard_rejects_uploads_and_oversized_chunked_bodies(path, size, status):
    sent = []
    chunks = [
        {"type": "http.request", "body": b"x" * (size // 2), "more_body": True},
        {"type": "http.request", "body": b"x" * (size - size // 2), "more_body": False},
    ]

    async def receive():
        return chunks.pop(0)

    async def send(event):
        sent.append(event)

    async def app(scope, receive, send):
        body = b""
        while True:
            event = await receive()
            body += event["body"]
            if not event.get("more_body"):
                break
        assert len(body) == size
        await send({"type": "http.response.start", "status": 200})

    asyncio.run(
        LocalRequestGuard(app)({"type": "http", "method": "POST", "path": path}, receive, send)
    )
    assert sent[0]["status"] == status
