'use client'

import { useAccount, useChainId, useSwitchChain } from 'wagmi'
import { sepolia, avalanche, polygon, bsc } from 'wagmi/chains'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertTriangle, ShieldCheck, Cpu } from 'lucide-react'

interface NetworkGuardProps {
  children: React.ReactNode
}

export function NetworkGuard({ children }: NetworkGuardProps) {
  const chainId = useChainId()
  const { switchChain, chains } = useSwitchChain()
  const { isConnected } = useAccount()

  // Supported chain IDs
  const supportedChainIds = [sepolia.id, avalanche.id, polygon.id, bsc.id]

  if (!isConnected) {
    return <>{children}</>
  }

  const isSupported = (supportedChainIds as number[]).includes(chainId)

  if (!isSupported) {
    return (
      <div className="container mx-auto px-4 py-12">
        <Alert variant="destructive" className="max-w-2xl mx-auto bg-red-950/20 border-red-900/50 text-red-400 p-6 rounded-xl shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex gap-3">
            <AlertTriangle className="h-6 w-6 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <AlertTitle className="text-lg font-bold text-zinc-100 flex items-center gap-2">
                Unsupported Network (Chain ID: {chainId})
              </AlertTitle>
              <AlertDescription className="mt-2 text-zinc-400 space-y-4">
                <p className="text-sm">
                  NEXUS BASTION-SC is ready for multi-chain defense, but your wallet is currently connected to a network we do not support for this cluster session.
                </p>
                <div className="space-y-2 p-3 bg-zinc-950/40 rounded-lg border border-zinc-800/60 text-xs">
                  <p className="text-zinc-500">
                    <strong>Supported Multi-Chain EVM Clusters:</strong>
                  </p>
                  <ul className="list-disc pl-4 space-y-1 text-zinc-300">
                    <li>Sepolia Testnet (Chain ID: {sepolia.id})</li>
                    <li>Avalanche C-Chain (Chain ID: {avalanche.id})</li>
                    <li>Polygon Mainnet (Chain ID: {polygon.id})</li>
                    <li>BNB Smart Chain (Chain ID: {bsc.id})</li>
                  </ul>
                </div>
                <div className="flex flex-wrap gap-2 pt-2">
                  <Button
                    onClick={() => switchChain?.({ chainId: sepolia.id })}
                    className="bg-amber-600 hover:bg-amber-500 text-zinc-950 font-bold"
                  >
                    Switch to Sepolia
                  </Button>
                  <Button
                    onClick={() => switchChain?.({ chainId: polygon.id })}
                    variant="outline"
                    className="border-zinc-800 hover:bg-zinc-800 text-zinc-200"
                  >
                    Switch to Polygon
                  </Button>
                  <Button
                    onClick={() => switchChain?.({ chainId: avalanche.id })}
                    variant="outline"
                    className="border-zinc-800 hover:bg-zinc-800 text-zinc-200"
                  >
                    Switch to Avalanche
                  </Button>
                </div>
              </AlertDescription>
            </div>
          </div>
        </Alert>
      </div>
    )
  }

  return <>{children}</>
}
