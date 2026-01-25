import { BorrowForm } from '@/components/loans/BorrowForm'
import { PoolStats } from '@/components/pool/PoolStats'
import { NetworkGuard } from '@/components/web3/NetworkGuard'
import { WalletRequired } from '@/components/web3/WalletRequired'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent } from '@/components/ui/card'
import { Shield, AlertTriangle } from 'lucide-react'

export default function BorrowPage() {
  return (
    <NetworkGuard>
      <WalletRequired>
        <div className="container mx-auto px-4 py-12">
          <h1 className="text-4xl font-bold mb-2">Borrow ETH</h1>
          <p className="text-muted-foreground mb-8">
            Apply for a collateralized loan with LGPD-compliant smart contract enforcement
          </p>

          {/* Pool Stats */}
          <div className="mb-8">
            <PoolStats />
          </div>

          <div className="max-w-2xl mx-auto space-y-6">
            {/* Important Notice */}
            <Alert>
              <Shield className="h-5 w-5" />
              <AlertTitle>LGPD Compliance Required</AlertTitle>
              <AlertDescription>
                Before borrowing, you must provide explicit consent according to LGPD Article 7.
                This consent is enforced at the smart contract level and will be recorded on-chain.
              </AlertDescription>
            </Alert>

            {/* Borrow Form */}
            <BorrowForm />

            {/* Loan Terms */}
            <Card className="bg-muted">
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-3">Loan Terms:</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Collateral Ratio</p>
                    <p className="font-semibold">150% (1.5x borrowed amount)</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Interest Rate</p>
                    <p className="font-semibold">5% APY</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Liquidation Threshold</p>
                    <p className="font-semibold">120% health factor</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Loan Duration</p>
                    <p className="font-semibold">Flexible (repay anytime)</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Warning */}
            <Alert variant="warning">
              <AlertTriangle className="h-5 w-5" />
              <AlertTitle>Risk Warning</AlertTitle>
              <AlertDescription>
                If your loan's health factor drops below 120%, it can be liquidated.
                Monitor your loans regularly and add collateral or repay if needed.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </WalletRequired>
    </NetworkGuard>
  )
}
