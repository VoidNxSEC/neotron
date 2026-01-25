# Security Policy

## Supported Versions

| Version | Supported          | Python Versions | Compliance Standards |
| ------- | ------------------ | --------------- | -------------------- |
| 1.0.x   | :white_check_mark: | 3.11, 3.12, 3.13| GDPR, LGPD, AI Act   |
| < 1.0   | :x:                | -               | -                    |

## Reporting a Vulnerability

We take the security of NEXUS and its compliance engines seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Disclosure Policy

1.  **Do not open a public GitHub issue.** Vulnerabilities should be handled discreetly to protect users.
2.  Send an email to `security@nexus-platform.com` (mock email for portfolio) with the subject `[SECURITY] Vulnerability Report`.
3.  Include details of the vulnerability, steps to reproduce, and the potential impact.
4.  The core team will acknowledge receipt within 24 hours.
5.  We will provide a timeline for the fix and coordinate the release of a patch.

### Responsible Disclosure

-   Please give us reasonable time to fix the issue before making it public.
-   Do not exploit the vulnerability to access data you do not own.
-   We promise not to pursue legal action against researchers who follow these guidelines.

## Compliance & Integrity

NEXUS is designed to enforce **GDPR** and **EU AI Act** compliance. A bypass of these guardrails is considered a Critical Security Vulnerability.

-   **Severity High**: Any bypass of `SENTINEL` guardrails that allows non-compliant data processing.
-   **Severity Critical**: Any bypass that allows automated decision-making without the required explanation generation (`ORACLE` failure).

## Infrastructure Security

Our infrastructure is defined by `flake.nix` and locked via `flake.lock`. We recommend:

-   Running `trivy fs .` to scan for filesystem vulnerabilities.
-   Using the provided `sentinel-ci.yml` for automated security checks on every PR.
