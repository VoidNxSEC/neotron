# EU AI Act Compliance with NEXUS

How NEXUS maps to the EU AI Act (Regulation (EU) 2024/1689) requirements for high-risk AI systems.

## Applicable Articles

### Article 13 - Transparency

> High-risk AI systems shall be designed and developed in such a way to ensure that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately.

**NEXUS Implementation:**

| Requirement | NEXUS Component | Details |
|-------------|----------------|---------|
| Interpretable output | ORACLE Framework | 5 explanation types: Feature Importance, Counterfactual, Chain of Thought, Rule-Based, Example-Based |
| Sufficient transparency | CORTEX Layer | Multi-agent consensus with individual agent reasoning exposed |
| Enable interpretation | API Endpoints | `/v1/oracle/explain` provides human-readable and machine-readable explanations |
| Confidence disclosure | Consensus Engine | Confidence scores from each agent + consensus confidence |

**How it works:**

1. Each CORTEX agent provides its reasoning and confidence score
2. The ORACLE framework generates structured explanations:
   - **Feature Importance**: Ranks which input factors most influenced the decision
   - **Chain of Thought**: Shows step-by-step reasoning from each agent
   - **Counterfactual**: Shows "what if" scenarios (e.g., "if credit_score were 600, decision would change")
3. All explanations are stored in the immutable audit trail

### Article 14 - Human Oversight

> High-risk AI systems shall be designed and developed in such a way, including with appropriate human-machine interface tools, that they can be effectively overseen by natural persons during the period in which the AI system is in use.

**NEXUS Implementation:**

| Requirement | NEXUS Component | Details |
|-------------|----------------|---------|
| Human-in-the-loop | REVIEW_REQUIRED decision | System can escalate uncertain decisions for human review |
| Override capability | Compliance API | Human operators can override any AI decision |
| Monitoring | Metrics endpoint | `/v1/metrics` exposes real-time provider health and circuit breaker status |
| Audit trail | AUDIT Layer | Immutable logs on IPFS/Arweave for 200+ year retention |
| Stop mechanism | Circuit Breakers | Automatic provider isolation on failure (configurable threshold) |

**Decision flow with human oversight:**

```
AI Decision
  |
  +-- APPROVED (confidence > 0.8) --> Proceed with audit log
  |
  +-- CONDITIONAL --> Proceed with restrictions + human notification
  |
  +-- REVIEW_REQUIRED --> Human must review before proceeding
  |
  +-- REJECTED --> Blocked with full explanation
```

## High-Risk AI Systems (Annex III)

NEXUS is designed for these Annex III categories:

### 5(b) - Creditworthiness Assessment

AI systems used to evaluate creditworthiness or establish credit scores.

**Demo scenario:** `demos/eu_ai_act_demo.py` demonstrates a credit scoring decision with full 4-layer compliance.

### 5(a) - Access to Essential Services

AI systems used to evaluate eligibility for public assistance benefits and services.

### 6(a) - Law Enforcement

AI systems used as polygraphs, for evaluating reliability of evidence, or predicting occurrence of criminal offenses.

## 4-Layer Defense-in-Depth Architecture

```
Layer 1: SENTINEL (Application)
  - Consent validation (LGPD Art. 7, GDPR Art. 6)
  - Input structure validation
  - Purpose limitation check

Layer 2: BASTION (Kernel)
  - seccomp-BPF syscall filtering
  - Makes violations physically impossible
  - Capability-based access control

Layer 3: CORTEX + ORACLE (AI)
  - 3-agent consensus (compliance, risk, decision)
  - ORACLE explainability (Art. 13 compliance)
  - Confidence scoring

Layer 4: AUDIT (Immutable Storage)
  - IPFS for development (mutable, pinned)
  - Arweave for production (permanent, 200+ years)
  - Content-addressed for integrity verification
```

## Compliance Verification

### Run the Demo

```bash
python demos/eu_ai_act_demo.py
```

This produces a complete report showing:
- Each layer's result and processing time
- ORACLE explanations (Feature Importance + Chain of Thought)
- Article 13 transparency mapping
- Article 14 human oversight mapping

### API Verification

```bash
# 1. Validate a decision through 4 layers
curl -X POST http://localhost:8000/v1/compliance/validate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "eu_pilot_test",
    "action": "loan_approval",
    "data": {"credit_score": 720, "amount": 50000},
    "consent_token": "lgpd_consent_pilot",
    "regulation": "AI_ACT"
  }'

# 2. Get explanation for the decision
curl -X POST http://localhost:8000/v1/oracle/explain \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approved",
    "input_data": {"credit_score": 720, "amount": 50000},
    "output_data": {"confidence": 0.85},
    "explanation_type": "feature_importance"
  }'

# 3. Retrieve the audit trail
curl http://localhost:8000/v1/compliance/audit/<audit_hash>
```

## Regulatory Mapping Summary

| EU AI Act Article | NEXUS Layer | Status |
|-------------------|-------------|--------|
| Art. 9 - Risk Management | SENTINEL + BASTION | Implemented |
| Art. 10 - Data Governance | SENTINEL (consent) | Implemented |
| Art. 13 - Transparency | ORACLE + CORTEX | Implemented |
| Art. 14 - Human Oversight | REVIEW_REQUIRED + Metrics | Implemented |
| Art. 15 - Accuracy/Robustness | Circuit Breakers + Fallback | Implemented |
| Art. 12 - Record-Keeping | AUDIT (IPFS/Arweave) | Implemented |
| Art. 17 - Quality Management | Test Suite + CI | Implemented |
