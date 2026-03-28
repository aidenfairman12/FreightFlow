'use client'

import { usePathname } from 'next/navigation'
import NavBar from './NavBar'
import MobileWarning from '@/components/MobileWarning'

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // Portfolio root — let the page control its own layout and scrolling
  if (pathname === '/') {
    return (
      <>
        <MobileWarning />
        {children}
      </>
    )
  }

  // FreightFlow app pages — fixed-height shell with NavBar
  return (
    <div className="flex h-screen flex-col">
      <MobileWarning />
      <NavBar />
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}
