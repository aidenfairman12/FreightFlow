import type { Metadata } from 'next'
import NavBar from '@/components/Navigation/NavBar'

export const metadata: Metadata = {
  title: 'PlaneLogistics',
  description: 'Swiss Airspace Real-Time Logistics Analytics',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, sans-serif', background: '#0f172a', color: '#f1f5f9' }}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
          <NavBar />
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {children}
          </div>
        </div>
      </body>
    </html>
  )
}
