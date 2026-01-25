import { LoanList } from '@/components/loans/LoanList'
import { NetworkGuard } from '@/components/web3/NetworkGuard'
import { WalletRequired } from '@/components/web3/WalletRequired'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Plus } from 'lucide-react'

export default function MyLoansPage() {
  return (
    <NetworkGuard>
      <WalletRequired>
        <div className="container mx-auto px-4 py-12">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-bold mb-2">My Loans</h1>
              <p className="text-muted-foreground">
                Manage your active loans and monitor health factors
              </p>
            </div>
            <Link href="/borrow">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Loan
              </Button>
            </Link>
          </div>

          <LoanList />
        </div>
      </WalletRequired>
    </NetworkGuard>
  )
}
