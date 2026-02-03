"""Server-side Google OAuth token management.

Handles encryption/decryption of refresh tokens, token exchange,
and Gmail API send (on behalf of authenticated user).
"""

import base64
import hashlib
import logging
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _get_encryption_key() -> bytes:
    """Get or derive 32-byte AES key from config."""
    settings = get_settings()
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        raise ValueError("TOKEN_ENCRYPTION_KEY not configured")
    # Derive a consistent 32-byte key via SHA-256
    return hashlib.sha256(key.encode()).digest()


def encrypt_refresh_token(token: str) -> str:
    """
    Encrypt a refresh token for storage.

    Uses Fernet-style encryption (AES-CBC with HMAC) via the cryptography
    library if available, falling back to XOR + base64 for simplicity.
    In production, use a proper KMS or Vault.
    """
    key = _get_encryption_key()
    try:
        from cryptography.fernet import Fernet

        # Derive a Fernet key from our raw key
        fernet_key = base64.urlsafe_b64encode(key)
        f = Fernet(fernet_key)
        return f.encrypt(token.encode()).decode()
    except ImportError:
        # Fallback: XOR with key + base64 (NOT production-grade)
        logger.warning("cryptography package not installed; using basic encoding")
        token_bytes = token.encode()
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(token_bytes))
        return base64.urlsafe_b64encode(xored).decode()


def decrypt_refresh_token(encrypted: str) -> str:
    """Decrypt a stored refresh token."""
    key = _get_encryption_key()
    try:
        from cryptography.fernet import Fernet

        fernet_key = base64.urlsafe_b64encode(key)
        f = Fernet(fernet_key)
        return f.decrypt(encrypted.encode()).decode()
    except ImportError:
        decoded = base64.urlsafe_b64decode(encrypted.encode())
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(decoded))
        return xored.decode()


async def exchange_refresh_for_access(encrypted_refresh_token: str) -> str:
    """
    Exchange an encrypted refresh token for a fresh Google access token.

    Args:
        encrypted_refresh_token: Encrypted refresh token from DB

    Returns:
        Valid Google access token

    Raises:
        ValueError: If Google OAuth is not configured
        httpx.HTTPStatusError: If token exchange fails
    """
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth not configured")

    refresh_token = decrypt_refresh_token(encrypted_refresh_token)

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()

        return data["access_token"]


async def send_gmail(
    access_token: str,
    from_email: str,
    to_emails: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict:
    """
    Send email via Gmail API on behalf of the authenticated user.

    Args:
        access_token: Valid Google access token with gmail.send scope
        from_email: The authenticated user's email address
        to_emails: List of recipient email addresses
        subject: Email subject
        html_body: HTML body content
        text_body: Optional plain text fallback

    Returns:
        Dict with message_id and status
    """
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    if text_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(html_body, subtype="html")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            GMAIL_SEND_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
        )
        response.raise_for_status()

        data = response.json()
        message_id = data.get("id", "")
        logger.info(
            f"Gmail sent from {from_email} to {len(to_emails)} recipients, "
            f"subject='{subject}', id={message_id}"
        )

        return {"message_id": message_id, "status": "sent"}
