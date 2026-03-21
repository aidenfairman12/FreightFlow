import { colors, buttonStyle } from '@/styles/theme'

interface ErrorBannerProps {
  message: string
  onRetry?: () => void
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '10px 14px',
      background: 'rgba(239, 68, 68, 0.1)',
      border: `1px solid ${colors.red}`,
      borderRadius: 8,
      color: colors.red,
      fontSize: 13,
    }}>
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <button onClick={onRetry} style={{ ...buttonStyle, fontSize: 12, padding: '4px 10px' }}>
          Retry
        </button>
      )}
    </div>
  )
}
