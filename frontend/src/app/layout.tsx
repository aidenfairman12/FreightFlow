import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { cn } from '@/lib/utils'
import LayoutShell from '@/components/Navigation/LayoutShell'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' })

export const metadata: Metadata = {
  title: 'FreightFlow',
  description: 'US Freight Logistics Intelligence Platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn('dark font-sans', inter.variable)}>
      <body>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  )
}
