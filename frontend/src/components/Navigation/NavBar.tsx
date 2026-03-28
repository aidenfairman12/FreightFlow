'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Truck, ArrowLeft } from 'lucide-react'

const APP_NAV = [
  { href: '/freightflow',    label: 'Risk Overview' },
  { href: '/critical-nodes', label: 'Critical Nodes' },
  { href: '/explorer',       label: 'Explorer' },
]

export default function NavBar() {
  const pathname = usePathname()

  return (
    <nav className="flex h-12 shrink-0 items-center gap-1 border-b border-border bg-background px-4">
      {/* Back to portfolio */}
      <Link
        href="/"
        className="mr-3 flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-card/50 hover:text-foreground no-underline"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Portfolio
      </Link>

      <span className="mr-3 h-4 w-px bg-border" />

      {/* FreightFlow brand */}
      <Link
        href="/freightflow"
        className="mr-4 flex items-center gap-2 text-sm font-bold tracking-tight text-primary no-underline"
      >
        <Truck className="h-4 w-4" />
        FreightFlow
      </Link>

      {/* App page links */}
      {APP_NAV.map(item => {
        const active = pathname === item.href || pathname.startsWith(item.href + '/')
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm no-underline transition-colors',
              active
                ? 'bg-card font-semibold text-foreground'
                : 'text-muted-foreground hover:bg-card/50 hover:text-foreground'
            )}
          >
            {item.label}
          </Link>
        )
      })}
    </nav>
  )
}
