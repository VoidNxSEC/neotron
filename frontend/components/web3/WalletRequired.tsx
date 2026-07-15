'use client'

import { useAccount } from 'wagmi'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Wallet } from 'lucide-react'

interface WalletRequiredProps {
  children: React.ReactNode
}

export function WalletRequired({ children }: WalletRequiredProps) {
  const { isConnected } = useAccount()

  if (!isConnected) {
    return (
      <div className="container mx-auto px-4 py-12">
        <Card className="max-w-lg mx-auto">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="p-4 rounded-full bg-primary/10">
                <Wallet className="h-12 w-12 text-primary" />
              </div>
            </div>
            <CardTitle className="text-2xl">Wallet Required</CardTitle>
            <CardDescription>
              Please connect your wallet to access this page, or if you don't have one, you can create one using the button below.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ConnectButton />
          </CardContent>
        </Card>
      </div>
    )
  }

  return <>{children}</>
}
