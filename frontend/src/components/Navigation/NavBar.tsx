'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

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
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      padding: '0 16px',
      height: 48,
      background: '#0f172a',
      borderBottom: '1px solid #1e293b',
      flexShrink: 0,
    }}>
      <Link href="/dashboard" style={{
        fontWeight: 700,
        fontSize: 15,
        color: '#38bdf8',
        textDecoration: 'none',
        marginRight: 20,
        letterSpacing: '-0.02em',
      }}>
        PlaneLogistics
      </Link>
      {NAV_ITEMS.map(item => {
        const active = pathname === item.href
        return (
          <Link
            key={item.href}
            href={item.href}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 13,
              fontWeight: active ? 600 : 400,
              color: active ? '#f1f5f9' : '#94a3b8',
              background: active ? '#1e293b' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.15s',
            }}
          >
            {item.label}
          </Link>
        )
      })}
    </nav>
  )
}
