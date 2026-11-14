"""Allowlisted local models, bounded inputs and honest, escaped explanations."""

import html
import re
import threading
from pathlib import Path

from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import MAX_EMAIL_CHARACTERS, Prediction
from phishguard.validation import ContractError, validate_record

MODELS = {
    "finetuned": "BERT-Tiny | original fine-tuned",
    "baseline_v2": "TF-IDF + logistic regression | baseline v2",
    "defended": "BERT-Tiny | augmentation defense",
    "pretrained": "DistilBERT | pretrained Hugging Face",
}
DEFAULT_MODEL = "finetuned"
IDLE = (
    '<div class="result empty"><span class="eyebrow">ANALYSIS</span>'
    "<h2>Ready when you are.</h2><p>Paste an English email, choose a model and "
    'select Analyze email.</p><p class="muted">Your result and its limitations '
    "will appear here.</p></div>"
)


def indicators(email):
    """Literal text observations, not inferred intent or transformer attribution."""
    text = email.text.casefold()
    patterns = (
        (r"https?://|www\.", "Web-link text is present. No destination was opened or checked."),
        (
            r"\b(password|credential|verification code|verify your account)\b",
            "Account or credential language is present.",
        ),
        (
            r"\b(urgent|immediately|expires?|suspend(?:ed)?)\b",
            "Time pressure or account-status language is present.",
        ),
        (r"\b(invoice|payment|wire transfer|gift card)\b", "Payment-related language is present."),
        (
            r"<[^>]+>",
            "Markup-like text is present. It is treated as text, never rendered as email HTML.",
        ),
    )
    return [description for pattern, description in patterns if re.search(pattern, text)] or [
        "None of the limited link/account/urgency/payment indicators matched. "
        "This is not evidence of safety."
    ]


def feature_evidence(model, email):
    """Largest signed linear terms, not causal or sender-authenticity claims."""
    matrix = model.transform.transform([preprocess(email.text)])
    terms = [
        (model.state.terms[index], float(value * model.state.coefficients[index]))
        for index, value in zip(matrix.indices, matrix.data, strict=True)
    ]
    return sorted(terms, key=lambda item: (-abs(item[1]), item[0]))[:6]


class DemoService:
    def __init__(self, root=Path("."), loader=None):
        self.root = root.resolve()
        self.loader = loader or self._load
        self.models = {}
        self.lock = threading.Lock()

    def _load(self, key):
        if key == "baseline_v2":
            from phishguard.baseline.model import load_model
            from phishguard.finetune.common import STUDY

            model = load_model(self.root / "models/baseline-v2")
            if model.revision != STUDY["baseline_v2_revision"]:
                raise ValueError("model_identity_mismatch")
            return model, model.state.threshold
        if key == "pretrained":
            from phishguard.comparison import MODEL, REFERENCE, SELECTION, checked_selection
            from phishguard.pretrained.adapter import load_classifier

            decision = checked_selection(self.root / SELECTION, self.root / REFERENCE)
            return load_classifier(self.root / MODEL), decision.threshold
        if key == "finetuned":
            from phishguard.defense.model import parent

            model = parent(
                self.root / "models/finetuned-v1",
                self.root / "data/manifests/finetuned-v1-selection.json",
            )
        else:
            from phishguard.defense.model import load_detector

            model = load_detector(
                self.root / "models/defended-v1",
                self.root / "data/manifests/defended-v1-selection.json",
            )
        return model, model.manifest["threshold"]

    def analyze(self, subject, body, key):
        if not isinstance(key, str) or key not in MODELS:
            return {"status": "invalid", "message": "Choose one of the available models."}
        try:
            email = validate_record("email", {"subject": subject, "body": body})
            preprocess(email.text)
        except (ContractError, ValueError, TypeError):
            return {
                "status": "invalid",
                "message": "Enter a nonempty email body with usable words. Subject and body "
                f"together must fit within {MAX_EMAIL_CHARACTERS:,} characters, including "
                "their two-character separator. Unsupported control characters are rejected.",
            }
        try:
            with self.lock:
                if key not in self.models:
                    self.models[key] = self.loader(key)
                model, threshold = self.models[key]
                raw = (
                    model.predict(email, threshold) if key == "pretrained" else model.predict(email)
                )
                if isinstance(raw, Prediction):
                    raw = {"prediction": raw.model_dump(), "input": {"truncated": False}}
                prediction = Prediction.model_validate(raw["prediction"])
                if prediction.threshold != threshold:
                    raise ValueError("prediction_threshold_mismatch")
                evidence = feature_evidence(model, email) if key == "baseline_v2" else []
            return {
                "status": "ok",
                "model": MODELS[key],
                "prediction": prediction.model_dump(),
                "input": raw["input"],
                "indicators": indicators(email),
                "features": evidence,
            }
        except Exception:
            # Never render/log exception text: a dependency can include private email in it.
            return {
                "status": "unavailable",
                "message": "This model could not be loaded or scored. Check its local artifacts "
                "and the setup guide, then retry. No score was produced.",
            }

    def render(self, subject, body, key):
        return render_result(self.analyze(subject, body, key))


def render_result(result):
    def escape(value):
        return html.escape(str(value), quote=True)

    if result["status"] != "ok":
        title = "Check your input" if result["status"] == "invalid" else "Model unavailable"
        return (
            f'<div class="result notice" role="status"><h2>{title}</h2>'
            f"<p>{escape(result['message'])}</p></div>"
        )
    p = result["prediction"]
    flagged = p["label"] == "phishing"
    label = "Potential phishing" if flagged else "Not flagged by this model"
    side = "at or above" if flagged else "below"
    details = result["input"]
    token_note = "The baseline uses the full accepted text after the documented preprocessing."
    if "original_tokens" in details:
        token_note = f"{details['used_tokens']} of {details['original_tokens']} tokens used. " + (
            "TRUNCATED: the end of this email was not evaluated."
            if details["truncated"]
            else "No token truncation."
        )
    observations = "".join(f"<li>{escape(item)}</li>" for item in result["indicators"])
    features = ""
    if result["features"]:
        items = "".join(
            f"<li><code>{escape(term)}</code>: {value:+.3f} toward "
            f"{'phishing' if value > 0 else 'legitimate'}</li>"
            for term, value in result["features"]
        )
        features = (
            f"<h3>Largest model contributions</h3><ul>{items}</ul><p class='muted'>"
            "TF-IDF value multiplied by its learned coefficient, in log-odds units. "
            "These are learned associations; the intercept and other terms also "
            "affect the decision.</p>"
        )
    return f"""<div class="result {"flagged" if flagged else "unflagged"}" role="status">
    <span class="eyebrow">{escape(result["model"])}</span><h2>{label}</h2>
    <div class="score">{p["score"] * 100:.1f}<small> / 100</small></div>
    <p>Model risk score · <strong>not a calibrated probability</strong></p>
    <p>The score {p["score"]:.6f} is {side} this model's validation-selected threshold
    {p["threshold"]:.2f}. Scores from different models are not directly comparable.</p>
    <h3>Reading this result</h3><p>{escape(token_note)}</p>
    <p>This English-text research model can miss phishing and flag legitimate mail.
    It does not authenticate the sender, check links or inspect attachments.</p>
    {features}<h3>Observable text indicators</h3><ul>{observations}</ul>
    <p class="muted">Indicators are simple text matches across the whole input,
    including any truncated part. They are not evidence of malicious intent or
    an explanation of the transformer's internal reasoning.</p>
    <details><summary>Model identity</summary><p><code>{escape(p["model_id"])}</code></p>
    <p class="revision">{escape(p["model_revision"])}</p></details>
    </div>"""
