"""
LGPD Kernel-Level Enforcement

Implements kernel-layer enforcement of LGPD (Lei Geral de Proteção de Dados)
using BASTION seccomp-BPF filters.

This provides defense-in-depth compliance where LGPD violations are not just
detected at the application layer (SENTINEL), but are physically impossible
at the kernel level (BASTION).

Architecture:
┌─────────────────────────────────────────────────────┐
│              LGPD Compliance Layers                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Application Layer (SENTINEL)                       │
│  ├── lgpd_art18_explanation_guardrail               │
│  ├── lgpd_art20_portability_guardrail               │
│  └── Business logic validation                      │
│                                                      │
│  Kernel Layer (BASTION) ← THIS MODULE               │
│  ├── lgpd_art7_consent_policy                       │
│  ├── lgpd_art16_data_access_policy                  │
│  └── Syscall-level enforcement                      │
│                                                      │
└─────────────────────────────────────────────────────┘

Key LGPD Articles with Kernel Enforcement:

Article 7 - Legal Bases for Processing
"Personal data processing is only permitted when the data subject provides
consent or one of the legal bases is met."

→ Kernel enforcement: Block file access to personal data without consent token

Article 16 - Data Subject Rights
"Data subjects have the right to request deletion of personal data."

→ Kernel enforcement: Prevent unauthorized data retention beyond legal period

Example:
    >>> from neutron.compliance.auditors.lgpd_kernel import (
    ...     lgpd_art7_consent_policy,
    ...     grant_lgpd_consent
    ... )
    >>>
    >>> # Without consent - file access blocked at kernel level
    >>> with lgpd_art7_consent_policy.enforce():
    ...     open("/data/pii/customer_123.json")  # → OSError: Permission denied
    >>>
    >>> # With consent - access allowed
    >>> grant_lgpd_consent("customer_123")
    >>> with lgpd_art7_consent_policy.enforce():
    ...     open("/data/pii/customer_123.json")  # → Success

Reference:
- LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
"""

from neutron.compliance.bastion import (
    KernelPolicy,
    ComplianceCapability,
    LayeredPolicy,
    grant_capability,
    revoke_capability,
    has_capability,
)

# Import application-layer guardrails from existing LGPD auditor
from neutron.compliance.auditors.lgpd import (
    lgpd_art18_explanation_guardrail,
    lgpd_art20_portability_guardrail,
)


# =============================================================================
# LGPD Article 7 - Consent Enforcement (Kernel Layer)
# =============================================================================

lgpd_art7_consent_policy = KernelPolicy(
    name="lgpd_art7_consent_enforcement",
    regulation="LGPD",
    blocked_syscalls=[
        "open",      # Block opening files
        "openat",    # Block opening files (modern interface)
        "read",      # Block reading data
        "readv",     # Block vectored reads
        "pread64",   # Block positioned reads
    ],
    required_capability=ComplianceCapability.CAP_CONSENT_TOKEN,
    action="ERRNO",
    errno=13,  # EACCES - Permission denied
    audit=True,
    description=(
        "LGPD Article 7 kernel enforcement: Blocks file access to personal "
        "data without valid consent token. This ensures compliance with "
        "LGPD's requirement that data processing only occurs with consent."
    ),
    metadata={
        "article": "LGPD Article 7",
        "article_title": "Bases Legais para o Tratamento",
        "protection": "Prevents unauthorized data access at syscall level",
        "severity": "BLOCKING",
    }
)

"""
LGPD Article 7 - Consent Kernel Policy

This policy enforces LGPD Article 7 at the kernel level by blocking syscalls
that could read personal data unless the process has a valid consent token.

Protected syscalls:
- open/openat: Block opening files containing personal data
- read/readv/pread64: Block reading data from open file descriptors

How it works:
1. Application requests access to personal data
2. BASTION checks for CAP_CONSENT_TOKEN capability
3. If no consent token → kernel returns EACCES (Permission denied)
4. If consent token present → access allowed
5. All attempts logged to audit trail

Usage:
    >>> # Grant consent for specific customer
    >>> grant_lgpd_consent("customer_123")
    >>>
    >>> # Access personal data under kernel enforcement
    >>> with lgpd_art7_consent_policy.enforce():
    ...     # File access requires consent token
    ...     data = read_customer_data("customer_123")
    >>>
    >>> # Revoke consent
    >>> revoke_lgpd_consent("customer_123")
"""


# =============================================================================
# LGPD Article 16 - Data Access Control (Kernel Layer)
# =============================================================================

lgpd_art16_data_access_policy = KernelPolicy(
    name="lgpd_art16_data_access_enforcement",
    regulation="LGPD",
    blocked_syscalls=[
        "unlink",      # Block file deletion
        "unlinkat",    # Block file deletion (modern interface)
        "rmdir",       # Block directory removal
        "rename",      # Block file renaming
        "renameat",    # Block file renaming (modern interface)
    ],
    required_capability=ComplianceCapability.CAP_PII_WRITE,
    action="ERRNO",
    errno=1,  # EPERM - Operation not permitted
    audit=True,
    description=(
        "LGPD Article 16 kernel enforcement: Blocks unauthorized deletion "
        "or modification of personal data. Ensures data subject rights to "
        "access and data portability are preserved."
    ),
    metadata={
        "article": "LGPD Article 16",
        "article_title": "Direitos do Titular",
        "protection": "Prevents unauthorized data modification/deletion",
        "severity": "BLOCKING",
    }
)

"""
LGPD Article 16 - Data Access Control Policy

This policy prevents unauthorized modification or deletion of personal data,
ensuring compliance with LGPD Article 16 (data subject rights).

Protected syscalls:
- unlink/unlinkat: Block deletion of files containing personal data
- rmdir: Block removal of directories with personal data
- rename/renameat: Block renaming (which could hide data)

This ensures:
1. Data subjects can exercise right to access (Art 18)
2. Data subjects can exercise right to portability (Art 20)
3. Controllers cannot delete data without proper authorization
4. Audit trail of all data modification attempts

Usage:
    >>> # Protect personal data directory
    >>> with lgpd_art16_data_access_policy.enforce():
    ...     # Unauthorized deletion attempts blocked
    ...     os.unlink("/data/pii/customer_123.json")  # → OSError: Operation not permitted
"""


# =============================================================================
# LGPD Article 46 - Data Retention Policy (Kernel Layer)
# =============================================================================

lgpd_art46_retention_policy = KernelPolicy(
    name="lgpd_art46_retention_enforcement",
    regulation="LGPD",
    blocked_syscalls=[
        "write",       # Block writing to retained files
        "writev",      # Block vectored writes
        "pwrite64",    # Block positioned writes
    ],
    required_capability=ComplianceCapability.CAP_PII_WRITE,
    action="ERRNO",
    errno=30,  # EROFS - Read-only file system
    audit=True,
    description=(
        "LGPD Article 46 kernel enforcement: Makes personal data immutable "
        "after retention period begins. Prevents unauthorized modification "
        "of data that must be preserved for legal/regulatory requirements."
    ),
    metadata={
        "article": "LGPD Article 46",
        "article_title": "Conservação de Dados Pessoais",
        "protection": "Enforces data immutability during retention",
        "severity": "WARNING",
    }
)

"""
LGPD Article 46 - Data Retention Policy

LGPD Article 46 requires controllers to eliminate personal data after the
purpose is fulfilled, except when retention is required by law or regulation.

This policy enforces immutability of retained data:
- Once data enters retention period, it cannot be modified
- Only authorized processes with CAP_PII_WRITE can modify
- All modification attempts logged to audit trail

Usage:
    >>> # Mark data for retention
    >>> with lgpd_art46_retention_policy.enforce():
    ...     # Data becomes immutable
    ...     modify_retained_data()  # → OSError: Read-only file system
"""


# =============================================================================
# Layered Enforcement (Application + Kernel)
# =============================================================================

lgpd_art18_layered = LayeredPolicy(
    name="lgpd_art18_full_enforcement",
    regulation="LGPD",
    application_check=lgpd_art18_explanation_guardrail,
    kernel_policy=lgpd_art7_consent_policy
)

"""
LGPD Article 18 - Layered Enforcement

Combines application-layer (SENTINEL) and kernel-layer (BASTION) enforcement:

Layer 1 (Application):
- Validates explanation is provided to data subject
- Checks business logic compliance

Layer 2 (Kernel):
- Blocks file access without consent token
- Physically prevents unauthorized data access

Usage:
    >>> with lgpd_art18_layered.enforce():
    ...     # Protected by both layers
    ...     result = process_personal_data(customer_id)
"""


lgpd_art20_layered = LayeredPolicy(
    name="lgpd_art20_full_enforcement",
    regulation="LGPD",
    application_check=lgpd_art20_portability_guardrail,
    kernel_policy=lgpd_art16_data_access_policy
)

"""
LGPD Article 20 - Layered Enforcement

Layer 1 (Application):
- Validates data portability interface is available
- Checks export format compliance

Layer 2 (Kernel):
- Prevents unauthorized deletion that would break portability
- Ensures data remains accessible for export

Usage:
    >>> with lgpd_art20_layered.enforce():
    ...     # Data export protected at both layers
    ...     export_data = customer.export_data()
"""


# =============================================================================
# Convenience Functions
# =============================================================================

def grant_lgpd_consent(customer_id: str) -> None:
    """
    Grant LGPD consent token for data processing

    This simulates the consent management system granting a consent
    token after the data subject provides explicit consent.

    Args:
        customer_id: Customer who granted consent

    Example:
        >>> grant_lgpd_consent("customer_123")
        >>> # Now can access customer_123's data
    """
    grant_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
    # In production, would also:
    # - Log consent grant to audit trail
    # - Store consent metadata (timestamp, scope, purpose)
    # - Associate with customer_id


def revoke_lgpd_consent(customer_id: str) -> None:
    """
    Revoke LGPD consent token

    This simulates the data subject withdrawing consent, which should
    immediately prevent further data processing.

    Args:
        customer_id: Customer who revoked consent

    Example:
        >>> revoke_lgpd_consent("customer_123")
        >>> # Access to customer_123's data now blocked
    """
    revoke_capability(ComplianceCapability.CAP_CONSENT_TOKEN)
    # In production, would also:
    # - Log consent revocation to audit trail
    # - Trigger data deletion if no other legal basis
    # - Notify downstream systems


def check_lgpd_consent(customer_id: str) -> bool:
    """
    Check if process has valid LGPD consent token

    Args:
        customer_id: Customer to check consent for

    Returns:
        True if consent token is valid, False otherwise

    Example:
        >>> if check_lgpd_consent("customer_123"):
        ...     process_data()
        ... else:
        ...     raise ComplianceViolation("No consent")
    """
    return has_capability(ComplianceCapability.CAP_CONSENT_TOKEN)


def get_lgpd_kernel_policies():
    """
    Get all LGPD kernel-level policies

    Returns:
        List of KernelPolicy instances for LGPD

    Example:
        >>> policies = get_lgpd_kernel_policies()
        >>> for policy in policies:
        ...     print(f"{policy.name}: {policy.description}")
    """
    return [
        lgpd_art7_consent_policy,
        lgpd_art16_data_access_policy,
        lgpd_art46_retention_policy,
    ]


def get_lgpd_layered_policies():
    """
    Get all LGPD layered policies (Application + Kernel)

    Returns:
        List of LayeredPolicy instances

    Example:
        >>> policies = get_lgpd_layered_policies()
        >>> # Enforce all layers
        >>> for policy in policies:
        ...     with policy.enforce():
        ...         protected_operation()
    """
    return [
        lgpd_art18_layered,
        lgpd_art20_layered,
    ]
