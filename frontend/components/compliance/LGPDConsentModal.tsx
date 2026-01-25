'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { useState } from 'react'

interface LGPDConsentModalProps {
  open: boolean
  onClose: () => void
  onConsent: () => void
}

export function LGPDConsentModal({ open, onClose, onConsent }: LGPDConsentModalProps) {
  const [understood, setUnderstood] = useState(false)

  const handleConsent = () => {
    if (understood) {
      onConsent()
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">🔐 LGPD Article 7 - Consent Required</DialogTitle>
          <DialogDescription>
            Smart contract compliance enforcement
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
            <h3 className="font-bold mb-2">Why is this required?</h3>
            <p className="text-sm">
              NEXUS BASTION-SC implements 4-layer compliance enforcement.
              Layer 3 (Smart Contract) requires your explicit consent before
              processing personal financial data according to Brazilian LGPD (General Data Protection Law).
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="font-semibold text-lg">Article 7 - Consent Conditions:</h4>
            <ul className="list-disc list-inside text-sm space-y-2 pl-2">
              <li>Your loan data will be stored on-chain (public blockchain)</li>
              <li>Audit logs will be stored on IPFS and Arweave (immutable storage)</li>
              <li>Your wallet address will be associated with loan history</li>
              <li>This consent is recorded on-chain and cannot be revoked</li>
              <li>Loan details (principal, collateral, interest) are publicly visible</li>
              <li>Transaction history will be permanently available on Sepolia testnet</li>
            </ul>
          </div>

          <div className="bg-yellow-50 dark:bg-yellow-950 p-4 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <p className="text-sm font-medium flex items-start gap-2">
              <span className="text-xl">⚠️</span>
              <span>
                The smart contract will <strong>REVERT</strong> your transaction if consent is not granted.
                This is enforced at the blockchain level to ensure compliance.
              </span>
            </p>
          </div>

          <div className="bg-muted p-4 rounded-lg">
            <h4 className="font-semibold mb-2">4-Layer Compliance Stack:</h4>
            <ol className="text-sm space-y-1 list-decimal list-inside">
              <li><strong>SENTINEL</strong>: Application-level Python validation</li>
              <li><strong>BASTION</strong>: Kernel-level seccomp-BPF syscall filtering</li>
              <li><strong>BASTION-SC</strong>: Smart contract LGPD enforcement (this layer)</li>
              <li><strong>Audit Trail</strong>: Immutable logs on IPFS + Arweave</li>
            </ol>
          </div>

          <div className="flex items-start space-x-3 p-3 border rounded-lg">
            <Checkbox
              id="consent"
              checked={understood}
              onCheckedChange={(checked) => setUnderstood(checked as boolean)}
            />
            <label htmlFor="consent" className="text-sm leading-relaxed cursor-pointer">
              I understand and <strong>explicitly consent</strong> to the processing of my financial data
              according to LGPD Article 7. I acknowledge that this consent will be recorded on-chain
              and that my loan data will be publicly visible on the blockchain.
            </label>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleConsent}
            disabled={!understood}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Grant Consent & Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
