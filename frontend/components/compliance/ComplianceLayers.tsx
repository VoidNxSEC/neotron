'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Shield, Lock, FileCheck, Database } from 'lucide-react'

export function ComplianceLayers() {
  const layers = [
    {
      name: 'Layer 1: SENTINEL',
      description: 'Application-level Python validation and data protection',
      status: 'active',
      location: 'Python backend service',
      icon: Shield,
      color: 'text-blue-600',
    },
    {
      name: 'Layer 2: BASTION',
      description: 'Kernel-level seccomp-BPF syscall filtering for process isolation',
      status: 'active',
      location: 'NixOS kernel module',
      icon: Lock,
      color: 'text-purple-600',
    },
    {
      name: 'Layer 3: BASTION-SC',
      description: 'Smart contract LGPD Article 7 enforcement',
      status: 'active',
      location: 'Ethereum Sepolia 0x35fF603BD286E287f932356316271D59a4ADa779',
      icon: FileCheck,
      color: 'text-green-600',
    },
    {
      name: 'Layer 4: Audit Trail',
      description: 'Immutable audit logs stored on distributed networks',
      status: 'active',
      location: 'IPFS + Arweave distributed storage',
      icon: Database,
      color: 'text-orange-600',
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl flex items-center gap-2">
          <Shield className="h-6 w-6" />
          4-Layer Compliance Stack
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {layers.map((layer, i) => {
          const Icon = layer.icon
          return (
            <div
              key={i}
              className="flex items-start gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className={`p-2 rounded-full bg-muted ${layer.color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{layer.name}</h3>
                  <Badge variant={layer.status === 'active' ? 'default' : 'secondary'}>
                    {layer.status === 'active' ? '✓ Active' : 'Inactive'}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-1">{layer.description}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Database className="h-3 w-3" />
                  {layer.location}
                </p>
              </div>
            </div>
          )
        })}

        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
          <h4 className="font-semibold mb-2 flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Compliance Guarantees
          </h4>
          <ul className="text-sm space-y-1 list-disc list-inside">
            <li>LGPD Article 7 consent enforcement at smart contract level</li>
            <li>All transactions validated through 4 independent layers</li>
            <li>Immutable audit trail for regulatory compliance</li>
            <li>Kernel-level protection against unauthorized data access</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
