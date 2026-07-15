import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Providers } from "@/lib/contracts/providers"
import { ConnectButton } from "@rainbow-me/rainbowkit"
import { MultiChainStatus } from "@/components/web3/MultiChainStatus"
import Link from "next/link"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "NEXUS BASTION-SC - DeFi with Kernel-Level Compliance",
  description: "First DeFi lending protocol with 4-layer compliance enforcement: SENTINEL, BASTION, BASTION-SC, and immutable audit trails",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-background">
            {/* Navigation */}
            <nav className="border-b">
              <div className="container mx-auto px-4 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-8">
                    <Link href="/" className="text-2xl font-bold">
                      NEXUS BASTION-SC
                    </Link>
                    <div className="hidden md:flex space-x-6">
                      <Link href="/assistant" className="hover:text-primary font-medium text-blue-500">
                        AI Assistant
                      </Link>
                      <Link href="/lend" className="hover:text-primary">
                        Lend
                      </Link>
                      <Link href="/borrow" className="hover:text-primary">
                        Borrow
                      </Link>
                      <Link href="/loans" className="hover:text-primary">
                        My Loans
                      </Link>
                      <Link href="/liquidate" className="hover:text-primary">
                        Liquidate
                      </Link>
                      <Link href="/compliance" className="hover:text-primary">
                        Compliance
                      </Link>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <MultiChainStatus />
                    <ConnectButton />
                  </div>
                </div>
              </div>
            </nav>

            {/* Main Content */}
            <main>{children}</main>

            {/* Footer */}
            <footer className="border-t mt-16">
              <div className="container mx-auto px-4 py-8">
                <div className="text-center text-sm text-muted-foreground">
                  <p>🛡️ Powered by 4-layer compliance: SENTINEL → BASTION → BASTION-SC → Audit Trail</p>
                  <p className="mt-2">Contract: 0x35fF603BD286E287f932356316271D59a4ADa779 (Sepolia)</p>
                </div>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  )
}
