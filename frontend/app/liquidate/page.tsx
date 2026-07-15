import { LiquidatableLoans } from '@/components/liquidation/LiquidatableLoans'
import { NetworkGuard } from '@/components/web3/NetworkGuard'
import { WalletRequired } from '@/components/web3/WalletRequired'
import { Card, CardContent } from '@/components/ui/card'
import { ShieldAlert, Cpu, Award, ShieldCheck } from 'lucide-react'

export default function LiquidatePage() {
  return (
    <NetworkGuard>
      <WalletRequired>
        <div className="container mx-auto px-4 py-12 max-w-6xl">
          <div className="space-y-2 mb-8">
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-red-500 via-orange-500 to-yellow-500 bg-clip-text text-transparent flex items-center gap-3">
              <ShieldAlert className="h-10 w-10 text-red-500 animate-pulse" />
              Threat Compliance Sandbox Dashboard
            </h1>
            <p className="text-muted-foreground text-lg">
              Monitor active sandboxed workloads, evaluate behavior safety, and halt compromised containers.
            </p>
          </div>

          <div className="mb-8">
            <Card className="bg-gradient-to-br from-slate-900 via-zinc-900 to-neutral-900 border border-zinc-800 shadow-xl overflow-hidden relative">
              <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl pointer-events-none" />
              <CardContent className="py-8 px-6">
                <h3 className="text-xl font-bold mb-6 text-zinc-100 flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-500" />
                  Autonomous Watchdog Interception Model
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="p-4 bg-zinc-950/50 rounded-xl border border-zinc-800/80 hover:border-zinc-700 transition duration-300">
                    <div className="flex items-center gap-2 mb-2">
                      <Cpu className="h-4 w-4 text-amber-500" />
                      <p className="font-semibold text-zinc-200">1. Monitor Behaviors</p>
                    </div>
                    <p className="text-xs text-zinc-400">
                      Layer 0 TemporalGuard and Layer 2 Landlock monitor processes in real-time.
                    </p>
                  </div>
                  <div className="p-4 bg-zinc-950/50 rounded-xl border border-zinc-800/80 hover:border-zinc-700 transition duration-300">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldAlert className="h-4 w-4 text-red-500" />
                      <p className="font-semibold text-zinc-200">2. Evaluate Safety</p>
                    </div>
                    <p className="text-xs text-zinc-400">
                      Workloads with a Behavior Safety Score below 120% are flagged as compromised.
                    </p>
                  </div>
                  <div className="p-4 bg-zinc-950/50 rounded-xl border border-zinc-800/80 hover:border-zinc-700 transition duration-300">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldAlert className="h-4 w-4 text-rose-500" />
                      <p className="font-semibold text-zinc-200">3. Trigger Intercept</p>
                    </div>
                    <p className="text-xs text-zinc-400">
                      Trigger containment to halt the compromised sandbox container via smart contracts.
                    </p>
                  </div>
                  <div className="p-4 bg-zinc-950/50 rounded-xl border border-zinc-800/80 hover:border-zinc-700 transition duration-300">
                    <div className="flex items-center gap-2 mb-2">
                      <Award className="h-4 w-4 text-yellow-500" />
                      <p className="font-semibold text-zinc-200">4. Claim Bounty</p>
                    </div>
                    <p className="text-xs text-zinc-400">
                      The compromised agent's security escrow is slashed, awarding the bounty to you.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <LiquidatableLoans />
        </div>
      </WalletRequired>
    </NetworkGuard>
  )
}

