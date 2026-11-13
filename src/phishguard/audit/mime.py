"""Offline MIME-to-text extraction; never extract files, fetch links or render HTML."""

import mailbox
import re
import tarfile
from email import policy
from email.parser import BytesParser
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from langdetect import PROFILES_DIRECTORY, DetectorFactory, LangDetectException
from pydantic import ValidationError

from phishguard.audit.common import PROTOCOL, AuditError
from phishguard.baseline.common import BaselineError
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import EmailInput


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"head", "script", "style", "noscript"}:
            self.hidden.append(tag)
        elif not self.hidden and tag in {"p", "div", "br", "li", "tr", "td", "h1", "h2"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.hidden:
            self.hidden = self.hidden[: self.hidden.index(tag)]
        elif not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def extract(raw: bytes) -> tuple[EmailInput, dict]:
    if len(raw) > PROTOCOL["raw_message_bytes"]:
        raise AuditError("raw_message_too_large")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    subject = str(message.get("Subject", ""))
    if subject.upper().strip() in PROTOCOL["system_subjects"]:
        raise AuditError("mailbox_system_record")
    subject, flags = re.subn(r"^(?:\s*\[(?:spam|phishing)\]\s*)+", "", subject, flags=re.I)
    # EmailMessage.get_body respects multipart/alternative and inline disposition.
    part = message.get_body(preferencelist=("plain", "html"))
    if part is None or part.get_filename() or part.get_content_maintype() != "text":
        raise AuditError("no_inline_text")
    data = part.get_payload(decode=True)
    if not isinstance(data, bytes):
        raise AuditError("invalid_text_payload")
    charset = part.get_content_charset() or "utf-8"
    fallback = False
    try:
        body = data.decode(charset, errors="strict")
    except (UnicodeError, LookupError):
        body = data.decode("utf-8", errors="replace")
        fallback = True
    if "\ufffd" in body + subject:
        raise AuditError("undecodable_text")
    html = part.get_content_type() == "text/html"
    if html:
        parser = VisibleText()
        parser.feed(body)
        parser.close()
        body = " ".join("".join(parser.parts).split())
    try:
        email = EmailInput(subject=subject, body=body)
        preprocess(email.text)
    except (ValidationError, BaselineError):
        raise AuditError("invalid_or_overlong_email") from None
    return email, {
        "html_body": html,
        "charset_fallback": fallback,
        "subject_flag_removed": bool(flags),
    }


@lru_cache(maxsize=1)
def language_factory():
    factory = DetectorFactory()
    factory.load_profile(PROFILES_DIRECTORY)
    factory.seed = PROTOCOL["language"]["seed"]
    return factory


def english(email: EmailInput) -> bool:
    try:
        detector = language_factory().create()
        detector.append(email.text)
        candidates = detector.get_probabilities()
    except LangDetectException:
        return False
    return bool(
        candidates
        and candidates[0].lang == "en"
        and candidates[0].prob >= PROTOCOL["language"]["minimum_probability"]
    )


def messages(path: Path, kind: str):
    """Yield stable row indexes and bounded raw bytes without materializing attachments."""
    limit = PROTOCOL["raw_message_bytes"]
    if kind == "mbox":
        box = mailbox.mbox(path, create=False)
        try:
            for index, key in enumerate(box.iterkeys()):
                if index >= PROTOCOL["max_archive_members"]:
                    raise AuditError("archive_member_limit")
                with box.get_file(key) as stream:
                    yield index, stream.read(limit + 1)
        finally:
            box.close()
    elif kind == "tar-bz2":
        expanded = 0
        with tarfile.open(path, mode="r|bz2") as archive:
            for index, member in enumerate(archive):
                expanded += member.size
                if (
                    index >= PROTOCOL["max_archive_members"]
                    or expanded > PROTOCOL["archive_expanded_bytes"]
                ):
                    raise AuditError("archive_expansion_limit")
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts or member.issym() or member.islnk():
                    raise AuditError("unsafe_archive_member")
                if not member.isfile() or not re.fullmatch(r"\d+\.[0-9a-f]{32}", name.name):
                    continue
                with archive.extractfile(member) as stream:
                    yield index, stream.read(limit + 1)
    else:
        raise AuditError("unsupported_archive")
