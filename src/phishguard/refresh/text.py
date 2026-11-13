"""Label-independent extraction repairs declared before new-corpus evaluation."""

import re
from email import policy
from email.parser import BytesParser

from pydantic import ValidationError

from phishguard.audit.common import AuditError
from phishguard.audit.mime import VisibleText
from phishguard.audit.mime import extract as original_extract
from phishguard.baseline.common import BaselineError
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import EmailInput

PLACEHOLDER = re.compile(
    r"^(?:this is an html.only message[.\s]*to view it,? "
    r"activate html in your email application[.\s]*"
    r"|normal|no.reply)$",
    re.I,
)
HTML_ROOT = re.compile(r"^\s*(?:<!doctype\s+html|<html\b|<body\b|<script\b)", re.I)
REDACTIONS = re.compile(
    r"\[(?:NAME|ORGANIZATION|DATE|PRODUCT|EMAIL_ADDRESS|TIME|URL|ADDRESS|REFERENCE_NUMBER|"
    r"PHONE_NUMBER|FINANCIAL_INFO|FILE_NAME|USERNAME|INITIALS|FILE_PATH|VERSION|IMAGE|"
    r"IP_ADDRESS|NUMBER|JOB_TITLE|LOCATION|EVENT|FAX_NUMBER|SYMBOL|COORDINATES|NATIONALITY)\]"
)


def remove_redactions(email):
    """Remove declared publisher placeholder types, independently of source and label."""
    try:
        result = EmailInput(
            subject=REDACTIONS.sub(" ", email.subject), body=REDACTIONS.sub(" ", email.body)
        )
        preprocess(result.text)
        return result
    except (ValidationError, BaselineError):
        raise AuditError("unusable_after_redaction_removal") from None


def visible(body):
    parser = VisibleText()
    parser.feed(body)
    parser.close()
    return " ".join("".join(parser.parts).split())


def clean_text(email):
    """Recognize a document root, not arbitrary code quoted in ordinary prose."""
    if not HTML_ROOT.search(email.body):
        return email, False
    try:
        cleaned = EmailInput(subject=email.subject, body=visible(email.body))
        preprocess(cleaned.text)
    except (ValidationError, BaselineError):
        raise AuditError("refresh_unusable_html_text") from None
    return cleaned, cleaned != email


def extract(raw):
    email, original_flags = original_extract(raw)
    fallback = False
    if PLACEHOLDER.fullmatch(email.body.strip()):
        message = BytesParser(policy=policy.default).parsebytes(raw)
        part = message.get_body(preferencelist=("html",))
        if part is not None and not part.get_filename():
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                try:
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="strict")
                    candidate = EmailInput(subject=email.subject, body=visible(body))
                    if len(candidate.body.split()) >= 3:
                        preprocess(candidate.text)
                        email, fallback = candidate, True
                except (UnicodeError, LookupError, ValidationError, BaselineError):
                    pass  # Keep the valid original; never invent unavailable content.
    try:
        email, markup = clean_text(email)
    except AuditError:
        markup = False  # Preserve valid original text if a repair would erase it.
    return email, {
        **original_flags,
        "placeholder_html_fallback": fallback,
        "html_in_plain_text": markup,
    }
