# NEXUS BASTION-SC Frontend

Production-ready Next.js 14 frontend for the BASTION-SC DeFi lending protocol with complete Web3 integration.

## Features

- **Lend/Borrow Interface**: Core DeFi functionality with deposit, withdraw, borrow, and repay
- **Liquidation Dashboard**: Monitor and liquidate risky loans
- **Compliance Viewer**: Showcase 4-layer compliance stack (SENTINEL, BASTION, BASTION-SC, Audit Trail)
- **LGPD Article 7 Enforcement**: Smart contract-level consent modal before borrowing
- **Real-time Pool Stats**: TVL, utilization, available liquidity

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Web3**: wagmi v2 + viem
- **Wallet**: RainbowKit
- **UI**: TailwindCSS + shadcn/ui
- **TypeScript**: Full type safety

## Contract Details

- **Network**: Sepolia Testnet
- **Contract Address**: `0x35fF603BD286E287f932356316271D59a4ADa779`
- **Chain ID**: 11155111

## Getting Started

### 1. Install Dependencies

```bash
pnpm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env.local` and fill in your values:

```bash
cp .env.example .env.local
```

Required variables:
- `NEXT_PUBLIC_SEPOLIA_RPC_URL`: Get from [Alchemy](https://www.alchemy.com/) or [Infura](https://www.infura.io/)
- `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`: Get from [WalletConnect Cloud](https://cloud.walletconnect.com/)

### 3. Run Development Server

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production

```bash
pnpm build
pnpm start
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Landing page
│   ├── lend/page.tsx      # Deposit/withdraw interface
│   ├── borrow/page.tsx    # Loan application
│   ├── loans/page.tsx     # My loans dashboard
│   ├── liquidate/page.tsx # Liquidation dashboard
│   └── compliance/page.tsx # Compliance viewer
├── components/
│   ├── ui/                # shadcn/ui components
│   ├── web3/              # Web3 guards (NetworkGuard, WalletRequired)
│   ├── pool/              # Pool components (PoolStats, DepositForm, etc)
│   ├── loans/             # Loan components (BorrowForm, LoanCard, etc)
│   ├── compliance/        # Compliance components (LGPDConsentModal, etc)
│   └── liquidation/       # Liquidation components
├── lib/
│   ├── contracts/         # Contract ABI + wagmi config
│   ├── hooks/             # Custom Web3 hooks
│   └── utils/             # Utility functions
└── public/                # Static assets
```

## Key Features

### 1. Lend/Borrow

- Deposit ETH to earn 5% APY
- Borrow with 150% collateral ratio
- Flexible repayment
- Real-time interest calculation

### 2. LGPD Compliance

- Modal consent before borrowing (LGPD Article 7)
- Smart contract enforcement
- On-chain consent recording
- 4-layer compliance stack visualization

### 3. Liquidation

- Monitor loans with health factor < 120%
- One-click liquidation
- Earn profit from collateral premium

### 4. Web3 Integration

- RainbowKit wallet connection
- Network switching to Sepolia
- Transaction confirmation UI
- Error handling

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_SEPOLIA_RPC_URL` | Sepolia RPC endpoint | Yes |
| `NEXT_PUBLIC_LENDING_PROTOCOL_ADDRESS` | Contract address | No (default provided) |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | WalletConnect project ID | Yes |

## Testing

1. Connect wallet (MetaMask, WalletConnect, etc.)
2. Switch to Sepolia Testnet
3. Get test ETH from [Sepolia Faucet](https://sepoliafaucet.com/)
4. Test deposit/borrow/repay flows
5. Monitor loan health factors
6. Test liquidation (requires undercollateralized loan)

## Deployment

### Vercel (Recommended)

```bash
vercel --prod
```

### Self-hosted

```bash
pnpm build
pnpm start
```

## Compliance Layers

1. **SENTINEL**: Application-level Python validation
2. **BASTION**: Kernel-level seccomp-BPF syscall filtering
3. **BASTION-SC**: Smart contract LGPD enforcement (this frontend)
4. **Audit Trail**: Immutable logs on IPFS + Arweave

## License

MIT

## Support

For issues or questions, please open an issue in the main NEXUS repository.
