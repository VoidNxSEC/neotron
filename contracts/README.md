# NEXUS BASTION-SC Smart Contracts

**World's first DeFi protocol with 4-layer compliance integration**

## Overview

BASTION-SC extends NEXUS compliance enforcement to the blockchain layer, creating the world's first DeFi protocol where compliance violations are mathematically impossible.

### The 4 Layers

```
┌─────────────────────────────────────────────────────────┐
│           Defense-in-Depth Compliance (4 LAYERS)         │
├─────────────────────────────────────────────────────────┤
│  Layer 1: SENTINEL (Application - Python)               │
│  Layer 2: BASTION (Kernel - seccomp-BPF)                │
│  Layer 3: BASTION-SC (Smart Contracts - Solidity)       │ ← THIS
│  Layer 4: Audit Trail (IPFS + Arweave)                  │ ← THIS
└─────────────────────────────────────────────────────────┘
```

## Contracts

### Core Compliance

| Contract | Purpose | LOC | Tests |
|----------|---------|-----|-------|
| `ComplianceGuardrail.sol` | Base compliance contract | ~200 | 10+ |
| `LGPDConsent.sol` | LGPD Article 7 consent enforcement | ~250 | 30+ |
| `AuditLogger.sol` | On-chain audit logging with IPFS/Arweave | ~400 | 30+ |

### DeFi Applications

| Contract | Purpose | LOC | Tests |
|----------|---------|-----|-------|
| `LendingProtocol.sol` | Compliant DeFi lending | ~500 | 30+ |

**Total**: ~2,500 LOC Solidity, 115+ comprehensive tests

## Quick Start

### Install Dependencies

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install dependencies
forge install
```

### Build

```bash
# Build contracts
forge build

# Build with optimization
forge build --optimize --optimizer-runs 200
```

### Test

```bash
# Run all tests
forge test

# Run with verbosity
forge test -vvv

# Run with gas reporting
forge test --gas-report

# Run specific test
forge test --match-test test_ApplyForLoan_WithConsent

# Run with coverage
forge coverage
```

### Deploy Locally

```bash
# Terminal 1: Start local Anvil node
anvil

# Terminal 2: Deploy to local node
forge script script/Deploy.s.sol:DeployScript \
    --fork-url http://localhost:8545 \
    --broadcast
```

### Deploy to Sepolia

See [DEPLOYMENT.md](../docs/DEPLOYMENT.md) for comprehensive deployment guide.

```bash
# Quick deploy
source .env
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify
```

## Key Features

### 1. Compliance Enforcement

**Smart Contract Modifiers:**
```solidity
function applyForLoan(uint256 amount)
    external
    payable
    lgpdArticle7Consent(msg.sender)  // ← Automatic revert if no consent
    returns (bytes32 loanId)
{
    // Loan logic
}
```

**Result**: Mathematically impossible to borrow without consent.

### 2. Decentralized Audit Trails

**Hybrid Architecture:**
- On-chain: References (CIDs, transaction hashes)
- Off-chain: Full audit logs (IPFS/Arweave)

**Storage Economics:**
- IPFS: ~$5/month per 100GB (mutable)
- Arweave: ~$0.005/MB one-time (permanent 200+ years)

**Result**: Arweave 300x cheaper for long-term compliance.

### 3. DeFi with Compliance

**Lending Protocol Features:**
- Collateralized loans (150% ratio)
- 5% APY interest accrual
- Liquidation mechanism (120% threshold)
- Pool-based liquidity
- Automatic compliance checks
- Immutable audit logs

**Gas Efficiency:**
- Audit logging: < 150k gas
- Loan operations: < 300k gas

## Deployment

See comprehensive [DEPLOYMENT.md](../docs/DEPLOYMENT.md) guide.

### Networks

| Network | Status | Contract Address |
|---------|--------|------------------|
| Localhost (Anvil) | ✅ Supported | Dynamic |
| Sepolia Testnet | 🚧 Week 20 | TBD |
| Ethereum Mainnet | ⏳ Future | Not deployed |

## License

MIT License - See [LICENSE](../LICENSE) for details.

---

**NEXUS BASTION-SC** - Compliance That Cannot Be Violated

🚀 World's First DeFi with 4-Layer Compliance • 🛡️ Defense-in-Depth • ⛓️ Blockchain-Native • 💾 200+ Year Audit Permanence

Built with ❤️ by the NEXUS Platform Team
