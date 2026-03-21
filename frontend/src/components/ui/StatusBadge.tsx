interface StatusBadgeProps {
  label: string
  color: string
}

export function StatusBadge({ label, color }: StatusBadgeProps) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 9999,
      fontSize: 11,
      fontWeight: 600,
      color: color,
      background: `${color}20`,
      textTransform: 'capitalize',
    }}>
      {label}
    </span>
  )
}
