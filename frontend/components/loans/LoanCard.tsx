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
import { Cpu, Calendar, ShieldAlert, Award } from 'lucide-react'

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
      <Card className="animate-pulse bg-zinc-900 border border-zinc-800">
        <CardHeader>
          <div className="h-6 bg-zinc-800 rounded w-48 animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-zinc-800 rounded animate-pulse w-full"></div>
            <div className="h-4 bg-zinc-800 rounded animate-pulse w-5/6"></div>
            <div className="h-4 bg-zinc-800 rounded animate-pulse w-4/5"></div>
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
    <Card className={`bg-gradient-to-br from-zinc-950 to-zinc-900 border transition duration-300 relative overflow-hidden ${
      isLiquidatable 
        ? 'border-red-900 shadow-[0_0_20px_rgba(239,68,68,0.1)]' 
        : 'border-zinc-800 hover:border-zinc-700 shadow-xl'
    }`}>
      <div className={`absolute top-0 left-0 w-[3px] h-full ${
        isLiquidatable ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'
      }`} />
      
      <CardHeader className="pb-4">
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <CardTitle className="text-base font-bold text-zinc-100 flex items-center gap-2">
              <Cpu className="h-4 w-4 text-zinc-400" />
              Sandbox Workload {formatAddress(loanId)}
            </CardTitle>
            <p className="text-xs text-zinc-500 flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Created: {formatDate(Number(loan.startTime))}
            </p>
          </div>
          <HealthFactorBadge healthFactor={healthFactorPercent} />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4 pt-2">
        <div className="grid grid-cols-2 gap-3 text-xs bg-zinc-950/40 p-3 rounded-lg border border-zinc-800/40">
          <div>
            <p className="text-zinc-500 mb-0.5">Compute Allocation</p>
            <p className="text-sm font-bold text-zinc-200">{formatETH(loan.principal)} ETH</p>
          </div>
          <div>
            <p className="text-zinc-500 mb-0.5">Escrow Deposit</p>
            <p className="text-sm font-bold text-zinc-200">{formatETH(loan.collateral)} ETH</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs bg-zinc-950/40 p-3 rounded-lg border border-zinc-800/40">
          <div>
            <p className="text-zinc-500 mb-0.5">Resource Fee Accrued</p>
            <p className="text-sm font-bold text-zinc-200">{formatETH(accruedInterest)} ETH</p>
          </div>
          <div>
            <p className="text-zinc-500 mb-0.5">Total Compute Debt</p>
            <p className="text-sm font-bold text-zinc-200">{formatETH(totalOwed)} ETH</p>
          </div>
        </div>

        <div className="space-y-2 pt-1">
          <div className="flex justify-between text-xs font-semibold">
            <span className="text-zinc-400 flex items-center gap-1">
              <ShieldAlert className="h-3.5 w-3.5 text-zinc-500" />
              Behavior Safety Score
            </span>
            <span className={healthFactorPercent < 120 ? 'text-red-500 font-extrabold' : 'text-zinc-300'}>
              {healthFactorPercent.toFixed(2)}%
            </span>
          </div>
          <Progress
            value={Math.min(healthFactorPercent, 200)}
            className={`h-2 ${healthFactorPercent < 120 ? 'bg-red-500' : 'bg-emerald-500'}`}
          />
          {isLiquidatable && (
            <p className="text-[10px] text-red-400 font-bold bg-red-950/20 p-2 rounded border border-red-900/30 flex items-center gap-1.5 animate-pulse">
              ⚠️ Under Threat Alert! Safety score below 120% threshold.
            </p>
          )}
        </div>

        <Button
          onClick={handleRepay}
          disabled={isPending || isConfirming || isRepaying}
          className="w-full text-xs font-bold py-5 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 hover:border-zinc-700 text-zinc-200 flex items-center gap-1.5"
          variant="outline"
        >
          {isPending || isConfirming ? 'Processing...' : (
            <>
              <Award className="h-3.5 w-3.5 text-yellow-500" />
              Release Workload & Reclaim Escrow
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
