import { DepositForm } from '@/components/pool/DepositForm'
import { WithdrawForm } from '@/components/pool/WithdrawForm'
import { PoolStats } from '@/components/pool/PoolStats'
import { UtilizationBar } from '@/components/pool/UtilizationBar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { NetworkGuard } from '@/components/web3/NetworkGuard'
import { WalletRequired } from '@/components/web3/WalletRequired'
import { Card, CardContent } from '@/components/ui/card'

export default function LendPage() {
  return (
    <NetworkGuard>
      <WalletRequired>
        <div className="container mx-auto px-4 py-12">
          <h1 className="text-4xl font-bold mb-2">Lend ETH & Earn Interest</h1>
          <p className="text-muted-foreground mb-8">
            Deposit ETH to the lending pool and earn interest from borrowers
          </p>

          {/* Pool Stats */}
          <div className="mb-8">
            <PoolStats />
          </div>

          {/* Utilization */}
          <div className="mb-8">
            <Card>
              <CardContent className="pt-6">
                <UtilizationBar />
              </CardContent>
            </Card>
          </div>

          {/* Deposit/Withdraw Tabs */}
          <div className="max-w-2xl mx-auto">
            <Tabs defaultValue="deposit" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="deposit">Deposit</TabsTrigger>
                <TabsTrigger value="withdraw">Withdraw</TabsTrigger>
              </TabsList>

              <TabsContent value="deposit" className="mt-6">
                <DepositForm />
              </TabsContent>

              <TabsContent value="withdraw" className="mt-6">
                <WithdrawForm />
              </TabsContent>
            </Tabs>
          </div>

          {/* Info */}
          <div className="max-w-2xl mx-auto mt-8">
            <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <CardContent className="pt-6">
                <h3 className="font-semibold mb-2">How it works:</h3>
                <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
                  <li>Deposit ETH to the lending pool</li>
                  <li>Earn interest from borrowers (5% APY)</li>
                  <li>Withdraw anytime (subject to liquidity availability)</li>
                  <li>All transactions are secured by 4-layer compliance</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </WalletRequired>
    </NetworkGuard>
  )
}
