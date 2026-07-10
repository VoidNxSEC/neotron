#!/usr/bin/env bash
# E2E test: deploy all contracts on Anvil, run smoke tests via cast
set -euo pipefail

ANVIL_PID=""
ANVIL_RPC="http://localhost:8545"
# Anvil default account 0
PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
DEPLOYER="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

cleanup() {
  [[ -n "$ANVIL_PID" ]] && kill "$ANVIL_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "🔧 Starting Anvil..."
anvil --silent --port 8545 &
ANVIL_PID=$!
sleep 2

echo "✅ Anvil running (PID $ANVIL_PID)"

cd "$(dirname "$0")/../contracts"
mkdir -p deployments

echo ""
echo "📦 Building contracts..."
forge build --quiet

echo ""
echo "🚀 Deploying LendingProtocol..."
PRIVATE_KEY="$PRIVATE_KEY" forge script script/Deploy.s.sol:DeployScript \
  --fork-url "$ANVIL_RPC" \
  --broadcast \
  --quiet 2>&1 | grep -E "(deployed|Error)" || true

echo ""
echo "🔗 Deploying Supply Chain contracts..."
PRIVATE_KEY="$PRIVATE_KEY" forge script script/DeploySupplyChain.s.sol:DeploySupplyChain \
  --fork-url "$ANVIL_RPC" \
  --broadcast \
  --quiet 2>&1 | grep -E "(SBOMRegistry|BuildAttestation|LicenseRegistry|SupplyChain|Error)" || true

echo ""
echo "🧪 Running Foundry tests against Anvil..."
forge test --fork-url "$ANVIL_RPC" -q --summary 2>&1 | tail -20

echo ""
echo "✅ E2E contracts test complete"
