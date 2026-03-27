'use client'

import NavBar from './NavBar'

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col">
      <NavBar />
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}
