'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDate, formatAddress, formatETH } from '@/lib/utils/formatters'
import { FileText, ExternalLink } from 'lucide-react'

// Mock audit trail data - in production, this would fetch from IPFS/Arweave
const mockAuditLogs = [
  {
    id: '1',
    timestamp: Date.now() / 1000 - 3600,
    event: 'LoanRequested',
    borrower: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
    amount: '1000000000000000000',
    ipfsHash: 'QmX7M9CiYXjVeFnrDbUXRmE6rKz4RPkpGUfLR4vWzJcvXH',
    arweaveId: 'abc123def456',
  },
  {
    id: '2',
    timestamp: Date.now() / 1000 - 7200,
    event: 'Deposited',
    lender: '0x123d35Cc6634C0532925a3b844Bc9e7595f0bEb',
    amount: '5000000000000000000',
    ipfsHash: 'QmY8N0CjZYkWgFoRdcVYsKd5RPkqHVgMR5wXaKdwXyG',
    arweaveId: 'xyz789ghi012',
  },
]

export function AuditTrail() {
  const [searchTerm, setSearchTerm] = useState('')

  const filteredLogs = mockAuditLogs.filter(
    (log) =>
      log.event.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.borrower?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.lender?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Audit Trail Viewer
        </CardTitle>
        <CardDescription>
          Immutable logs stored on IPFS and Arweave
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Search by event, address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Button variant="outline">
            <FileText className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>

        <div className="space-y-3">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No audit logs found
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div
                key={log.id}
                className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge>{log.event}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(Number(log.timestamp))}
                      </span>
                    </div>
                    {log.borrower && (
                      <p className="text-sm">
                        Borrower: <code className="text-xs">{formatAddress(log.borrower)}</code>
                      </p>
                    )}
                    {log.lender && (
                      <p className="text-sm">
                        Lender: <code className="text-xs">{formatAddress(log.lender)}</code>
                      </p>
                    )}
                    <p className="text-sm">
                      Amount: <strong>{formatETH(BigInt(log.amount))} ETH</strong>
                    </p>
                  </div>
                </div>

                <div className="flex gap-2 mt-3">
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() =>
                      window.open(`https://ipfs.io/ipfs/${log.ipfsHash}`, '_blank')
                    }
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    IPFS
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() =>
                      window.open(`https://arweave.net/${log.arweaveId}`, '_blank')
                    }
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Arweave
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="mt-4 p-3 bg-muted rounded-lg text-sm">
          <p className="font-medium mb-1">📌 Immutable Storage</p>
          <p className="text-xs text-muted-foreground">
            All audit logs are stored on both IPFS (InterPlanetary File System) and Arweave
            for permanent, tamper-proof record keeping.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
