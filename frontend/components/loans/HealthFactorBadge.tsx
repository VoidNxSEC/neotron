'use client'

import { Badge } from '@/components/ui/badge'
import { getHealthFactorColor, getHealthFactorLabel } from '@/lib/utils/calculations'

interface HealthFactorBadgeProps {
  healthFactor: number
}

export function HealthFactorBadge({ healthFactor }: HealthFactorBadgeProps) {
  const label = getHealthFactorLabel(healthFactor)
  const colorClass = getHealthFactorColor(healthFactor)

  const variant = healthFactor >= 130 ? 'default' : healthFactor >= 120 ? 'outline' : 'destructive'

  return (
    <Badge variant={variant} className={colorClass}>
      {label}: {healthFactor.toFixed(2)}%
    </Badge>
  )
}
