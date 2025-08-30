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

    # Try user keys JSON as fallback
    user_keys = load_user_keys()
    return user_keys.get(json_key)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and user keys"""

    # API Keys with fallback to user_keys.json
    assemblyai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    murf_api_key: Optional[str] = None
    ws_murf_api_url: Optional[str] = None

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load API keys with fallback mechanism
        self.assemblyai_api_key = get_api_key_from_sources(
            "ASSEMBLYAI_API_KEY", "assemblyai_api_key"
        )
        self.google_api_key = get_api_key_from_sources(
            "GOOGLE_API_KEY", "google_api_key"
        )
        self.murf_api_key = get_api_key_from_sources(
            "MURF_API_KEY", "murf_api_key"
        )
        self.ws_murf_api_url = get_api_key_from_sources(
            "WS_MURF_API_URL", "ws_murf_api_url"
        )


# Global settings instance
settings = Settings()


def get_api_key(key_name: str) -> Optional[str]:
    """Get the API key for a specific service"""
    return getattr(settings, key_name, None)


# Utility functions for managing user keys
def update_user_key(key_name: str, key_value: str):
    """Update a specific user key in the JSON file"""
    user_keys = load_user_keys()
    user_keys[key_name] = key_value
    save_user_keys(user_keys)
    # Reload settings to pick up the new key
    global settings
    settings = Settings()


def get_all_user_keys() -> Dict[str, Any]:
    """Get all user keys from JSON file"""
    return load_user_keys()


def list_available_keys():
    """List which keys are available from which sources"""
    user_keys = load_user_keys()
    return {
        "assemblyai_api_key": {
            "env_available": bool(os.getenv("ASSEMBLYAI_API_KEY")),
            "user_available": "assemblyai_api_key" in user_keys,
            "current_value": bool(settings.assemblyai_api_key),
        },
        "google_api_key": {
            "env_available": bool(os.getenv("GOOGLE_API_KEY")),
            "user_available": "google_api_key" in user_keys,
            "current_value": bool(settings.google_api_key),
        },
        "murf_api_key": {
            "env_available": bool(os.getenv("MURF_API_KEY")),
            "user_available": "murf_api_key" in user_keys,
            "current_value": bool(settings.murf_api_key),
        },
        "ws_murf_api_url": {
            "env_available": bool(os.getenv("WS_MURF_API_URL")),
            "user_available": "ws_murf_api_url" in user_keys,
            "current_value": bool(settings.ws_murf_api_url),
        },
    }
