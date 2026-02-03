"""Server-side Google OAuth token management.

Handles encryption/decryption of refresh tokens and token exchange
for Calendar API access.
"""

import base64
import hashlib
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


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
