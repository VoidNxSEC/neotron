# NEXUS BASTION-SC Deployment Guide

**Comprehensive guide for deploying NEXUS compliance-enabled smart contracts**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Sepolia Testnet Deployment](#sepolia-testnet-deployment)
4. [Mainnet Deployment](#mainnet-deployment)
5. [Contract Verification](#contract-verification)
6. [Post-Deployment Testing](#post-deployment-testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

1. **Foundry** - Ethereum development toolkit
   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

2. **Node.js** (v18+) - For frontend integration (Week 21)
   ```bash
   # Check version
   node --version
   ```

3. **Wallet** - MetaMask or similar for testnet testing

4. **Testnet ETH** - Get Sepolia ETH from faucets:
   - [Alchemy Sepolia Faucet](https://sepoliafaucet.com/)
   - [Infura Sepolia Faucet](https://www.infura.io/faucet/sepolia)
   - [QuickNode Faucet](https://faucet.quicknode.com/ethereum/sepolia)

### Configuration

1. **Copy environment template:**
   ```bash
   cd contracts
   cp .env.example .env
   ```

2. **Generate deployment wallet:**
   ```bash
   # Generate new wallet (TESTNET ONLY - never use for mainnet!)
   cast wallet new

   # Output:
   # Successfully created new keypair.
   # Address:     0x...
   # Private key: 0x...

   # Add private key to .env
   echo "PRIVATE_KEY=0x..." >> .env
   ```

3. **Get RPC URL:**
   - Sign up at [Alchemy](https://www.alchemy.com/) or [Infura](https://infura.io/)
   - Create Sepolia app
   - Copy HTTPS RPC URL to `.env`

4. **Get Etherscan API key:**
   - Sign up at [Etherscan](https://etherscan.io/apis)
   - Create API key
   - Add to `.env`

---

## Local Development Setup

### Start Local Anvil Node

```bash
# Terminal 1: Start Anvil (local Ethereum node)
anvil

# Anvil will create 10 test accounts with 10000 ETH each
# Copy one of the private keys for local testing
```

### Deploy Locally

```bash
# Terminal 2: Deploy to local Anvil
forge script script/Deploy.s.sol:DeployScript \
    --fork-url http://localhost:8545 \
    --broadcast \
    -vvvv

# Output will show deployed contract addresses
```

### Run Tests

```bash
# Run all tests
forge test

# Run with gas reporting
forge test --gas-report

# Run specific test
forge test --match-test test_ApplyForLoan_WithConsent
```

---

## Sepolia Testnet Deployment

### Pre-Deployment Checklist

- [ ] `.env` configured with testnet private key
- [ ] Testnet wallet has > 0.1 ETH (for deployment gas)
- [ ] RPC URL configured (Alchemy/Infura)
- [ ] Etherscan API key configured
- [ ] Run tests locally: `forge test`
- [ ] Simulate deployment: `forge script script/Deploy.s.sol --fork-url $SEPOLIA_RPC_URL`

### Deploy to Sepolia

```bash
# Load environment variables
source .env

# Deploy (without verification first)
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --slow \
    -vvvv

# Deployment output:
# ========================================
# NEXUS BASTION-SC Deployment
# ========================================
# Deployer: 0x...
# Deployer balance: X.XX ETH
# Chain ID: 11155111
# ========================================
#
# Deploying LendingProtocol...
# LendingProtocol deployed at: 0x...
#
# Deployment Complete!
# ========================================
```

### Verify Deployment

```bash
# Verify on Etherscan
forge verify-contract \
    <LENDING_PROTOCOL_ADDRESS> \
    src/LendingProtocol.sol:LendingProtocol \
    --chain-id 11155111 \
    --etherscan-api-key $ETHERSCAN_API_KEY

# Or use combined deploy + verify
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify \
    --etherscan-api-key $ETHERSCAN_API_KEY \
    -vvvv
```

### Save Deployment Info

Deployment addresses are automatically saved to `deployments/sepolia.json`:

```json
{
  "network": "sepolia",
  "chainId": 11155111,
  "timestamp": 1234567890,
  "deployer": "0x...",
  "contracts": {
    "LendingProtocol": "0x..."
  },
  "config": {
    "collateralRatio": 150,
    "interestRate": 500,
    "liquidationThreshold": 120
  }
}
```

---

## Mainnet Deployment

**⚠️ CRITICAL WARNING:**
- Mainnet deployment uses REAL ETH
- Triple-check all configurations
- Use hardware wallet for private key security
- Test EXTENSIVELY on Sepolia first
- Consider multisig deployment for production
- Get security audit before mainnet deployment

### Pre-Mainnet Checklist

- [ ] Security audit completed
- [ ] All tests passing (100% coverage)
- [ ] Deployed and tested on Sepolia for 2+ weeks
- [ ] Gas optimization completed
- [ ] Emergency procedures documented
- [ ] Multisig wallet configured (recommended)
- [ ] Bug bounty program launched
- [ ] Insurance coverage obtained (if applicable)

### Mainnet Deployment Process

```bash
# 1. Final test run
forge test --gas-report

# 2. Simulate mainnet deployment (dry run)
forge script script/Deploy.s.sol \
    --fork-url $MAINNET_RPC_URL

# 3. Deploy to mainnet (REAL ETH)
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $MAINNET_RPC_URL \
    --broadcast \
    --verify \
    --etherscan-api-key $ETHERSCAN_API_KEY \
    --slow \
    -vvvv

# 4. Verify contract on Etherscan
# 5. Transfer ownership to multisig (if applicable)
# 6. Announce deployment on social media
# 7. Monitor for 48 hours
```

---

## Contract Verification

### Automatic Verification (Recommended)

```bash
# During deployment
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify \
    --etherscan-api-key $ETHERSCAN_API_KEY
```

### Manual Verification

```bash
# If automatic verification fails
forge verify-contract \
    <CONTRACT_ADDRESS> \
    src/LendingProtocol.sol:LendingProtocol \
    --chain-id 11155111 \
    --etherscan-api-key $ETHERSCAN_API_KEY \
    --watch
```

### Verification Status

Check verification status on Etherscan:
- Sepolia: `https://sepolia.etherscan.io/address/<CONTRACT_ADDRESS>`
- Mainnet: `https://etherscan.io/address/<CONTRACT_ADDRESS>`

Look for green checkmark: ✅ Contract Source Code Verified

---

## Post-Deployment Testing

### 1. Read Contract State

```bash
# Get contract constants
cast call <LENDING_PROTOCOL_ADDRESS> "COLLATERAL_RATIO()" --rpc-url $SEPOLIA_RPC_URL
# Returns: 150

cast call <LENDING_PROTOCOL_ADDRESS> "INTEREST_RATE()" --rpc-url $SEPOLIA_RPC_URL
# Returns: 500 (5% in basis points)
```

### 2. Test Deposit Workflow

```bash
# Deposit 1 ETH to lending pool
cast send <LENDING_PROTOCOL_ADDRESS> \
    "deposit()" \
    --value 1ether \
    --private-key $PRIVATE_KEY \
    --rpc-url $SEPOLIA_RPC_URL

# Check pool status
cast call <LENDING_PROTOCOL_ADDRESS> \
    "getPoolStatus()" \
    --rpc-url $SEPOLIA_RPC_URL
```

### 3. Test Consent Workflow

```bash
# Grant LGPD Article 7 consent
cast send <LENDING_PROTOCOL_ADDRESS> \
    "grantConsent(address,uint256,string)" \
    <LENDING_PROTOCOL_ADDRESS> \
    31536000 \
    "Loan application and credit scoring" \
    --private-key $PRIVATE_KEY \
    --rpc-url $SEPOLIA_RPC_URL

# Check consent status
cast call <LENDING_PROTOCOL_ADDRESS> \
    "checkConsent(address)" \
    <YOUR_ADDRESS> \
    --rpc-url $SEPOLIA_RPC_URL
```

### 4. Test Loan Workflow

```bash
# Apply for 1 ETH loan with 1.5 ETH collateral
cast send <LENDING_PROTOCOL_ADDRESS> \
    "applyForLoan(uint256)" \
    1000000000000000000 \
    --value 1.5ether \
    --private-key $PRIVATE_KEY \
    --rpc-url $SEPOLIA_RPC_URL

# Get loan ID from transaction logs
# Check loan details
cast call <LENDING_PROTOCOL_ADDRESS> \
    "getLoan(bytes32)" \
    <LOAN_ID> \
    --rpc-url $SEPOLIA_RPC_URL
```

### 5. Monitor Events

```bash
# Watch for deposit events
cast logs --address <LENDING_PROTOCOL_ADDRESS> \
    --from-block latest \
    --rpc-url $SEPOLIA_RPC_URL

# Or use Etherscan UI to view events
```

---

## Troubleshooting

### Common Issues

#### 1. "Insufficient funds for gas"

**Solution:**
```bash
# Check balance
cast balance <YOUR_ADDRESS> --rpc-url $SEPOLIA_RPC_URL

# Get testnet ETH from faucet
# Wait 5-10 minutes for faucet transaction to confirm
```

#### 2. "nonce too low"

**Solution:**
```bash
# Reset nonce by sending 0 ETH to yourself
cast send <YOUR_ADDRESS> \
    --value 0 \
    --private-key $PRIVATE_KEY \
    --rpc-url $SEPOLIA_RPC_URL
```

#### 3. "Contract verification failed"

**Solution:**
```bash
# Retry with --watch flag
forge verify-contract <ADDRESS> \
    src/LendingProtocol.sol:LendingProtocol \
    --chain-id 11155111 \
    --etherscan-api-key $ETHERSCAN_API_KEY \
    --watch

# Or flatten contract and verify manually on Etherscan
forge flatten src/LendingProtocol.sol > flattened.sol
```

#### 4. "Deployment transaction reverted"

**Solution:**
```bash
# Simulate deployment to see error
forge script script/Deploy.s.sol \
    --fork-url $SEPOLIA_RPC_URL

# Check deployer balance
cast balance <DEPLOYER_ADDRESS> --rpc-url $SEPOLIA_RPC_URL

# Check gas price
cast gas-price --rpc-url $SEPOLIA_RPC_URL
```

#### 5. "RPC URL not responding"

**Solution:**
```bash
# Test RPC connectivity
cast block-number --rpc-url $SEPOLIA_RPC_URL

# Try alternative RPC provider
# Alchemy: https://eth-sepolia.g.alchemy.com/v2/...
# Infura: https://sepolia.infura.io/v3/...
```

### Getting Help

- **GitHub Issues**: [github.com/kernelcore/neutron/issues](https://github.com/kernelcore/neutron/issues)
- **Foundry Book**: [book.getfoundry.sh](https://book.getfoundry.sh)
- **Etherscan Support**: [etherscan.io/contactus](https://etherscan.io/contactus)

---

## Next Steps

After successful deployment:

1. **Week 21**: Build frontend with Web3 integration
2. **Week 22**: Add advanced DeFi features (flash loans, yield farming)
3. **Week 23**: Production deployment and monitoring
4. **Security**: Schedule external audit
5. **Documentation**: Create user guides and API docs

---

## Deployment History

| Network | Contract | Address | Deployment Date | Status |
|---------|----------|---------|-----------------|--------|
| Sepolia | LendingProtocol | TBD | TBD | Pending |
| Mainnet | LendingProtocol | TBD | TBD | Not deployed |

---

## Security Considerations

### Private Key Management

**CRITICAL**: Never commit private keys to version control!

```bash
# Check .gitignore includes .env
cat .gitignore | grep .env

# If not, add it:
echo ".env" >> .gitignore
```

### Gas Optimization

Current gas costs (Sepolia):
- Deploy LendingProtocol: ~2,500,000 gas (~0.025 ETH @ 10 gwei)
- Deposit: ~50,000 gas
- Apply for loan: ~250,000 gas
- Repay loan: ~100,000 gas

### Emergency Procedures

If vulnerability discovered:
1. Pause contract (if pausable functionality added)
2. Contact users via social media
3. Prepare upgrade/migration plan
4. Deploy fixed version
5. Migrate user funds

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-22
**Maintained by**: NEXUS Platform Team
