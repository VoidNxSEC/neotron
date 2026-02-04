# ADR 004: On-Chain Compliance Enforcement & Gas Overhead

## Status
Accepted

## Context
During the audit of the `Bastion-SC` layer (Smart Contracts), we observed that the `ComplianceGuardrail` system strictly blocks all interactions (Lending, Borrowing, Liquidation) if the user has not explicitly signed an LGPD Consent (`grantConsent`).

This introduces two side effects:
1.  **Test Complexity:** Integration tests must strictly follow the `Grant Consent -> Perform Action` flow, breaking stateless test assumptions.
2.  **Gas Overhead:** Compliance checks add approximately **150k to 350k gas** per state-changing transaction due to storage reads/writes and event logging.

## Decision
We decide to **MAINTAIN** the strict enforcement mechanism and **ACCEPT** the gas overhead.

### Justification
1.  **Defense-in-Depth:** The Smart Contract layer is the final line of defense. If the Python Sentinel layer fails, the contract *must* reject non-compliant data.
2.  **Immutable Audit:** The cost of gas pays for the immutable proof of compliance, which is the project's core value proposition (Enterprise DeFi).
3.  **Fail-Safe Default:** It is safer to fail a transaction than to process non-consented data (which creates legal liability).

## Consequences
1.  **Testing:** All test suites must implement `setUp` routines that simulate user consent granting.
2.  **Frontend:** The UI must verify `hasConsent` before allowing users to submit transaction forms, preventing wasted gas on inevitable reverts.
3.  **Economics:** Users must be informed that higher gas fees are due to "Regulatory Insurance".
