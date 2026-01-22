#!/bin/bash
# Script para verificar saldo no Sepolia

if [ -z "$1" ]; then
    echo "Uso: ./check_balance.sh <ENDEREÇO_DA_WALLET>"
    echo "Exemplo: ./check_balance.sh 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    exit 1
fi

ADDRESS=$1
RPC_URL="https://rpc.sepolia.org"

echo "Verificando saldo no Sepolia..."
echo "Endereço: $ADDRESS"
echo ""

BALANCE=$(cast balance $ADDRESS --rpc-url $RPC_URL)
BALANCE_ETH=$(cast --from-wei $BALANCE)

echo "Saldo: $BALANCE_ETH ETH"
echo ""

if (( $(echo "$BALANCE_ETH >= 0.1" | bc -l) )); then
    echo "✅ Saldo suficiente para deployment!"
else
    echo "❌ Saldo insuficiente. Precisa de pelo menos 0.1 ETH"
fi
