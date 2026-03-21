import { Badge } from '@/components/ui/badge'

interface StatusBadgeProps {
  label: string
  color: string
}

export function StatusBadge({ label, color }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className="text-xs font-semibold capitalize"
      style={{ color, borderColor: color, backgroundColor: `${color}20` }}
    >
      {label}
    </Badge>
  )
}
