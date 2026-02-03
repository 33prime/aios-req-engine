"""Content sanitization for emails and transcripts.

Strips PII, signatures, and forwarded chains before signal ingestion.
All sanitization happens in memory — raw content never hits the database.
"""

import re

# Phone number patterns (US, international)
_PHONE_PATTERNS = [
    r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",  # US formats
    r"\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}",  # International
]
_PHONE_RE = re.compile("|".join(_PHONE_PATTERNS))

# SSN pattern
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Credit card pattern (basic)
_CC_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

# Email signature delimiters
_SIGNATURE_DELIMITERS = [
    r"^-- $",  # Standard sig delimiter
    r"^—$",
    r"^_{3,}$",
    r"^-{3,}$",
    r"^Sent from my ",
    r"^Get Outlook for ",
    r"^Sent via ",
]
_SIGNATURE_RE = re.compile("|".join(_SIGNATURE_DELIMITERS), re.MULTILINE)

# Forwarded chain patterns
_FORWARD_PATTERNS = [
    r"^>+\s?",  # Quoted lines
    r"^On .+ wrote:$",  # "On ... wrote:" header
    r"^-{2,}\s*Forwarded message\s*-{2,}$",
    r"^From:\s+.+$",  # Forwarded header block
    r"^Date:\s+.+$",
    r"^Subject:\s+.+$",
    r"^To:\s+.+$",
]
_FORWARD_HEADER_RE = re.compile(
    r"^On .+ wrote:$|^-{2,}\s*Forwarded message\s*-{2,}$",
    re.MULTILINE,
)


def _redact_pii(text: str) -> str:
    """Replace phone numbers, SSNs, and credit cards with placeholders."""
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _SSN_RE.sub("[SSN]", text)
    text = _CC_RE.sub("[CARD]", text)
    return text


def _strip_signature(text: str) -> str:
    """Remove email signature block (everything after the delimiter)."""
    match = _SIGNATURE_RE.search(text)
    if match:
        return text[: match.start()].rstrip()
    return text


def _strip_forwarded_chains(text: str) -> str:
    """Remove forwarded/quoted content from email body."""
    match = _FORWARD_HEADER_RE.search(text)
    if match:
        return text[: match.start()].rstrip()

    # Also strip consecutive quoted lines (> prefix)
    lines = text.split("\n")
    result_lines = []
    consecutive_quoted = 0
    for line in lines:
        if line.startswith(">"):
            consecutive_quoted += 1
            if consecutive_quoted <= 2:
                # Keep first couple of quoted lines for context
                result_lines.append(line)
        else:
            consecutive_quoted = 0
            result_lines.append(line)

    return "\n".join(result_lines)


def sanitize_email_body(
    body: str,
    strip_signatures: bool = True,
    strip_forwards: bool = True,
    redact_pii: bool = True,
) -> str:
    """
    Sanitize email body before ingestion as a signal.

    Processing order:
    1. Strip forwarded chains (remove quoted/forwarded content)
    2. Strip signature block (after -- or common delimiters)
    3. Redact PII (phone numbers, SSNs, credit cards)
    4. Normalize whitespace

    Args:
        body: Raw email body text
        strip_signatures: Remove email signature blocks
        strip_forwards: Remove forwarded/quoted content
        redact_pii: Replace phone numbers, SSNs, etc.

    Returns:
        Sanitized text safe for signal storage
    """
    if not body:
        return ""

    text = body.strip()

    if strip_forwards:
        text = _strip_forwarded_chains(text)

    if strip_signatures:
        text = _strip_signature(text)

    if redact_pii:
        text = _redact_pii(text)

    # Normalize whitespace: collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def sanitize_transcript(text: str, redact_pii: bool = True) -> str:
    """
    Sanitize meeting transcript before ingestion as a signal.

    Lighter touch than email — just PII redaction and whitespace normalization.

    Args:
        text: Raw transcript text
        redact_pii: Replace phone numbers, SSNs, etc.

    Returns:
        Sanitized transcript text
    """
    if not text:
        return ""

    result = text.strip()

    if redact_pii:
        result = _redact_pii(result)

    # Normalize whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()
