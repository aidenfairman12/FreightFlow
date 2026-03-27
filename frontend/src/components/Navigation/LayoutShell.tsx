'use client'

import NavBar from './NavBar'
import MobileWarning from '@/components/MobileWarning'

export default function LayoutShell({ children }: { children: React.ReactNode }) {
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
