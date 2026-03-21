import { colors } from '@/styles/theme'
import { EmptyState } from './EmptyState'

interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
  align?: 'left' | 'center' | 'right'
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  emptyMessage?: string
  maxRows?: number
  onRowClick?: (row: T) => void
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  emptyMessage = 'No data available',
  maxRows,
  onRowClick,
}: DataTableProps<T>) {
  const rows = maxRows ? data.slice(0, maxRows) : data

  if (rows.length === 0) {
    return <EmptyState message={emptyMessage} />
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                style={{
                  textAlign: col.align ?? 'left',
                  padding: '8px 10px',
                  color: colors.textMuted,
                  fontSize: 11,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  borderBottom: `1px solid ${colors.border}`,
                  whiteSpace: 'nowrap',
                }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              onClick={() => onRowClick?.(row)}
              style={{
                cursor: onRowClick ? 'pointer' : undefined,
                borderBottom: `1px solid ${colors.border}`,
              }}
            >
              {columns.map(col => (
                <td
                  key={col.key}
                  style={{
                    padding: '8px 10px',
                    color: colors.text,
                    textAlign: col.align ?? 'left',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {col.render
                    ? col.render(row)
                    : String(row[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
