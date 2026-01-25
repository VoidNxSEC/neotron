'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { HealthFactorBadge } from './HealthFactorBadge'
import { useLoanDetails } from '@/lib/hooks/useUserLoans'
import { useLoanHealth } from '@/lib/hooks/useLoanHealth'
import { useRepay } from '@/lib/hooks/useRepay'
import { formatETH, formatAddress, formatDate } from '@/lib/utils/formatters'
import { useState } from 'react'

interface LoanCardProps {
  loanId: `0x${string}`
}

export function LoanCard({ loanId }: LoanCardProps) {
  const { loan, isLoading: isLoadingLoan } = useLoanDetails(loanId)
  const { healthFactor, accruedInterest, isLiquidatable } = useLoanHealth(loanId)
  const { repay, isPending, isConfirming } = useRepay()
  const [isRepaying, setIsRepaying] = useState(false)

  if (isLoadingLoan || !loan) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-6 bg-muted rounded w-48"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="h-4 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const totalOwed = loan.principal + accruedInterest
  const healthFactorPercent = Number(healthFactor) / 100

  const handleRepay = async () => {
    setIsRepaying(true)
    try {
      await repay(loanId, formatETH(totalOwed))
    } catch (err) {
      console.error('Repay failed:', err)
    } finally {
      setIsRepaying(false)
    }
  }

  return (
    <Card className={isLiquidatable ? 'border-red-500' : ''}>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg">Loan {formatAddress(loanId)}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Started: {formatDate(Number(loan.startTime))}
            </p>
          </div>
          <HealthFactorBadge healthFactor={healthFactorPercent} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Principal</p>
            <p className="text-lg font-semibold">{formatETH(loan.principal)} ETH</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Collateral</p>
            <p className="text-lg font-semibold">{formatETH(loan.collateral)} ETH</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Interest Accrued</p>
            <p className="text-lg font-semibold">{formatETH(accruedInterest)} ETH</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total Owed</p>
            <p className="text-lg font-semibold">{formatETH(totalOwed)} ETH</p>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Health Factor</span>
            <span className="font-medium">{healthFactorPercent.toFixed(2)}%</span>
          </div>
          <Progress
            value={Math.min(healthFactorPercent, 200)}
            className={healthFactorPercent < 120 ? 'bg-red-500' : 'bg-green-500'}
          />
          {isLiquidatable && (
            <p className="text-sm text-red-600 font-medium">
              ⚠️ This loan is at risk of liquidation!
            </p>
          )}
        </div>

        <Button
          onClick={handleRepay}
          disabled={isPending || isConfirming || isRepaying}
          className="w-full"
          variant={isLiquidatable ? 'destructive' : 'default'}
        >
          {isPending || isConfirming ? 'Processing...' : `Repay ${formatETH(totalOwed)} ETH`}
        </Button>
      </CardContent>
    </Card>
  )
}
