"""Tests for content sanitizer."""


from app.core.content_sanitizer import sanitize_email_body, sanitize_transcript


class TestSanitizeEmailBody:
    """Tests for email body sanitization."""

    def test_strips_phone_numbers(self):
        body = "Call me at 555-123-4567 or +1 (800) 555-0199"
        result = sanitize_email_body(body)
        assert "555-123-4567" not in result
        assert "800" not in result
        assert "[PHONE]" in result

    def test_strips_ssn(self):
        body = "My SSN is 123-45-6789"
        result = sanitize_email_body(body)
        assert "123-45-6789" not in result
        assert "[SSN]" in result

    def test_strips_credit_card(self):
        body = "Card number: 4111 1111 1111 1111"
        result = sanitize_email_body(body)
        assert "4111" not in result
        assert "[CARD]" in result

    def test_strips_email_signature(self):
        body = "Here are the requirements.\n\n-- \nJohn Doe\nVP Engineering\n555-555-5555"
        result = sanitize_email_body(body)
        assert "Here are the requirements." in result
        assert "John Doe" not in result
        assert "VP Engineering" not in result

    def test_strips_sent_from_signature(self):
        body = "The feature should work like X.\n\nSent from my iPhone"
        result = sanitize_email_body(body)
        assert "The feature should work like X." in result
        assert "Sent from my iPhone" not in result

    def test_strips_forwarded_chains(self):
        body = (
            "I agree with this approach.\n\n"
            "On Mon, Jan 5, 2026 at 3:00 PM John wrote:\n"
            "> Original message content\n"
            "> More quoted text"
        )
        result = sanitize_email_body(body)
        assert "I agree with this approach." in result
        assert "John wrote:" not in result

    def test_empty_body_returns_empty(self):
        assert sanitize_email_body("") == ""
        assert sanitize_email_body("   ") == ""

    def test_preserves_normal_content(self):
        body = "We need a dashboard with real-time analytics for our sales team."
        result = sanitize_email_body(body)
        assert result == body

    def test_normalizes_whitespace(self):
        body = "Paragraph one.\n\n\n\n\nParagraph two."
        result = sanitize_email_body(body)
        assert "\n\n\n" not in result
        assert "Paragraph one.\n\nParagraph two." == result

    def test_no_pii_redaction_when_disabled(self):
        body = "Call me at 555-123-4567"
        result = sanitize_email_body(body, redact_pii=False)
        assert "555-123-4567" in result
        assert "[PHONE]" not in result

    def test_no_signature_strip_when_disabled(self):
        body = "Content\n\n-- \nSignature"
        result = sanitize_email_body(body, strip_signatures=False)
        assert "Signature" in result

    def test_international_phone(self):
        body = "Reach me at +44 20 7946 0958"
        result = sanitize_email_body(body)
        assert "+44" not in result
        assert "[PHONE]" in result


class TestSanitizeTranscript:
    """Tests for transcript sanitization."""

    def test_strips_phone_numbers(self):
        text = "Speaker 1: You can reach me at 555-123-4567"
        result = sanitize_transcript(text)
        assert "555-123-4567" not in result
        assert "[PHONE]" in result

    def test_strips_ssn(self):
        text = "Speaker 2: My SSN is 123-45-6789"
        result = sanitize_transcript(text)
        assert "123-45-6789" not in result
        assert "[SSN]" in result

    def test_preserves_normal_transcript(self):
        text = "Speaker 1: We need the login feature by Q2.\nSpeaker 2: I agree."
        result = sanitize_transcript(text)
        assert result == text

    def test_empty_transcript(self):
        assert sanitize_transcript("") == ""

    def test_normalizes_whitespace(self):
        text = "Line one.\n\n\n\n\nLine two."
        result = sanitize_transcript(text)
        assert "\n\n\n" not in result
