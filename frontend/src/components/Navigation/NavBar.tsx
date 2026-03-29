'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Truck } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/',               label: 'Risk Overview' },
  { href: '/explorer',       label: 'Explorer' },
  { href: '/critical-nodes', label: 'Critical Nodes' },
]

export default function NavBar() {
  const pathname = usePathname()

  return (
    <nav className="flex h-12 shrink-0 items-center gap-1 border-b border-border bg-background px-4">
      <Link
        href="/"
        className="mr-5 flex items-center gap-2 text-sm font-bold tracking-tight text-primary no-underline"
      >
        <Truck className="h-4 w-4" />
        FreightFlow
      </Link>
      {NAV_ITEMS.map(item => {
        const active = item.href === '/'
          ? pathname === '/'
          : pathname === item.href || pathname.startsWith(item.href + '/')
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
