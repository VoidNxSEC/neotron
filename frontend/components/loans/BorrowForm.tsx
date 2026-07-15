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
import { Shield, ShieldAlert, Cpu, Activity, Coins } from 'lucide-react'

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
      <Card className="bg-gradient-to-br from-zinc-950 to-zinc-900 border border-zinc-800 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />
        <CardHeader className="border-b border-zinc-800/50 pb-4">
          <CardTitle className="text-xl font-bold text-zinc-100 flex items-center gap-2">
            <Cpu className="h-5 w-5 text-amber-500" />
            Deploy Isolated Sandbox Container
          </CardTitle>
          <CardDescription className="text-zinc-400">
            Allocate sandboxed execution bandwidth with {COLLATERAL_RATIO}% security escrow.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-6">
          <Alert className="bg-amber-950/20 border-amber-900/50 text-amber-400">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle className="font-semibold text-zinc-200">LGPD Article 7 — Legal Compliance</AlertTitle>
            <AlertDescription className="text-xs text-zinc-400">
              On-chain cryptographically signed user consent is required before container spin-up.
            </AlertDescription>
          </Alert>

          {availableLiquidity > 0n && (
            <div className="text-xs text-zinc-400 bg-zinc-900/60 p-2.5 rounded-lg border border-zinc-800/60 flex justify-between items-center">
              <span className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5 text-emerald-500" /> Available System Compute Pool:</span>
              <span className="font-bold text-zinc-200">{formatETH(availableLiquidity)} ETH</span>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
              <Coins className="h-3.5 w-3.5 text-amber-500" /> Compute Resource Allocation (ETH)
            </label>
            <Input
              type="number"
              placeholder="Amount of resource budget to allocate"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              step="0.01"
              min="0"
              className="bg-zinc-950 border-zinc-800 text-zinc-100 focus:ring-amber-500 focus:border-amber-500"
            />
          </div>

          <div className="p-4 bg-zinc-950/50 border border-zinc-800 rounded-lg space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-zinc-500">Compute Budget Limit:</span>
              <span className="font-semibold text-zinc-300">{amount || '0'} ETH</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Required Security Escrow ({COLLATERAL_RATIO}%):</span>
              <span className="font-semibold text-zinc-300">{requiredCollateral} ETH</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Resource Overhead Accumulation:</span>
              <span className="font-semibold text-emerald-400">5% APY</span>
            </div>
          </div>

          <Button
            onClick={handleBorrow}
            disabled={isPending || isConfirming || !amount || Number(amount) <= 0}
            className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-zinc-950 font-extrabold shadow-lg hover:scale-[1.01] transition-all duration-300 py-6"
          >
            {!consentGiven
              ? 'Authorize LGPD Consent'
              : isPending
              ? 'Signing Transaction...'
              : isConfirming
              ? 'Spawning Sandbox...'
              : 'Deploy Sandbox Workload'}
          </Button>

          {error && (
            <Alert variant="destructive" className="bg-red-950/20 border-red-900/50 text-red-400">
              <AlertDescription className="text-xs">
                {error.message || 'Failed to deploy container. Please check Web3 provider.'}
              </AlertDescription>
            </Alert>
          )}

          {isSuccess && hash && (
            <Alert className="bg-emerald-950/20 border-emerald-900/50 text-emerald-400">
              <Shield className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Sandbox successfully deployed! Transaction: {hash.slice(0, 10)}...{hash.slice(-8)}
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
