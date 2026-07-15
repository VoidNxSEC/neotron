'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useWithdraw } from '@/lib/hooks/useWithdraw'
import { usePoolStatus } from '@/lib/hooks/usePoolStatus'
import { formatETH } from '@/lib/utils/formatters'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function WithdrawForm() {
  const [amount, setAmount] = useState('')
  const { withdraw, isPending, isConfirming, isSuccess, hash, error } = useWithdraw()
  const { availableLiquidity } = usePoolStatus()

  const handleWithdraw = async () => {
    if (!amount || Number(amount) <= 0) return
    try {
      await withdraw(amount)
    } catch (err) {
      console.error('Withdraw failed:', err)
    }
  }

  const handleMaxClick = () => {
    if (availableLiquidity) {
      setAmount(formatETH(availableLiquidity))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Withdraw ETH</CardTitle>
        <CardDescription>
          Withdraw your deposited ETH plus earned interest
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {availableLiquidity > 0n && (
          <div className="text-sm text-muted-foreground">
            Available to withdraw: {formatETH(availableLiquidity)} ETH
          </div>
        )}

        <div className="space-y-2">
          <div className="flex gap-2">
            <Input
              type="number"
              placeholder="Amount in ETH"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              step="0.01"
              min="0"
            />
            <Button variant="outline" onClick={handleMaxClick} disabled={availableLiquidity === 0n}>
              Max
            </Button>
          </div>
        </div>

        <Button
          onClick={handleWithdraw}
          disabled={isPending || isConfirming || !amount || Number(amount) <= 0}
          className="w-full"
        >
          {isPending ? 'Confirming...' : isConfirming ? 'Processing...' : 'Withdraw'}
        </Button>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              {error.message || 'Failed to withdraw. Please try again.'}
            </AlertDescription>
          </Alert>
        )}

        {isSuccess && hash && (
          <Alert>
            <AlertDescription>
              Withdrawal successful! Transaction: {hash.slice(0, 10)}...{hash.slice(-8)}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
