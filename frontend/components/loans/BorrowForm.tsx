'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useBorrow } from '@/lib/hooks/useBorrow'
import { usePoolStatus } from '@/lib/hooks/usePoolStatus'
import { LGPDConsentModal } from '@/components/compliance/LGPDConsentModal'
import { formatETH } from '@/lib/utils/formatters'
import { COLLATERAL_RATIO } from '@/lib/utils/constants'

export function BorrowForm() {
  const [amount, setAmount] = useState('')
  const [consentGiven, setConsentGiven] = useState(false)
  const [showConsentModal, setShowConsentModal] = useState(false)
  const { borrow, isPending, isConfirming, isSuccess, hash, error } = useBorrow()
  const { availableLiquidity } = usePoolStatus()

  // Calculate required collateral (150%)
  const requiredCollateral = amount ? (Number(amount) * (COLLATERAL_RATIO / 100)).toFixed(4) : '0'

  const handleBorrow = async () => {
    if (!consentGiven) {
      setShowConsentModal(true)
      return
    }

    if (!amount || Number(amount) <= 0) return

    try {
      await borrow(amount, requiredCollateral)
    } catch (err) {
      console.error('Borrow failed:', err)
    }
  }

  const handleConsentAndBorrow = async () => {
    setConsentGiven(true)
    setShowConsentModal(false)
    // Borrow will be called automatically
    if (amount && Number(amount) > 0) {
      try {
        await borrow(amount, requiredCollateral)
      } catch (err) {
        console.error('Borrow failed:', err)
      }
    }
  }

  useEffect(() => {
    if (isSuccess) {
      setAmount('')
    }
  }, [isSuccess])

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Apply for Loan</CardTitle>
          <CardDescription>
            Borrow ETH with {COLLATERAL_RATIO}% collateral at 5% APY
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="warning">
            <AlertTitle>LGPD Article 7 - Consent Required</AlertTitle>
            <AlertDescription>
              You must provide explicit consent before borrowing. This is enforced at the smart contract level.
            </AlertDescription>
          </Alert>

          {availableLiquidity > 0n && (
            <div className="text-sm text-muted-foreground">
              Available to borrow: {formatETH(availableLiquidity)} ETH
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">Loan Amount (ETH)</label>
            <Input
              type="number"
              placeholder="Amount to borrow"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              step="0.01"
              min="0"
            />
          </div>

          <div className="p-4 bg-muted rounded-lg space-y-2">
            <div className="flex justify-between text-sm">
              <span>Loan Amount:</span>
              <span className="font-medium">{amount || '0'} ETH</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Required Collateral ({COLLATERAL_RATIO}%):</span>
              <span className="font-medium">{requiredCollateral} ETH</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Interest Rate:</span>
              <span className="font-medium">5% APY</span>
            </div>
          </div>

          <Button
            onClick={handleBorrow}
            disabled={isPending || isConfirming || !amount || Number(amount) <= 0}
            className="w-full"
          >
            {!consentGiven
              ? 'Review LGPD Consent'
              : isPending
              ? 'Confirming...'
              : isConfirming
              ? 'Processing...'
              : 'Borrow'}
          </Button>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                {error.message || 'Failed to apply for loan. Please try again.'}
              </AlertDescription>
            </Alert>
          )}

          {isSuccess && hash && (
            <Alert>
              <AlertDescription>
                Loan approved! Transaction: {hash.slice(0, 10)}...{hash.slice(-8)}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <LGPDConsentModal
        open={showConsentModal}
        onClose={() => setShowConsentModal(false)}
        onConsent={handleConsentAndBorrow}
      />
    </>
  )
}
