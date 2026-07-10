import { ComplianceLayers } from '@/components/compliance/ComplianceLayers'
import { AuditTrail } from '@/components/compliance/AuditTrail'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Shield, CheckCircle } from 'lucide-react'

export default function CompliancePage() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="h-10 w-10 text-blue-600" />
          <div>
            <h1 className="text-4xl font-bold">Compliance & Audit Trail</h1>
            <p className="text-muted-foreground">
              Transparent, immutable, and LGPD-compliant
            </p>
          </div>
        </div>
      </div>

      {/* Compliance Status */}
      <div className="mb-8">
        <Card className="bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
          <CardContent className="py-6">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div>
                <h3 className="font-bold text-lg">All Systems Operational</h3>
                <p className="text-sm text-muted-foreground">
                  4 compliance layers active and enforcing LGPD regulations
                </p>
              </div>
              <div className="ml-auto">
                <Badge className="bg-green-600">100% Compliant</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Compliance Layers */}
        <div>
          <ComplianceLayers />
        </div>

        {/* Additional Info */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>LGPD Article 7 Enforcement</CardTitle>
              <CardDescription>
                Brazilian General Data Protection Law compliance
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">What is LGPD Article 7?</h4>
                <p className="text-sm text-muted-foreground">
                  Article 7 of Brazil's LGPD requires explicit consent before processing
                  personal data. Our smart contract enforces this by requiring users to
                  provide consent before borrowing.
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Smart Contract Enforcement</h4>
                <p className="text-sm text-muted-foreground">
                  Unlike traditional applications where consent can be bypassed,
                  BASTION-SC enforces consent at the blockchain level. Transactions
                  will revert if consent is not granted.
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Immutable Records</h4>
                <p className="text-sm text-muted-foreground">
                  All consent records and transactions are stored on IPFS and Arweave,
                  creating a permanent audit trail for compliance verification.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Why This Matters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>
                <strong>Regulatory Compliance:</strong> Financial institutions must
                comply with data protection laws like LGPD, GDPR, and CCPA.
              </p>
              <p>
                <strong>User Trust:</strong> Transparent consent mechanisms build
                trust and protect user rights.
              </p>
              <p>
                <strong>Innovation:</strong> NEXUS BASTION-SC demonstrates how
                blockchain can enforce regulatory compliance automatically.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Audit Trail */}
      <div>
        <AuditTrail />
      </div>
    </div>
  )
}
