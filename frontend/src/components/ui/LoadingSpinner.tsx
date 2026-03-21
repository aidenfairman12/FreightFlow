import { colors } from '@/styles/theme'

interface LoadingSpinnerProps {
  message?: string
}

export function LoadingSpinner({ message = 'Loading…' }: LoadingSpinnerProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 40,
      gap: 12,
    }}>
      <div
        style={{
          width: 28,
          height: 28,
          border: `3px solid ${colors.border}`,
          borderTop: `3px solid ${colors.accent}`,
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <span style={{ color: colors.textMuted, fontSize: 13 }}>{message}</span>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
