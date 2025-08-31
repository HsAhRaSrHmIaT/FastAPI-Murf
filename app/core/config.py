"""Configuration settings and environment variables

This module now supports optional encryption of user-provided API keys using a
single MASTER_KEY (Fernet). When `MASTER_KEY` is present in the environment
values written to `user_keys.json` will be encrypted; when absent we fall back
to plaintext so local development / localhost works without extra setup.
"""

import os
import json
from typing import Optional, Dict, Any, TYPE_CHECKING
from pydantic_settings import BaseSettings
from pydantic import Field

try:
    from cryptography.fernet import Fernet, InvalidToken
    _CRYPTO_AVAILABLE = True
except Exception:
    # cryptography is optional for local/dev runs. If it's missing, we will
    # gracefully fall back to plaintext storage but warn when attempting to
    # use encryption in production.
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore
    _CRYPTO_AVAILABLE = False


USER_KEYS_FILE = "user_keys.json"
MASTER_KEY_ENV = "MASTER_KEY"

# Warn if a master key exists but cryptography isn't installed
if os.getenv(MASTER_KEY_ENV) and not _CRYPTO_AVAILABLE:
    print(
        "WARNING: MASTER_KEY is set but 'cryptography' is not available; "
        "encryption will be disabled. Install 'cryptography' or unset MASTER_KEY."
    )


def _get_master_key() -> Optional[bytes]:
    v = os.getenv(MASTER_KEY_ENV)
    return v.encode() if v else None


if TYPE_CHECKING:
    from cryptography.fernet import Fernet  # pragma: no cover

def has_master_key() -> bool:
    """Return True when a MASTER_KEY is configured in the environment."""
    # Require both the env var and the cryptography library to be present so
    # that the application can actually encrypt/decrypt stored values.
    return bool(_get_master_key()) and _CRYPTO_AVAILABLE


def _get_fernet() -> Optional["Fernet"]: #type: ignore
    key = _get_master_key()
    if not key:
        return None
    if not _CRYPTO_AVAILABLE:
        # cryptography isn't available; cannot create a Fernet instance
        return None
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    if not f:
        # No master key configured: return plaintext to preserve existing behavior
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext_or_plain: str) -> str:
    f = _get_fernet()
    if not f:
        # No master key configured: assume values are plaintext
        return ciphertext_or_plain
    try:
        return f.decrypt(ciphertext_or_plain.encode()).decode()
    except (InvalidToken, ValueError):
        # Not encrypted or wrong key: return input as-is
        return ciphertext_or_plain


def load_user_keys() -> Dict[str, Any]:
    """Load user keys from JSON file, decrypting values when possible."""
    if os.path.exists(USER_KEYS_FILE):
        try:
            with open(USER_KEYS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"Error loading user keys: {e}")
            return {}
        # Decrypt only values (assumes mapping of key->value)
        decrypted: Dict[str, Any] = {}
        for k, v in raw.items():
            if isinstance(v, str):
                decrypted[k] = decrypt_value(v)
            else:
                decrypted[k] = v
        return decrypted
    return {}


def save_user_keys(user_keys: Dict[str, Any]):
    """Save user keys to JSON file, encrypting values when possible."""
    try:
        to_save: Dict[str, Any] = {}
        for k, v in user_keys.items():
            if isinstance(v, str):
                to_save[k] = encrypt_value(v)
            else:
                to_save[k] = v
        with open(USER_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"Error saving user keys: {e}")


def get_api_key_from_sources(env_var: str, json_key: str) -> Optional[str]:
    """Get API key from environment variable first, then from user_keys.json"""
    # Try environment variable first
    env_value = os.getenv(env_var)
    if env_value:
        return env_value
    return None


def get_api_key_from_env(env_var: str) -> Optional[str]:
    """Get API key from environment variable only."""
    return os.getenv(env_var)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and user keys"""

    # API Keys - now handled per-user via headers, no env fallback needed
    # These fields are kept for backward compatibility but not loaded from env

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Note: API keys are now loaded automatically by Pydantic BaseSettings from .env file
        # Manual loading removed to allow proper .env file support


# Global settings instance
settings = Settings()



# --- Per-request API key extraction ---
from fastapi import Request, WebSocket

def get_api_keys_from_request(request: Request = None, websocket: WebSocket = None) -> dict:
    """
    Extract API keys from headers (REST or WebSocket). Fallback to env if not present.
    Returns a dict: { 'assemblyai_api_key': ..., 'google_api_key': ..., 'murf_api_key': ... }
    """
    headers = None
    if request is not None:
        headers = request.headers
    elif websocket is not None:
        headers = websocket.headers
    else:
        headers = {}

    def get_key(header_name, env_var):
        # Custom header, e.g. x-assemblyai-api-key
        value = headers.get(header_name, None)
        if value and value.strip():  # Only return non-empty values
            return value
        return None  # No fallback to environment variables

    return {
        'assemblyai_api_key': get_key('x-assemblyai-api-key', 'ASSEMBLYAI_API_KEY'),
        'google_api_key': get_key('x-google-api-key', 'GOOGLE_API_KEY'),
        'murf_api_key': get_key('x-murf-api-key', 'MURF_API_KEY'),
    }

