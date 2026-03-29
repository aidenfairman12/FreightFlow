import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { cn } from '@/lib/utils'
import LayoutShell from '@/components/Navigation/LayoutShell'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' })

export const metadata: Metadata = {
  title: 'FreightFlow',
  description: 'Interactive US supply chain risk intelligence — visualise freight flows, concentration risk, and systemic vulnerabilities across critical industries. Built on FAF5 data.',
  openGraph: {
    title: 'FreightFlow',
    description: 'Interactive US supply chain risk intelligence — visualise freight flows, concentration risk, and systemic vulnerabilities across critical industries.',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: 'FreightFlow',
    description: 'Interactive US supply chain risk intelligence built on FAF5 freight data.',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn('dark font-sans', inter.variable)}>
      <body>
        <LayoutShell>{children}</LayoutShell>
        <Analytics />
      </body>
    </html>
  )
}
