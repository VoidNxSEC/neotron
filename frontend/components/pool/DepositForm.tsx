'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useDeposit } from '@/lib/hooks/useDeposit'
import { useAccount, useBalance } from 'wagmi'
import { formatETH } from '@/lib/utils/formatters'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function DepositForm() {
  const [amount, setAmount] = useState('')
  const { deposit, isPending, isConfirming, isSuccess, hash, error } = useDeposit()
  const { address } = useAccount()
  const { data: balance } = useBalance({ address })

  const handleDeposit = async () => {
    if (!amount || Number(amount) <= 0) return
    try {
      await deposit(amount)
    } catch (err) {
      console.error('Deposit failed:', err)
    }
  }

  const handleMaxClick = () => {
    if (balance) {
      // Leave 0.01 ETH for gas
      const maxAmount = Math.max(0, Number(formatETH(balance.value)) - 0.01)
      setAmount(maxAmount.toString())
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deposit ETH</CardTitle>
        <CardDescription>
          Deposit ETH to earn interest from borrowers
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {balance && (
          <div className="text-sm text-muted-foreground">
            Balance: {formatETH(balance.value)} ETH
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
            <Button variant="outline" onClick={handleMaxClick} disabled={!balance}>
              Max
            </Button>
          </div>
        </div>

        <Button
          onClick={handleDeposit}
          disabled={isPending || isConfirming || !amount || Number(amount) <= 0}
          className="w-full"
        >
          {isPending ? 'Confirming...' : isConfirming ? 'Processing...' : 'Deposit'}
        </Button>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              {error.message || 'Failed to deposit. Please try again.'}
            </AlertDescription>
          </Alert>
        )}

        {isSuccess && hash && (
          <Alert>
            <AlertDescription>
              Deposit successful! Transaction: {hash.slice(0, 10)}...{hash.slice(-8)}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
