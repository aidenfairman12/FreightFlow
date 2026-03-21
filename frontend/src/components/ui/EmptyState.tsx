import { colors } from '@/styles/theme'

interface EmptyStateProps {
  message: string
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 32,
      color: colors.textDim,
      fontSize: 13,
    }}>
      {message}
    </div>
  )
}
