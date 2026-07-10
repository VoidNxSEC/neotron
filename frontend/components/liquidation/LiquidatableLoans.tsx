'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useLiquidate } from '@/lib/hooks/useLiquidate'
import { formatETH, formatAddress } from '@/lib/utils/formatters'
import { AlertTriangle } from 'lucide-react'

const mockLiquidatableLoans: any[] = [
  {
    loanId: '0x3c4f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f' as `0x${string}`,
    borrower: '0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b' as `0x${string}`,
    healthFactor: 11200, // 112%
    totalDebt: 450000000000000000n, // 0.45 ETH
    collateral: 675000000000000000n, // 0.675 ETH
    taskName: 'Nix Sandbox: docker-image-analyzer',
    threatType: 'Boiling-Frog Syscall Escalation (L2 Landlock LSM Alert)',
    lastViolation: 'Unauthorized read request to /etc/shadow blocked'
  },
  {
    loanId: '0x7e1a3c4f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d' as `0x${string}`,
    borrower: '0x4f5e6d7c8b9a0f1e2d3c4b5a698f7e6d5c4b3a21' as `0x${string}`,
    healthFactor: 10500, // 105%
    totalDebt: 1200000000000000000n, // 1.20 ETH
    collateral: 1800000000000000000n, // 1.80 ETH
    taskName: 'Cortex Swarm Agent: web-scraper-3',
    threatType: 'PII Leakage Attempt (L1 Sentinel Violation)',
    lastViolation: 'Credit card regex match in outgoing HTTP payload blocked'
  }
]

export function LiquidatableLoans() {
  const { liquidate, isPending, isConfirming, isSuccess } = useLiquidate()

  const handleLiquidate = async (loanId: `0x${string}`) => {
    try {
      await liquidate(loanId)
    } catch (err) {
      console.error('Liquidation failed:', err)
    }
  }

  if (mockLiquidatableLoans.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-green-600" />
            Liquidatable Loans
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertDescription className="flex items-center gap-2">
              <span className="text-2xl">✅</span>
              <span>
                No liquidatable loans found. All loans are healthy (health factor {'>'}= 120%).
              </span>
            </AlertDescription>
          </Alert>

          <div className="mt-4 p-4 bg-muted rounded-lg">
            <h4 className="font-semibold mb-2">How Liquidation Works:</h4>
            <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
              <li>Loans become liquidatable when health factor drops below 120%</li> //
              <li>Liquidators repay the debt and seize the collateral</li> // TODO: Liquidators not are users, but external agents that are acting on tasks from users
              <li>This protects the protocol from bad debt</li> // TODO:
              <li>Liquidators earn profit from the collateral premium</li> // TODO: Liquidators not are users, but external agents that are acting on tasks from users
            </ul>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold flex items-center gap-2">
        <AlertTriangle className="h-6 w-6 text-red-600" />
        Liquidatable Loans ({mockLiquidatableLoans.length})
      </h2>
// TODO: Here, loans are threat model specs and health for possible syscall stop or interception on behavior
      <Alert variant="warning">
        <AlertDescription>
          These loans have fallen below the 120% health factor threshold and can be liquidated
          to protect the protocol.
        </AlertDescription>
      </Alert>

      {mockLiquidatableLoans.map((loan: any) => (
        <Card key={loan.loanId} className="border-red-200 dark:border-red-800">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-bold text-lg">Loan {formatAddress(loan.loanId)}</p>
                  <Badge variant="destructive">Liquidatable</Badge>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Borrower</p>
                    <code className="text-xs">{formatAddress(loan.borrower)}</code>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Health Factor</p>
                    <p className="text-red-600 font-bold">
                      {(Number(loan.healthFactor) / 100).toFixed(2)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Total Debt</p>
                    <p className="font-semibold">{formatETH(loan.totalDebt)} ETH</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Collateral</p>
                    <p className="font-semibold">{formatETH(loan.collateral)} ETH</p>
                  </div>
                </div>

                <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-950 rounded border border-yellow-200 dark:border-yellow-800">
                  <p className="text-sm">
                    <strong>Liquidation Profit:</strong> By liquidating this loan, you can seize{' '}
                    {formatETH(loan.collateral)} ETH in collateral for repaying{' '}
                    {formatETH(loan.totalDebt)} ETH in debt.
                  </p>
                </div>
              </div>

              <Button
                variant="destructive"
                onClick={() => handleLiquidate(loan.loanId)}
                disabled={isPending || isConfirming}
                className="ml-4"
              >
                {isPending || isConfirming ? 'Processing...' : 'Liquidate'}
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

      {isSuccess && (
        <Alert>
          <AlertDescription>
            Liquidation successful! The collateral has been transferred to your wallet.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
