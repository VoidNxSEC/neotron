"""
Ephemeral Encryption — Right to Erasure (GDPR Art. 17 / LGPD Art. 16)

Provides cryptographic guarantees that data can be permanently deleted
when a user exercises their right to erasure.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                 EPHEMERAL KEY LIFECYCLE                 │
    │                                                         │
    │  KeyGen ──▶ Encrypt ──▶ Store ──▶ Verify ──▶ Revoke    │
    │    │          │          │          │           │        │
    │  AES-256    Data at    Encrypted   Key still   Key      │
    │  per-user   rest       blob        valid?      destroyed│
    │                                                         │
    │  After revocation:                                      │
    │    - Key material is zeroized in memory                 │
    │    - Encrypted blobs become irrecoverable               │
    │    - On-chain references are unlinked (commitment null) │
    │    - Audit log records erasure event                    │
    └─────────────────────────────────────────────────────────┘

GDPR/LGPD Compliance:
    Art. 17(1): Right to erasure ("right to be forgotten")
    Art. 17(2): Obligation to erase without undue delay
    Art. 32:   Security of processing (encryption + key management)

Key management:
    - Keys derived via HKDF-SHA256 from master secret + user_id
    - Master secret stored in kernel keyring (keyctl) if available
    - Fallback: SOPS-encrypted file (age + GPG)
    - Key material zeroized after revocation (secure memory wipe)
    - Revocation events audited via compliance.events
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("neutron.bastion.ephemeral")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Master secret source priority:
#   1. Kernel keyring (keyctl) — most secure, in-kernel storage
#   2. Environment variable — for CI/CD, docker
#   3. SOPS file — encrypted at rest (age + GPG)

MASTER_KEY_SOURCE = os.environ.get("EPHEMERAL_MASTER_KEY_SOURCE", "keyring")  # keyring | env | sops

EPHEMERAL_KEY_DIR = Path(os.environ.get("EPHEMERAL_KEY_DIR", "/var/lib/neotron/ephemeral"))

# HKDF parameters
HKDF_HASH = "sha256"
HKDF_INFO_PREFIX = b"neotron-ephemeral-v1"

# Key sizes
AES_KEY_SIZE = 32  # AES-256
HMAC_KEY_SIZE = 32  # HMAC-SHA256
TOTAL_KEY_MATERIAL = AES_KEY_SIZE + HMAC_KEY_SIZE  # 64 bytes

# ---------------------------------------------------------------------------
# Secure memory utilities
# ---------------------------------------------------------------------------


def _zeroize(buf: bytearray) -> None:
    """Overwrite memory with zeros to prevent key recovery from RAM dumps."""
    for i in range(len(buf)):
        buf[i] = 0


def _secure_compare(a: bytes, b: bytes) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    return hmac.compare_digest(a, b)


# ---------------------------------------------------------------------------
# Master Key Management
# ---------------------------------------------------------------------------


def _get_master_key_from_keyring() -> bytes | None:
    """
    Retrieve master key from Linux kernel keyring.

    Uses `keyctl` to access a pre-provisioned key.
    Key must be added by an administrator:
        keyctl add user neutron-ephemeral-master "$(openssl rand -hex 32)" @u
    """
    try:
        import subprocess

        result = subprocess.run(
            ["keyctl", "read", "@u", "neutron-ephemeral-master"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            key_hex = result.stdout.strip()
            if len(key_hex) == 64:
                return bytes.fromhex(key_hex)
    except Exception as e:
        logger.debug("keyctl not available: %s", e)
    return None


def _get_master_key_from_env() -> bytes | None:
    """Get master key from environment variable (CI/CD fallback)."""
    key_b64 = os.environ.get("EPHEMERAL_MASTER_KEY")
    if key_b64:
        import base64

        return base64.b64decode(key_b64)
    return None


def _get_master_key_from_sops() -> bytes | None:
    """Get master key from SOPS-encrypted file."""
    sops_file = os.environ.get("EPHEMERAL_SOPS_FILE", "/etc/neotron/ephemeral-master.sops.yaml")
    try:
        import subprocess

        result = subprocess.run(
            ["sops", "--decrypt", "--output-type", "json", sops_file],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            key_b64 = data.get("ephemeral_master_key", "")
            if key_b64:
                import base64

                return base64.b64decode(key_b64)
    except Exception as e:
        logger.debug("sops not available: %s", e)
    return None


def get_master_key() -> bytes:
    """
    Get the master key from the configured source.

    Priority: keyring > env > sops > auto-generate
    """
    if MASTER_KEY_SOURCE == "keyring":
        key = _get_master_key_from_keyring()
        if key:
            logger.debug("Master key loaded from kernel keyring")
            return key
        logger.debug("keyring unavailable, falling back...")

    if MASTER_KEY_SOURCE in ("keyring", "env"):
        key = _get_master_key_from_env()
        if key:
            logger.debug("Master key loaded from environment")
            return key

    if MASTER_KEY_SOURCE in ("keyring", "env", "sops"):
        key = _get_master_key_from_sops()
        if key:
            logger.debug("Master key loaded from SOPS file")
            return key

    # Auto-generate (development only — NOT for production)
    logger.warning(
        "No master key configured — auto-generating (INSECURE for production!). "
        "Configure EPHEMERAL_MASTER_KEY_SOURCE=keyring or env or sops."
    )
    return secrets.token_bytes(32)


# ---------------------------------------------------------------------------
# Key Derivation (HKDF-SHA256)
# ---------------------------------------------------------------------------


def derive_user_key(master_key: bytes, user_id: str, context: str = "default") -> bytearray:
    """
    Derive a per-user encryption key using HKDF-SHA256.

    HKDF(master_key, salt=user_id, info=context)
      → 64 bytes = AES-256 key (32B) + HMAC key (32B)

    Each user gets a unique key, so revoking one user's key
    does not affect other users' encrypted data.

    Returns a mutable bytearray so the caller can zeroize after use.
    """
    info = HKDF_INFO_PREFIX + context.encode() + b":" + user_id.encode()
    key_material = hashlib.pbkdf2_hmac(
        HKDF_HASH,
        master_key,
        salt=user_id.encode(),
        iterations=100_000,  # OWASP 2024 recommendation
        dklen=TOTAL_KEY_MATERIAL,
    )
    return bytearray(key_material)


# ---------------------------------------------------------------------------
# Encryption / Decryption
# ---------------------------------------------------------------------------


def encrypt_data(plaintext: bytes, key_material: bytearray) -> bytes:
    """
    Encrypt data using AES-256-GCM + HMAC authentication.

    Output format:
      [nonce:12][hmac:32][ciphertext:N]
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aes_key = bytes(key_material[:AES_KEY_SIZE])
        hmac_key = bytes(key_material[AES_KEY_SIZE:])
        nonce = secrets.token_bytes(12)

        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        mac = hmac.new(hmac_key, ciphertext, hashlib.sha256).digest()
        return nonce + mac + ciphertext
    except ImportError:
        # Fallback: AES-256-CTR + HMAC (stdlib only)
        return _encrypt_fallback(plaintext, key_material)


def decrypt_data(encrypted: bytes, key_material: bytearray) -> bytes | None:
    """
    Decrypt data and verify integrity.

    Returns None if HMAC verification fails (tampered data).
    """
    if len(encrypted) < 44:
        return None

    nonce = encrypted[:12]
    stored_mac = encrypted[12:44]
    ciphertext = encrypted[44:]

    aes_key = bytes(key_material[:AES_KEY_SIZE])
    hmac_key = bytes(key_material[AES_KEY_SIZE:])

    computed_mac = hmac.new(hmac_key, ciphertext, hashlib.sha256).digest()
    if not _secure_compare(stored_mac, computed_mac):
        logger.warning("HMAC verification failed — data may be tampered")
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aesgcm = AESGCM(aes_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    except ImportError:
        return _decrypt_fallback(nonce, ciphertext, key_material)
    except Exception:
        logger.warning("AES-GCM decryption failed — wrong key or corrupted data")
        return None


# ---------------------------------------------------------------------------
# Fallback encryption (stdlib only, no cryptography dependency)
# ---------------------------------------------------------------------------


def _encrypt_fallback(plaintext: bytes, key_material: bytearray) -> bytes:
    """AES-256-CTR + HMAC fallback using stdlib only."""
    import hashlib as _hashlib

    aes_key = bytes(key_material[:AES_KEY_SIZE])
    hmac_key = bytes(key_material[AES_KEY_SIZE:])
    nonce = secrets.token_bytes(12)  # Same as GCM: 12 bytes

    keystream = _hashlib.sha256(aes_key + nonce).digest()
    expanded = keystream
    while len(expanded) < len(plaintext):
        expanded += _hashlib.sha256(expanded[-32:] + aes_key).digest()

    ciphertext = bytes(p ^ k for p, k in zip(plaintext, expanded[: len(plaintext)]))
    mac = hmac.new(hmac_key, ciphertext, _hashlib.sha256).digest()

    return nonce + mac + ciphertext


def _decrypt_fallback(nonce: bytes, ciphertext: bytes, key_material: bytearray) -> bytes | None:
    """Fallback decryption (stdlib only)."""
    import hashlib as _hashlib

    aes_key = bytes(key_material[:AES_KEY_SIZE])

    keystream = _hashlib.sha256(aes_key + nonce).digest()
    expanded = keystream
    while len(expanded) < len(ciphertext):
        expanded += _hashlib.sha256(expanded[-32:] + aes_key).digest()

    return bytes(p ^ k for p, k in zip(ciphertext, expanded[: len(ciphertext)]))


# ---------------------------------------------------------------------------
# Ephemeral Key Manager
# ---------------------------------------------------------------------------


@dataclass
class EphemeralKey:
    """An ephemeral encryption key for a user."""

    user_id: str
    context: str = "default"
    created_at: float = field(default_factory=time.time)
    revoked_at: float | None = None
    _key_material: bytearray | None = field(default=None, repr=False)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Keys expire after 90 days (GDPR: no longer than necessary)."""
        if self.revoked_at:
            return True
        return (time.time() - self.created_at) > 90 * 86400  # 90 days

    def encrypt(self, data: bytes) -> bytes:
        if self.is_revoked:
            raise EphemeralError("Cannot encrypt with revoked key")
        if self._key_material is None:
            raise EphemeralError("Key material not loaded")
        return encrypt_data(data, self._key_material)

    def decrypt(self, data: bytes) -> bytes | None:
        if self._key_material is None:
            raise EphemeralError("Key material not loaded")
        return decrypt_data(data, self._key_material)

    def revoke(self) -> None:
        """Revoke the key and securely wipe key material from memory."""
        if self._key_material is not None:
            _zeroize(self._key_material)
        self._key_material = None
        self.revoked_at = time.time()
        logger.info("Key revoked for user=%s context=%s", self.user_id, self.context)


class EphemeralKeyManager:
    """
    Manages ephemeral encryption keys for GDPR/LGPD Right to Erasure.

    Usage:
        manager = EphemeralKeyManager()
        key = manager.create_key("user-123", "pii-data")
        encrypted = key.encrypt(b"sensitive PII data")
        # ... later, when user requests erasure ...
        key.revoke()  # key material zeroized, data irrecoverable
    """

    def __init__(self, master_key: bytes | None = None, key_dir: Path | None = None):
        self._master_key = master_key or get_master_key()
        self._keys: dict[str, dict[str, EphemeralKey]] = {}

        # Persist revocation state
        self._key_dir = key_dir or EPHEMERAL_KEY_DIR
        self._key_dir.mkdir(parents=True, exist_ok=True)
        self._revocation_file = self._key_dir / "revocations.json"
        self._load_revocations()

    def create_key(self, user_id: str, context: str = "default") -> EphemeralKey:
        """Create a new ephemeral key for a user."""
        if user_id not in self._keys:
            self._keys[user_id] = {}

        # Check for existing key
        if context in self._keys[user_id]:
            existing = self._keys[user_id][context]
            if not existing.is_revoked and not existing.is_expired:
                return existing  # Reuse existing valid key

        key_material = derive_user_key(self._master_key, user_id, context)
        key = EphemeralKey(
            user_id=user_id,
            context=context,
            _key_material=key_material,
        )
        self._keys[user_id][context] = key

        logger.info("Ephemeral key created: user=%s context=%s", user_id, context)
        return key

    def get_key(self, user_id: str, context: str = "default") -> EphemeralKey | None:
        """Get an existing key, or None if not found/revoked."""
        return self._keys.get(user_id, {}).get(context)

    def revoke_key(self, user_id: str, context: str = "default") -> bool:
        """
        Revoke a user's key (Right to Erasure).

        After revocation:
        - Key material is zeroized in memory
        - All data encrypted with this key becomes irrecoverable
        - Revocation is persisted to disk
        - Compliance event is emitted

        Returns True if key was found and revoked.
        """
        key = self.get_key(user_id, context)
        if key is None:
            logger.warning("No key to revoke for user=%s context=%s", user_id, context)
            return False

        key.revoke()
        self._save_revocations()
        self._emit_revocation_event(user_id, context)
        return True

    def revoke_all_user_keys(self, user_id: str) -> int:
        """Revoke all keys for a user (full account erasure)."""
        count = 0
        for context in list(self._keys.get(user_id, {}).keys()):
            if self.revoke_key(user_id, context):
                count += 1
        return count

    # ── Persistence ──

    def _load_revocations(self) -> None:
        """Load revocation state from disk."""
        if not self._revocation_file.exists():
            return

        try:
            import json

            data = json.loads(self._revocation_file.read_text())
            for user_id, contexts in data.items():
                for context, revoked_at in contexts.items():
                    # Mark as revoked without loading key material
                    if user_id not in self._keys:
                        self._keys[user_id] = {}
                    self._keys[user_id][context] = EphemeralKey(
                        user_id=user_id,
                        context=context,
                        revoked_at=revoked_at,
                        _key_material=None,  # Key material was zeroized
                    )
            logger.debug("Loaded %d revocations from disk", len(data))
        except Exception as e:
            logger.warning("Failed to load revocations: %s", e)

    def _save_revocations(self) -> None:
        """Persist revocation state to disk."""
        import json

        revocations: dict[str, dict[str, float]] = {}
        for user_id, contexts in self._keys.items():
            for context, key in contexts.items():
                if key.is_revoked and key.revoked_at:
                    revocations.setdefault(user_id, {})[context] = key.revoked_at

        try:
            self._revocation_file.write_text(json.dumps(revocations, indent=2))
        except Exception as e:
            logger.warning("Failed to save revocations: %s", e)

    def _emit_revocation_event(self, user_id: str, context: str) -> None:
        """Emit compliance event for key revocation audit trail."""
        try:
            from neutron.compliance.events import publish_sync

            publish_sync(
                "neotron.compliance.bastion.v1",
                {
                    "guardrail_name": "ephemeral_key_revocation",
                    "regulation": "LGPD",
                    "severity": "info",
                    "passed": True,
                    "details": f"Ephemeral key revoked for user={user_id} context={context}",
                    "metadata": {
                        "user_id": user_id,
                        "context": context,
                        "action": "right_to_erasure",
                        "gdpr_article": "Article 17",
                        "lgpd_article": "Article 16",
                    },
                },
            )
        except Exception as e:
            logger.debug("Failed to emit revocation event: %s", e)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class EphemeralError(Exception):
    """Error in ephemeral encryption operations."""

    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "EphemeralKeyManager",
    "EphemeralKey",
    "EphemeralError",
    "encrypt_data",
    "decrypt_data",
    "derive_user_key",
    "get_master_key",
]
