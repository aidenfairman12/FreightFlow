'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Plane } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Live Map' },
  { href: '/analytics', label: 'KPIs' },
  { href: '/economics', label: 'Economics' },
  { href: '/predictions', label: 'ML & Predictions' },
  { href: '/scenarios', label: 'Scenarios' },
  { href: '/schedule', label: 'Schedule' },
]

export default function NavBar() {
  const pathname = usePathname()

  return (
    <nav className="flex h-12 shrink-0 items-center gap-1 border-b border-border bg-background px-4">
      <Link
        href="/dashboard"
        className="mr-5 flex items-center gap-2 text-sm font-bold tracking-tight text-primary no-underline"
      >
        <Plane className="h-4 w-4" />
        PlaneLogistics
      </Link>
      {NAV_ITEMS.map(item => {
        const active = pathname === item.href
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
