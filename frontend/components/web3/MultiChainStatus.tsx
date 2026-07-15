'use client'

import { useState } from 'react'
import { useChainId, useSwitchChain, useAccount } from 'wagmi'
import { sepolia, avalanche, polygon, bsc } from 'wagmi/chains'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Shield, Activity, Zap, Cpu, Network, CheckCircle2 } from 'lucide-react'

export function MultiChainStatus() {
  const chainId = useChainId()
  const { switchChain } = useSwitchChain()
  const { isConnected } = useAccount()
  const [isOpen, setIsOpen] = useState(false)

  // System status of each supported cluster
  const networks = [
    {
      id: sepolia.id,
      name: 'Sepolia (Eth)',
      type: 'EVM',
      sentinelStatus: 'ACTIVE',
      watchdogs: 12,
      latency: '24ms',
      color: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
      action: () => switchChain?.({ chainId: sepolia.id })
    },
    {
      id: polygon.id,
      name: 'Polygon Mainnet',
      type: 'EVM',
      sentinelStatus: 'ACTIVE',
      watchdogs: 28,
      latency: '15ms',
      color: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
      action: () => switchChain?.({ chainId: polygon.id })
    },
    {
      id: avalanche.id,
      name: 'Avalanche C-Chain',
      type: 'EVM',
      sentinelStatus: 'ACTIVE',
      watchdogs: 24,
      latency: '11ms',
      color: 'text-red-500 bg-red-500/10 border-red-500/20',
      action: () => switchChain?.({ chainId: avalanche.id })
    },
    {
      id: bsc.id,
      name: 'BNB Smart Chain',
      type: 'EVM',
      sentinelStatus: 'ACTIVE',
      watchdogs: 42,
      latency: '18ms',
      color: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20',
      action: () => switchChain?.({ chainId: bsc.id })
    },
    {
      id: 99999, // Solana Custom identifier
      name: 'Solana Mainnet',
      type: 'Non-EVM',
      sentinelStatus: 'SVM MONITOR',
      watchdogs: 89,
      latency: '4ms',
      color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
      action: () => alert('Solana SVM compliance sentinel is active in simulation mode. Wallet integration uses Solana Wallet Adapter.')
    }
  ]

  const activeNetwork = networks.find(n => n.id === chainId) || (isConnected ? {
    id: chainId,
    name: `Unknown Chain (${chainId})`,
    type: 'EVM',
    sentinelStatus: 'UNPROTECTED',
    watchdogs: 0,
    latency: 'N/A',
    color: 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20',
    action: () => {}
  } : {
    id: 0,
    name: 'Disconnected',
    type: 'N/A',
    sentinelStatus: 'STANDBY',
    watchdogs: 195,
    latency: '0ms',
    color: 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20',
    action: () => {}
  })

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-800/80 bg-zinc-950/60 hover:bg-zinc-900/60 transition duration-300 text-xs font-semibold text-zinc-300"
      >
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
            activeNetwork.sentinelStatus === 'ACTIVE' || activeNetwork.sentinelStatus === 'SVM MONITOR' ? 'bg-emerald-400' : 'bg-amber-400'
          }`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${
            activeNetwork.sentinelStatus === 'ACTIVE' || activeNetwork.sentinelStatus === 'SVM MONITOR' ? 'bg-emerald-500' : 'bg-amber-500'
          }`} />
        </span>
        <Network className="h-3.5 w-3.5 text-zinc-400" />
        <span>Cluster: {activeNetwork.name}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2.5 w-80 rounded-xl border border-zinc-800 bg-zinc-950 p-4 shadow-2xl z-50 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800/60 pb-2">
            <h4 className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-emerald-500" />
              Multi-Chain Guard Status
            </h4>
            <Badge variant="outline" className="text-[10px] bg-emerald-950/20 text-emerald-400 border-emerald-900/40">
              {networks.reduce((acc, curr) => acc + curr.watchdogs, 0)} Active Watchdogs
            </Badge>
          </div>

          <div className="space-y-2">
            {networks.map((net) => {
              const isCurrent = net.id === chainId || (net.id === 99999 && !isConnected && false)
              return (
                <div
                  key={net.name}
                  className={`p-2.5 rounded-lg border text-xs transition duration-200 ${
                    isCurrent ? 'bg-zinc-900/50 border-zinc-700/60' : 'bg-zinc-950 border-zinc-900 hover:border-zinc-800'
                  }`}
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="font-semibold text-zinc-200 flex items-center gap-1.5">
                      <Cpu className="h-3.5 w-3.5 text-zinc-400" />
                      {net.name}
                    </span>
                    <Badge className={`text-[9px] font-bold ${net.color} border py-0 px-1`}>
                      {net.sentinelStatus}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-[10px] text-zinc-500 mb-2">
                    <span>Latency: {net.latency} | eBPF Watchdogs: {net.watchdogs}</span>
                    <span>{net.type}</span>
                  </div>
                  {!isCurrent && (
                    <Button
                      onClick={() => {
                        net.action()
                        setIsOpen(false)
                      }}
                      className="w-full text-[10px] font-extrabold h-7 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                    >
                      {net.id === 99999 ? 'Inspect Solana Monitor' : `Switch to ${net.name}`}
                    </Button>
                  )}
                  {isCurrent && (
                    <div className="text-[10px] font-semibold text-emerald-400 flex items-center gap-1 bg-emerald-950/20 p-1.5 rounded border border-emerald-900/30">
                      <CheckCircle2 className="h-3 w-3" />
                      Wallet Connected & Guardrails Engaged
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
