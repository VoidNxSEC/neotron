import { PoolStats } from '@/components/pool/PoolStats'
import { ComplianceLayers } from '@/components/compliance/ComplianceLayers'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { Shield, TrendingUp, Lock, Database } from 'lucide-react'

export default function Home() {
  return (
    <main className="container mx-auto px-4 py-12">
      {/* Hero Section */}
      <section className="text-center mb-16">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            NEXUS BASTION-SC
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-8">
            First DeFi Protocol with Kernel-Level Compliance Enforcement
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/lend">
              <Button size="lg" className="text-lg px-8">
                <TrendingUp className="mr-2 h-5 w-5" />
                Start Lending
              </Button>
            </Link>
            <Link href="/borrow">
              <Button size="lg" variant="outline" className="text-lg px-8">
                Borrow ETH
              </Button>
            </Link>
            <Link href="/compliance">
              <Button size="lg" variant="outline" className="text-lg px-8">
                <Shield className="mr-2 h-5 w-5" />
                View Compliance
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold text-center mb-8">Why NEXUS BASTION-SC?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <Shield className="h-10 w-10 text-blue-600 mb-2" />
              <CardTitle>4-Layer Compliance</CardTitle>
              <CardDescription>
                From Python validation to kernel-level protection and smart contract enforcement
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <Lock className="h-10 w-10 text-purple-600 mb-2" />
              <CardTitle>LGPD Article 7</CardTitle>
              <CardDescription>
                Smart contract enforces Brazilian data protection law with explicit consent
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <Database className="h-10 w-10 text-green-600 mb-2" />
              <CardTitle>Immutable Audit Trail</CardTitle>
              <CardDescription>
                All transactions logged on IPFS and Arweave for permanent compliance records
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Pool Stats */}
      <section className="mb-16">
        <h2 className="text-3xl font-bold mb-6">Pool Status</h2>
        <PoolStats />
      </section>

      {/* Compliance Showcase */}
      <section className="mb-16">
        <ComplianceLayers />
      </section>

      {/* Contract Info */}
      <section className="mb-8">
        <Card className="bg-muted">
          <CardContent className="py-6">
            <div className="text-center space-y-2">
              <p className="text-sm text-muted-foreground">Deployed on Sepolia Testnet</p>
              <code className="text-xs bg-background px-3 py-1 rounded border">
                0x35fF603BD286E287f932356316271D59a4ADa779
              </code>
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  )
}
