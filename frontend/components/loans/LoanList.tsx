'use client'

import { useUserLoans } from '@/lib/hooks/useUserLoans'
import { LoanCard } from './LoanCard'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function LoanList() {
  const { loanIds, isLoading, error } = useUserLoans()

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-64 bg-muted rounded-xl animate-pulse"></div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Failed to load loans: {error.message}
        </AlertDescription>
      </Alert>
    )
  }

  if (!loanIds || loanIds.length === 0) {
    return (
      <Alert>
        <AlertDescription>
          You don't have any active loans. Apply for a loan to get started.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Your Loans ({loanIds.length})</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {loanIds.map((loanId) => (
          <LoanCard key={loanId} loanId={loanId} />
        ))}
      </div>
    </div>
  )
}
