'use client'

import { useAccount, useChainId, useSwitchChain } from 'wagmi'
import { sepolia } from 'wagmi/chains'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'

interface NetworkGuardProps {
  children: React.ReactNode
}

export function NetworkGuard({ children }: NetworkGuardProps) {
  const chainId = useChainId()
  const { switchChain } = useSwitchChain()
  const { isConnected } = useAccount()

  if (!isConnected) {
    return <>{children}</>
  }

  if (chainId !== sepolia.id) {
    return (
      <div className="container mx-auto px-4 py-12">
        <Alert variant="destructive" className="max-w-2xl mx-auto">
          <AlertTriangle className="h-5 w-5" />
          <AlertTitle>Wrong Network</AlertTitle>
          <AlertDescription className="mt-2">
            <p className="mb-4">
              You are connected to the wrong network. NEXUS BASTION-SC is deployed on Sepolia Testnet.
            </p>
            <div className="space-y-2">
              <p className="text-sm">
                <strong>Current Network:</strong> {chainId}
              </p>
              <p className="text-sm">
                <strong>Required Network:</strong> Sepolia Testnet (Chain ID: {sepolia.id})
              </p>
            </div>
            <Button
              onClick={() => switchChain?.({ chainId: sepolia.id })}
              className="mt-4"
            >
              Switch to Sepolia
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return <>{children}</>
}
