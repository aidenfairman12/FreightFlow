'use client'

import { useState, useEffect } from 'react'
import { Monitor } from 'lucide-react'

export default function MobileWarning() {
  const [isMobile, setIsMobile] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  if (!isMobile || dismissed) return null

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-6 bg-background px-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
        <Monitor className="h-8 w-8 text-sky-400" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-white">Best on Desktop</h2>
        <p className="mt-2 max-w-xs text-sm leading-relaxed text-white/50">
          FreightFlow uses interactive maps and data panels that require a larger screen to use comfortably.
        </p>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="rounded-lg border border-white/10 bg-white/5 px-5 py-2 text-sm text-white/60 transition-colors hover:bg-white/10 hover:text-white/80"
      >
        Continue anyway
      </button>
    </div>
  )
}
