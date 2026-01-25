'use client'

import { Progress } from '@/components/ui/progress'
import { usePoolStatus } from '@/lib/hooks/usePoolStatus'
import { formatPercentage } from '@/lib/utils/formatters'

export function UtilizationBar() {
  const { utilizationRate, isLoading } = usePoolStatus()

  if (isLoading) {
    return <div className="h-4 bg-muted rounded animate-pulse"></div>
  }

  const utilizationPercent = Number(utilizationRate) / 100

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Pool Utilization</span>
        <span className="font-medium">{formatPercentage(utilizationRate)}</span>
      </div>
      <Progress value={utilizationPercent} className="h-3" />
    </div>
  )
}
