"""
SOPS Secrets Connector for NEXUS platform.

Reads decrypted secrets from /run/secrets/ (sops-nix at boot)
with transparent fallback to environment variables.

Priority order:
  1. /run/secrets/<secret_name>   (sops-nix decrypted files)
  2. os.getenv(VAR_NAME)          (explicit env var override)
  3. default value                (provided by caller)

Usage:
    from neutron.core.sops import secret

    api_key = secret("anthropic_api_key")           # -> /run/secrets/anthropic_api_key
    api_key = secret("ANTHROPIC_API_KEY")           # same — normalized to lowercase
    api_key = secret("anthropic_api_key", "")       # with default
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("neutron.core.sops")

# sops-nix decrypts secrets here at boot time
_SECRETS_DIR = Path(os.getenv("SOPS_SECRETS_DIR", "/run/secrets"))


def _normalize(name: str) -> str:
    """Normalize secret name to lowercase for /run/secrets lookup."""
    return name.lower()


def _env_name(name: str) -> str:
    """Normalize secret name to UPPERCASE for env var lookup."""
    return name.upper()


def secret(name: str, default: str = "") -> str:
    """Read a secret from environment variable or SOPS (/run/secrets).

    Priority:
      1. Environment variable (set by flake devShell or explicit override)
      2. /run/secrets/<name> (sops-nix decrypted at boot)
      3. default

    Args:
        name:    Secret name (case-insensitive). E.g. "anthropic_api_key".
        default: Value to return if secret is not found anywhere.

    Returns:
        The secret value, or *default* if not found.
    """
    # 1. Try environment variable first (flake shellHook or explicit override)
    env_value = os.getenv(_env_name(name), "")
    if env_value:
        logger.debug("Loaded secret '%s' from environment", name)
        return env_value

    # 2. Try /run/secrets/<name> (sops-nix)
    secret_path = _SECRETS_DIR / _normalize(name)
    if secret_path.exists():
        try:
            value = secret_path.read_text().strip()
            if value:
                logger.debug("Loaded secret '%s' from %s", name, secret_path)
                return value
        except OSError as e:
            logger.warning("Cannot read secret file %s: %s", secret_path, e)

    # 3. Return default
    logger.debug(
        "Secret '%s' not found in env(%s) or %s",
        name, _env_name(name), _SECRETS_DIR,
    )
    return default


def secret_or_env(sops_name: str, env_name: str, default: str = "") -> str:
    """Read a secret where the SOPS name differs from the env var name.

    Args:
        sops_name: Filename under /run/secrets/ (lowercase).
        env_name:  Environment variable name (uppercase).
        default:   Fallback value.
    """
    secret_path = _SECRETS_DIR / sops_name.lower()

    if secret_path.exists():
        try:
            value = secret_path.read_text().strip()
            if value:
                return value
        except OSError as e:
            logger.warning("Cannot read %s: %s", secret_path, e)

    return os.getenv(env_name, default)


def secrets_available() -> bool:
    """Return True if the SOPS secrets directory is accessible."""
    return _SECRETS_DIR.is_dir()


def audit_secrets() -> dict[str, str]:
    """Return a dict of known secrets and their source (for health checks).

    Values are masked — only shows source, not the actual secret.
    """
    known = [
        "anthropic_api_key",
        "deepseek_api_key",
        "openai_api_key",
        "openrouter_api_key",
        "gemini_api_key",
        "replicate_api_key",
        "api_secret_key",
        "database_url",
    ]

    result: dict[str, str] = {}
    for name in known:
        path = _SECRETS_DIR / name
        if path.exists():
            try:
                val = path.read_text().strip()
                result[name] = "sops:/run/secrets" if val else "empty"
            except OSError:
                result[name] = "permission_denied"
        elif os.getenv(name.upper()):
            result[name] = "env_var"
        else:
            result[name] = "missing"

    return result
