import { LiquidatableLoans } from '@/components/liquidation/LiquidatableLoans'
import { NetworkGuard } from '@/components/web3/NetworkGuard'
import { WalletRequired } from '@/components/web3/WalletRequired'
import { Card, CardContent } from '@/components/ui/card'

export default function LiquidatePage() {
  return (
    <NetworkGuard>
      <WalletRequired>
        <div className="container mx-auto px-4 py-12">
          <h1 className="text-4xl font-bold mb-2">Liquidation Dashboard</h1>
          <p className="text-muted-foreground mb-8">
            Monitor undercollateralized loans and liquidate them to maintain protocol health
          </p>

          <div className="mb-8">
            <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <CardContent className="py-6">
                <h3 className="font-semibold mb-3">How Liquidation Works:</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground mb-1">1. Identify Risky Loans</p>
                    <p>Loans with health factor below 120% become liquidatable</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground mb-1">2. Liquidate</p>
                    <p>Repay the borrower's debt and seize their collateral</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground mb-1">3. Earn Profit</p>
                    <p>Collateral (150%) exceeds debt (100%), yielding profit</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground mb-1">4. Protect Protocol</p>
                    <p>Prevents bad debt and maintains pool health</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <LiquidatableLoans />
        </div>
      </WalletRequired>
    </NetworkGuard>
  )
}
