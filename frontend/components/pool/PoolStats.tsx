'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePoolStatus } from '@/lib/hooks/usePoolStatus'
import { formatETH, formatPercentage } from '@/lib/utils/formatters'

export function PoolStats() {
  const { totalDeposits, totalBorrowed, availableLiquidity, utilizationRate, isLoading } = usePoolStatus()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-muted rounded w-24"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-32"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const stats = [
    {
      title: 'Total Deposits',
      value: `${formatETH(totalDeposits)} ETH`,
      description: 'Total liquidity in pool',
    },
    {
      title: 'Total Borrowed',
      value: `${formatETH(totalBorrowed)} ETH`,
      description: 'Currently borrowed',
    },
    {
      title: 'Available',
      value: `${formatETH(availableLiquidity)} ETH`,
      description: 'Available to borrow',
    },
    {
      title: 'Utilization',
      value: formatPercentage(utilizationRate),
      description: 'Pool utilization rate',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, index) => (
        <Card key={index}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {stat.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stat.value}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stat.description}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
